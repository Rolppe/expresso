# RELAYS OFF FIRST (devsafe, 17.9.2026): before any other import or initialization
import devsafe
devsafe.relays_off()

# IMPORT LIBRARIES
import utime
import json
import sys
import socket
import network
import select
import bluetooth
import time
import adafruit_max31865  as max31865
import asyncio

# IMPORT FUNCTIONS, CLASSES AND CONFIGURATIONS
from machine            import Pin, ADC
from micropython        import const
from functions          import save_settings, load_settings, print_values, fast_heatup, pre_infusion, pressure_calibration_run, pressure_zero_run, pressure_capture_run, pressure_sweep_run, pressure_hold_run, run_shot, hot_water_run
from commands           import handle_command
from classes            import BrewData, HeatingSpeedCalculator, Thermostat, TemperatureSensor, PressureSensor, PumpRatioCalculator, PumpPressureController
from bluetooth_handler  import BLEHandler
from brew_logger        import BrewSessionLogger, brew_log_service
from secrets            import ssid, password
from preset             import FEATURES, PINS, MAX31865_CONFIG, TARGET_TEMPERATURES, DIAGNET, BLE
from backflush          import run_backflush


# ============================================================================
# INITIALIZATION
# ============================================================================

# Wi-Fi only for the diagnostics link (EXPRESSO-DIAGNET 20.10.2026): stdout tee + shot samples as UDP to
# the collector. Earlier the radio was off for bluetooth stability; DIAGNET['enabled'] False restores that.
import diagnet
import brew_logger as _brew_logger_mod
diag = diagnet.start(network, socket, utime, DIAGNET, ssid, password)
_brew_logger_mod.SINK = diag

# INITIALIZE PT100 TEMPERATURE SENSOR WITH MAX31865
temperature_sensor = TemperatureSensor(max31865, PINS, MAX31865_CONFIG)
# Core 1 reader (EXPRESSO-TEMPSTALE-JA-OLETUS) starts in watchdog_feeder, after the relay guard's timer

# INITIALIZE PRESSURE SENSOR HANDLER
pressure_sensor = PressureSensor(utime, asyncio, Pin, PINS, ADC)

# SCALE_POLL_MS (user decision, 19.9.2026): the HX711 answers at 11.6 samples/s (scale.py line 7),
# a ~86 ms sample interval, so 50 ms catches every sample. 50*FLOW_MIN_POINTS(4)=200 ms fits inside
# FLOW_WINDOW_MS=1000 with double margin; one missed reading is 2*50=100 ms, under
# FLOW_STALE_MS=500; the tray watchdog (TRAY_STALE_MS=2000) sees two samples well before that.
SCALE_POLL_MS = 50

# INITIALIZE DRIP-TRAY SCALE (18.9.2026)
# Two HX711 cells on the pins scale.py defaults to (DT 18/20, SCK 19); scale_cal.json holds the
# calibration. link_ok() takes ~200 ms and is the only check that a scale is physically there - a
# machine without one must still boot, so every failure here leaves tray_scale None and the rest of
# the firmware runs exactly as before.
try:
    from scale import Scale
    tray_scale = Scale()
    if not tray_scale.link_ok():
        print('SCALE none: no answer on both cells')
        tray_scale = None
    else:
        print('SCALE ready: %s' % tray_scale.info())
except Exception as e:
    print('SCALE none: %s' % e)
    tray_scale = None

# INITIALIZE HEATING SPEED CALCULATOR
heating_speed_calculator = HeatingSpeedCalculator(utime, asyncio)
            
# INITIALIZE MAIN DATA HANDLER
brew_data = BrewData(
    Pin,
    ADC,
    PINS,
    TARGET_TEMPERATURES,
    FEATURES,
    heating_speed_calculator,
    temperature_sensor,
    pressure_sensor
)


