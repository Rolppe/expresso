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
    from classes import PumpPressureController, FlowController
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
        flow_controller = None
        if brew_data.get_flow_mode() and brew_data.get_flow() is not None:
            flow_controller = FlowController(utime, brew_data.get_flow_target(),
                                             brew_data.learned_ff_brew)
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
            target = brew_pressure
            if flow_controller is not None:
                flow_controller.set_target(brew_data.get_flow_target())
                duty = flow_controller.update(brew_data.get_flow(), pressure)
                if duty is None:
                    print('%s_FLOW_OFF reason=scale silent' % label)
                    flow_controller = None
                    pressure_controller.update(pressure, target)
                else:
                    pressure_controller.apply_duty(duty, pressure)
            else:
                pressure_controller.update(pressure, target)
            brew_data.pressure_filtered = pressure_controller.filtered

            if utime.ticks_diff(now, last_pump_ratio_time) >= 1000:
                brew_data.set_pump_ratio(pump_ratio_calculator.get_ratio())
                last_pump_ratio_time = now

            if utime.ticks_diff(now, last_log) >= 100:
                last_log = now
                fsp = brew_data.get_flow_target() if flow_controller is not None else 0.0
                fsat = (1 if flow_controller.saturated else 0) if flow_controller is not None else 0
                print('%s %d %.1f %.1f %d %.2f %.1f %.1f %.1f %s fsp=%.2f fsat=%d' % (
                                                        label, elapsed_ms, pressure, brew_pressure,
                                                        pressure_controller.on, pressure_controller.duty,
                                                        brew_data.pressure_sensor.window_peak,
                                                        brew_data.weight_a, brew_data.weight_b,
                                                        weight_flow_log(brew_data), fsp, fsat))

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

# PCAL-KORJAUS 19.9.2026. The old run opened a fixed 10 s window at once and averaged seconds
# 5-10 whether or not the target had been reached, so a slow rise - air in the system, a cold
# machine, a tight restrictor - stored a point measured off a *rising* pressure, and the error
# always pointed the same way. The run is now in phases and the measurement window starts only
# after the pressure has settled (user, 19.9.2026).
# Measured 19.9.2026, closed circuit: ONE pump stroke is worth about 1 bar - at a 2 bar target the
# hold sawtoothed 1.05-2.82 bar, and at 8 bar every run tripped the old 1.0 bar overshoot limit at
# 9.0-9.25. The dose is the pump's, not the software's, so the criteria are on a 1 s average of the
# pressure rather than on the instantaneous reading: the sawtooth is real and it cancels in the mean,
# which is also what a damped reference gauge shows.
PCAL_COARSE_GAP = 1.5       # bar below the target where the full pump cycle stops. Room for one
                            # stroke (~1 bar) plus the reading's own lag: the closed circuit rises
                            # ~3.5 bar/s at full duty, so a late stop is a bar of overshoot that
                            # cannot be undone.
# Settled does NOT mean "at the target": one stroke is worth about a bar, so the hold lands wherever
# the last dose left it, and no band narrower than a dose can be reached on purpose. What the
# calibration needs is a *stable* pressure whose true value the reference gauge reads - the target is
# only where we aim. Settled therefore means the 1 s average stopped drifting, within reach of the aim.
PCAL_DRIFT = 0.15           # bar; allowed change of the 1 s average over one second
PCAL_REACH = 1.5            # bar; how far from the target the settled pressure may be
PCAL_DRIFT_MS = 2000        # ms over which the drift is measured. Not a quiet period: the circuit
                            # leaks back fast enough that holding a pressure needs a stroke about
                            # every window, so silence never comes (machine, 19.9.2026). A creep is
                            # told from a steady sawtooth by the length of the window instead - over
                            # 2 s a creep moves and a sawtooth does not.
PCAL_TOPUP = 0.2            # bar below the target where the fine phase fires one more stroke
PCAL_OVERSHOOT = 1.5        # bar above the target, on the average, that ends the run as a runaway
PCAL_AVG_TAU = 1.0          # s; low-pass that judges *settled* and *overshoot*
PCAL_FAST_TAU = 0.3         # s; low-pass that drives the pump. Faster than PCAL_AVG_TAU so it does
                            # not lag a full-duty rise, slower than the raw reading so a single
                            # noisy sample cannot fire a stroke - and one stroke is worth a whole
                            # bar, so a noise-triggered dose lands the hold a bar off target.
