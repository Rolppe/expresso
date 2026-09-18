import os

# ============================================================================
#  PRE-INFUSION
# ============================================================================

async def pre_infusion(brew_data, utime, asyncio, pump_ratio_calculator, keep_running=None):
    
    RELAY_PUMP, RELAY_SOLENOID, RELAY_HEATER = brew_data.get_relays()
    SWITCH_BREW = brew_data.get_switch_brew()
    # keep_running: brew switch for a real shot, test-shot condition for tshot (17.9.2026)
    if keep_running is None:
        keep_running = SWITCH_BREW.value
    
    brew_data.set_mode('pre-infusion initialization')
    pressure = brew_data.get_pressure()
    
    last_pump_ratio_time = utime.ticks_ms()
    
    # Get boiler temperature
    boiler_temperature = brew_data.get_boiler_temperature()
    
    # Open solenoid for water to flow to grouphead
    RELAY_SOLENOID.value(1)
    
    # Target pre-infusion pressure (bar), set from app slider (1-4 bar)
    pre_infusion_pressure = brew_data.get_pre_infusion_pressure()
    
    # If theres a pressure in system, let stabilize to pre-infusion pressure
    while pressure > pre_infusion_pressure - 0.1 and keep_running():
        
        brew_data.set_mode('pre-infusion pressure stabilization')
        
        # Read sensor pressure (no temperature read: MAX31865 blocks >= 75 ms)
        pressure = brew_data.get_pressure()

        await asyncio.sleep_ms(20)
        
        
    # ===== PRE-INFUSION: BUILD-UP AND TIMED HOLD ===== #
    # One fast loop (~20 ms): no temperature reads (MAX31865 blocks >= 75 ms), pump by
    # PumpPressureController. Build-up ends when the target is first reached; the timer starts then.
    from classes import PumpPressureController
    # Build-up follows a ramped setpoint instead of a duty ceiling (18.9.2026). History: test shots
    # 3-5 (needle valve) overshot 2.0 -> 4.1-4.5 bar, so devsafe6 capped the duty at 80 % up to half
    # the target and 25 % above it. The first real shot on coffee (06:56:42) showed why that is the
    # wrong shape: against a puck 25 % duty settles at ~1.35 bar and never reaches 2.0, the hold then
    # started on a noise spike in the 16.7 ms average and the restored full duty shot to 3.84 bar.
    # A ramped setpoint keeps the pump continuous while it is far below target (the flush rule) and
    # lets the controller approach the target at a known rate, so the pump+sensor delay costs about
    # RAMP_BAR_PER_S * delay (~0.14 bar) instead of a step response.
    RAMP_BAR_PER_S = 2.0
    brew_data.pressure_sensor.reset_average()
    controller = PumpPressureController(RELAY_PUMP, pump_ratio_calculator, utime,
                                        ff=brew_data.learned_ff_pre, max_duty=1.0)
    brew_data.set_mode('pre-infusion pressure build-up')
    ramp_start = utime.ticks_ms()
    ramp_base = 0.0
    hold_start = None
    build_up = True
    end = None
    last_log = 0
    while keep_running():
        now = utime.ticks_ms()
        pressure = brew_data.get_pressure_average(utime)
        if build_up:
            # While the controller still runs the pump continuously (far below the target) the
            # setpoint stays at the target: rate-limiting there would chop the pump, which is exactly
            # what a flush must never do. The ramp starts from the pressure at which the continuous
            # region ends, so the last stretch is a rate-limited approach, and the hold starts when
            # the ramp is done - not when a noisy sample happens to touch the target.
            ramp_from = pre_infusion_pressure - controller.continuous_error
            if controller.filtered < ramp_from or controller.filtered < pre_infusion_pressure * 0.5:
                ramp_start = now
                ramp_base = controller.filtered
                target = pre_infusion_pressure
            else:
                ramped = ramp_base + RAMP_BAR_PER_S * utime.ticks_diff(now, ramp_start) / 1000.0
                if ramped >= pre_infusion_pressure:
                    ramped = pre_infusion_pressure
                    build_up = False
                    hold_start = now
                    brew_data.set_mode('pre-infusion main')
                    # Duration from app slider (pit:), was a fixed 5 s
                    end = utime.ticks_add(now, int(float(brew_data.get_pre_infusion_time() or 0) * 1000))
                target = ramped
        else:
            target = pre_infusion_pressure
        controller.update(pressure, target)
        brew_data.pressure_filtered = controller.filtered

        if end is not None and utime.ticks_diff(end, now) <= 0:
            break

        if utime.ticks_diff(now, last_pump_ratio_time) >= 1000:
            brew_data.set_pump_ratio(round(pump_ratio_calculator.get_ratio()))
            last_pump_ratio_time = now
        if utime.ticks_diff(now, last_log) >= 100:
            last_log = now
            print('PI %d %.1f %.1f %d %.2f %.1f %.1f %.1f %s' % (now, pressure, target, controller.on,
                                              controller.duty, brew_data.pressure_sensor.window_peak,
                                              brew_data.weight_a, brew_data.weight_b,
                                              weight_flow_log(brew_data)))

        await asyncio.sleep_ms(0)

    controller.stop()
    if hold_start is not None and utime.ticks_diff(utime.ticks_ms(), hold_start) >= 2000:
        brew_data.learned_ff_pre = min(0.9, max(0.05, controller.duty_avg))
    print('PI_END learned_ff_pre=%.2f' % brew_data.learned_ff_pre)


