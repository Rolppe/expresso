import bluetooth
from micropython import const
import json
import asyncio
from commands import handle_command

# ============================================================================
# CONSTANTS
# ============================================================================
_ADV_TYPE_FLAGS = const(0x01)
_ADV_TYPE_NAME = const(0x09)
_ADV_TYPE_UUID16_COMPLETE = const(0x03)
_ADV_TYPE_APPEARANCE = const(0x19)

_CENTRAL_UUID = bluetooth.UUID('0000180a-0000-1000-8000-00805f9b34fb')
_DATA_CHAR_UUID = bluetooth.UUID('00002a29-0000-1000-8000-00805f9b34fb')
_COMMAND_CHAR_UUID = bluetooth.UUID('00002a2a-0000-1000-8000-00805f9b34fb')


MAX_NOTIFY = 240
# Dropped in this order when a packet does not fit: the newest and least critical field first.
# Adding weight pushed the longest mode string to 246 B and the whole packet - pressure,
# temperature, mode - was lost exactly during a shot (18.9.2026).
NOTIFY_DROP_ORDER = ()     # weight moved to scale_payload (V-210, 20.10.2026): nothing left to drop

# Brew log multipack (EXPRESSO-UUTTOLOKI, 5.10.2026), the August firmware's protocol unchanged for the app:
# meta (header + events) -> samples parts of BREW_LOG_CHUNK_ROWS rows -> end, one frame per transmission
# tick. A frame longer than one notify goes out in pieces of at most MAX_NOTIFY B and ends in a newline;
# the app joins pieces until the JSON closes. No other notify may go out between a frame's pieces, so live
# telemetry and settings pause for the whole multipack. The pending log stays until brew_log:ack.
BREW_LOG_CHUNK_ROWS = 20
NOTIFY_CHUNK_GAP_MS = 12        # between pieces of one frame (August: tighter dropped pieces mid-multipack)
BREW_LOG_STEP_FAIL_MAX = 8      # failed meta sends before the multipack waits for the next request


def brew_log_frame(log, step):
    """Frame <step> of the multipack as a dict: 0 = meta, 1..n_parts = samples, n_parts + 1 = end."""
    samples = log['samples']
    n = len(samples)
    n_parts = (n + BREW_LOG_CHUNK_ROWS - 1) // BREW_LOG_CHUNK_ROWS
    if step == 0:
        meta = {'type': 'brew_log', 'part': 'meta', 'v': log.get('v', 3), 'id': log['id'],
                'sample_hz': log.get('sample_hz', 10), 'duration_ms': log.get('duration_ms', 0),
                'n_samples': n, 'n_events': len(log['events']), 'n_parts': n_parts,
                'truncated': log.get('truncated', False), 'scale_at_end_g': log.get('scale_at_end_g', 0),
                'events': log['events']}
        if log.get('scale_meta') is not None:
            meta['scale_meta'] = log['scale_meta']
        return meta
    if step <= n_parts:
        a = (step - 1) * BREW_LOG_CHUNK_ROWS
        return {'type': 'brew_log', 'part': 'samples', 'id': log['id'], 'i': step - 1, 'of': n_parts,
                'rows': samples[a:a + BREW_LOG_CHUNK_ROWS]}
    return {'type': 'brew_log', 'part': 'end', 'id': log['id'], 'n_samples': n}


def brew_log_steps(log):
    return (len(log['samples']) + BREW_LOG_CHUNK_ROWS - 1) // BREW_LOG_CHUNK_ROWS + 2


def frame_pieces(json_data, chunk):
    """One multipack frame as notify pieces of at most <chunk> bytes, newline-terminated."""
    raw = (json_data + '\n').encode('utf-8')
    return [raw[i:i + chunk] for i in range(0, len(raw), chunk)]