PCAL_SETTLE_MS = 1000       # time inside the band before the hold starts
PCAL_HOLD_MS = 30000        # measurement hold: the gauge is read by eye, so it is long
PCAL_STROKE_MS = 17         # one 60 Hz mains cycle: the smallest dose the pump can give
PCAL_TIMEOUT_MS = 60000     # approach timeout -> reason 'not settled', no point stored


async def pressure_calibration_run(brew_data, utime, asyncio, stage):
    RELAY_PUMP, RELAY_SOLENOID, RELAY_HEATER = brew_data.get_relays()
    SWITCH_BREW, SWITCH_WATER, SWITCH_STEAM = brew_data.get_switches()

    if stage == 'pre':
        target = brew_data.get_pre_infusion_pressure()
    else:
        target = brew_data.get_brew_pressure()

    window_ms = brew_data.get_pcal_window_ms()
    brew_data.pressure_calibration_begin(stage, target)
    brew_data.set_mode('pressure calibration')
    RELAY_HEATER.value(0)
    print('PCAL_START %s target=%.2f window=%d drift=%.2f reach=%.2f' % (
        stage, target, window_ms, PCAL_DRIFT, PCAL_REACH))

    from classes import PumpPressureController, PumpRatioCalculator
    hold_controller = None
    raw_sum = 0.0
    raw_n = 0
    p_min = 99.0
    p_max = -99.0
    p_avg = None
    p_fast = None
    p_ref = None
    ref_t = utime.ticks_ms()
    drift = 99.0
    last_avg = utime.ticks_ms()
    reason = ''
    start = utime.ticks_ms()
    settled_since = None
    hold_start = None
    last_stroke = utime.ticks_add(start, -window_ms)
    try:
        RELAY_SOLENOID.value(1)
        while True:
            now = utime.ticks_ms()
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
            dt = utime.ticks_diff(now, last_avg) / 1000.0
            last_avg = now
            if p_avg is None:
                p_avg = pressure
                p_fast = pressure
            else:
                a = dt / PCAL_AVG_TAU
                p_avg += (pressure - p_avg) * (1.0 if a > 1.0 else a)
                b = dt / PCAL_FAST_TAU
                p_fast += (pressure - p_fast) * (1.0 if b > 1.0 else b)

            if hold_start is None:
                if utime.ticks_diff(now, start) > PCAL_TIMEOUT_MS:
                    reason = 'not settled'
                    break
                # The pump only adds: in a closed circuit an overshoot is permanent, so it must not
                # start the measurement window - it ends the run instead (user, 19.9.2026).
                if p_avg > target + PCAL_OVERSHOOT or pressure > target + 2.5:
                    reason = 'overshoot %.2f bar' % (p_avg if p_avg > target + PCAL_OVERSHOOT else pressure)
                    break
                # The coarse switch reads the instantaneous pressure, not the average: at a full-duty
                # rise the 1 s low-pass lags by seconds, and a laggy stop overshoots by more than the
                # stroke it was meant to leave room for. The average is used only near the target,
                # where the sawtooth - not the lag - is what has to be filtered out.
                # Each timescale drives what it is good for. The coarse stop reads the fastest
                # value available: stopping a little early is harmless - the fine phase tops up -
                # while stopping late cannot be undone. Judging it on p_fast cost an
                # 'overpressure 12.0 bar' abort on the machine, 19.9.2026.
                if pressure < target - PCAL_COARSE_GAP:
                    RELAY_PUMP.value(1)                 # coarse phase: full cycle
                    settled_since = None
                else:
                    RELAY_PUMP.value(0)                 # fine phase: one stroke per window
                    # The top-up trigger is a control action and reads the instantaneous pressure:
                    # on the laggy average the fine phase keeps dosing while the average catches up,
                    # and each dose is a whole bar. The average judges *settled*; it does not drive.
                    if p_fast < target - PCAL_TOPUP and utime.ticks_diff(now, last_stroke) >= window_ms:
                        last_stroke = now
                        RELAY_PUMP.value(1)
                        await asyncio.sleep_ms(PCAL_STROKE_MS)
                        RELAY_PUMP.value(0)
                    if utime.ticks_diff(now, ref_t) >= PCAL_DRIFT_MS:
                        drift = 99.0 if p_ref is None else abs(p_avg - p_ref)
                        p_ref = p_avg
                        ref_t = now
                    if drift > PCAL_DRIFT or abs(p_avg - target) > PCAL_REACH:
                        settled_since = None
                    elif settled_since is None:
                        settled_since = now
                    elif utime.ticks_diff(now, settled_since) >= PCAL_SETTLE_MS:
                        hold_start = now
                        # The hold is handed to the ordinary pressure controller. Measured
                        # 19.9.2026: one stroke per 500 ms window swings 4.6 bar at an 8 bar target,
                        # while the controller's own time-proportional chopping swings 1.8 bar at
                        # 10 bar and 0.6 bar at 5 bar. The fine phase earns its place in the
                        # approach, where it prevents an overshoot that cannot be undone - not in
                        # the hold, where more frequent, smaller doses win.
                        hold_controller = PumpPressureController(
                            RELAY_PUMP, PumpRatioCalculator(utime, asyncio), utime, ff=0.05)
                        print('PCAL_SETTLED %s t=%.1f p=%.2f drift=%.2f' % (
                            stage, utime.ticks_diff(now, start) / 1000.0, p_avg, drift))
            else:
                hold_controller.update(pressure, target)
                raw_sum += brew_data.get_pressure_raw()
                raw_n += 1
                if pressure < p_min:
                    p_min = pressure
                if pressure > p_max:
                    p_max = pressure
                if utime.ticks_diff(now, hold_start) >= PCAL_HOLD_MS:
                    break

            await asyncio.sleep_ms(0)
    finally:
        if hold_controller is not None:
            hold_controller.stop()
        RELAY_PUMP.value(0)
        RELAY_SOLENOID.value(0)
        brew_data.set_mode('IDLE')

    if reason or raw_n == 0:
        print('PCAL_ABORT %s reason=%s' % (stage, reason or 'no samples'))
        brew_data.pressure_calibration_end(stage, None, reason)
    else:
        # p_min/p_max over the hold are the ripple measurement: one pump stroke is the smallest dose
        # there is, so this is what a longer window has to beat before it is worth anything.
        print('PCAL_END %s raw=%.3f n=%d p_min=%.2f p_max=%.2f window=%d reason=ok' % (
            stage, raw_sum / raw_n, raw_n, p_min, p_max, window_ms))
        brew_data.pressure_calibration_end(stage, raw_sum / raw_n, '')


