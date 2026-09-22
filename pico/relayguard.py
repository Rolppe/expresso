# ============================================================================
# RELAY GUARD — safety limits at the pump and heater relays (EXPRESSO-TURVA-TOIMILAITE, 22.9.2026)
# ============================================================================
#
# Why (paketit/TURVAKATO.md, kohta 2): every safety limit used to live inside one command's
# function, so a new command could skip a limit by forgetting it (phold 19.9.2026: no tray limit;
# mcal and the psweep trim: no overpressure limit). Here the limits sit at the actuator instead.
# BrewData.get_relays() hands out GuardedRelay objects, so every RELAY_PUMP.value(1) and
# RELAY_HEATER.value(1) in the firmware passes allow() whatever the path, including paths that do
# not exist yet. testit/turva_toimilaite_smoke.py checks that no path reaches the raw pins.
#
# Limits are a last line, not the paths' own limits: each is looser than every path's own
# (overpressure 13.0 bar = the highest path limit; run time 180 s > phold 120 s and pgap 120 s),
# so no existing run stops earlier than before. They hold on every path, the user's own included:
#   - dev_safe                    -> pump and heater off
#   - pressure > 13.0 bar         -> pump off (3 polls in a row, ADC read by the guard itself)
#   - pump run > 180 s            -> pump off until the path stops asking for 5 s
#   - boiler >= 160 C (sensor fault reads 200) or reading older than 10 s -> heater off
# Sensor plausibility (TURVAKATO kohta 5, 22.9.2026), same guard:
#   - pressure sensor reads far below 0 bar (raw < -1.5 bar: an open or shorted sensor reads about
#     -3.5) 3 polls in a row -> pump off; every pressure limit is blind without the sensor
#   - heater on for 120 s of on-time while the boiler is > 5 C under its target and the pump is
#     off, and the reading rose less than 2 C -> heater off until restart (a sensor off the boiler
#     reads a plausible room temperature and would heat without end)
# Not detectable here: a pressure sensor stuck at a plausible 0 bar. Hot water and a flush with no
# puck also stay near 0 bar with the pump on, so "no pressure while pumping" is not a fault.
# The drip-tray weight is NOT here on purpose (user, 19.9.2026): the tray limit applies to test
# commands only, and a real shot has a cup on the scale. The tray check during test runs lives in
# functions.tray_guard_poll().
#
# Continuous runs (hot water holds the pump on with one value(1)) are covered by poll(), run from a
# machine.Timer every POLL_MS. Timer callbacks are scheduled between bytecodes, so poll() runs even
# inside the busy 1 kHz loops of pstep/pgap/plen that never yield to asyncio. It reads only the ADC
# and brew_data fields (no SPI, no HX711), so it cannot collide with a read in progress.
# ============================================================================

PRESSURE_MAX_BAR   = 13.0     # highest path limit (run_shot); pcal 12.0, test commands 11.0
PRESSURE_TRIP_N    = 3        # consecutive polls over the limit: one raw burst can be a stroke peak
PUMP_RUN_MAX_MS    = 180000   # longest legit run: phold 120 s, pgap cap 120 s, a shot ~60 s
PUMP_RUN_GAP_MS    = 5000     # pump off (and not asked for) this long ends a run; backflush pauses 10 s
HEATER_TEMP_MAX_C  = 160.0    # setpoint cap is 150 C (classes.SETPOINT_MAX_C); sensor fault reads 200
HEATER_TEMP_STALE_MS = 10000  # run_shot reads every 2 s, the main loop every pass
PRESSURE_RAW_MIN_BAR = -1.5   # uncalibrated; 0 bar reads ~0, an open sensor ~-3.5
HEATER_NORISE_ON_MS  = 120000 # heater on-time allowed without a rise, far under target
HEATER_NORISE_RISE_C = 2.0
HEATER_NORISE_BELOW_C = 5.0   # counted only this far under target: the thermostat then heats
                              # >= 55 % of the time (heat_cycler), so the boiler must warm up
POLL_MS            = 100      # guard poll period; 20 ms would jitter the 1 kHz capture loops