# Pisin tehtavan kierros sitten viime nollauksen: pim:1-saadin nollaa sen ennen asyncio-vuoroaan ja kirjaa EU_STALL-
# riville, kuka vuoron varasi (EXPRESSO-ESIUUTTO-VUORONVARAUS, 26.9.2026)
brew_data.tbusy = ['-', 0]

# Brew log (EXPRESSO-UUTTOLOKI, 5.10.2026): run_shot starts and ends a session on the brew switch, the BLE
# task samples it at 10 Hz and sends the finished shot to the app as the August brew_log multipack
brew_data.brew_logger = BrewSessionLogger(utime)
brew_data.tray_scale = tray_scale
# The app straight over Wi-Fi (wifilink.py, EXPRESSO-WIFI-APPI vaihe 1): needs DIAGNET's radio and boot id
brew_data.wifi_link = None
brew_data.diag = diag                   # run_shot sets diag.quiet (EXPRESSO-WIFI-AIKAIKKUNA)
if diag is not None:
    try:
        import wifilink, hashlib, os as _os
        import bluetooth_handler as _bh
        brew_data.wifi_link = wifilink.WifiLink(brew_data, diag, socket, utime, hashlib, json, handle_command, _bh,
                                                wifilink.load_key(_os))
    except Exception as e:
        print('WIFI_START_FAIL %r' % (e,))
if tray_scale is not None:
    import scalecal
    brew_data.scale_cal = scalecal.ScaleCal(tray_scale, utime, lambda: brew_data.mode == 'IDLE')


# 30 ms task lateness since the last DIAG_HB: max us and count over 100 ms (EXPRESSO-GC-UUTTO 20.10.2026: the user saw
# delays of up to ~0.5 s after the machine had been on for long, maybe also without the Zero; the HB tracks it by uptime)
brew_data.lmax = [0, 0]


def task_late(t_sl):
    if t_sl is None:
        return
    l = utime.ticks_diff(utime.ticks_us(), t_sl) - 30000
    lm = brew_data.lmax
    if l > lm[0]:
        lm[0] = l
    if l > 100000:
        lm[1] += 1


def task_busy(name, t0):
    d = utime.ticks_diff(utime.ticks_us(), t0)
    tb = brew_data.tbusy
    if d > tb[1]:
        tb[0] = name
        tb[1] = d


# ============================================================================
# BLE COMMUNICATION
# ============================================================================

async def ble_communication(brew_data):
    ble = bluetooth.BLE()
    ble_handler = BLEHandler(ble, brew_data)

    last_transmission_time = utime.ticks_ms()

    t_sl = None
    while True:
        task_late(t_sl)
        t0 = utime.ticks_us()
        # Lähetetään data max 5 kertaa sekunnissa
        if utime.ticks_diff(utime.ticks_ms(), last_transmission_time) >= 200:
            last_transmission_time = utime.ticks_ms()
            ble_handler.run_transmission()

        # Brew log: 10 Hz sample during a shot, hand-over to the multipack when it is done (UUTTOLOKI)
        brew_log_service(brew_data, utime)

        # Mainostus disconnectin jälkeen
        ble_handler.advertise_if_needed()
        task_busy('ble', t0)

        t_sl = utime.ticks_us()
        await asyncio.sleep_ms(30)


# BLE off (preset BLE, EXPRESSO-WIFI-AIKAIKKUNA 20.10.2026): the brew log still samples at the BLE task's pace,
# and the Wi-Fi link sends the finished shot. The radio's BLE side is never activated.
async def brew_log_only(brew_data):
    t_sl = None
    while True:
        task_late(t_sl)
        t0 = utime.ticks_us()
        brew_log_service(brew_data, utime)
        task_busy('log', t0)
        t_sl = utime.ticks_us()
        await asyncio.sleep_ms(30)



# ============================================================================
# LOCAL PROGRAM
# ============================================================================