def weight_flow_log(brew_data):
    """Tail of the 10 Hz log lines: tray weight and flow, or '-' when there is no scale or the
    samples are stale. Appended after the per-cell fields so the positional indices keep meaning."""
    w = brew_data.get_weight()
    f = brew_data.get_flow()
    return 'w=%s f=%s' % ('-' if w is None else '%.1f' % w,
                          '-' if f is None else '%.2f' % f)


# ============================================================================
# SHOT (brew switch or remote test shot)
# ============================================================================

async def run_shot(brew_data, utime, asyncio, pump_ratio_calculator, keep_running, label='PB',
                   limit_weight=False):
    # Pre-infusion, brew loop, soft pressure release, solenoid off. Moved from main.py so a remote
    # test shot (tshot:) runs exactly the brew-switch code path (17.9.2026).
    from classes import PumpPressureController
    from preset import FEATURES
    RELAY_PUMP, RELAY_SOLENOID, RELAY_HEATER = brew_data.get_relays()

    brew_data.set_mode('BREW')
    await asyncio.sleep_ms(50)
    RELAY_HEATER.value(0)
    start_time = utime.ticks_ms()
    abort_reason = ''
    over = [0, 0]          # [consecutive samples over the limit, last sample timestamp]
    weight_start = brew_data.get_weight() if limit_weight else None

    def running():
        nonlocal abort_reason
        if abort_reason:
            return False
        # Only while the pump is adding pressure: with the solenoid closed the boiler's own thermal
        # expansion reaches ~14 bar at idle (17.9.2026), and a shot must be allowed to open the
        # solenoid and release it
        if brew_data.pressure_filtered > 13.0 and RELAY_PUMP.value():
            abort_reason = 'overpressure %.1f bar' % brew_data.pressure_filtered
            return False
        # Test shots only: stop before the drip tray overflows (18.9.2026). A real shot has a cup on
        # the same scale, so the switch path passes limit_weight=False and is never stopped by weight.
        if limit_weight:
            limit = brew_data.get_weight_limit()
            rise_limit = brew_data.get_weight_rise_limit()
            if limit > 0 or rise_limit > 0:
                weight = brew_data.get_weight()
                age = utime.ticks_diff(utime.ticks_ms(), brew_data.get_weight_ms())
                # A scale that stops answering leaves brew_data.weight frozen at its last value, so
                # a limit would never fire - the exact case the limits exist for
                if weight is None or age > 2000:
                    abort_reason = 'scale silent %d ms' % age
                    return False
                if rise_limit > 0 and weight_start is None:
                    abort_reason = 'no weight at shot start'
                    return False
                # Two consecutive *samples* over a limit, not two loop iterations: the loop runs at
                # ~1 ms and the scale at ~10 Hz, and single spikes of -16 g were seen in telemetry
                ms = brew_data.get_weight_ms()
                if ms != over[1]:
                    over[1] = ms
                    hit = (limit > 0 and weight >= limit) or \
                          (rise_limit > 0 and weight - weight_start >= rise_limit)
                    over[0] = over[0] + 1 if hit else 0
                if over[0] >= 2:
                    if limit > 0 and weight >= limit:
                        abort_reason = 'tray %.0f g >= limit %.0f g' % (weight, limit)
                    else:
                        abort_reason = 'shot added %.0f g >= %.0f g' % (weight - weight_start, rise_limit)
                    return False
        return keep_running()

    try:
        # ===== PRE-INFUSION ===== #
        if brew_data.get_pre_infusion_mode():
            await pre_infusion(brew_data, utime, asyncio, pump_ratio_calculator, running)

        # ===== BREW LOOP ===== #
        brew_data.set_mode('brew loop initialization')
        last_pump_ratio_time = utime.ticks_ms()
        RELAY_SOLENOID.value(1)
        brew_data.set_mode('brew loop')

        # Fast loop (~20-25 ms): pump decided every iteration by PumpPressureController;
        # boiler temperature (MAX31865 blocks >= 75 ms) only every 2 s for telemetry.
        brew_data.pressure_sensor.reset_average()
        pressure_controller = PumpPressureController(RELAY_PUMP, pump_ratio_calculator, utime,
                                                     ff=brew_data.learned_ff_brew)
        brew_start = utime.ticks_ms()
        last_temperature_read = utime.ticks_ms()
        last_log = 0
        last_loop = utime.ticks_ms()
        max_loop_ms = 0
        loops = 0
        while running():
            now = utime.ticks_ms()
            elapsed_ms = utime.ticks_diff(now, start_time)
            loop_ms = utime.ticks_diff(now, last_loop)
            last_loop = now
            loops += 1
            if loops > 1 and loop_ms > max_loop_ms:
                max_loop_ms = loop_ms

            # ===== HEATER: off 0.1 s, on 0.05 s ===== #
            if (elapsed_ms % 150) < 100:
                RELAY_HEATER.value(0)
            else:
                RELAY_HEATER.value(1)

            if utime.ticks_diff(now, last_temperature_read) >= 2000:
                brew_data.get_boiler_temperature()
                last_temperature_read = utime.ticks_ms()

            # ===== PRESSURE + PUMP ===== #
            pressure = brew_data.get_pressure_average(utime)
            brew_pressure = brew_data.get_brew_pressure()
            pressure_controller.update(pressure, brew_pressure)
            brew_data.pressure_filtered = pressure_controller.filtered

            if utime.ticks_diff(now, last_pump_ratio_time) >= 1000:
                brew_data.set_pump_ratio(pump_ratio_calculator.get_ratio())
                last_pump_ratio_time = now

            if utime.ticks_diff(now, last_log) >= 100:
                last_log = now
                print('%s %d %.1f %.1f %d %.2f %.1f %.1f %.1f %s' % (label, elapsed_ms, pressure, brew_pressure,
                                                        pressure_controller.on, pressure_controller.duty,
                                                        brew_data.pressure_sensor.window_peak,
                                                        brew_data.weight_a, brew_data.weight_b,
                                                        weight_flow_log(brew_data)))

            # Yield to BLE without adding delay
            await asyncio.sleep_ms(0)

        pressure_controller.stop()
        RELAY_HEATER.value(0)
        if utime.ticks_diff(utime.ticks_ms(), brew_start) >= 8000:
            brew_data.learned_ff_brew = min(0.9, max(0.05, pressure_controller.duty_avg))
        print('%s_END loops=%d max_loop_ms=%d reason=%s learned_ff_brew=%.2f' % (
            label, loops, max_loop_ms, abort_reason or 'stopped', brew_data.learned_ff_brew))

        # ===== PRESSURE SOFT RELEASE ===== #
        RELAY_PUMP.value(0)
        brew_data.set_pump_ratio(0)
        if brew_data.get_pressure() >= brew_data.get_soft_pressure_release_arming_pressure() and brew_data.get_pressure_soft_release_mode():
            brew_data.set_mode('soft pressure release')
            soft_pressure_release_time = brew_data.get_pressure_soft_release_time()
            print("soft release time: " + str(soft_pressure_release_time))
            # App slider sends fractional seconds (srt:), range() would raise TypeError
            await asyncio.sleep_ms(int(float(soft_pressure_release_time) * 1000))

        # ===== PRESSURE DRAIN ===== #
        RELAY_SOLENOID.value(0)
        if FEATURES['after_brew_pressure_drain_flag']:
            brew_data.set_mode('after brew pressure drain')
            pressure = brew_data.get_pressure()
            while pressure > 1.5:
                await asyncio.sleep(0.5)
                RELAY_SOLENOID.value(1)
                await asyncio.sleep(0.5)
                RELAY_SOLENOID.value(0)
                pressure = brew_data.get_pressure()
    finally:
        RELAY_PUMP.value(0)
        RELAY_HEATER.value(0)
        RELAY_SOLENOID.value(0)
    return abort_reason


