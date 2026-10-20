# ============================================================================
# BREW SESSION LOGGER (on-device, RAM only) — EXPRESSO-UUTTOLOKI 5.10.2026
# ============================================================================
# Port of the August 2026 brew_logger (phone files/firmware/brew_logger.py, 10.8.2026) to the current
# firmware, so every real shot reaches the app's brew_shots.jsonl again (KAYTTAJAN-TIEDOT luku 7). The
# app is unchanged, so the export keeps the August v3 format byte for byte:
#   row = [t_ms, T_x10, P_x100, F_x100, hx_a_raw, hx_b_raw, W_x10, flags], flags bit0 pump, bit1 heater
#   events = [[name, t_ms], ...], session_start / phase_<NAME> / log_stop / session_end
# Differences from August, all for this firmware:
# - No pump edge events: the phase-controlled pump switches every mains cycle, which would put thousands
#   of edges into the meta JSON (August already dropped heater edges for that reason, L6 MemoryError).
#   The relay state stays in every row's flags. Events are capped at MAX_EVENTS.
# - Sampling runs from the BLE task (brew_log_service), not inside the shot loops, so the approved control
#   loops keep their timing. Rows carry their own t_ms, so a missed 100 ms slot is a gap, not a shift.
# - export_dict hands its lists over instead of deep-copying them: the copy doubled the peak heap.
# - print instead of debug_log, which this firmware does not have.

MAX_SESSION_MS = 65000      # hard cap on a session (pre + brew + soft release)
MIN_SESSION_MS = 15000      # shorter = accidental tap: discarded, no BLE log, no app prompt
SAMPLE_INTERVAL_MS = 100    # 10 Hz
MAX_EVENTS = 40
# diagnet.DiagNet or None (EXPRESSO-DIAGNET 20.10.2026): main.py sets it; every row also goes to the network
SINK = None

_ST_IDLE = 0
_ST_RECORDING = 1
_ST_READY = 2

# brew_data.mode -> the August phase names the app knows
_PHASES = (
    ('pre-infusion', 'PRE_INFUSION'),
    ('brew loop', 'BREW'),
    ('soft pressure release', 'SOFT_RELEASE'),
)


def phase_of(mode):
    for prefix, name in _PHASES:
        if mode.startswith(prefix):
            return name
    return None


