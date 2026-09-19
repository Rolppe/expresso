#!/usr/bin/env python3
"""tray_guard_smoke.py — suunnittelijan holdout kaukalovahdille (EXPRESSO-KAUKALOVAHTI).

Ajaa `pressure_hold_run`:n ja `pressure_capture_run`:n CPythonilla valelaitteilla ja tarkistaa,
ettei kumpikaan kytke relettä, kun kaukaloa ei voi nähdä, ja että molemmat katkeavat rajaan.
Laukaisija 19.9.2026: phold 60 ajoi kaukalon yli, koska painoraja oli vain tshot-polulla
(paketit/TURVAKATO.md).

    python3 testit/tray_guard_smoke.py       RESULT: <n> failed, epänolla paluuarvo jos punaisia

Toteuttaja ei muokkaa tätä tiedostoa (brief: must not).
"""

import asyncio
import io
import os
import sys
import time
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pico'))
import functions as F


class Pin:
    def __init__(self):
        self.v = 0
        self.ons = 0

    def value(self, x=None):
        if x is None:
            return self.v
        if x and not self.v:
            self.ons += 1
        self.v = x


class Adc:
    def read_u16(self):
        return 30000


class Sensor:
    def __init__(self):
        self.pressure_sensor = Adc()
        self.gain = 1.0
        self.offset = -0.99


class BrewData:
    """weight_mode: 'ok' | 'none' | 'stale' | 'rise' | 'max'."""

    def __init__(self, weight_mode='ok', wmax=470.0, wrise=250.0, phase_us=None):
        self.pump, self.solenoid, self.heater = Pin(), Pin(), Pin()
        self.brew, self.water, self.steam = Pin(), Pin(), Pin()
        self.pressure_sensor = Sensor()
        self.dev_safe = False
        self.phold_abort = False
        self.pcap_abort = False
        self.pcap_target_bar = None
        self.pcap_gate_phase_us = phase_us
        self.mode = None
        self.weight_mode = weight_mode
        self.wmax, self.wrise = wmax, wrise
        self.t0 = time.monotonic()
        self.base = 100.0

    # --- releet ja kytkimet
    def get_relays(self):
        return self.pump, self.solenoid, self.heater

    def get_switches(self):
        return self.brew, self.water, self.steam

    def set_mode(self, m):
        self.mode = m

    # --- vaaka
    def _elapsed(self):
        return time.monotonic() - self.t0

    def get_weight(self):
        if self.weight_mode == 'none':
            return None
        if self.weight_mode == 'max':
            return self.base + 400.0 * self._elapsed()      # ylittää wmax 470 alle sekunnissa
        if self.weight_mode == 'rise':
            return self.base + 300.0 * self._elapsed()      # ylittää wrise 250 alle sekunnissa
        return self.base

    def get_weight_ms(self):
        if self.weight_mode == 'stale':
            return int(self.t0 * 1000) - 60000              # aina yli 2 s vanha
        return int(time.monotonic() * 1000)

    def get_weight_limit(self):
        return self.wmax

    def get_weight_rise_limit(self):
        return self.wrise


class Utime:
    def ticks_ms(self):
        return int(time.monotonic() * 1000)

    def ticks_us(self):
        return time.monotonic_ns() // 1000

    def ticks_diff(self, a, b):
        return a - b

    def ticks_add(self, a, b):
        return a + b


class Asyncio:
    async def sleep_ms(self, ms):
        await asyncio.sleep(ms / 1000.0)


def run_hold(bd, seconds):
    buf = io.StringIO()
    with redirect_stdout(buf):
        asyncio.run(F.pressure_hold_run(bd, Utime(), Asyncio(), seconds))
    return buf.getvalue()


def run_cap(bd, ms):
    buf = io.StringIO()
    with redirect_stdout(buf):
        asyncio.run(F.pressure_capture_run(bd, Utime(), Asyncio(), ms))
    return buf.getvalue()


def main():
    fails = []

    def check(name, cond, extra=''):
        if not cond:
            fails.append(name)
            print('FAIL ' + name + (' — ' + extra if extra else ''))

    def last(out):
        lines = [l for l in out.strip().splitlines() if l]
        return lines[-1] if lines else '(tyhjä)'

    # --- 1. Ei vaakaa: kumpikaan ei saa kytkeä relettä
    for name, runner, arg in (('phold', run_hold, 5), ('pcap', run_cap, 400)):
        bd = BrewData(weight_mode='none')
        out = runner(bd, arg)
        check('%s: ei vaakaa -> reason=noscale' % name, 'reason=noscale' in out, last(out))
        check('%s: ei vaakaa -> pumppua ei kytketty' % name, bd.pump.ons == 0, 'ons=%d' % bd.pump.ons)
        check('%s: ei vaakaa -> venttiiliä ei kytketty' % name, bd.solenoid.ons == 0,
              'ons=%d' % bd.solenoid.ons)

    # --- 2. Vanhentunut lukema: sama kohtelu
    for name, runner, arg in (('phold', run_hold, 5), ('pcap', run_cap, 400)):
        bd = BrewData(weight_mode='stale')
        out = runner(bd, arg)
        check('%s: vanha lukema -> reason=noscale' % name, 'reason=noscale' in out, last(out))
        check('%s: vanha lukema -> pumppua ei kytketty' % name, bd.pump.ons == 0,
              'ons=%d' % bd.pump.ons)

    # --- 3. Rajaa ei asetettu: ajo ei ala
    for name, runner, arg in (('phold', run_hold, 5), ('pcap', run_cap, 400)):
        bd = BrewData(wmax=0.0, wrise=0.0)
        out = runner(bd, arg)
        check('%s: ei rajaa -> reason=nolimit' % name, 'reason=nolimit' in out, last(out))
        check('%s: ei rajaa -> pumppua ei kytketty' % name, bd.pump.ons == 0, 'ons=%d' % bd.pump.ons)

    # --- 4. Kaukalo täyttyy kesken ajon: katkeaa ja releet jäävät nolliin
    bd = BrewData(weight_mode='max')
    out = run_hold(bd, 30)
    check('phold: wmax ylittyy -> reason=tray', 'reason=tray' in out, last(out))
    check('phold: wmax ylittyy -> pumppu pois', bd.pump.value() == 0)
    check('phold: wmax ylittyy -> venttiili pois', bd.solenoid.value() == 0)

    bd = BrewData(weight_mode='rise', wmax=0.0, wrise=250.0)
    out = run_hold(bd, 30)
    check('phold: wrise ylittyy -> reason=trayrise', 'reason=trayrise' in out, last(out))
    check('phold: wrise ylittyy -> pumppu pois', bd.pump.value() == 0)

    bd = BrewData(weight_mode='max')
    out = run_cap(bd, 400)
    check('pcap: wmax ylittyy -> reason=tray', 'reason=tray' in out, last(out))
    check('pcap: wmax ylittyy -> pumppu pois', bd.pump.value() == 0)

    # --- 5. Normaali ajo rajojen sisällä ei saa katketa vahtiin
    bd = BrewData(weight_mode='ok')
    out = run_hold(bd, 2)
    check('phold: rajojen sisällä reason=ok', 'reason=ok' in out, last(out))
    check('phold: rajojen sisällä pumppu kytkettiin', bd.pump.ons >= 1)

    bd = BrewData(weight_mode='ok')
    out = run_cap(bd, 400)
    check('pcap: rajojen sisällä reason=ok', 'reason=ok' in out, last(out))
    check('pcap: rajojen sisällä pumppu kytkettiin', bd.pump.ons >= 1)

    print('RESULT: %d failed' % len(fails))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
