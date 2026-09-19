#!/usr/bin/env python3
"""psweep_read.py — PWM-1B5: pyyhkäisylokin analysaattori (paketit/PUMPPU-PWM.md säännöt 9-12).

  python3 psweep_read.py <sweep.log>   Lukee pyyhkäisylokin, tulostaa PSWEEP_*/PSKIP_INV.
  python3 psweep_read.py --selftest    Synteettiset lokit, tulostaa RESULT: <n> failed.

Loki jakautuu `PCAP_START`-riveittäin segmentteihin. Portitetuille segmenteille taitos on sama
menettely kuin `pskip_delay.analyze`:ssa (spec 2.2), tuotu sellaisenaan. `PSKIP_INV inv_ms`:n
modulus on verkkojakso (segmentin oma `on_us`), ei portin jakso (sääntö 9, korjattu 19.9.2026).
Referenssisegmenteistä (`gate=off`) luetaan vaihe ja verkkotaajuus `mains_freq.py`:n
`refine_peak`/`goertzel`-funktioilla (spec 2.4).

Tuomio luetaan `delay_ms`:n hajonnasta, ei `inv_ms`:n (PWM-1B6, sääntö 14): kun portin jakso on
lyhyt mittausikkuna oikeaan, vaste seuraa porttia eikä yksittäistä iskua, ja vaihesiirto siirtää
porttia ja vastetta yhdessä — oikea invariantti on `delay_ms` sellaisenaan, ympyrälaskettuna
segmentin oman `period_us`:n yli. `mean_ms`/`spread_ms` (`inv_ms`:stä) jäävät riville
kirjanpidoksi iskunvalintamallista."""

import math
import os
import random
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mains_freq import RAW_TO_BAR_GAIN, RAW_TO_BAR_OFFSET, goertzel, refine_peak  # noqa: E402
from pskip_delay import analyze as pskip_analyze  # noqa: E402

def parse_segments(path):
    """Jakaa lokin `PCAP_START`-riveittäin: otsikkokentät, raakanäytteet, `PCAP_END`:n
    n/dur_us/reason (spec kohta 2.1)."""
    segs = []
    cur = None
    with open(path, 'r', errors='replace') as f:
        for line in f:
            line = line.strip()
            if line.startswith('PCAP_START'):
                fields = dict(p.split('=', 1) for p in line.split()[1:] if '=' in p)
                cur = {
                    'seg': int(fields['seg']) if 'seg' in fields else len(segs),
                    'gate': fields.get('gate', 'off'),
                    'gain': float(fields.get('gain', 1.0)),
                    'offset': float(fields.get('offset', 0.0)),
                    'period_us': int(fields['period_us']) if 'period_us' in fields else None,
                    'on_us': int(fields['on_us']) if 'on_us' in fields else None,
                    'phase_us': int(fields['phase_us']) if 'phase_us' in fields else None,
                    'samples': [], 'n': None, 'dur_us': None, 'reason': None,
                }
            elif line.startswith('PCAP_END') and cur is not None:
                fields = dict(p.split('=', 1) for p in line.split()[1:] if '=' in p)
                cur['n'], cur['dur_us'] = int(fields.get('n', len(cur['samples']))), int(fields.get('dur_us', 0))
                cur['reason'] = fields.get('reason', '')
                segs.append(cur)
                cur = None
            elif line.startswith('PCAP ') and cur is not None:
                cur['samples'].extend(int(v) for v in line.split()[3:])
    return segs

def bar_series(seg):
    return [seg['gain'] * (v * RAW_TO_BAR_GAIN + RAW_TO_BAR_OFFSET) + seg['offset']
            for v in seg['samples']]

def fwhm_bins(fold, best_bin):
    """Taitoksen huipun leveys puolikkaalla korkeudella, bineinä, ympyränä (spec kohta 2.3)."""
    n = len(fold)
    lo, hi = min(fold), max(fold)
    if hi - lo <= 1e-12:
        return float(n)
    half = lo + (hi - lo) / 2.0
    left = right = 0
    while left < n - 1 and fold[(best_bin - left - 1) % n] >= half:
        left += 1
    while right < n - 1 and fold[(best_bin + right + 1) % n] >= half:
        right += 1
    return float(left + right + 1)

def analyze_ref(seg):
    """Referenssisegmentin taajuus ja vaihe (spec kohta 2.4): `refine_peak` taajuudelle, `goertzel`
    samasta taajuudesta vaiheelle."""
    fs = 1e6 * seg['n'] / seg['dur_us']
    x = bar_series(seg)
    mean_x = sum(x) / len(x) if x else 0.0
    xc = [v - mean_x for v in x]
    freq, amp = refine_peak(xc, fs)
    _, phase = goertzel(xc, fs, freq)
    return freq, amp, math.degrees(phase) % 360.0

