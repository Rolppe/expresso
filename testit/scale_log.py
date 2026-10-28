#!/usr/bin/env python3
"""Log every scale sample from the BLE telemetry as CSV: epoch,grams.

The plateau detector answers "has it settled"; accuracy work needs the raw trace, so any window can
be re-cut afterwards for mean, sd and drift slope. Reads the phone's log only.
"""
import subprocess, re, sys, time

import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import localenv  # noqa: E402,F401  local.env -> os.environ (README: Local configuration)
ADB = os.environ.get('PICO_ADB') or os.path.expanduser('~/.local/share/platform-tools/adb')
PHONE = os.environ.get('PICO_PHONE', '192.0.2.11:5555')
rx = re.compile(r'\[DATA\] RX settings \{(.*)\}')
out = open(sys.argv[1] if len(sys.argv) > 1 else '/tmp/scale.csv', 'a', buffering=1)
proc = subprocess.Popen([ADB, '-s', PHONE, 'logcat', '-T', '1', '-v', 'time', '-s', 'flutter'],
                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1)
n = 0
for line in proc.stdout:
    m = rx.search(line)
    if not m:
        continue
    d = dict(p.split(': ', 1) for p in m.group(1).split(', ') if ': ' in p)
    if 'weight' not in d:
        continue
    try:
        g = float(d['weight'])
    except ValueError:
        continue
    out.write('%.3f,%.4f\n' % (time.time(), g))
    n += 1
