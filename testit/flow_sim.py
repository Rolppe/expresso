#!/usr/bin/env python3
"""Which real-time flow estimator, given the measured scale? Host-only, no device.

Measured on the Pico 18.9.2026 (flow_rate_probe.py): one sample every 86.2 ms (11.6 Hz),
single-sample sd 0.22-0.26 g, consecutive-difference sd = sd*sqrt(2) -> white noise.
Also measured: single-sample -16 g glitches in 0.19 % of samples, tray creep after hot water
~0.2-0.7 g/s, restricted test-shot flow 2.3 g/s, free flow 8.7 g/s.

Scores each candidate on the same synthetic shot: noise while flow is steady, latency to 90 % of
the step, and worst error caused by one -16 g glitch.
"""
import math
import random
import statistics as st

DT = 0.0862
SIGMA = 0.25
GLITCH_P = 0.0019
GLITCH_G = -16.0
FLOW = 2.3            # restricted test shot
DRIFT = 0.2           # tray creep, g/s
T_START = 4.0
T_END = 29.0
T_TOTAL = 34.0


def truth(t):
    """True tray mass (g) at time t, with a 0.4 s ramp at shot start and 0.8 s tail at the end."""
    if t < T_START:
        return DRIFT * t
    base = DRIFT * t
    a = min(t - T_START, 0.4)
    m = 0.5 * FLOW * a * a / 0.4 + FLOW * max(0.0, t - T_START - 0.4)
    if t > T_END:
        d = min(t - T_END, 0.8)
        m -= 0.5 * FLOW * d * d / 0.8          # after-flow decays over 0.8 s
        m = m  # tail keeps adding, decaying
    return base + m


def true_flow(t):
    if t < T_START:
        return 0.0
    if t < T_START + 0.4:
        return FLOW * (t - T_START) / 0.4
    if t <= T_END:
        return FLOW
    if t < T_END + 0.8:
        return FLOW * (1 - (t - T_END) / 0.8)
    return 0.0


def samples(seed=1, glitches=True):
    random.seed(seed)
    out = []
    t = 0.0
    while t < T_TOTAL:
        g = truth(t) + random.gauss(0, SIGMA)
        if glitches and random.random() < GLITCH_P:
            g += GLITCH_G
        out.append((t, g))
        t += DT
    return out


# ------------------------------------------------------------ estimators --
def ls_window(hist, span):
    """Least squares slope over the last `span` seconds."""
    t_last = hist[-1][0]
    h = [p for p in hist if t_last - p[0] <= span]
    n = len(h)
    if n < 3:
        return None
    t0 = h[0][0]
    sx = sy = sxx = sxy = 0.0
    for t, g in h:
        x = t - t0
        sx += x
        sy += g
        sxx += x * x
        sxy += x * g
    den = n * sxx - sx * sx
    if abs(den) < 1e-9:
        return None
    return (n * sxy - sx * sy) / den


def run_ls(data, span, median3=False, hist_n=64):
    hist = []
    raw = []
    out = []
    for t, g in data:
        raw.append((t, g))
        if median3:
            if len(raw) < 3:
                continue
            g = sorted(x[1] for x in raw[-3:])[1]
            t = raw[-2][0]                      # median of 3 -> one sample of delay
        hist.append((t, g))
        if len(hist) > hist_n:
            hist.pop(0)
        f = ls_window(hist, span)
        out.append((data[-1][0] if False else t, f))
    return out


def run_median8_ls16(data):
    """What the firmware has today: median of a window of 8, then LS over 16 filtered values."""
    buf = []
    hist = []
    out = []
    for t, g in data:
        buf.append(g)
        if len(buf) > 8:
            buf.pop(0)
        v = sorted(buf)
        if len(v) >= 5:
            v = v[1:-1]
        gf = sum(v) / len(v)
        hist.append((t, gf))
        if len(hist) > 16:
            hist.pop(0)
        out.append((t, ls_window(hist, 99.0)))
    return out


def run_alpha_beta(data, tau, median3=False):
    """Critically damped double-exponential tracker: state mass + flow, one sample of memory.
    alpha/beta from a chosen time constant tau (s): alpha = 1-exp(-dt/tau) shaped for slope."""
    a = 1 - math.exp(-DT / tau)
    alpha = 1 - (1 - a) ** 2
    beta = a * a
    m = None
    f = 0.0
    raw = []
    out = []
    for t, g in data:
        raw.append((t, g))
        if median3:
            if len(raw) < 3:
                continue
            g = sorted(x[1] for x in raw[-3:])[1]
            t = raw[-2][0]
        if m is None:
            m = g
            out.append((t, 0.0))
            continue
        m_pred = m + f * DT
        r = g - m_pred
        m = m_pred + alpha * r
        f = f + (beta / DT) * r
        out.append((t, f))
    return out


# ---------------------------------------------------------------- scoring --
def score(name, fn, seeds=(1, 2, 3, 4, 5)):
    noises, lats, worst = [], [], []
    for s in seeds:
        clean = fn(samples(s, glitches=False))
        steady = [f for t, f in clean if T_START + 3 < t < T_END - 1 and f is not None]
        noises.append(st.stdev(steady))
        bias = st.mean(steady) - (FLOW + DRIFT)
        lat = None
        for t, f in clean:
            if f is not None and t > T_START and f >= 0.9 * (FLOW + DRIFT):
                lat = t - T_START
                break
        lats.append(lat if lat is not None else float('nan'))
        dirty = fn(samples(s, glitches=True))
        w = 0.0
        for (t, f), (t2, fc) in zip(dirty, clean):
            if f is not None and fc is not None and T_START < t < T_END:
                w = max(w, abs(f - fc))
        worst.append(w)
    print('%-34s kohina sd %5.2f g/s   viive 90%% %5.2f s   pahin piikkivirhe %6.2f g/s   harha %+.2f'
          % (name, st.mean(noises), st.mean(lats), max(worst), bias))


if __name__ == '__main__':
    print('Synteettinen uutto: tosi virtaus %.1f g/s, ryomintaharha %.1f g/s, sd %.2f g, %.1f Hz'
          % (FLOW, DRIFT, SIGMA, 1 / DT))
    print()
    score('nyt: median8 -> LS16 (1,4 s)', run_median8_ls16)
    for span in (0.5, 0.75, 1.0, 1.5, 2.0):
        score('LS raaka %.2f s' % span, lambda d, s=span: run_ls(d, s))
    for span in (0.75, 1.0, 1.5):
        score('LS med3 %.2f s' % span, lambda d, s=span: run_ls(d, s, median3=True))
    for tau in (0.2, 0.35, 0.5, 0.75):
        score('alpha-beta tau %.2f s' % tau, lambda d, x=tau: run_alpha_beta(d, x))
    for tau in (0.35, 0.5):
        score('alpha-beta med3 tau %.2f s' % tau, lambda d, x=tau: run_alpha_beta(d, x, median3=True))
