# RELAYS OFF FIRST (devsafe, 17.9.2026): before any other import or initialization
import devsafe
devsafe.relays_off()

# IMPORT LIBRARIES
import utime
import json
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
from functions          import save_settings, load_settings, print_values, fast_heatup, pre_infusion, pressure_calibration_run, pressure_zero_run, pressure_capture_run, pressure_sweep_run, pressure_hold_run, run_shot
from commands           import handle_command
from classes            import BrewData, HeatingSpeedCalculator, Thermostat, TemperatureSensor, PressureSensor, PumpRatioCalculator, PumpPressureController
from bluetooth_handler  import BLEHandler
from secrets            import ssid, password
from preset             import FEATURES, PINS, MAX31865_CONFIG, TARGET_TEMPERATURES
from backflush          import run_backflush


# ============================================================================
# INITIALIZATION
# ============================================================================

# Turn off wifi for bluetooth stability
wlan = network.WLAN(network.STA_IF)
wlan.active(False)

# INITIALIZE PT100 TEMPERATURE SENSOR WITH MAX31865
temperature_sensor = TemperatureSensor(max31865, PINS, MAX31865_CONFIG)

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

    while True:
        t0 = utime.ticks_us()
        # Lähetetään data max 5 kertaa sekunnissa
        if utime.ticks_diff(utime.ticks_ms(), last_transmission_time) >= 200:
            last_transmission_time = utime.ticks_ms()
            ble_handler.run_transmission()

        # Mainostus disconnectin jälkeen
        ble_handler.advertise_if_needed()
        task_busy('ble', t0)

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
    thermostat = Thermostat(brew_data, TARGET_TEMPERATURES, RELAY_HEATER, temperature_sensor)

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
            await run_shot(brew_data, utime, asyncio, pump_ratio_calculator, SWITCH_BREW.value, 'PB')
        
        
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
            # The weight limits are deliberately not persisted, so they are off after every restart
            # and flash. Print their state with every test shot: without this the log cannot tell a
            # protected run from an unprotected one (18.9.2026).
            _wmax, _wrise = brew_data.get_weight_limit(), brew_data.get_weight_rise_limit()
            _limits = ('wmax:%.0f ' % _wmax if _wmax > 0 else '') + \
                      ('wrise:%.0f' % _wrise if _wrise > 0 else '')
            _fmode = ('%.2f' % brew_data.get_flow_target()) if brew_data.get_flow_mode() else 'off'
            print('TS_START %.1f s pre=%s %.1f bar %.1f s brew=%.1f bar limits=%s fmode=%s pim=%d' % (
                test_shot_seconds, brew_data.get_pre_infusion_mode(), brew_data.get_pre_infusion_pressure(),
                brew_data.get_pre_infusion_time(), brew_data.get_brew_pressure(),
                _limits.strip() or 'OFF', _fmode, getattr(brew_data, 'pre_infusion_method', 0)))
            await run_shot(brew_data, utime, asyncio, pump_ratio_calculator, test_shot_running, 'TS',
                           limit_weight=True)
            brew_data.set_mode('IDLE')
        
        
        # ============================================================================
        # HOT WATER MODE - LOCAL PROGRAM
        # ============================================================================

        # If water switch is on
        if SWITCH_WATER.value():
            
            # Set mode to 'water'
            brew_data.set_mode('WATER')
            
            # Set on boiler heater
            RELAY_HEATER.value(1)
            
            # set on water
            RELAY_PUMP.value(1)
            
            # Run cycle for hot water as long as hot water switch is on. The temperature is read
            # once a second so the relay guard's heater limits see a fresh value
            # (EXPRESSO-TURVA-TOIMILAITE, 22.9.2026); a stale reading would switch the heater off.
            last_temperature_read = utime.ticks_ms()
            while (SWITCH_WATER.value()):
                await asyncio.sleep_ms(50)
                if utime.ticks_diff(utime.ticks_ms(), last_temperature_read) >= 1000:
                    brew_data.get_boiler_temperature()
                    last_temperature_read = utime.ticks_ms()
                
            # Set heater and pump relays off after hot water kloop
            RELAY_PUMP.value(0)
            RELAY_HEATER.value(0)
           
           
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
    poller = select.poll()
    poller.register(sys.stdin, select.POLLIN)
    buf = ''
    while True:
        t0 = utime.ticks_us()
        while poller.poll(0):
            ch = sys.stdin.read(1)
            if ch == '\r' or ch == '\n':
                line = buf.strip()
                buf = ''
                if line.startswith('CMD '):
                    command = line[4:].strip()
                    handle_command(brew_data, command)
                    print('%s %s' % ('CMD_OK' if brew_data.command_known else 'CMD_UNKNOWN', command))
            elif len(buf) < 80:
                buf += ch
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
    while True:
        t0 = utime.ticks_us()
        devsafe.feed()
        task_busy('wd', t0)
        await asyncio.sleep_ms(1000)


# ============================================================================
# ASYNC HANDLING
# ============================================================================

async def async_main():
    await asyncio.gather(ble_communication(brew_data), local_program(brew_data),
                         serial_commands(brew_data), watchdog_feeder(), scale_reader(brew_data))

try:
    asyncio.run(async_main())
finally:
    # Ctrl-C (KeyboardInterrupt), a crash or any exit: relays down before the REPL takes over.
    # The watchdog keeps running: tools must call devsafe.enter()/feed(), otherwise the Pico resets.
    devsafe.relays_off()
    print('DEVSAFE relays off (main exited) relays=%s' % devsafe.relays_state())