# ============================================================================
# PRESSURE CALIBRATION RUN
# ============================================================================

async def pressure_calibration_run(brew_data, utime, asyncio, stage):
    # 10 s of water at the stage's target pressure so the user can read a reference gauge.
    # Samples the uncalibrated sensor value over the last 5 s for the correction.
    RELAY_PUMP, RELAY_SOLENOID, RELAY_HEATER = brew_data.get_relays()
    SWITCH_BREW, SWITCH_WATER, SWITCH_STEAM = brew_data.get_switches()

    if stage == 'pre':
        target = brew_data.get_pre_infusion_pressure()
    else:
        target = brew_data.get_brew_pressure()

    brew_data.pressure_calibration_begin(stage, target)
    brew_data.set_mode('pressure calibration')
    RELAY_HEATER.value(0)

    from classes import PumpPressureController, PumpRatioCalculator
    controller = PumpPressureController(RELAY_PUMP, PumpRatioCalculator(utime, asyncio), utime)
    raw_sum = 0.0
    raw_n = 0
    reason = ''
    start = utime.ticks_ms()
    try:
        RELAY_SOLENOID.value(1)
        while utime.ticks_diff(utime.ticks_ms(), start) < 10000:
            if SWITCH_BREW.value() or SWITCH_WATER.value() or SWITCH_STEAM.value():
                reason = 'machine switch'
                break
            if brew_data.pcal_cancel:
                reason = 'cancelled'
                break

            pressure = brew_data.get_pressure_average(utime)
            if pressure > 12.0:
                reason = 'overpressure %.1f bar' % pressure
                break

            controller.update(pressure, target)

            if utime.ticks_diff(utime.ticks_ms(), start) >= 5000:
                raw_sum += brew_data.get_pressure_raw()
                raw_n += 1

            await asyncio.sleep_ms(0)
    finally:
        RELAY_PUMP.value(0)
        RELAY_SOLENOID.value(0)
        brew_data.set_mode('IDLE')

    if reason or raw_n == 0:
        brew_data.pressure_calibration_end(stage, None, reason)
    else:
        brew_data.pressure_calibration_end(stage, raw_sum / raw_n, '')