def circular_stats(values_ms, modulus_ms):
    """Ympyräkeskiarvo ja -hajonta modulo `modulus_ms` (spec kohta 2.5)."""
    ang = [2.0 * math.pi * v / modulus_ms for v in values_ms]
    c = sum(math.cos(a) for a in ang) / len(ang)
    s = sum(math.sin(a) for a in ang) / len(ang)
    r = math.hypot(c, s)
    mean_ms = (math.atan2(s, c) % (2.0 * math.pi)) * modulus_ms / (2.0 * math.pi)
    spread_ms = math.sqrt(max(0.0, -2.0 * math.log(max(r, 1e-12)))) * modulus_ms / (2.0 * math.pi)
    return mean_ms, spread_ms

def process(path):
    """Analysoi yhden pyyhkäisylokin; palauttaa (tulosterivit, paluuarvo)."""
    lines = []
    segs = parse_segments(path)
    gated = [s for s in segs if s['gate'] == 'on']
    ref = [s for s in segs if s['gate'] == 'off']
    if len(segs) < 3 or not gated or not ref:
        lines.append('PSWEEP_NOSWEEP segments=%d' % len(segs))
        return lines, 1
    fs_avg = sum(1e6 * s['n'] / s['dur_us'] for s in segs) / len(segs)
    lines.append('PSWEEP_SEGS n=%d gated=%d ref=%d fs=%.1f'
                  % (len(segs), len(gated), len(ref), fs_avg))
    mains_ms = gated[0]['on_us'] / 1000.0
    period_ms = gated[0]['period_us'] / 1000.0
    inv_values = []
    delay_values = []
    for s in gated:
        res = pskip_analyze(s['samples'], s['dur_us'], s['n'], s['gain'], s['offset'],
                             s['period_us'], s['phase_us'])
        width = fwhm_bins(res['fold'], res['bin'])
        inv_ms = (res['delay_ms'] - s['phase_us'] / 1000.0) % mains_ms
        inv_values.append(inv_ms)
        delay_values.append(res['delay_ms'])
        lines.append('PSKIP_INV phase_us=%d delay_ms=%.3f inv_ms=%.3f amp=%.3f conf=%.2f '
                      'width_bins=%.1f' % (s['phase_us'], res['delay_ms'], inv_ms, res['amp'],
                                            res['conf'], width))
        if res['conf'] < 2.0:
            lines.append('note: conf below 2.0, not enough to decide (reason=%s)' % s['reason'])
    ref_results = [(s,) + analyze_ref(s) for s in ref]
    for s, freq, amp, phase_deg in ref_results:
        lines.append('PSWEEP_REF seg=%d f=%.3f amp=%.3f phase_deg=%.1f'
                      % (s['seg'], freq, amp, phase_deg))
    f_vals = [r[1] for r in ref_results]
    mean_f = sum(f_vals) / len(f_vals)
    spread_f = max(f_vals) - min(f_vals) if len(f_vals) > 1 else 0.0
    lines.append('PSWEEP_MAINS f=%.3f spread=%.3f from=ref n=%d' % (mean_f, spread_f, len(f_vals)))
    mean_ms, spread_ms = circular_stats(inv_values, mains_ms)
    delay_mean_ms, delay_spread_ms = circular_stats(delay_values, period_ms)
    bin_ms = period_ms / 40.0
    verdict = 'vakaa' if delay_spread_ms <= 1.5 * bin_ms else 'hajoaa'
    lines.append('PSWEEP_INV mean_ms=%.3f spread_ms=%.3f delay_mean_ms=%.3f delay_spread_ms=%.3f '
                  'n=%d verdict=%s'
                  % (mean_ms, spread_ms, delay_mean_ms, delay_spread_ms, len(inv_values), verdict))
    return lines, 0

# SELFTEST — synthetic sweep logs, spec kohta 3
SELF_PERIOD_US, SELF_MAINS_US, SELF_N = 39920, 19960, 2000
SELF_GAIN, SELF_OFFSET = 1.0, -0.99

def _bar_to_raw(bar):
    v = ((bar - SELF_OFFSET) / SELF_GAIN - RAW_TO_BAR_OFFSET) / RAW_TO_BAR_GAIN
    return int(max(0, min(65535, round(v))))

def _synth_samples(n, delay_s, f_true, gated, phase_us, seed, noise_sd=0.36, amp_bar=0.30,
                    tau_s=0.003, base_bar=7.7):
    """Isku verkkotaajuudella `f_true`, kukin lisää `amp_bar * exp(-dt/tau_s)`-pulssin `delay_s`
    jäljessä iskuhetkeä; portti läpäisee iskun näytteen indeksistä pääteltynä (sääntö 6)."""
    rnd = random.Random(seed); x = [0.0] * n; k = 0
    while k / f_true < n / 1000.0:
        t = k / f_true
        i = int(t * 1000.0)
        passed = True if not gated else (((i * 1000 + phase_us) % SELF_PERIOD_US) < SELF_MAINS_US)
        if 0 <= i < n and passed:
            t0 = t + delay_s
            for j in range(max(0, int(t0 * 1000.0)), n):
                dt = j / 1000.0 - t0
                if dt < 0:
                    continue
                if dt > 8 * tau_s:
                    break
                x[j] += amp_bar * math.exp(-dt / tau_s)
        k += 1
    return [_bar_to_raw(base_bar + v + rnd.gauss(0.0, noise_sd)) for v in x]

