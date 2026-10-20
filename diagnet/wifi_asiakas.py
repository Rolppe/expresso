#!/usr/bin/env python3
"""wifi_asiakas.py — äpin suoran Wi-Fi-kanavan testiasiakas (EXPRESSO-WIFI-APPI vaihe 1, paketit/WIFI-APPI.md luku 4).

    python3 diagnet/wifi_asiakas.py --avain-tiedosto <polku> [--host 192.0.2.13] [--s 5] [komento ...]

Tekee saman kuin äppi: `hello` → boot-id, `sub`, annetut komennot allekirjoitettuina, ja tulostaa vastaanotetut
oliot tiivistettynä (lajit ja määrät, ackit, asetukset, mittaa live-tahdin). Avainta ei tulosteta koskaan.
"""

import argparse
import collections
import hashlib
import hmac
import json
import socket
import sys
import time


def laji(d):
    t = d.get('type')
    if t:
        return '%s:%s' % (t, d.get('part', d.get('r', '')))
    if 'boiler_temperature' in d:
        return 'live'
    if 'weight_g' in d:
        return 'vaaka'
    if 'brew_pressure' in d:
        return 'asetukset_B'
    if 'fast_heatup_mode' in d:
        return 'asetukset_A'
    if 'cal_phase' in d:
        return 'cal'
    if 'pcal_state' in d:
        return 'pcal'
    return '?'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--avain-tiedosto', required=True)
    ap.add_argument('--host', default='192.0.2.13')
    ap.add_argument('--portti', type=int, default=47211)
    ap.add_argument('--s', type=float, default=5.0)
    ap.add_argument('komennot', nargs='*')
    a = ap.parse_args()
    avain = bytes.fromhex(open(a.avain_tiedosto).read().strip())
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0.2)
    kohde = (a.host, a.portti)

    def vastaanota(kesto):
        loppu = time.time() + kesto
        out = []
        while time.time() < loppu:
            try:
                data, _ = s.recvfrom(4096)
            except socket.timeout:
                continue
            out.append((time.time(), json.loads(data)))
        return out

    t0 = time.time()
    s.sendto(b'EXA1 hello', kohde)
    hello = [d for _, d in vastaanota(1.0) if d.get('type') == 'hello']
    if not hello:
        print('EI_HELLO %s:%d' % kohde)
        return 2
    boot = hello[0]['boot']
    print('HELLO boot=%s %.0f ms' % (boot, (time.time() - t0) * 1000))
    seq = [int(time.time())]

    def laheta(cmd):
        seq[0] += 1
        m = hmac.new(avain, ('%s %d %s' % (boot, seq[0], cmd)).encode(), hashlib.sha256).hexdigest()[:16]
        s.sendto(('EXA1 %s %d %s %s' % (boot, seq[0], m, cmd)).encode(), kohde)

    laheta('sub')
    for k in a.komennot:
        laheta(k)
    saadut = vastaanota(a.s)
    lajit = collections.Counter(laji(d) for _, d in saadut)
    print('SAADUT', dict(lajit))
    for _, d in saadut:
        if d.get('type') == 'ack':
            print('ACK', d)
    live = [t for t, d in saadut if 'boiler_temperature' in d]
    if len(live) > 1:
        print('LIVE %.1f Hz' % ((len(live) - 1) / (live[-1] - live[0])))
    viim = {}
    for _, d in saadut:
        viim[laji(d)] = d
    for k in ('live', 'vaaka', 'asetukset_A', 'asetukset_B', 'cal'):
        if k in viim:
            print(k.upper(), json.dumps(viim[k]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
