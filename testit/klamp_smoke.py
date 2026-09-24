#!/usr/bin/env python3
"""klamp_smoke.py — kuristimen lämmitys klamp:<s> (käyttäjä 24.9.2026, KAYTTAJAN-TIEDOT).

Ajaa firmwaren `throttle_warmup_run`-korutiinin CPythonilla valelaitteilla kuten phold_smoke.py,
mutta paine tulee yksinkertaisesta laitosmallista: p lähestyy aikavakiolla arvoa
P_full(t) × pumppu päällä, joten firmwaren oma PumpPressureController ajaa oikeaa silmukkaa.

    python3 testit/klamp_smoke.py        RESULT: <n> failed, epänolla paluuarvo jos punaisia

Tapaukset: tasainen kuristin → tasanne ja reason=done; tasanteen jälkeen kiristyvä kuristin →
pumppua rajoitetaan eikä ajo pääty doneen, ja kun kuristin taas aukeaa → done; ylipaine, kytkin,
klamp:stop, kaukalo ja noreach.
"""

import asyncio
import io
import os
import sys
import time
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pico'))
import functions as F


class Plant:
    """p' = (P_full(t) * pump - p) / tau; tayttovaihe: ensimmaiset fill_s sekuntia paine ~0."""
    def __init__(self, p_full, tau=0.8, fill_s=0.5):
        self.p_full, self.tau, self.fill_s = p_full, tau, fill_s
        self.p = 0.0
        self.t0 = time.monotonic()
        self.last = self.t0
        self.pump = None

    def step(self):
        now = time.monotonic()
        dt, self.last = now - self.last, now
        t = now - self.t0
        drive = self.p_full(t) if (self.pump.v and t >= self.fill_s) else 0.0
        self.p += (drive - self.p) * min(1.0, dt / self.tau)
        return self.p


class Pin:
    def __init__(self, v=0):
        self.v = v

    def value(self, x=None):
        if x is None:
            return self.v
        self.v = x


class Adc:
    def __init__(self, plant, raw=None):
        self.plant, self.raw = plant, raw

    def read_u16(self):
        if self.raw is not None:
            return self.raw
        return (self.plant.step() - F.PCAP_RAW_B) / F.PCAP_RAW_A


class Sensor:
    def __init__(self, plant, raw=None):
        self.pressure_sensor = Adc(plant, raw)
        self.gain = 1.0
        self.offset = 0.0

    def reset_average(self):
        pass


class Ratio:
    def set_pump_on(self):
        pass

    def set_pump_off(self):
        pass


class BrewData:
    def __init__(self, p_full=lambda t: 8.0, raw=None, weight=100.0):
        self.pump, self.solenoid, self.heater = Pin(), Pin(), Pin()
        self.brew, self.water, self.steam = Pin(), Pin(), Pin()
        self.plant = Plant(p_full)
        self.plant.pump = self.pump
        self.pressure_sensor = Sensor(self.plant, raw)
        self.dev_safe = False
        self.klamp_abort = False
        self.mode = None
        self.weight = weight
        self.pressure_filtered = 0.0

    def get_relays(self):
        return self.pump, self.solenoid, self.heater

    def get_switches(self):
        return self.brew, self.water, self.steam

    def set_mode(self, m):
        self.mode = m

    def get_pressure_average(self, utime):
        return round(self.plant.step(), 2)

    def get_weight(self):
        return self.weight

    def get_weight_ms(self):
        return int(time.monotonic() * 1000)

    def get_weight_limit(self):
        return 720.0

    def get_weight_rise_limit(self):
        return 250.0


class Utime:
    def ticks_ms(self):
        return int(time.monotonic() * 1000)

    def ticks_diff(self, a, b):
        return a - b

    def ticks_add(self, a, b):
        return a + b


class Asyncio:
    async def sleep_ms(self, ms):
        await asyncio.sleep(ms / 1000.0)


def run(bd, seconds, abort_after=None, switch_after=None):
    async def main():
        task = asyncio.ensure_future(F.throttle_warmup_run(bd, Utime(), Asyncio(), Ratio(), seconds))
        if abort_after is not None:
            await asyncio.sleep(abort_after)
            bd.klamp_abort = True
        if switch_after is not None:
            await asyncio.sleep(switch_after)
            bd.brew.value(1)
        await task

    buf = io.StringIO()
    with redirect_stdout(buf):
        asyncio.run(main())
    return buf.getvalue()


def field(line, key):
    for part in line.split():
        if part.startswith(key + '='):
            return part.split('=', 1)[1]
    return None