def write_sweep_log(path, delay_s, f_true, n_phase=5, seed=1, n=SELF_N):
    phases = [k * SELF_PERIOD_US // n_phase for k in range(n_phase)]
    segs = [(None, 'off')] + [(p, 'on') for p in phases] + [(None, 'off')]
    with open(path, 'w') as f:
        f.write('PSWEEP_START segs=%d n=%d ms=%d target=7.70 period_us=%d on_us=%d\n'
                % (len(segs), n_phase, n, SELF_PERIOD_US, SELF_MAINS_US))
        for k, (p, g) in enumerate(segs):
            head = ('PCAP_START rate=1000 n=%d settle=target gain=%.4f offset=%.3f seg=%d gate=%s'
                    % (n, SELF_GAIN, SELF_OFFSET, k, g))
            if g == 'on':
                head += ' period_us=%d on_us=%d phase_us=%d' % (SELF_PERIOD_US, SELF_MAINS_US, p)
            f.write(head + '\n')
            samples = _synth_samples(n, delay_s, f_true, g == 'on', p or 0, seed * 10 + k)
            for r in range(n // 20):
                row = samples[r * 20:(r + 1) * 20]
                f.write('PCAP %d %d %s\n' % (r * 20, r * 20 * 1000, ' '.join(str(v) for v in row)))
            f.write('PCAP_END n=%d dur_us=%d pmax=8.50 seg=%d reason=ok\n' % (n, n * 1000, k))
        f.write('PSWEEP_END segs=%d dur_ms=%d reason=ok\n' % (len(segs), len(segs) * 2000))
    return phases

def _field(line, key):
    return dict(p.split('=', 1) for p in line.split()[1:] if '=' in p)[key]

def selftest():
    fails = []

    def check(name, cond, extra=''):
        print(('PASS ' if cond else 'FAIL ') + name + (' — ' + extra if extra else ''))
        if not cond: fails.append(name)

    tmp = tempfile.mkdtemp(prefix='psweep-read-selftest-')
    p1 = os.path.join(tmp, 'd9.log'); write_sweep_log(p1, delay_s=0.009, f_true=50.1, seed=1)
    lines1, _ = process(p1)
    inv1 = next(ln for ln in lines1 if ln.startswith('PSWEEP_INV'))
    check('vakio viive: PSWEEP_INV spread_ms alle 3,0', float(_field(inv1, 'spread_ms')) < 3.0, inv1)
    p2 = os.path.join(tmp, 'd14.log'); write_sweep_log(p2, delay_s=0.014, f_true=50.1, seed=2)
    lines2, _ = process(p2)
    inv2 = next(ln for ln in lines2 if ln.startswith('PSWEEP_INV'))
    mean1, mean2 = float(_field(inv1, 'mean_ms')), float(_field(inv2, 'mean_ms'))
    shift = (mean2 - mean1) % (SELF_MAINS_US / 1000.0)
    check('viive 9 ms -> 14 ms siirtää mean_ms:ää 5 ms (+-2 ms)', abs(shift - 5.0) <= 2.0,
          '%.2f -> %.2f (siirtyma %.2f ms)' % (mean1, mean2, shift))
    p3 = os.path.join(tmp, 'ferr.log'); write_sweep_log(p3, delay_s=0.009, f_true=50.2, seed=3)
    lines3, _ = process(p3)
    w1 = [float(_field(ln, 'width_bins')) for ln in lines1 if ln.startswith('PSKIP_INV')]
    w3 = [float(_field(ln, 'width_bins')) for ln in lines3 if ln.startswith('PSKIP_INV')]
    b0, b3 = sum(w1) / len(w1), sum(w3) / len(w3)
    check('0,1 Hz taajuusvirhe kasvattaa width_bins-keskiarvoa', b3 > b0, '%.1f -> %.1f' % (b0, b3))
    p4 = os.path.join(tmp, 'plain.log')
    with open(p4, 'w') as f:
        f.write('PCAP_START rate=1000 n=20 settle=target gain=1.0 offset=-0.99 gate=off\n')
        f.write('PCAP 0 0 %s\n' % ' '.join(['30000'] * 20))
        f.write('PCAP_END n=20 dur_us=20000 pmax=5.00 reason=ok\n')
    lines4, rc4 = process(p4)
    check('yksisegmenttinen pcap-loki torjutaan', rc4 != 0 and any(
        ln.startswith('PSWEEP_NOSWEEP') for ln in lines4), str(lines4))
    print('\nRESULT: %d failed' % len(fails))
    return 1 if fails else 0

def main(argv):
    if '--selftest' in argv:
        sys.exit(selftest())
    if len(argv) < 2:
        sys.stderr.write('usage: psweep_read.py <sweep.log> | --selftest\n')
        sys.exit(2)
    lines, rc = process(argv[1])
    for ln in lines:
        print(ln)
    sys.exit(rc)

if __name__ == '__main__':
    main(sys.argv)
