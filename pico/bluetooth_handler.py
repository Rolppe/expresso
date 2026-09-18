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
NOTIFY_DROP_ORDER = ('weight',)


def live_payload(brew_data):
    """The live telemetry packet. Cached values only: reading the sensors here blocked the asyncio
    loop for >= 90 ms every 200 ms (MAX31865 time.sleep + 20 ms pressure window, 17.9.2026)."""
    weight = brew_data.get_weight()
    if weight is not None:
        weight = round(weight, 1)      # 0.1 g is below the measured noise; the full float cost
                                       # 18 characters of a 240 B packet
    return {
        'boiler_temperature'         : brew_data.boiler_temperature,
        'pressure'                   : brew_data.pressure,
        'mode'                       : brew_data.get_mode(),
        'brew_temperature'           : brew_data.get_brew_temperature(),
        'pre_infusion_mode'          : brew_data.get_pre_infusion_mode(),
        'pressure_soft_release_mode' : brew_data.get_pressure_soft_release_mode(),
        'fast_heatup_mode'           : brew_data.get_fast_heatup_mode(),
        'pump_ratio'                 : brew_data.get_pump_ratio(),
        'weight'                     : weight
    }


def flow_payload(brew_data):
    """Flow gets a packet of its own, ~35 B (18.9.2026). It does not fit in the live packet: with the
    longest mode string that one is 250 B before flow and already has to drop weight to fit 240.
    Weight rides along so a consumer gets the pair from one packet even then. None when there is no
    flow to report - no scale, or samples too stale to differentiate."""
    flow = brew_data.get_flow()
    if flow is None:
        return None
    weight = brew_data.get_weight()
    return {'flow': round(flow, 2),        # the fit's own noise is 0.2 g/s, so 0.01 g/s is plenty
            'weight': None if weight is None else round(weight, 1)}


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

        self._connections = set()
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
            print("Connected - sending initial settings")
            asyncio.create_task(self.send_settings())   # asetukset heti yhteydessä

        elif event == 2:    # Disconnected
            conn_handle, _, _ = data
            self._connections.discard(conn_handle)
            self._advertise_pending = True

        elif event == 3:    # Write (komento)
            conn_handle, value_handle = data
            value = self._ble.gatts_read(value_handle)
            command = value.decode('utf-8').strip()

            print(f"Received: '{command}'")

            updated = handle_command(self.brew_data, command)

            if updated:
                asyncio.create_task(self.send_settings())   # asetukset heti muutoksen jälkeen


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
        flow = flow_payload(self.brew_data)
        if flow is not None:
            self._notify(flow)

        # Pressure calibration wizard state, only while it is in use
        if self.brew_data.pcal_state != 'idle':
            self._notify(self.brew_data.get_pressure_calibration_status())

        # Settings every 10th transmission (2 s) so the app's sliders stay in sync
        self._tx_count = getattr(self, '_tx_count', 0) + 1
        if self._tx_count % 10 == 0:
            await self.send_settings()

    def run_transmission(self):
        asyncio.create_task(self.send_data())


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