async def local_program(brew_data):
    
    # Set flag for indicating if settings are to be fetched
    brew_data.set_setting_changed()
    
    # Initialize switches, leds and relays
    LED_SWITCH_BREW, LED_SWITCH_WATER, LED_SWITCH_STEAM = brew_data.get_leds()
    SWITCH_BREW, SWITCH_WATER, SWITCH_STEAM             = brew_data.get_switches()
    RELAY_PUMP, RELAY_SOLENOID, RELAY_HEATER            = brew_data.get_relays()
    

    # LOAD SAVED SETTINGS
    load_settings(json, brew_data)

    # INITIALIZE THERMOSTAT
    thermostat = Thermostat(brew_data, TARGET_TEMPERATURES, RELAY_HEATER, temperature_sensor, utime)

    # INITIALIZE PUMP RATIO CALCULATOR
    pump_ratio_calculator = PumpRatioCalculator(utime, asyncio)
    pump_ratio_calculator.start(initial_pump_on=False)
    
    
    # INITIALIZE BREW VALUES
    
    
    # ============================================================================
    # BACKFLUSH -  LOCAL PROGRAM
    # ============================================================================

    # If brew Switch is on at boot start backflush cleaning program
    if SWITCH_BREW.value():
        await run_backflush(brew_data, thermostat)
        
        
    # ============================================================================
    # FAST HEATUP - LOCAL PROGRAM
    # ============================================================================
    
    # If fast heatup mode is on, start fast heatup program
    if brew_data.get_fast_heatup_mode() and brew_data.get_boiler_temperature() < 50:
        brew_data.set_mode('fast_heatup')
        await fast_heatup(utime, asyncio, brew_data)
        
        
    # Development and test commands own the loop while they run, so thermostat.run() does not
    # run and the heater would stay in whatever state it was left (up to 120 s in phold, longer
    # in pgap before its cap). Heater off first; the thermostat takes over again on the next
    # pass (EXPRESSO-TURVA-PIKAKORJAUKSET, 21.9.2026).
    async def dev_run(coro):
        RELAY_HEATER.value(0)
        await coro

    # ============================================================================
    # MAIN LOOP - LOCAL PROGRAM
    # ============================================================================
        
    while True:
        
        # Get brew settings from brew_data object
        if brew_data.get_setting_changed():
            save_settings(brew_data, json)
            
        # Get boiler  temperature
        boiler_temperature = brew_data.get_boiler_temperature()
        
        # Read pressure sensor
        pressure = brew_data.get_pressure()
        
        # Save heating speed
        heating_speed = brew_data.get_heating_speed()
            
        # DEV SAFE (dev:safe): relays off, no heating or pumping until dev:resume
        if brew_data.dev_safe:
            devsafe.relays_off()
            brew_data.set_mode('DEV_SAFE')
            await asyncio.sleep_ms(100)
            continue
        
        # STANDBY (VALMIUSTILA): any switch counts as activity; the idle timer is checked once per pass,
        # before the thermostat reads the target. Reads only, nothing blocking.
        _now = utime.ticks_ms()
        if SWITCH_BREW.value() or SWITCH_WATER.value() or SWITCH_STEAM.value():
            brew_data.note_activity(_now, 'switch')
        brew_data.update_standby(_now)

        # RUN THERMOSTAT
        thermostat.run()
        
        # PRESSURE CALIBRATION (requested from the app over BLE)
        pcal_stage = brew_data.take_pressure_calibration_request()
        if pcal_stage:
            await dev_run(pressure_calibration_run(brew_data, utime, asyncio, pcal_stage))

        if brew_data.take_pressure_zero_request():
            await dev_run(pressure_zero_run(brew_data, utime, asyncio))
            continue

        pcap_ms = brew_data.take_pressure_capture_request()
        if pcap_ms:
            await dev_run(pressure_capture_run(brew_data, utime, asyncio, pcap_ms))
            continue

        psweep_ms = brew_data.take_pressure_sweep_request()
        if psweep_ms:
            await dev_run(pressure_sweep_run(brew_data, utime, asyncio, psweep_ms))
            continue

        if brew_data.take_pressure_vent_request():
            from functions import pressure_vent_run
            await dev_run(pressure_vent_run(brew_data, utime, asyncio))
            continue

        plen_target = brew_data.take_pressure_len_request()
        if plen_target is not None:
            from functions import pressure_len_run
            await dev_run(pressure_len_run(brew_data, utime, asyncio, plen_target))
            continue

        pgap_target = brew_data.take_pressure_gap_request()
        if pgap_target is not None:
            from functions import pressure_gap_run
            await dev_run(pressure_gap_run(brew_data, utime, asyncio, pgap_target))
            continue

        vkello_target = brew_data.take_pressure_clock_request()
        if vkello_target is not None:
            from functions import pressure_clock_run
            await dev_run(pressure_clock_run(brew_data, utime, asyncio, vkello_target))
            continue

        vsweep_reps = brew_data.take_phase_sweep_request()
        if vsweep_reps:
            from functions import pressure_phase_sweep_run
            await dev_run(pressure_phase_sweep_run(brew_data, utime, asyncio, vsweep_reps))
            continue

        pstep_target = brew_data.take_pressure_step_request()
        if pstep_target is not None:
            from functions import pressure_step_run
            await dev_run(pressure_step_run(brew_data, utime, asyncio, pstep_target))
            continue

        mcal_ms = brew_data.take_mains_calibration_request()
        if mcal_ms:
            from functions import mains_calibrate
            await dev_run(mains_calibrate(brew_data, utime, asyncio, mcal_ms))
            continue

        phold_s = brew_data.take_pressure_hold_request()
        if phold_s:
            await dev_run(pressure_hold_run(brew_data, utime, asyncio, phold_s))
            continue

        ys = getattr(brew_data, 'ystall_request', None)
        if ys:
            brew_data.ystall_request = None
            from ystall import ystall_run
            await dev_run(ystall_run(brew_data, utime, asyncio, ys[0], ys[1]))
            continue

        klamp_s = brew_data.take_throttle_warmup_request()
        if klamp_s:
            from functions import throttle_warmup_run
            await dev_run(throttle_warmup_run(brew_data, utime, asyncio, pump_ratio_calculator, klamp_s))
            continue

        # PRINT VALUES
        if FEATURES['print_values_flag']:
            print_values(brew_data)
        
        # Set delay for resource sharing
        await asyncio.sleep_ms(5)
        
        
        # ============================================================================
        # BREW MODE - LOCAL PROGRAM
        # ============================================================================
        
        # If brew switch is on start brewing (code path shared with the remote test shot)
        if SWITCH_BREW.value():
            if getattr(brew_data, 'throttle_set', 0):
                # Kuristimen saatotila (kuri:1, TILAUS-M): pumppu joka toisella jaksolla ilman paineensaatoa.
                # Testikomento kuten muut: dev_run sammuttaa lammittimen (EXPRESSO-TURVA-DEVRUN 5.10.2026).
                from functions import throttle_set_run
                await dev_run(throttle_set_run(brew_data, utime, asyncio, pump_ratio_calculator, SWITCH_BREW.value))
            else:
                await run_shot(brew_data, utime, asyncio, pump_ratio_calculator, SWITCH_BREW.value, 'PB')
            brew_data.note_activity(utime.ticks_ms(), 'switch')
        
        
        # ============================================================================
        # REMOTE TEST SHOT (tshot:<seconds>) - same code path as the brew switch
        # ============================================================================
        
        test_shot_seconds = brew_data.take_test_shot_request()
        if test_shot_seconds and not (SWITCH_BREW.value() or SWITCH_WATER.value() or SWITCH_STEAM.value()):
            test_shot_end = utime.ticks_add(utime.ticks_ms(), int(test_shot_seconds * 1000))
            
            def test_shot_running():
                # Any machine switch, tshot:stop, dev:safe or the time limit ends the test shot
                if SWITCH_BREW.value() or SWITCH_WATER.value() or SWITCH_STEAM.value():
                    return False
                if brew_data.test_shot_abort or brew_data.dev_safe:
                    return False
                return utime.ticks_diff(test_shot_end, utime.ticks_ms()) > 0
            
            # Test shots need the absolute tray limit too (EXPRESSO-KAUKALOVAHTI-KOKONAISPAINO,
            # 21.9.2026): without wmax, or with the tray already at it, the shot does not start.
            from functions import tray_guard_start
            _tray_state, _tray_reason = tray_guard_start(brew_data, utime)
            if _tray_reason:
                print('TS_END loops=0 max_loop_ms=0 reason=%s' % _tray_reason)
                continue
            # The weight limits are persisted in settings.txt (devsafe12), but a lost or reset file turns
            # them off. Print their state with every test shot: without this the log cannot tell a
            # protected run from an unprotected one (18.9.2026).
            _wmax, _wrise = brew_data.get_weight_limit(), brew_data.get_weight_rise_limit()
            _limits = ('wmax:%.0f ' % _wmax if _wmax > 0 else '') + \
                      ('wrise:%.0f' % _wrise if _wrise > 0 else '')
            _fmode = ('%.2f' % brew_data.get_flow_target()) if brew_data.get_flow_mode() else 'off'
            print('TS_START %.1f s pre=%s %.1f bar %.1f s brew=%.1f bar limits=%s fmode=%s pim=%d bim=%d' % (
                test_shot_seconds, brew_data.get_pre_infusion_mode(), brew_data.get_pre_infusion_pressure(),
                brew_data.get_pre_infusion_time(), brew_data.get_brew_pressure(),
                _limits.strip() or 'OFF', _fmode, getattr(brew_data, 'pre_infusion_method', 0),
                getattr(brew_data, 'brew_method', 0)))
            await run_shot(brew_data, utime, asyncio, pump_ratio_calculator, test_shot_running, 'TS',
                           limit_weight=True)
            brew_data.set_mode('IDLE')
            brew_data.note_activity(utime.ticks_ms(), 'tshot')
        
        
        # ============================================================================
        # HOT WATER MODE - LOCAL PROGRAM
        # ============================================================================

        # If water switch is on
        if SWITCH_WATER.value():
            await hot_water_run(brew_data, thermostat, utime, asyncio)
           
           
        # ============================================================================
        # STEAM MODE - LOCAL PROGRAM
        # ============================================================================
    
        if SWITCH_STEAM.value():
            brew_data.set_mode('STEAM')
            
        else:
            brew_data.set_mode('IDLE')


