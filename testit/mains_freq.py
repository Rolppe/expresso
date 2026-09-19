#!/usr/bin/env python3
"""mains_freq.py — analyse a pcap: raw pressure capture for the mains frequency driving the pump.

Usage:
  python3 mains_freq.py <capture.log>   Parse a pico_dev.py capture log, print MAINS/HARM2.
  python3 mains_freq.py --selftest      Synthetic 50/60 Hz self-check, prints RESULT: <n> failed.

Protocol (PUMPPU-PWM.md "Kaappauksen sarjaprotokolla"):
    PCAP_START rate=1000 n=<n> settle_ms=1000
    PCAP <idx> <t_us> <v0> <v1> ... <v19>
    PCAP_END n=<n> dur_us=<d> pmax=<bar> reason=<ok|overpressure|switch|devsafe|stop>

Real sample rate comes from PCAP_END's dur_us/n, not the nominal 1000 Hz (sääntö, "Analysaattorin
sääntö"). A linear trend (pressure rising during the capture) is removed first. The half-wave
rectified pump gives one stroke per full mains cycle, so the fundamental is the mains frequency;
Goertzel runs at 0.1 Hz steps over 40.0-70.0 Hz for it and 80.0-140.0 Hz for the second harmonic.
"""

import sys
import math

# Raw-ADC -> bar, factory formula (classes.py:930). Capture is uncalibrated raw counts (sääntö 2),
# so only the linear gain is used for an AC amplitude (the offset is a DC shift, irrelevant here).
RAW_TO_BAR_GAIN = 0.000314936
RAW_TO_BAR_OFFSET = -3.522929

MAINS_BAND = (40.0, 70.0)
HARM2_BAND = (80.0, 140.0)
BAND_STEP_HZ = 0.1
PEAK_EXCLUDE_HZ = 1.0   # window excluded around the best bin before a second, distinct peak is sought


def parse_log(path):
    """Parse one pcap: capture out of a serial log; returns (samples, dur_us, n, reason) from the
    last PCAP_START..PCAP_END block found."""
    samples, dur_us, n, reason = [], None, None, None
    with open(path, 'r', errors='replace') as f:
        for line in f:
            line = line.strip()
            if line.startswith('PCAP_START'):
                samples, dur_us, n, reason = [], None, None, None
            elif line.startswith('PCAP_END'):
                fields = dict(p.split('=', 1) for p in line.split()[1:] if '=' in p)
                n = int(fields.get('n', len(samples)))
                dur_us = int(fields.get('dur_us', 0))
                reason = fields.get('reason', '')
            elif line.startswith('PCAP '):
                samples.extend(int(v) for v in line.split()[3:])   # idx, t_us, then 20 raw values
    return samples, dur_us, n, reason


def detrend(x):
    """Remove the least-squares linear trend (pressure rising during the capture, sääntö 2)."""
    n = len(x)
    if n < 2:
        return list(x)
    mean_i = (n - 1) / 2.0
    mean_x = sum(x) / n
    num = den = 0.0
    for i, v in enumerate(x):
        di = i - mean_i
        num += di * (v - mean_x)
        den += di * di
    slope = num / den if den else 0.0
    return [v - (mean_x + slope * (i - mean_i)) for i, v in enumerate(x)]


def goertzel_amp(x, fs, freq):
    """Goertzel single-frequency estimate; returns the equivalent sinusoid amplitude."""
    n = len(x)
    if n == 0:
        return 0.0
    coeff = 2.0 * math.cos(2.0 * math.pi * freq / fs)
    s1 = s2 = 0.0
    for v in x:
        s0 = v + coeff * s1 - s2
        s2, s1 = s1, s0
    power = max(0.0, s1 * s1 + s2 * s2 - coeff * s1 * s2)
    return 2.0 * math.sqrt(power) / n