# ============================================================================
# FAST HEATUP
# ============================================================================

async def fast_heatup(utime, brew_data): 
        
    RELAY_PUMP, RELAY_SOLENOID, RELAY_HEATER = brew_data.get_relays()
    
    # Fill the boiler
    RELAY_SOLENOID.value(1)
    RELAY_PUMP.value(1)
    await asyncio.sleep(2)
    RELAY_PUMP.value(0)
    RELAY_SOLENOID.value(0)

    # Heat the boiler
    RELAY_HEATER.value(1)
    while brew_data.get_boiler_temperature() < 85:
        await asyncio.sleep(1)
    while brew_data.get_boiler_temperature() < 110:
        RELAY_HEATER.value(1)
        await asyncio.sleep(1)
        RELAY_HEATER.value(0)
        await asyncio.sleep(1.5)
    while brew_data.get_boiler_temperature() < 115:
        RELAY_HEATER.value(1)
        await asyncio.sleep(1)
        RELAY_HEATER.value(0)
        await asyncio.sleep(2)
    
    # keep the temperature
    for i in range(200):
        if brew_data.get_boiler_temperature() < 115:
            RELAY_HEATER.value(1)
            await asyncio.sleep(1)
            RELAY_HEATER.value(0)
            await asyncio.sleep(2)
        else:
            await asyncio.sleep(1)
        await asyncio.sleep(1)
    
    # Cool the boiler to under 105 celsius
    while brew_data.get_boiler_temperature() > 99:
        await asyncio.sleep(1)
        
    # Fill the boiler
    RELAY_SOLENOID.value(1)
    RELAY_PUMP.value(1)
    await asyncio.sleep(0.5)
    RELAY_PUMP.value(0)
    RELAY_SOLENOID.value(0)
    
    # Sleep while boiler stabilizes
    await asyncio.sleep(15)


# ============================================================================
# PRINT VALUES
# ============================================================================

def print_values(brew_data):
 
    # Get state of data
    boiler_temperature = brew_data.get_boiler_temperature()
    mode               = brew_data.get_mode()
    heating_speed      = brew_data.get_heating_speed()
    
    RELAY_PUMP, RELAY_SOLENOID, RELAY_HEATER = brew_data.get_relays()
    SWITCH_BREW, SWITCH_WATER, SWITCH_STEAM  = brew_data.get_switches()
    
    # Print values
    print('Mode: ', mode)
    print('Boiler temperature: ', boiler_temperature)
    print('heating_speed: ',      heating_speed)
    print('switch_brew: ',        SWITCH_BREW.value())
    print('switch_water: ',       SWITCH_WATER.value()) 
    print('switch_steam: ',       SWITCH_STEAM.value())
    print('RELAY_HEATER: ',       RELAY_HEATER.value())
    print('RELAY_SOLENOID: ',     RELAY_SOLENOID.value())
    print('RELAY_PUMP: ',         RELAY_PUMP.value())
    print('')