def main():
    fails = []

    def check(name, cond, extra=''):
        print(('PASS ' if cond else 'FAIL ') + name + (' — ' + extra if extra else ''))
        if not cond:
            fails.append(name)

    def end_of(out):
        e = [l for l in out.splitlines() if l.startswith('KLAMP_END')]
        return e[0] if len(e) == 1 else ''

    # 1. Tasainen kuristin, taysi pumppu 8 bar: tasanne ~8, sitten pito ilman rajoitusta -> done
    bd = BrewData()
    out = run(bd, 20)
    end = end_of(out)
    rise = [l for l in out.splitlines() if l.startswith('KLAMP_RISE')]
    check('1 KLAMP_START ja yksi KLAMP_END', 'KLAMP_START s=20' in out and bool(end), end)
    check('1 tasanne löytyy', len(rise) == 1 and 'reason=plateau' in rise[0], rise[0] if rise else '')
    check('1 tavoite on tasanteen paine (~8 bar), ei vakio', abs(float(field(end, 'target') or 0) - 8.0) < 0.3, end)
    check('1 reason=done', field(end, 'reason') == 'done', end)
    check('1 duty_avg >= KLAMP_DONE_DUTY', float(field(end, 'duty_avg') or 0) >= F.KLAMP_DONE_DUTY, end)
    check('1 releet pois ja IDLE', bd.pump.value() == 0 and bd.solenoid.value() == 0 and bd.mode == 'IDLE')

    # 2. Tavoite seuraa kuristinta: tasanne 6,5 bar -> tavoite ~6,5
    bd = BrewData(p_full=lambda t: 6.5)
    end = end_of(run(bd, 20))
    check('2 tavoite ~6,5 bar toisella kuristimella', abs(float(field(end, 'target') or 0) - 6.5) < 0.3, end)

    # 3. Kuristin kiristyy tasanteen jälkeen (taysi pumppu 7 -> 9 bar 5,5 s:ssa, tasanne ~5 s):
    #    pumppua rajoitetaan tavoitteessa, eika ajo paaty doneen vaan aikarajaan.
    bd = BrewData(p_full=lambda t: 7.0 if t < 5.5 else 9.0)
    out = run(bd, 12)
    end = end_of(out)
    duties = [float(field(l, 'duty')) for l in out.splitlines() if l.startswith('KLAMP ') and field(l, 'target') != '0.00']
    check('3 kiristynyt kuristin: reason=timeout, ei done', field(end, 'reason') == 'timeout', end)
    check('3 pumppua rajoitettiin (duty < 0.9)', bool(duties) and min(duties) < 0.9, 'min %.2f' % min(duties or [1]))
    check('3 paine pysyi tavoitteen lähellä', abs(bd.pressure_filtered - float(field(end, 'target') or 0)) < 0.5,
          'filt %.2f target %s' % (bd.pressure_filtered, field(end, 'target')))

    # 3b. Kiristys palautuu ja kuristin aukeaa lampimana tasannetta vapaammaksi (9 -> 6,5 bar
    #     9 s:ssa): rajoitus loppuu -> done. Rajatapaus, jota ei testata: jos taysi paine palaa
    #     tasan tasanteen tasolle, tavoite on tasannesaannon jaannosnousun verran sen alla
    #     (malli 6,96 vs 7,0) ja saadin rajoittaa hieman (duty ~0,94) -> timeout, ei done.
    bd = BrewData(p_full=lambda t: 7.0 if t < 5.5 else (9.0 if t < 9.0 else 6.5))
    out = run(bd, 25)
    end = end_of(out)
    duties = [float(field(l, 'duty')) for l in out.splitlines() if l.startswith('KLAMP ') and field(l, 'target') != '0.00']
    check('3b rajoitus ensin (duty < 0.9)', bool(duties) and min(duties) < 0.9, 'min %.2f' % min(duties or [1]))
    check('3b rajoituksen loputtua reason=done', field(end, 'reason') == 'done', end)
    check('3b done vasta palautumisen jälkeen (ms > 9000 + DONE_MS)',
          int(field(end, 'ms') or 0) > 9000 + F.KLAMP_DONE_MS, end)

    # 4. Ylipaine raa'asta näytteestä
    bd = BrewData(raw=int((14.0 - F.PCAP_RAW_B) / F.PCAP_RAW_A))
    end = end_of(run(bd, 20))
    check('4 ylipaine lopettaa', field(end, 'reason') == 'overpressure', end)
    check('4 releet pois', bd.pump.value() == 0 and bd.solenoid.value() == 0)

    # 5. Kytkin kesken ajon
    bd = BrewData()
    end = end_of(run(bd, 20, switch_after=0.5))
    check('5 kytkin lopettaa', field(end, 'reason') == 'switch', end)
    check('5 releet pois', bd.pump.value() == 0)

    # 6. klamp:stop kesken ajon
    bd = BrewData()
    end = end_of(run(bd, 20, abort_after=0.5))
    check('6 stop lopettaa', field(end, 'reason') == 'stop', end)
    check('6 abort-lippu nollattu', bd.klamp_abort is False)

    # 7. Kaukalo jo rajalla: ajo ei ala, pumppu ei käynnisty
    bd = BrewData(weight=730.0)
    out = run(bd, 20)
    check('7 kaukalo rajalla: reason=tray, ei KLAMP_STARTia', 'reason=tray' in out and 'KLAMP_START' not in out,
          out.strip())
    check('7 pumppu ei käynnistynyt', bd.pump.value() == 0)

    # 8. Paine ei nouse (kuristin auki / vuoto): noreach nousun katolla
    saved = F.KLAMP_RISE_MAX_MS
    F.KLAMP_RISE_MAX_MS = 1500
    try:
        bd = BrewData(p_full=lambda t: 0.5)
        end = end_of(run(bd, 20))
    finally:
        F.KLAMP_RISE_MAX_MS = saved
    check('8 ei tasannetta yli 1 barin: reason=noreach', field(end, 'reason') == 'noreach', end)

    print('RESULT: %d failed' % len(fails))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
