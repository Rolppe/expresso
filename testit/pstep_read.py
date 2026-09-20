#!/usr/bin/env python3
"""pstep_read.py — lukee `pico_dev.py pstep`:n lokin ja mittaa viiveen.

Mitattava suure (kayttajan tilaus 20.9.2026): viive siita hetkesta, jolloin firmware sammutti
pumpun yhdeksi verkkojaksoksi, siihen hetkeen, jolloin se yksi puuttuva isku nakyy paineessa.
Firmware merkitsee kaskyhetken `PSTEP_MARK reach=<i> notch=<i> stop=<i> n=<N>` -rivilla, ja
naytevali on 1000 us, joten indeksi on millisekunti.

Menetelma:
  1. raaka ADC -> bar samalla kaavalla ja samalla gain/offsetilla kuin laitteessa;
  2. yhden verkkojakson liukuva keskiarvo poistaa 50 Hz:n vareilyn ja jattaa verhokayran;
  3. verhokayralle sovitetaan suora ohitusta edeltavasta ikkunasta (paine on tasapainossa,
     joten se on lahes vaakasuora) ja jaannos on d[i];
  4. viive on ensimmainen nayte ohituksen jalkeen, jossa d alittaa -K*sd, ja toinen luku on
     jaannoksen pohjan kohta. sd tulee samasta ohitusta edeltavasta ikkunasta, joten kynnys on
     mitattu eika valittu.

Sama luenta ajetaan pumpun sammutukselle (`stop`), joka on riippumaton toinen askel: sen viive
kuuluu olla sama, ja ero kertoo kummankin lukeman epavarmuuden.

Kaytto:
  pstep_read.py <loki.log> [--pre 300] [--win 400] [--k 4.0]
  pstep_read.py --selftest
"""
import argparse
import re
import sys

RAW_A = 0.000314936          # functions.py PCAP_RAW_A
RAW_B = -3.522929            # functions.py PCAP_RAW_B
RATE_US = 1000
MAINS_US = 19960


def movavg(x, n):
    """Kausaalinen (perassa laahaava) liukuva keskiarvo yhden verkkojakson yli.

    Keskitetty ikkuna olisi vaihevirheeton, mutta se nakee tulevaisuuteen: itsetestissa se
    havaitsi pudotuksen 7-8 ms ennen kuin se tapahtui, eli tasan puoli ikkunaa etuajassa. Se on
    tappava virhe, kun mitattava suure on 70-90 ms:n viive. Kausaalinen ikkuna ei voi reagoida
    ennen tapahtumaa; se viivastyttaa havaintoa, ja jaljelle jaava virhe on yksisuuntainen ja
    mitattavissa itsetestilla."""
    out = [0.0] * len(x)
    run = 0.0
    for i, v in enumerate(x):
        run += v
        if i >= n:
            run -= x[i - n]
        out[i] = run / min(i + 1, n)
    return out


def parse(path):
    gain, offset, rate = 1.0, 0.0, RATE_US
    marks = {}
    rows = {}
    with open(path, 'r', errors='replace') as fh:
        for line in fh:
            if line.startswith('PSTEP_START'):
                for key in ('gain', 'offset'):
                    m = re.search(key + r'=(-?\d+\.?\d*)', line)
                    if m:
                        if key == 'gain': gain = float(m.group(1))
                        else: offset = float(m.group(1))
                m = re.search(r'rate=(\d+)', line)
                if m: rate = 1000000 // int(m.group(1))
            elif line.startswith('PSTEP_MARK'):
                for key in ('reach', 'notch', 'stop', 'n'):
                    m = re.search(key + r'=(-?\d+)', line)
                    if m: marks[key] = int(m.group(1))
            elif line.startswith('PSTEP '):
                parts = line.split()
                start = int(parts[1])
                rows[start] = [int(v) for v in parts[2:]]
    if not rows:
        raise SystemExit('ei PSTEP-rivejä tiedostossa %s' % path)
    raw = []
    for start in sorted(rows):
        if start != len(raw):
            raise SystemExit('PSTEP-rivit eivät ole yhtenäisiä: odotettiin %d, saatiin %d'
                             % (len(raw), start))
        raw.extend(rows[start])
    bar = [gain * (v * RAW_A + RAW_B) + offset for v in raw]
    return bar, marks, rate