def live_payload(brew_data):
    """The live telemetry packet. Cached values only: reading the sensors here blocked the asyncio
    loop for >= 90 ms every 200 ms (MAX31865 time.sleep + 20 ms pressure window, 17.9.2026)."""
    data = {
        'boiler_temperature'         : brew_data.boiler_temperature,
        'pressure'                   : brew_data.pressure,
        'mode'                       : brew_data.get_mode(),
        'brew_temperature'           : brew_data.get_brew_temperature(),
        'pre_infusion_mode'          : brew_data.get_pre_infusion_mode(),
        'pressure_soft_release_mode' : brew_data.get_pressure_soft_release_mode(),
        'fast_heatup_mode'           : brew_data.get_fast_heatup_mode(),
        'pump_ratio'                 : brew_data.get_pump_ratio(),
    }
    if brew_data.standby:
        # VALMIUSTILA (5.10.2026): the key rides only while standby holds - standby is IDLE-only, so the
        # packet carries the shortest mode string and stays within 240 B; a live packet without it means off.
        data['standby'] = True
    return data


def scale_payload(brew_data):
    """Weight and flow in the app's keys (V-210, 20.10.2026: the firmware sent `weight`/`flow`, the app reads
    `weight_g`/`weight_abs_g`/`flow_g_s`, so weight, flow, the tray check and auto-tare never worked). Own
    packet, ~70 B: it never fit in the live one with the longest mode string. weight_abs_g is the calibrated
    absolute mass (tray check: |abs| < 200 g = no tray), weight_g the same minus the app's tare. A stale flow
    is 0.0, not null: the app keeps its last value on null. None without a scale or a reading."""
    if getattr(brew_data, 'tray_scale', None) is None:
        return None
    weight = brew_data.get_weight()
    if weight is None:
        return None
    flow = brew_data.get_flow()
    return {'weight_g': round(weight - (getattr(brew_data, 'tare_abs_g', None) or 0.0), 1),   # 0.1 g is below the noise
            'weight_abs_g': round(weight, 1),
            'flow_g_s': 0.0 if flow is None else round(flow, 2)}   # the fit's own noise is 0.2 g/s


def trim_payload(data, json_module, max_len=MAX_NOTIFY):
    """JSON of the packet, dropping fields in NOTIFY_DROP_ORDER until it fits. None when even the
    trimmed packet is too long - the caller must say so rather than send something a central cannot
    receive."""
    json_data = json_module.dumps(data)
    for field in NOTIFY_DROP_ORDER:
        if len(json_data) <= max_len:
            return json_data
        if field in data:
            data = dict(data)
            del data[field]
            json_data = json_module.dumps(data)
    return json_data if len(json_data) <= max_len else None


class BLEHandler:
    def __init__(self, ble, brew_data):
        self.brew_data = brew_data
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(self._irq)

        # GATT-palvelut
        ((self._handle_tx, self._handle_rx),) = self._ble.gatts_register_services((
            (_CENTRAL_UUID, (
                (_DATA_CHAR_UUID, bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY),
                (_COMMAND_CHAR_UUID, bluetooth.FLAG_WRITE),
            )),
        ))
        # Command writes up to 128 B (EXPRESSO-WIFI-APPI vaihe 0): the default 20 B buffer cut longer
        # commands such as cal:quick:<g> or pcal:m:<stage>:<bar>; serial accepts 80 characters
        try:
            self._ble.gatts_set_buffer(self._handle_rx, 128)
        except Exception as e:
            print('BLE rx buffer %r' % (e,))

        self._connections = set()
        self._mtus = {}             # conn_handle -> ATT MTU from _IRQ_MTU_EXCHANGED (default 23)
        self._brew_step = None      # next multipack frame; None = no multipack in flight
        self._brew_lid = None
        self._brew_fails = 0
        self._brew_busy = False
        self._payload = BLEHandler._advertising_payload(
            name='EspressoPico',
            services=[_CENTRAL_UUID]
        )

        self._advertise_pending = True
        self._advertise()


    # ====================== ASETUSTEN LÄHETTÄMINEN ======================
    # One notify must stay within one BLE link-layer packet (251 B): a 309 B telemetry packet
    # hung the Pico 2 W BLE stack within seconds (17.9.2026). Oversize packets are dropped.
    MAX_NOTIFY = 240

    def _notify(self, data):
        if self._brew_step is not None:
            return      # a multipack is in flight: a packet between its pieces corrupts the app's frame
        json_data = trim_payload(data, json, self.MAX_NOTIFY)
        if json_data is None:
            print('notify dropped: %d B > %d' % (len(json.dumps(data)), self.MAX_NOTIFY))
            return
        for conn_handle in self._connections:
            self._ble.gatts_notify(conn_handle, self._handle_tx, json_data)

    async def send_settings(self):
        """Asetukset kahtena pienenä pakettina (yhteyden muodostuessa, muutoksessa ja 2 s välein)"""
        if not self._connections:
            return
        brew_temperature = self.brew_data.get_brew_temperature()
        self._notify({
            'brew_temperature': brew_temperature,
            'pre_infusion_mode': self.brew_data.get_pre_infusion_mode(),
            'pressure_soft_release_mode': self.brew_data.get_pressure_soft_release_mode(),
            'fast_heatup_mode': self.brew_data.get_fast_heatup_mode()
        })
        self._notify({
            'brew_temperature': brew_temperature,
            'brew_pressure': self.brew_data.get_brew_pressure(),
            'pre_infusion_pressure': self.brew_data.get_pre_infusion_pressure(),
            'pre_infusion_time': self.brew_data.get_pre_infusion_time(),
            'pressure_soft_release_time': self.brew_data.get_pressure_soft_release_time()
        })