class RelayGuard:
    def __init__(self, brew_data, utime, read_pressure=None):
        self.bd = brew_data
        self.utime = utime
        # read_pressure() -> bar, read straight from the ADC; None in host tests that set pressure
        self.read_pressure = read_pressure
        self.relays = {}
        self.block = {}           # name -> reason of the trip in force (log once per trip)
        self.over_n = 0
        self.sensor_bad_n = 0
        self.pressure = 0.0
        self.raw_bar = 0.0
        self.heat_on_ms = 0           # heater on-time in the current no-rise window
        self.heat_min_c = None        # lowest reading in that window
        self.heat_dead = False        # latched until restart
        self.last_poll = None
        self.pump_run_start = None
        self.pump_last_want = None    # last time the pump was on or asked to be
        self.trips = []           # (ms, name, reason) for the log; the latest few only
        self.timer = None

    # ----- limits -------------------------------------------------------------

    def _pump_reason(self, now):
        if self.bd.dev_safe:
            return 'devsafe'
        if self.over_n >= PRESSURE_TRIP_N:
            return 'overpressure'
        if self.sensor_bad_n >= PRESSURE_TRIP_N:
            return 'pressuresensor'
        if self.pump_run_start is not None and \
                self.utime.ticks_diff(now, self.pump_run_start) > PUMP_RUN_MAX_MS:
            return 'runtime'
        return None

    def _heater_reason(self, now):
        if self.bd.dev_safe:
            return 'devsafe'
        if self.heat_dead:
            return 'norise'
        t = self.bd.boiler_temperature
        if t is None or t >= HEATER_TEMP_MAX_C:
            return 'overtemp'
        ms = getattr(self.bd, 'boiler_temperature_ms', None)
        if ms is None or self.utime.ticks_diff(now, ms) > HEATER_TEMP_STALE_MS:
            return 'tempstale'
        return None

    def _reason(self, name, now):
        if name == 'pump':
            return self._pump_reason(now)
        if name == 'heater':
            return self._heater_reason(now)
        return None

    # ----- relay side ---------------------------------------------------------

    def allow(self, name):
        """Called by GuardedRelay.value(1). Returns True when the relay may switch on."""
        now = self.utime.ticks_ms()
        if name == 'pump':
            # A run starts when the pump comes on after a PUMP_RUN_GAP_MS pause. Refused requests
            # count as wanting the pump, so a path that keeps asking after a runtime trip (the
            # switch still held) does not get a fresh 180 s by being refused for 5 s.
            if self.pump_last_want is None or \
                    self.utime.ticks_diff(now, self.pump_last_want) >= PUMP_RUN_GAP_MS:
                self.pump_run_start = now
            self.pump_last_want = now
        r = self._reason(name, now)
        if r:
            self._trip(name, r, now)
            return False
        return True

    def _trip(self, name, reason, now):
        relay = self.relays.get(name)
        if relay is not None:
            relay.pin.value(0)
        if self.block.get(name) != reason:
            self.block[name] = reason
            self.trips.append((now, name, reason))
            if len(self.trips) > 8:
                self.trips.pop(0)
            try:
                print('GUARD_TRIP %s reason=%s bar=%.1f temp=%s' % (
                    name, reason, self.pressure, self.bd.boiler_temperature))
            except Exception:
                pass

    # ----- periodic -----------------------------------------------------------

    def poll(self, *_):
        """Timer callback (and host tests). Forces a relay off while its limit is hit."""
        try:
            now = self.utime.ticks_ms()
            if self.read_pressure is not None:
                self.pressure, self.raw_bar = self.read_pressure()
            else:
                self.pressure = self.raw_bar = getattr(self.bd, 'pressure', 0.0) or 0.0
            self.over_n = self.over_n + 1 if self.pressure > PRESSURE_MAX_BAR else 0
            self.sensor_bad_n = self.sensor_bad_n + 1 if self.raw_bar < PRESSURE_RAW_MIN_BAR else 0
            pump = self.relays.get('pump')
            pump_on = pump is not None and pump.pin.value()
            if pump_on:
                self.pump_last_want = now
            dt = 0 if self.last_poll is None else self.utime.ticks_diff(now, self.last_poll)
            self.last_poll = now
            self._norise(now, dt, pump_on)
            for name, relay in self.relays.items():
                r = self._reason(name, now)
                if r is None:
                    self.block.pop(name, None)
                    continue
                if relay.pin.value():
                    self._trip(name, r, now)
        except Exception as e:
            # A guard that cannot check fails safe: everything it guards goes off
            for relay in self.relays.values():
                relay.pin.value(0)
            self.block['all'] = 'guarderror'
            try:
                print('GUARD_TRIP all reason=guarderror %s' % e)
            except Exception:
                pass

    def _norise(self, now, dt, pump_on):
        heater = self.relays.get('heater')
        t = self.bd.boiler_temperature
        try:
            target = self.bd.get_target_temperature()
        except Exception:
            target = None
        if heater is None or t is None or target is None or pump_on or \
                t > target - HEATER_NORISE_BELOW_C:
            # Water flowing in cools the boiler, and near the target the thermostat heats little:
            # neither is a no-rise fault. Start a new window.
            self.heat_on_ms = 0
            self.heat_min_c = None
            return
        if self.heat_min_c is None or t < self.heat_min_c:
            self.heat_min_c = t
        if t - self.heat_min_c >= HEATER_NORISE_RISE_C:
            self.heat_on_ms = 0
            self.heat_min_c = t
            return
        if heater.pin.value():
            self.heat_on_ms += dt
        if self.heat_on_ms >= HEATER_NORISE_ON_MS:
            self.heat_dead = True

    def start(self):
        from machine import Timer
        self.timer = Timer(-1, mode=Timer.PERIODIC, period=POLL_MS, callback=self.poll)

    def status(self):
        return ' '.join('%s=%s' % kv for kv in self.block.items()) or 'ok'


class GuardedRelay:
    """Same interface as machine.Pin for the calls the firmware makes: value() and value(v).
    value(0) always passes; value(1) passes only when the guard allows it."""
    def __init__(self, pin, guard, name):
        self.pin = pin
        self.guard = guard
        self.name = name
        guard.relays[name] = self

    def value(self, v=None):
        if v is None:
            return self.pin.value()
        if not v:
            self.pin.value(0)
            return
        if 'all' in self.guard.block or not self.guard.allow(self.name):
            self.pin.value(0)
            return
        self.pin.value(1)

    def on(self):
        self.value(1)

    def off(self):
        self.value(0)
