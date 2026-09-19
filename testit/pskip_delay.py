#!/usr/bin/env python3
"""pskip_delay.py — PWM-1B3: pump-to-pressure-sensor delay from a gated pcap capture.

Usage:
  python3 pskip_delay.py <capture.log>   Parse a gated pcap log (gate=on), print PSKIP_*.
  python3 pskip_delay.py --selftest      Synthetic gated captures, prints RESULT: <n> failed.

`PSKIP_DELAY` is what a single gated capture can measure: the gap between the gate's rising edge
and the folded response peak. That is sääntö 5's combination (A)+(B) — the hydraulic delay from a
passed stroke reaching the sensor, PLUS the SSR's zero-crossing wait on the Pico's own clock (0 to
one mains half-cycle of unknown phase per gate reopening, PUMPPU-PWM.md "Vaihe 1b" sääntö 5). It
is not a pure hydraulic delay; separating (A) from (B) needs repeating the capture at several
`phase_us` values and reading the invariant `PSKIP_DELAY(p) - p` (sääntö 9).

Protocol (PUMPPU-PWM.md "Protokollalisäys vaiheeseen 1b"):
    PCAP_START rate=1000 n=<n> settle=target gain=<g> offset=<o> gate=on period_us=<T> on_us=<u>
               phase_us=<p>
    PCAP <idx> <t_us> <v0> <v1> ... <v19>
    PCAP_END n=<n> dur_us=<d> pmax=<bar> reason=<...>

A log without `gate=on` or without `phase_us` is not a portioned run this analyzer can read;
`PSKIP_NOGATE` is printed and the process exits non-zero. Portioning itself is never inferred from
the waveform — spec kohta 5 measured that unreliable — only trusted from the header.
"""

import math
import os
import random
import statistics
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mains_freq import parse_log, goertzel_amp, RAW_TO_BAR_GAIN, RAW_TO_BAR_OFFSET  # noqa: E402

FOLD_BINS = 40


def read_header(path):
    """Read the last PCAP_START line's gated-protocol fields that mains_freq.parse_log does not
    return: gate on/off, the gate period, and the sampling phase offset."""
    fields = {}
    with open(path, 'r', errors='replace') as f:
        for line in f:
            line = line.strip()
            if line.startswith('PCAP_START'):
                fields = dict(p.split('=', 1) for p in line.split()[1:] if '=' in p)
    return fields


def boxcar_diff(bar, L):
    """Residual = bar - centered boxcar(bar, L); drops L//2 samples from each end (sääntö 8: a
    boxcar the length of the gate period nulls the gate frequency and its harmonics, so the
    difference keeps them and removes everything slower, without the curvature a linear detrend
    would leave under the capture's exponential pressure decay)."""
    half = L // 2
    n = len(bar)
    return [bar[i] - sum(bar[i - half:i + half]) / L for i in range(half, n - half)]


def analyze(samples, dur_us, n, gain, offset, period_us, phase_us):
    """spec kohta 2: live-calibrated bar, boxcar residual, fold on the nominal 1000 us sample
    interval, spectrum on the real fs."""
    fs = n / (dur_us * 1e-6)
    bar = [gain * (v * RAW_TO_BAR_GAIN + RAW_TO_BAR_OFFSET) + offset for v in samples]
    L = int(round(period_us * fs / 1e6))
    half = L // 2
    res = boxcar_diff(bar, L)

    fold_sum = [0.0] * FOLD_BINS
    fold_cnt = [0] * FOLD_BINS
    for k, i in enumerate(range(half, n - half)):
        phase = ((i * 1000 + phase_us) % period_us) / float(period_us)
        b = min(int(phase * FOLD_BINS), FOLD_BINS - 1)
        fold_sum[b] += res[k]
        fold_cnt[b] += 1
    fold = [fold_sum[b] / fold_cnt[b] if fold_cnt[b] else 0.0 for b in range(FOLD_BINS)]

    best_bin = max(range(FOLD_BINS), key=lambda b: fold[b])
    delay_ms = (best_bin + 0.5) * period_us / FOLD_BINS / 1000.0
    amp = max(fold) - min(fold)

    sd_res = statistics.pstdev(res) if len(res) > 1 else 0.0
    per_bin = len(res) / float(FOLD_BINS)
    conf = amp / (2.0 * sd_res / math.sqrt(per_bin)) if sd_res > 1e-9 else float('inf')

    diffs = [fold[b] - fold[b + 20] for b in range(20)]
    rms = math.sqrt(sum(d * d for d in diffs) / len(diffs))
    asym = rms / amp if amp > 1e-9 else float('inf')

    sub_freq = 1e6 / period_us
    fund_freq = 1e6 / (period_us / 2.0)
    sub_amp = goertzel_amp(res, fs, sub_freq)
    fund_amp = goertzel_amp(res, fs, fund_freq)

    return {'fs': fs, 'fold': fold, 'bin': best_bin, 'delay_ms': delay_ms, 'amp': amp,
            'conf': conf, 'asym': asym, 'sub_freq': sub_freq, 'sub_amp': sub_amp,
            'fund_freq': fund_freq, 'fund_amp': fund_amp}


