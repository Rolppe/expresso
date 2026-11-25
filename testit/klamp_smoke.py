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
import math
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
        if callable(self.raw):
            return self.raw(self.plant)
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

    # 9. Kylma kuristin (taysi paine 10,5 bar): painekatto 9 bar, ei PCAP-katkaisua (klamp-20260925-b)
    peak = [0.0]
    bd = BrewData(p_full=lambda t: 10.5)
    orig = bd.plant.step

    def tracked():
        p = orig()
        peak[0] = max(peak[0], p)
        return p
    bd.plant.step = tracked
    out = run(bd, 12)
    end = end_of(out)
    check('9 kylma kuristin: ei overpressure', field(end, 'reason') != 'overpressure', end)
    check('9 reason=timeout (rajoitus jatkuu)', field(end, 'reason') == 'timeout', end)
    check('9 painekatto KLAMP_RISE reason=clamp', any('reason=clamp' in l for l in out.splitlines()))
    check('9 tavoite 9,0', abs(float(field(end, 'target') or 0) - F.KLAMP_MAX_BAR) < 0.01, end)
    check('9 paine <= 9,x bar (huippu %.2f)' % peak[0], peak[0] < 10.0, 'peak %.2f' % peak[0])

    # 10. Yksi hairionayte > 11 bar ei katkaise, kaksi perakkaista katkaisee (PcapOver)
    hi = int((14.0 - F.PCAP_RAW_B) / F.PCAP_RAW_A)
    cnt = [0]

    def spike1(plant):
        cnt[0] += 1
        return hi if cnt[0] == 30 else int((plant.step() - F.PCAP_RAW_B) / F.PCAP_RAW_A)
    bd = BrewData(raw=spike1)
    end = end_of(run(bd, 3))
    check('10 yksi nayte yli 11 bar ei katkaise', field(end, 'reason') == 'timeout' and cnt[0] > 30, end)
    cnt[0] = 0

    def spike2(plant):
        cnt[0] += 1
        return hi if cnt[0] in (30, 31) else int((plant.step() - F.PCAP_RAW_B) / F.PCAP_RAW_A)
    bd = BrewData(raw=spike2)
    end = end_of(run(bd, 3))
    check('10 kaksi perakkaista katkaisee', field(end, 'reason') == 'overpressure', end)
    check('10 releet pois', bd.pump.value() == 0 and bd.solenoid.value() == 0)
    g = F.PcapOver()
    seq = [g.hit(b) for b in (12.0, 5.0, 12.0, 12.0)]
    check('10 PcapOver: ylitys, nollaus, kaksi -> [F,F,F,T]', seq == [False, False, False, True], str(seq))
    check('10 PcapOver: raja ei ylity tasan 11,0', F.PcapOver().hit(11.0) is False)

    # 11. Nopea nousu (klamp-20261125-b: 9 bar 949 ms:ssa, ~15 bar/s): pumpun viive ja 100 ms
    #     keskiarvo -> katon kohdalla aloitettu saato ylitti PCAP_OVER_BAR:n. Ennakoiva katto (a3f2f48)
    #     ottaa saatimen kayttoon ennen 9 baria; raaka paine ei saa ylittaa 11 baria kahdesti.
    for name, p_full, tau in (('16/0.45', 16.0, 0.45), ('20/0.5', 20.0, 0.5)):
        r = run_fast(p_full, tau)
        end = r['end']
        check('11 nopea nousu %s: ei overpressure' % name, bool(end) and field(end, 'reason') != 'overpressure', end)
        check('11 nopea nousu %s: KLAMP_RISE reason=clamp ennen 9 baria' % name,
              'reason=clamp' in r['rise'] and float(field(r['rise'], 'at') or 99) < F.KLAMP_MAX_BAR, r['rise'])
        check('11 nopea nousu %s: huippu < 10,5 bar (%.2f)' % (name, r['peak']), r['peak'] < 10.5)
        check('11 nopea nousu %s: loppuosan ka 9,0 +-0,3 (%.2f)' % (name, r['tail']), abs(r['tail'] - 9.0) < 0.3)

    print('RESULT: %d failed' % len(fails))
    return 1 if fails else 0


class SimClock:
    t = 0  # ms; simuloitu kello: deterministinen, ei riipu isannan kuormasta


class FastPlant:
    """1 ms askel: pumpun vaikutus viiveella delay_ms, p' = (p_full*pump - p)/tau, 100 ms keskiarvo
    (get_pressure_average) ja raaka-aaltoilu (PCAP-raja) kuten laitteella."""
    def __init__(self, p_full, tau, delay_ms=70, ripple=1.4):
        self.p_full, self.tau, self.delay, self.ripple = p_full, tau, delay_ms, ripple
        self.p, self.hist, self.pumph, self.last, self.peak, self.pump = 0.0, [], [], 0, 0.0, None

    def adv(self):
        while self.last < SimClock.t:
            self.last += 1
            self.pumph.append(self.pump.v)
            on = self.pumph[-1 - self.delay] if len(self.pumph) > self.delay else 0
            self.p = max(0.0, self.p + ((self.p_full if on else 0.0) - self.p) * (0.001 / self.tau))
            self.hist.append(self.p)
            self.peak = max(self.peak, self.p)

    def avg(self):
        self.adv()
        h = self.hist[-100:] or [0.0]
        return sum(h) / len(h)

    def raw(self):
        self.adv()
        return self.p + self.ripple * math.sin(2 * math.pi * SimClock.t / 20.0)


class FastBrewData(BrewData):
    def __init__(self, plant):
        super().__init__()
        self.plant = plant
        plant.pump = self.pump
        self.pressure_sensor = Sensor(plant, raw=lambda pl: (pl.raw() - F.PCAP_RAW_B) / F.PCAP_RAW_A)

    def get_pressure_average(self, utime):
        return round(self.plant.avg(), 2)

    def get_weight_ms(self):
        return SimClock.t


class SimUtime(Utime):
    def ticks_ms(self):
        return SimClock.t


class SimAsyncio:
    async def sleep_ms(self, ms):
        SimClock.t += ms


def run_fast(p_full, tau, seconds=12):
    SimClock.t = 0
    plant = FastPlant(p_full, tau)
    bd = FastBrewData(plant)
    buf = io.StringIO()
    with redirect_stdout(buf):
        asyncio.run(F.throttle_warmup_run(bd, SimUtime(), SimAsyncio(), Ratio(), seconds))
    lines = buf.getvalue().splitlines()
    end = [l for l in lines if l.startswith('KLAMP_END')]
    rise = [l for l in lines if l.startswith('KLAMP_RISE')]
    tail = plant.hist[-3000:] or [0.0]
    return dict(end=end[0] if len(end) == 1 else '', rise=rise[0] if rise else '', peak=plant.peak,
                tail=sum(tail) / len(tail))


if __name__ == '__main__':
    sys.exit(main())
