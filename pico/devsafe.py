# ============================================================================
# DEVSAFE — relays down before any development operation, hardware watchdog
# ============================================================================
#
# Development runs without anyone at the machine (17.9.2026). Two rules:
#   1. Every stop of the firmware (Ctrl-C, crash, main exit) and every development operation
#      (flash, file read, REPL) starts with relays_off() and a read-back of the relay pins.
#      main.py wraps asyncio.run() in try/finally; tools call enter() right after Ctrl-C.
#   2. A hardware watchdog (8 s) resets a hung Pico (e.g. the 17.9.2026 BLE stack hang that needed
#      a power cycle). The firmware feeds it once a second; tools holding the REPL call feed().
#      A watchdog reset clears the watchdog, and boot drives the relays off before anything else.
# ============================================================================

from machine import Pin, WDT

RELAY_PINS = (11, 12, 13)      # RELAY_PUMP, RELAY_SOLENOID, RELAY_HEATER (preset.PINS)
WDT_TIMEOUT_MS = 8000          # RP2350 maximum is ~8.3 s

_wdt = None


def relays_off():
    for n in RELAY_PINS:
        Pin(n, Pin.OUT, value=0).value(0)


def relays_state():
    return [Pin(n).value() for n in RELAY_PINS]


def start_watchdog():
    global _wdt
    if _wdt is None:
        _wdt = WDT(timeout=WDT_TIMEOUT_MS)
    return _wdt


def feed():
    if _wdt is not None:
        _wdt.feed()


def enter():
    """Call first in every development operation. Returns True when all relays read back 0."""
    relays_off()
    feed()
    state = relays_state()
    ok = state == [0, 0, 0]
    print('DEVSAFE relays=%s ok=%s watchdog=%s' % (state, ok, _wdt is not None))
    return ok