def print_result(res, phase_us, n):
    print('PSKIP phase_us=%d n=%d fs=%.1f Hz' % (phase_us, n, res['fs']))
    print('PSKIP_FOLD ' + ' '.join('%.3f' % v for v in res['fold']))
    print('PSKIP_DELAY %.1f ms conf=%.2f amp=%.3f bar' % (res['delay_ms'], res['conf'], res['amp']))
    print('PSKIP_ASYM %.2f' % res['asym'])
    print('PSKIP_SUB %.1f Hz amp=%.3f bar' % (res['sub_freq'], res['sub_amp']))
    print('PSKIP_FUND %.1f Hz amp=%.3f bar' % (res['fund_freq'], res['fund_amp']))
    if res['conf'] < 2.0:
        print('PSKIP_UNDECIDED conf alle 2.0 — ajo ei riitä päätökseen')


def load_and_analyze(path):
    """Returns a result dict, or None if the log is not a gated run (missing gate=on or
    phase_us)."""
    samples, dur_us, n, reason, gain, offset = parse_log(path)
    hdr = read_header(path)
    if not samples or not dur_us or not n or hdr.get('gate') != 'on' or 'phase_us' not in hdr:
        return None
    period_us = int(hdr['period_us'])
    phase_us = int(hdr['phase_us'])
    return analyze(samples, dur_us, n, gain, offset, period_us, phase_us), phase_us, n


# SELFTEST — synthetic gated capture, spec kohta 3

T_US, GATE_US = 19960, 39920
N_SELFTEST = 1500
RATE_US = 1000


def synth_bars(delay_us, mains_off_us=0, phase_us=0, gated=True, seed=1, n=N_SELFTEST):
    """Pressure as a bar series: exponentially decaying baseline (laitoksen aikavakio 0,81 s), a
    passed stroke adds a pulse `0.30 * exp(-(t - t_k - D) / 3 ms)` (0,30 bar mitattu väreily 7,7
    barissa), gaussian noise sd 0,36 bar (mitattu raakahajonta 7,69 barissa)."""
    rnd = random.Random(seed)
    bars = []
    for i in range(n):
        t = i * float(RATE_US)
        p = 7.7 - 0.8 * (1.0 - math.exp(-t / 810000.0))
        k = 0
        while True:
            tk = k * T_US + mains_off_us
            if tk > t:
                break
            passed = True if not gated else (((tk + phase_us) % GATE_US) < T_US)
            if passed and t >= tk + delay_us:
                p += 0.30 * math.exp(-(t - tk - delay_us) / 3000.0)
            k += 1
        bars.append(p + rnd.gauss(0.0, 0.36))
    return bars


def bars_to_raw(bars, gain=1.0, offset=-0.99):
    """Invert the factory formula the way a real capture with live calibration would be encoded."""
    return [max(0, min(65535, int(round(((b - offset) / gain - RAW_TO_BAR_OFFSET) / RAW_TO_BAR_GAIN))))
            for b in bars]