class BrewSessionLogger:
    def __init__(self, utime):
        self.utime = utime
        self._state = _ST_IDLE
        self._t0 = 0
        self._next_sample = 0
        self._samples = []
        self._events = []
        self._truncated = False
        self._id = 0
        self._phase = None
        self._w0 = None
        self._scale_at_end_g = 0.0
        self._scale_meta = None

    def start(self, now, weight_g=None, scale_meta=None):
        """New shot (brew switch on). A new shot replaces an unacked one."""
        self._id = (self._id + 1) & 0xFFFF or 1
        self._t0 = now
        self._samples = []
        self._events = [['session_start', 0]]
        self._truncated = False
        self._next_sample = now
        self._phase = None
        self._w0 = weight_g     # session tare: W in the rows is weight minus this
        self._scale_at_end_g = 0.0
        self._scale_meta = scale_meta
        self._state = _ST_RECORDING
        print('BREW_LOG start id=%d v=3' % self._id)
        if SINK is not None:
            SINK.shot_start()

    def _event(self, name, t_ms):
        if len(self._events) < MAX_EVENTS:
            self._events.append([name, t_ms])

    def session_weight(self, weight_g):
        if weight_g is None:
            return 0.0
        return weight_g - (self._w0 if self._w0 is not None else weight_g)

    def tick(self, now, temp_c, press_bar, flow_g_s, weight_g, pump_on, heater_on, hx_a=0, hx_b=0, mode=None):
        """Call often while a shot runs; samples at 10 Hz. Returns True when the session just became READY
        (MAX_SESSION_MS reached)."""
        if self._state != _ST_RECORDING:
            return False
        if self._w0 is None and weight_g is not None:
            self._w0 = weight_g
        t_ms = self._rel_ms(now)
        if t_ms >= MAX_SESSION_MS:
            self._truncated = True
            return self._finalize(now, weight_g, 'max')
        if mode is not None:
            phase = phase_of(mode)
            if phase is not None and phase != self._phase:
                self._phase = phase
                self._event('phase_' + phase, t_ms)
        # Slots on a 100 ms grid from the start, not 100 ms after the last sample: called every ~30 ms,
        # the latter gave 120 ms rows (8.3 Hz, smoke 5.10.2026). A late call takes the slot it is in and
        # skips the ones it missed.
        if self.utime.ticks_diff(now, self._next_sample) >= 0:
            self._next_sample = self.utime.ticks_add(self._next_sample, SAMPLE_INTERVAL_MS)
            while self.utime.ticks_diff(now, self._next_sample) >= 0:
                self._next_sample = self.utime.ticks_add(self._next_sample, SAMPLE_INTERVAL_MS)
            row = [
                t_ms,
                int(round((temp_c or 0.0) * 10.0)),
                int(round((press_bar or 0.0) * 100.0)),
                int(round((flow_g_s or 0.0) * 100.0)),
                int(hx_a),
                int(hx_b),
                int(round(self.session_weight(weight_g) * 10.0)),
                (1 if pump_on else 0) | ((1 if heater_on else 0) << 1),
            ]
            self._samples.append(row)
            if SINK is not None:
                SINK.sample(row)
        return False

    def end_session(self, now, weight_g, reason='spr_end'):
        """Stop logging (before the solenoid dumps the group). True if the session became READY,
        False if it was discarded as too short or was not recording."""
        if self._state != _ST_RECORDING:
            return False
        t_ms = self._rel_ms(now)
        self._event('log_stop', t_ms)
        self._event('log_stop_' + reason, t_ms)
        return self._finalize(now, weight_g, reason)

    def is_active(self):
        return self._state == _ST_RECORDING

    def is_ready(self):
        return self._state == _ST_READY

    def session_id(self):
        return self._id

    def export_dict(self):
        """The brew_log body for BLE. Hands the sample and event lists over and returns to IDLE: the log
        then lives only in brew_data.pending_brew_log until the app acks it."""
        samples, events = self._samples, self._events
        out = {
            'type': 'brew_log',
            'v': 3,
            'id': self._id,
            'sample_hz': 10,
            'duration_ms': samples[-1][0] if samples else 0,
            'n_samples': len(samples),
            'n_events': len(events),
            'truncated': self._truncated,
            'scale_at_end_g': round(self._scale_at_end_g, 2),
            'samples': samples,
            'events': events,
        }
        if self._scale_meta is not None:
            out['scale_meta'] = self._scale_meta
        self.abandon()
        return out

    def abandon(self):
        if SINK is not None and self._state == _ST_RECORDING:
            SINK.shot_end('abandon', len(self._samples))
        self._samples = []
        self._events = []
        self._scale_meta = None
        self._state = _ST_IDLE

    def _rel_ms(self, now):
        d = self.utime.ticks_diff(now, self._t0)
        return d if d > 0 else 0

    def _finalize(self, now, weight_g, reason):
        t_ms = self._rel_ms(now)
        if SINK is not None:
            SINK.shot_end(reason, len(self._samples))
        if t_ms < MIN_SESSION_MS or not self._samples:
            print('BREW_LOG discard id=%d t=%d < %d reason=%s' % (self._id, t_ms, MIN_SESSION_MS, reason))
            self._state = _ST_IDLE      # shot_end already went out above
            self.abandon()
            return False
        self._event('session_end', t_ms)
        self._scale_at_end_g = self.session_weight(weight_g)
        self._state = _ST_READY
        print('BREW_LOG ready id=%d n=%d ev=%d trunc=%d end_w=%.1f reason=%s' % (
            self._id, len(self._samples), len(self._events), 1 if self._truncated else 0,
            self._scale_at_end_g, reason))
        return True


def brew_log_service(brew_data, utime):
    """One logger step from the BLE task: a sample while a shot records, and the hand-over to the BLE
    multipack once the session is READY. Never raises - the log must not take a task down with it."""
    log = getattr(brew_data, 'brew_logger', None)
    if log is None:
        return
    try:
        if log.is_active():
            hx_a = hx_b = 0
            scale = getattr(brew_data, 'tray_scale', None)
            if scale is not None:
                hx_a, hx_b = scale.raw_a, scale.raw_b
            log.tick(utime.ticks_ms(), brew_data.boiler_temperature, brew_data.pressure, brew_data.flow,
                     brew_data.weight, brew_data.RELAY_PUMP.value(), brew_data.RELAY_HEATER.value(),
                     hx_a, hx_b, brew_data.mode)
        if log.is_ready():
            brew_data.pending_brew_log = log.export_dict()
            brew_data.brew_log_tx_reset = True
            brew_data.brew_log_send_requested = True
    except Exception as e:
        print('BREW_LOG service error: %r' % (e,))
        try:
            log.abandon()
        except Exception:
            pass