async def pressure_zero_run(brew_data, utime, asyncio):
    # A resting reading is not a zero: with the solenoid closed the boiler's own thermal expansion
    # reaches ~14 bar at idle (functions.py running(), 17.9.2026), and the after-brew drain stops at
    # 1.5 bar *indicated* - a threshold read from the very calibration under test. The zero is taken
    # vented: heater off, solenoid cycled until the raw value stops moving (user, 19.9.2026).
    RELAY_PUMP, RELAY_SOLENOID, RELAY_HEATER = brew_data.get_relays()
    RELAY_HEATER.value(0)
    RELAY_PUMP.value(0)
    brew_data.set_mode('pressure zero')
    print('PZERO_START')
    prev = None
    stable = 0
    raw = 0.0
    cycles = 0
    try:
        for cycles in range(1, 31):
            RELAY_SOLENOID.value(1)
            await asyncio.sleep_ms(500)
            RELAY_SOLENOID.value(0)
            await asyncio.sleep_ms(500)
            for _ in range(8):
                brew_data.get_pressure_average(utime)
                await asyncio.sleep_ms(20)
            raw = brew_data.get_pressure_raw()
            if prev is not None and abs(raw - prev) < 0.02:
                stable += 1
            else:
                stable = 0
            prev = raw
            if stable >= 3:
                break
    finally:
        RELAY_SOLENOID.value(0)
        RELAY_PUMP.value(0)
        brew_data.set_mode('IDLE')

    sensor = brew_data.pressure_sensor
    offset = -sensor.gain * raw
    if stable < 3:
        print('PZERO_ABORT reason=not stable raw=%.3f cycles=%d' % (raw, cycles))
        return
    if not sensor.calibration_valid(sensor.gain, offset):
        print('PZERO_ABORT reason=rejected gain=%.4f offset=%.3f' % (sensor.gain, offset))
        return
    sensor.set_calibration(sensor.gain, offset)
    sensor.save_calibration()
    print('PZERO_OK raw=%.3f gain=%.4f offset=%.3f cycles=%d' % (raw, sensor.gain, offset, cycles))


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