def band_peak(x, fs, band, step=BAND_STEP_HZ, exclude_hz=PEAK_EXCLUDE_HZ):
    """Scan a frequency band at `step` Hz; return (freq, amp, conf), conf = best bin's amplitude
    over the highest amplitude of a second, distinct peak (outside +-exclude_hz of the best bin)."""
    f_lo, f_hi = band
    freqs = [f_lo + i * step for i in range(int(round((f_hi - f_lo) / step)) + 1)]
    amps = [goertzel_amp(x, fs, f) for f in freqs]
    best_i = max(range(len(amps)), key=lambda i: amps[i])
    best_f, best_amp = freqs[best_i], amps[best_i]
    second_amp = 0.0
    for f, a in zip(freqs, amps):
        if abs(f - best_f) >= exclude_hz and a > second_amp:
            second_amp = a
    conf = best_amp / second_amp if second_amp > 1e-9 else float('inf')
    return best_f, best_amp, conf


def analyze(raw_samples, fs):
    x = detrend([float(v) for v in raw_samples])
    mains_f, mains_amp, mains_conf = band_peak(x, fs, MAINS_BAND)
    harm_f, harm_amp, harm_conf = band_peak(x, fs, HARM2_BAND)
    return {'mains_f': mains_f, 'mains_amp': mains_amp * RAW_TO_BAR_GAIN, 'mains_conf': mains_conf,
            'harm_f': harm_f, 'harm_amp': harm_amp * RAW_TO_BAR_GAIN, 'harm_conf': harm_conf}


def print_result(r):
    print('MAINS %.1f Hz amp=%.3f bar conf=%.2f' % (r['mains_f'], r['mains_amp'], r['mains_conf']))
    print('HARM2 %.1f Hz amp=%.3f bar' % (r['harm_f'], r['harm_amp']))


# SELFTEST — synthetic half-wave-rectified pump waveform at 50.0 and 60.0 Hz

def synth_capture(freq_hz, n=2000, dt_s=0.001, noise_sd_bar=0.25, ramp_bar=2.0, base_bar=5.0,
                   stroke_amp_bar=0.6, seed=0):
    """A mains-driven pump strokes once per positive half-cycle (diode half-wave rectified,
    PUMPPU-PWM.md sääntö 3): max(0, sin(2*pi*f*t)). Add noise and the ramp a real capture rides on
    top of, then convert to raw ADC counts (factory formula)."""
    import random
    rnd = random.Random(seed)
    duration_s = n * dt_s
    samples = []
    for i in range(n):
        t = i * dt_s
        stroke = max(0.0, math.sin(2.0 * math.pi * freq_hz * t)) * stroke_amp_bar
        bar = base_bar + ramp_bar * (t / duration_s) + stroke + rnd.gauss(0.0, noise_sd_bar)
        raw = int(max(0, min(65535, round((bar - RAW_TO_BAR_OFFSET) / RAW_TO_BAR_GAIN))))
        samples.append(raw)
    return samples, 1.0 / dt_s


def selftest():
    fails = []

    def check(name, cond, extra=''):
        print(('PASS ' if cond else 'FAIL ') + name + (' — ' + extra if extra else ''))
        if not cond:
            fails.append(name)

    for expected in (50.0, 60.0):
        samples, fs = synth_capture(expected, seed=int(expected))
        r = analyze(samples, fs)
        print_result(r)
        check('%.1f Hz found within 0.5 Hz' % expected, abs(r['mains_f'] - expected) <= 0.5,
              'got %.1f Hz' % r['mains_f'])
        check('%.1f Hz conf > 2.0' % expected, r['mains_conf'] > 2.0, 'got conf=%.2f' % r['mains_conf'])

    print('\nRESULT: %d failed' % len(fails))
    return 1 if fails else 0


def main(argv):
    if '--selftest' in argv:
        sys.exit(selftest())
    if len(argv) < 2:
        sys.stderr.write('usage: mains_freq.py <capture.log> | --selftest\n')
        sys.exit(2)
    samples, dur_us, n, reason = parse_log(argv[1])
    if not samples or not dur_us or not n:
        sys.stderr.write('no PCAP data found in %s\n' % argv[1])
        sys.exit(1)
    fs = 1e6 * n / dur_us   # real sample rate, from PCAP_END's dur_us/n, not the nominal 1000 Hz
    r = analyze(samples, fs)
    print_result(r)
    if r['mains_conf'] < 2.0:
        print('note: conf below 2.0, not enough to decide (reason=%s)' % reason)


if __name__ == '__main__':
    main(sys.argv)
