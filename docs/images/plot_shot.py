#!/usr/bin/env python3
"""Plot one logged test shot from the device log testit/c1x-20261020-shot1.log.

The log is console output captured from a real Pico over USB serial (20 s test shot: 2.5 bar
pre-infusion, then 8 bar brew, water only). Lines used:
  EU <ms> <bar> <target> <pump_on> <duty> ... w=<scale g> f=<flow g/s>   (every 100 ms)
  EB_START t_ms=<ms>, EB_HOLD t_ms=<ms>, EU_HOLD t_ms=<ms>               (phase markers)
No smoothing or resampling is applied; the raw values are drawn.

Usage (needs matplotlib):  python3 docs/images/plot_shot.py [log] [out.png]
Run from the repository root.
"""
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

log = sys.argv[1] if len(sys.argv) > 1 else "testit/c1x-20261020-shot1.log"
out = sys.argv[2] if len(sys.argv) > 2 else "docs/images/shot-pressure-weight.png"

t, p, tgt, w, f = [], [], [], [], []
marks = {}
for line in open(log, encoding="utf-8", errors="replace"):
    m = re.match(r"^EU (\d+) (-?[\d.]+) ([\d.]+) .* w=([\d.]+) f=(-?[\d.]+)", line)
    if m:
        t.append(int(m[1]) / 1000)
        p.append(float(m[2]))
        tgt.append(float(m[3]))
        w.append(float(m[4]))
        f.append(float(m[5]))
        continue
    m = re.match(r"^(EU_HOLD|EB_START|EB_HOLD) t_ms=(\d+)", line)
    if m:
        marks[m[1]] = int(m[2]) / 1000

w0 = w[0]
w = [x - w0 for x in w]  # weight gained since the start of the shot

fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 5.2), sharex=True,
                             gridspec_kw={"height_ratios": [3, 2], "hspace": 0.08})
a1.plot(t, tgt, color="#999999", lw=1.4, ls="--", label="target pressure")
a1.plot(t, p, color="#c0392b", lw=1.6, label="measured pressure")
a1.set_ylabel("pressure (bar)")
a1.set_ylim(-1.5, 10)
a1.grid(alpha=0.25)

a2.plot(t, w, color="#1f5fa8", lw=1.6, label="water on scale")
a2.set_ylabel("weight gained (g)", color="#1f5fa8")
a2.set_xlabel("time since shot start (s)")
a2.grid(alpha=0.25)
a3 = a2.twinx()
a3.plot(t, f, color="#e08a00", lw=1.0, alpha=0.8, label="flow (g/s)")
a3.set_ylabel("flow (g/s)", color="#b86e00")

phases = [(0, marks.get("EB_START", 5.1), "pre-infusion 2.5 bar"),
          (marks.get("EB_START", 5.1), t[-1], "brew 8 bar")]
for ax in (a1, a2):
    for x0, x1, _ in phases[1:]:
        ax.axvline(x0, color="#555555", lw=0.8)
a1.text(phases[0][1] / 2, 9.2, phases[0][2], ha="center", fontsize=9)
a1.text((phases[1][0] + phases[1][1]) / 2, 9.2, phases[1][2], ha="center", fontsize=9)

h1, l1 = a1.get_legend_handles_labels()
h2, l2 = a2.get_legend_handles_labels()
h3, l3 = a3.get_legend_handles_labels()
a1.legend(h1, l1, loc="lower right", fontsize=8, frameon=False)
a2.legend(h2 + h3, l2 + l3, loc="upper left", fontsize=8, frameon=False)
a1.set_title("eXpresso: one logged test shot (device log, unprocessed samples)", fontsize=10)
fig.savefig(out, dpi=100, bbox_inches="tight")
print(out, len(t), "samples", "marks", marks)