# ============================================================================
# SERIAL COMMANDS - "CMD <command>" lines on USB (same dispatcher as BLE)
# ============================================================================

async def serial_commands(brew_data):
    import sys
    from commands import SerialLine
    poller = select.poll()
    poller.register(sys.stdin, select.POLLIN)
    rd = getattr(sys.stdin, 'buffer', sys.stdin)    # bytes: text mode raised UnicodeError on a stray byte
    sl = SerialLine()
    while True:
        t0 = utime.ticks_us()
        # An exception in a gathered task ends all of them (relays off, watchdog reset): none may leave here
        try:
            while poller.poll(0):
                b = rd.read(1)
                if not b:
                    break
                v = b[0]
                line = sl.feed(ord(v) if isinstance(v, str) else v)
                if line is not None and line.startswith('CMD '):
                    command = line[4:].strip()
                    handle_command(brew_data, command)
                    print('%s %s' % ('CMD_OK' if brew_data.command_known else 'CMD_UNKNOWN', command))
        except Exception as e:
            sl = SerialLine()
            try:
                print('SER_ERR %r' % (e,))
            except Exception:
                pass
        task_busy('ser', t0)
        await asyncio.sleep_ms(50)


# ============================================================================
# WATCHDOG
# ============================================================================

async def scale_reader(brew_data):
    """Keep brew_data.weight fresh. Scale.update() never blocks: it returns None until the HX711 has
    a sample ready, so this task costs one bit-banged read (~1 ms) per sample and nothing otherwise.
    It runs in its own task, not in the control loops, which are timed to ~1 ms per iteration."""
    if tray_scale is None:
        return
    while True:
        t0 = utime.ticks_us()
        scale_poll_once()
        task_busy('scale', t0)
        await asyncio.sleep_ms(SCALE_POLL_MS)