# ============================================================================
# SAVE SETTINGS
# ============================================================================

def save_settings(brew_data, json_module):
    # Get settings from brew_data object
    brew_temperature           = brew_data.get_brew_temperature()
    steam_temperature          = brew_data.get_steam_temperature()
    pre_infusion_time          = brew_data.get_pre_infusion_time()
    pressure_soft_release_time = brew_data.get_pressure_soft_release_time()
    pre_heat_time              = brew_data.get_pre_heat_time()
    pre_infusion_mode          = brew_data.get_pre_infusion_mode()
    pressure_soft_release_mode = brew_data.get_pressure_soft_release_mode()
    fast_heatup_mode           = brew_data.get_fast_heatup_mode()
    brew_pressure              = brew_data.get_brew_pressure()
    pre_infusion_pressure      = brew_data.get_pre_infusion_pressure()
    
    # Form the data
    data = {
        'brew_temperature'          : brew_temperature,
        'steam_temperature'         : steam_temperature,
        'pre_infusion_time'         : pre_infusion_time,
        'pressure_soft_release_time': pressure_soft_release_time,
        'pre_infusion_mode'         : pre_infusion_mode,
        'pressure_soft_release_mode': pressure_soft_release_mode,
        'fast_heatup_mode'          : fast_heatup_mode,
        'brew_pressure'             : brew_pressure,
        'pre_infusion_pressure'     : pre_infusion_pressure,
        # Test-shot weight limits (18.9.2026). Persisted after all: they are read only when
        # run_shot gets limit_weight=True, which happens for tshot and never for the brew switch,
        # so a stored limit cannot affect a real shot. Not persisting them meant the protection was
        # silently off after every restart and flash - a memory burden on the user, not a safeguard.
        'weight_limit'              : brew_data.get_weight_limit(),
        'weight_rise_limit'         : brew_data.get_weight_rise_limit()
    }
    
    # Save data to file in json format
    with open('settings.txt', 'w') as file:
        json_module.dump(data, file)
    
    print("save_settings")


# ============================================================================
# LOAD SETTINGS
# ============================================================================

def load_settings(json_module, brew_data):
    
    # Get values from file to variables
    try:
        with open('settings.txt', 'r') as file:
            data = json_module.load(file)
            
            brew_temperature           = data.get('brew_temperature')
            steam_temperature          = data.get('steam_temperature')
            pre_infusion_time          = data.get('pre_infusion_time')
            pressure_soft_release_time = data.get('pressure_soft_release_time')
            pre_infusion_mode          = data.get('pre_infusion_mode')
            pressure_soft_release_mode = data.get('pressure_soft_release_mode')
            fast_heatup_mode           = data.get('fast_heatup_mode')
        
        # Set settings to brew_data object
        brew_data.set_brew_temperature(brew_temperature)
        brew_data.set_steam_temperature(steam_temperature)
        brew_data.set_pre_infusion_time(pre_infusion_time)
        brew_data.set_pressure_soft_release_time(pressure_soft_release_time)
        brew_data.set_pre_infusion_mode(pre_infusion_mode)
        brew_data.set_pressure_soft_release_mode(pressure_soft_release_mode)
        brew_data.set_fast_heatup_mode(fast_heatup_mode)
        
        # Pressures were added 17.9.2026: older settings.txt has no keys -> keep defaults
        if data.get('brew_pressure') is not None:
            brew_data.set_brew_pressure(data.get('brew_pressure'))
        if data.get('pre_infusion_pressure') is not None:
            brew_data.set_pre_infusion_pressure(data.get('pre_infusion_pressure'))
        # Weight limits added 18.9.2026: same rule, a file without the keys keeps the defaults (off)
        if data.get('weight_limit') is not None:
            brew_data.set_weight_limit(data.get('weight_limit'))
        if data.get('weight_rise_limit') is not None:
            brew_data.set_weight_rise_limit(data.get('weight_rise_limit'))
        
        print('Loaded settings: brew_temperature, steam_temperature, pre_infusion_time, pressure_soft_release_time, pre_infusion_mode, pressure_soft_release_mode, fast_heatup_mode')
        return True
    
    # If data is not available: remove settings file and return False
    except (OSError, ValueError):   # ValueError = JSON syntax error 
        try:
            os.remove('settings.txt')
            print('settings.txt deleted pecause of error')
        except OSError:
            print('tried to delete settings.txt pecause of error but theres error in file deleting process')
        
        return False