# ====================== REAALIAIKAISTEN TIETOJEN LÄHETTÄMINEN ======================

    async def send_data(self):
        """Lähettää jatkuvasti reaaliaikaiset mittaustiedot"""
        if not self._connections:
            return

        data = {
            'boiler_temperature': self.brew_data.get_boiler_temperature(),
            'pressure': self.brew_data.get_pressure(),
            'mode': self.brew_data.get_mode(),
            'pump_ratio': 0   # voit lisätä myöhemmin jos tarvitset
        }

        json_data = json.dumps(data)
        for conn_handle in self._connections:
            self._ble.gatts_notify(conn_handle, self._handle_tx, json_data)

    # ====================== IRQ (komentojen käsittely) ======================
    def _irq(self, event, data):
        if event == 1:      # Connected
            conn_handle, _, _ = data
            self._connections.add(conn_handle)
            self._mtus[conn_handle] = 23
            print("Connected - sending initial settings")
            asyncio.create_task(self.send_settings())   # asetukset heti yhteydessä
            # A shot that finished while the phone was away goes out from its meta again (UUTTOLOKI)
            if self.brew_data.pending_brew_log is not None:
                self.brew_data.brew_log_tx_reset = True
                self.brew_data.brew_log_send_requested = True

        elif event == 2:    # Disconnected
            conn_handle, _, _ = data
            self._connections.discard(conn_handle)
            self._mtus.pop(conn_handle, None)
            self._advertise_pending = True

        elif event == 21:   # _IRQ_MTU_EXCHANGED: the phone's MTU sets the multipack piece size
            conn_handle, mtu = data
            self._mtus[conn_handle] = mtu

        elif event == 3:    # Write (komento)
            conn_handle, value_handle = data
            value = self._ble.gatts_read(value_handle)
            command = value.decode('utf-8').strip()

            print(f"Received: '{command}'")

            updated = handle_command(self.brew_data, command)

            if updated or self.brew_data.settings_requested:
                self.brew_data.settings_requested = False
                asyncio.create_task(self.send_settings())   # asetukset heti muutoksen jälkeen / sync


    def advertise_if_needed(self):
        if self._advertise_pending:
            self._advertise_pending = False
            self._advertise()

    def _advertise(self, interval_us=500000):
        self._ble.gap_advertise(None)
        self._ble.gap_advertise(interval_us, adv_data=self._payload)

    # ====================== DATAN LÄHETTÄMINEN ======================
    async def send_data(self):
        """Lähettää reaaliaikaisen datan kaikille yhteyksissä oleville laitteille"""
        if not self._connections:
            return

        self._notify(live_payload(self.brew_data))
        sp = scale_payload(self.brew_data)
        if sp is not None:
            self._notify(sp)

        # Scale calibration wizard state (scalecal.py), only while it is in use
        sc = getattr(self.brew_data, 'scale_cal', None)
        if sc is not None and sc.active():
            self._notify(sc.status())

        # Pressure calibration wizard state, only while it is in use
        if self.brew_data.pcal_state != 'idle':
            self._notify(self.brew_data.get_pressure_calibration_status())

        # Settings every 10th transmission (2 s) so the app's sliders stay in sync
        self._tx_count = getattr(self, '_tx_count', 0) + 1
        if self._tx_count % 10 == 0:
            await self.send_settings()

    def run_transmission(self):
        bd = self.brew_data
        if bd.brew_log_send_requested and bd.pending_brew_log is not None:
            if not self._brew_busy:
                self._brew_busy = True
                asyncio.create_task(self.send_brew_log_step())
            return
        if self._brew_step is not None:
            if bd.pending_brew_log is None:
                self._brew_step = None      # acked mid-multipack: live telemetry resumes
            return
        asyncio.create_task(self.send_data())

    def _chunk(self, conn_handle):
        return max(20, min(self.MAX_NOTIFY, self._mtus.get(conn_handle, 23) - 3))

    async def _notify_frame(self, json_data):
        """One multipack frame to every connection; raises if none got it, so the step is not advanced."""
        ok = 0
        err = None
        for conn_handle in list(self._connections):
            try:
                pieces = frame_pieces(json_data, self._chunk(conn_handle))
                for i, piece in enumerate(pieces):
                    if i:
                        await asyncio.sleep_ms(NOTIFY_CHUNK_GAP_MS)
                    self._ble.gatts_notify(conn_handle, self._handle_tx, piece)
                ok += 1
            except Exception as e:
                err = e
        if not ok:
            raise err if err is not None else OSError('brew_log: no connection')

    async def send_brew_log_step(self):
        """Send one multipack frame. A failed send repeats the same frame on the next tick; the step only
        advances after a successful notify (August: samples without meta made the app reject the log)."""
        bd = self.brew_data
        try:
            log = bd.pending_brew_log
            if log is None:
                bd.brew_log_send_requested = False
                self._brew_step = None
                return
            if bd.brew_log_tx_reset or self._brew_step is None or self._brew_lid != log['id']:
                bd.brew_log_tx_reset = False
                self._brew_step = 0
                self._brew_lid = log['id']
                self._brew_fails = 0
                print('BREW_LOG tx start id=%s n=%d steps=%d' % (log['id'], len(log['samples']), brew_log_steps(log)))
            if not self._connections:
                return      # keep the request: a reconnect resends from meta
            step = self._brew_step
            try:
                import gc
                gc.collect()
            except Exception:
                pass
            raw = json.dumps(brew_log_frame(log, step))
            try:
                await self._notify_frame(raw)
            except Exception as e:
                self._brew_fails += 1
                print('BREW_LOG tx fail step=%d n=%d: %r' % (step, self._brew_fails, e))
                if step == 0 and self._brew_fails >= BREW_LOG_STEP_FAIL_MAX:
                    bd.brew_log_send_requested = False      # brew_log? or a reconnect asks again
                    self._brew_step = None
                return
            self._brew_fails = 0
            if step + 1 >= brew_log_steps(log):
                print('BREW_LOG tx done id=%s' % log['id'])
                bd.brew_log_send_requested = False
                self._brew_step = None
            else:
                self._brew_step = step + 1
        finally:
            self._brew_busy = False


    @staticmethod
    def _advertising_payload(limited_disc=False, br_edr=False, name=None, services=None, appearance=0):
        payload = bytearray()
        def _append(adv_type, value):
            nonlocal payload
            payload += bytearray([len(value) + 1, adv_type]) + value

        _append(_ADV_TYPE_FLAGS, bytearray([(0x01 if limited_disc else 0x02) + (0x18 if br_edr else 0x04)]))
        if name:
            _append(_ADV_TYPE_NAME, name.encode())
        if services:
            for uuid in services:
                b = bytes(uuid)
                if len(b) == 2:
                    _append(_ADV_TYPE_UUID16_COMPLETE, b)
        if appearance:
            _append(_ADV_TYPE_APPEARANCE, bytearray([appearance & 0xFF, appearance >> 8]))
        return payload