def write_log(path, raw, phase_us, gated=True, gain=1.0, offset=-0.99):
    n = len(raw)
    with open(path, 'w') as fh:
        if gated:
            fh.write('PCAP_START rate=%d n=%d settle=target gain=%.4f offset=%.3f gate=on '
                      'period_us=%d on_us=%d phase_us=%d\n'
                      % (RATE_US, n, gain, offset, GATE_US, T_US, phase_us))
        else:
            fh.write('PCAP_START rate=%d n=%d settle=target gain=%.4f offset=%.3f gate=off\n'
                      % (RATE_US, n, gain, offset))
        for r in range(n // 20):
            vals = ' '.join(str(v) for v in raw[r * 20:(r + 1) * 20])
            fh.write('PCAP %d %d %s\n' % (r * 20, r * 20 * RATE_US, vals))
        fh.write('PCAP_END n=%d dur_us=%d pmax=8.00 reason=ok\n' % (n, (n - 1) * RATE_US))
    return path


def selftest():
    fails = []
    max_err_ms = 0.0

    def check(name, cond, extra=''):
        print(('PASS ' if cond else 'FAIL ') + name + (' — ' + extra if extra else ''))
        if not cond:
            fails.append(name)

    def synth_gated_log(tmp, name, delay_us, seed, mains_off_us=0, phase_us=0,
                         gain=1.0, offset=-0.99):
        bars = synth_bars(delay_us, mains_off_us=mains_off_us, phase_us=phase_us, seed=seed)
        raw = bars_to_raw(bars, gain=gain, offset=offset)
        return write_log(os.path.join(tmp, name), raw, phase_us, gain=gain, offset=offset)

    tmp = tempfile.mkdtemp(prefix='pskip-delay-selftest-')

    # 1. D at 3, 9, 15 ms, mains_off=0, phase_us=0, seeds 1-3.
    for D_ms, seed in ((3, 1), (9, 2), (15, 3)):
        p = synth_gated_log(tmp, 'd%d.log' % D_ms, D_ms * 1000, seed)
        r, phase_us, n = load_and_analyze(p)
        err_ms = abs(r['delay_ms'] - D_ms)
        max_err_ms = max(max_err_ms, err_ms)
        check('D=%d ms: viive 2,0 ms sisallä (seed %d)' % (D_ms, seed), err_ms <= 2.0,
              'sai %.2f ms, ero %.3f ms' % (r['delay_ms'], err_ms))
        check('D=%d ms: conf >= 2.0' % D_ms, r['conf'] >= 2.0, 'conf=%.2f' % r['conf'])

    # 2. mains_off = 7000 us, D = 3 ms -> yhdistelma (A)+(B), odotettu 10 ms.
    p = synth_gated_log(tmp, 'off7.log', 3000, seed=4, mains_off_us=7000)
    r, phase_us, n = load_and_analyze(p)
    err_ms = abs(r['delay_ms'] - 10.0)
    max_err_ms = max(max_err_ms, err_ms)
    check('mains_off 7 ms nostaa viiveen 10 ms:iin', err_ms <= 2.0,
          'sai %.2f ms, ero %.3f ms' % (r['delay_ms'], err_ms))

    # 3. Toistettavuus: D = 9 ms, siemenet 1, 7, 11 -> sama bin (+-1 bin, 998 us).
    bins = []
    for seed in (1, 7, 11):
        p = synth_gated_log(tmp, 'rep%d.log' % seed, 9000, seed)
        r, phase_us, n = load_and_analyze(p)
        bins.append(r['bin'])
    check('kolme siementa antavat saman binin', max(bins) - min(bins) <= 1, str(bins))

    # 4. Kalibrointi: sama fysikaalinen bar-sarja, eri offset -> sama PSKIP_DELAY (boxcar poistaa
    # DC:n, joten jäännös on tarkalleen offsetista riippumaton lukuunottamatta pyoristysta).
    bars = synth_bars(9000, seed=5)
    raw_a = bars_to_raw(bars, gain=1.0, offset=-0.99)
    raw_b = bars_to_raw(bars, gain=1.0, offset=0.0)
    p_a = write_log(os.path.join(tmp, 'cal-a.log'), raw_a, 0, gain=1.0, offset=-0.99)
    p_b = write_log(os.path.join(tmp, 'cal-b.log'), raw_b, 0, gain=1.0, offset=0.0)
    r_a, _, _ = load_and_analyze(p_a)
    r_b, _, _ = load_and_analyze(p_b)
    check('offset ei muuta PSKIP_DELAY:aa', r_a['delay_ms'] == r_b['delay_ms'],
          '%.2f vs %.2f' % (r_a['delay_ms'], r_b['delay_ms']))

    print('\nsuurin viive-ero itsetestissa: %.3f ms' % max_err_ms)
    print('RESULT: %d failed' % len(fails))
    return 1 if fails else 0


def main(argv):
    if '--selftest' in argv:
        sys.exit(selftest())
    if len(argv) < 2:
        sys.stderr.write('usage: pskip_delay.py <capture.log> | --selftest\n')
        sys.exit(2)
    loaded = load_and_analyze(argv[1])
    if loaded is None:
        print('PSKIP_NOGATE tämä loki ei ole portitettu ajo')
        sys.exit(1)
    res, phase_us, n = loaded
    print_result(res, phase_us, n)


if __name__ == '__main__':
    main(sys.argv)