def measure(bar, event, pre_ms, win_ms, k, rate_us):
    """Palauttaa (onset_ms, trough_ms, depth_bar, sd_bar) tai None jos ikkuna ei mahdu."""
    per = max(2, int(round(MAINS_US / rate_us)))
    env = movavg(bar, per)
    lo = event - pre_ms
    if lo < per or event + win_ms >= len(bar):
        return None
    pre = env[lo:event]
    n = len(pre)
    mean_i = (n - 1) / 2.0
    mean_y = sum(pre) / n
    sxx = sum((i - mean_i) ** 2 for i in range(n))
    sxy = sum((i - mean_i) * (pre[i] - mean_y) for i in range(n))
    slope = sxy / sxx if sxx else 0.0
    resid = [pre[i] - (mean_y + slope * (i - mean_i)) for i in range(n)]
    sd = (sum(r * r for r in resid) / n) ** 0.5
    onset = None
    trough_i, trough_d = None, 0.0
    for i in range(event, event + win_ms):
        pred = mean_y + slope * ((i - lo) - mean_i)
        d = env[i] - pred
        if onset is None and d < -k * sd:
            onset = i - event
        if d < trough_d:
            trough_d, trough_i = d, i - event
    return onset, trough_i, trough_d, sd


def report(path, pre_ms, win_ms, k):
    bar, marks, rate = parse(path)
    notch, stop = marks.get('notch', -1), marks.get('stop', -1)
    print('PSTEP_N n=%d reach=%d notch=%d stop=%d' % (len(bar), marks.get('reach', -1), notch, stop))
    if notch >= 0:
        base = sum(bar[max(0, notch - pre_ms):notch]) / max(1, min(pre_ms, notch))
        print('PSTEP_BASE bar=%.2f' % base)
    out = {}
    for name, event in (('NOTCH', notch), ('STOP', stop)):
        if event < 0:
            print('PSTEP_%s reason=ei_merkitty' % name); continue
        r = measure(bar, event, pre_ms, win_ms, k, rate)
        if r is None:
            print('PSTEP_%s reason=ikkuna_ei_mahdu' % name); continue
        onset, trough, depth, sd = r
        out[name] = onset
        print('PSTEP_%s onset_ms=%s trough_ms=%s depth_bar=%.3f sd_bar=%.3f snr=%.1f' % (
            name, 'ei' if onset is None else onset, 'ei' if trough is None else trough,
            depth, sd, (abs(depth) / sd) if sd else 0.0))
    if out.get('NOTCH') is not None and out.get('STOP') is not None:
        print('PSTEP_DELAY notch_ms=%d stop_ms=%d ero_ms=%d' % (
            out['NOTCH'], out['STOP'], out['STOP'] - out['NOTCH']))
    elif out.get('NOTCH') is not None:
        print('PSTEP_DELAY notch_ms=%d stop_ms=ei' % out['NOTCH'])


def selftest():
    """Synteettinen ajo: tunnettu viive sisaan, sama luku ulos."""
    import math
    import random
    random.seed(7)
    ok = True
    for true_delay in (40, 80, 120):
        n, notch = 4000, 2000
        bar = []
        for i in range(n):
            ripple = 0.35 * math.sin(2 * math.pi * i * RATE_US / MAINS_US)
            level = 7.0
            if i >= notch + true_delay:
                # yksi puuttuva isku: kuoppa, joka palautuu noin yhden jakson aikana
                age = i - (notch + true_delay)
                level -= 0.60 * math.exp(-age / 25.0)
            bar.append(level + ripple + random.gauss(0, 0.05))
        r = measure(bar, notch, 300, 400, 4.0, RATE_US)
        onset = r[0]
        good = onset is not None and abs(onset - true_delay) <= 6
        ok = ok and good
        print('SELFTEST true=%d onset=%s trough=%s %s' % (
            true_delay, onset, r[1], 'OK' if good else 'FAIL'))
    print('SELFTEST %s' % ('OK' if ok else 'FAIL'))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('log', nargs='?')
    ap.add_argument('--pre', type=int, default=300, help='ohitusta edeltävä ikkuna, ms')
    ap.add_argument('--win', type=int, default=400, help='etsintäikkuna ohituksen jälkeen, ms')
    ap.add_argument('--k', type=float, default=4.0, help='kynnys hajonnan kerrannaisina')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.log:
        ap.error('anna loki tai --selftest')
    report(a.log, a.pre, a.win, a.k)
    return 0


if __name__ == '__main__':
    sys.exit(main())