def scale_poll_once():
    try:
        grams = tray_scale.update()
        if grams is not None:
            brew_data.weight = grams
            brew_data.weight_ms = utime.ticks_ms()
            brew_data.weight_a = tray_scale.last_a
            brew_data.weight_b = tray_scale.last_b
            if brew_data.scale_cal is not None:
                brew_data.scale_cal.on_sample(tray_scale.raw_a, tray_scale.raw_b)
        if brew_data.scale_cal is not None:
            brew_data.scale_cal.tick()
        # Every iteration, not only when a new sample arrived: flow() reads no sensor, and it is
        # the call that turns a frozen reading into None once the samples go stale.
        brew_data.flow = tray_scale.flow(brew_data.flow_window_ms)
    except Exception:
        pass


# The capture loops (pstep/pgap/plen) never yield, so scale_reader does not run during them. They
# call this through functions.tray_guard_poll() once a second to keep the tray check alive during
# the run (EXPRESSO-TURVA-TOIMILAITE, 22.9.2026). Not a task: nothing else reads the HX711 then.
if tray_scale is not None:
    brew_data.scale_poll = scale_poll_once


async def watchdog_feeder():
    # Relay guard poll runs on a machine.Timer, not in this task: it must also run inside the
    # busy capture loops that never yield (relayguard.py). Started here, next to the watchdog.
    brew_data.relay_guard.start()
    devsafe.start_watchdog()
    # Core 1 only now: with its sleep loop already running, the guard's Timer(-1) found the rp2 default alarm
    # pool full at boot (OSError ENOMEM, main exited, 5.10.2026 flash on the Zero). It reads the temperature from
    # here on, at rest too (C1-JAKSOT vaihe 2): core 0's read_rtd slept 75 ms twice a main loop round.
    temperature_sensor.c1_start(utime)
    temperature_sensor.c1_rest_on()
    while True:
        t0 = utime.ticks_us()
        devsafe.feed()
        task_busy('wd', t0)
        await asyncio.sleep_ms(1000)


# ============================================================================
# ASYNC HANDLING
# ============================================================================

async def async_main():
    print('BLE %s' % ('on' if BLE.get('enabled') else 'off'))
    tasks = [ble_communication(brew_data) if BLE.get('enabled') else brew_log_only(brew_data), local_program(brew_data),
             serial_commands(brew_data), watchdog_feeder(), scale_reader(brew_data)]
    if diag is not None:
        tasks.append(diag.run(brew_data, asyncio, task_busy))
    if brew_data.wifi_link is not None:
        tasks.append(brew_data.wifi_link.run(asyncio, task_busy))
    await asyncio.gather(*tasks)

try:
    asyncio.run(async_main())
except BaseException as e:
    # Relays first, then the traceback into the diagnostics ring: the watchdog resets the Pico 8 s later
    # and the REPL's own traceback would never leave over the network.
    devsafe.relays_off()
    if diag is not None:
        sys.print_exception(e)
    raise
finally:
    # Ctrl-C (KeyboardInterrupt), a crash or any exit: relays down before the REPL takes over.
    # The watchdog keeps running: tools must call devsafe.enter()/feed(), otherwise the Pico resets.
    devsafe.relays_off()
    print('DEVSAFE relays off (main exited) relays=%s' % devsafe.relays_state())
    if diag is not None:
        diag.flush()
