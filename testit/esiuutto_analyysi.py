#!/usr/bin/env python3
"""esiuutto_analyysi.py — esiuuton laitelokien vertailu (EXPRESSO-ESIUUTTO-25BAR, 24.9.2026).

Lukee testiuuton lokin (`pico_dev.py shot`), tunnistaa esiuuton tavan TS_START-rivin `pim=`-kentasta
ja sen riveista, ja laskee molemmille samat suureet:
  - pim:0 (lahtotaso): PI-rivit (100 ms, 16,7 ms keskiarvo); pito alkaa ensimmaisesta rivista, jolla
    rampattu asetusarvo on palannut tavoitteeseen (tai paine >= tavoite - 0,1, jos ramppia ei nay).
  - pim:1: EU-rivit (100 ms, jaksokeskipaine 20 ms); pito EU_HOLD-rivista.
Suureet: nousuaika tavoitteeseen, yliampuma (huippu nousussa ja pidon ensimmaiset 1,0 s -
tavoite), pidon keskiarvo ja hajonta 1 s:n jalkeen, pidon suurin poikkeama. pim:1:lta lisaksi
EU_CUT/EU_COAST/EU_END-kentat (katkaisu, jalkinousu, 10/20 ms tauot, myohastymiset, kello).

    python3 testit/esiuutto_analyysi.py <loki> [<loki> ...]
"""
import re
import statistics
import sys

OVER_S = 1.0     # vanhan PI:n yliampuma tuli pidon alun jalkeen (18.9.2026: 2,0 -> 3,84 bar)


def parse(path):
    text = open(path, errors='replace').read()
    lines = text.splitlines()
    ts = next((l for l in lines if l.startswith('TS_START')), '')
    m = re.search(r'pim=(\d)', ts)
    rows, kind, hold_t, target = [], None, None, None
    for l in lines:
        f = l.split()
        if l.startswith('PI ') and len(f) >= 6:
            kind = kind or 'pim0'
            rows.append((int(f[1]) / 1000.0, float(f[2]), float(f[3])))
        elif l.startswith('EU ') and len(f) >= 7:
            kind = 'pim1'
            rows.append((int(f[1]) / 1000.0, float(f[2]), float(f[3])))
        elif l.startswith('EU_HOLD'):
            hold_t = int(re.search(r't_ms=(\d+)', l).group(1)) / 1000.0
        elif l.startswith('EU_START'):
            target = float(re.search(r'target=(\S+)', l).group(1))
    if not rows:
        return {'path': path, 'error': 'ei PI- eika EU-riveja'}
    t0 = rows[0][0]
    rows = [(t - t0, p, sp) for t, p, sp in rows]
    if hold_t is not None:
        hold_t -= t0 if kind == 'pim0' else 0.0
    if target is None:
        target = max(sp for _, _, sp in rows)
    if kind == 'pim0':
        ramp_seen = False
        for t, p, sp in rows:
            if sp < target - 1e-6: ramp_seen = True
            elif ramp_seen: hold_t = t; break
        if hold_t is None:
            hold_t = next((t for t, p, _ in rows if p >= target - 0.1), None)
    kv = {}
    for key in ('EU_CUT', 'EU_COAST', 'EU_END', 'TS_END', 'PI_END'):
        l = next((x for x in lines if x.startswith(key)), '')
        kv[key] = dict(re.findall(r'(\w+)=(\S+)', l))
    r = {'path': path, 'kind': kind, 'pim_ts': m.group(1) if m else '?', 'target': target, 'n': len(rows),
         'hold_t': hold_t, 'kv': kv}
    if hold_t is None:
        r['error'] = 'pito ei alkanut'
        r['max'] = max(p for _, p, _ in rows)
        return r
    rise = [p for t, p, _ in rows if t < hold_t + OVER_S]
    hold = [p for t, p, _ in rows if t >= hold_t + OVER_S]
    r['over'] = max(rise) - target
    r['max'] = max(p for _, p, _ in rows)
    if len(hold) >= 2:
        r['hold_mean'] = statistics.mean(hold)
        r['hold_sd'] = statistics.pstdev(hold)
        r['hold_dev'] = max(abs(p - target) for p in hold)
        r['hold_s'] = rows[-1][0] - hold_t - OVER_S
    return r


def show(r):
    print('== %s' % r['path'])
    if 'kind' not in r:
        print('   VIRHE: %s' % r['error']); return
    print('   tapa %s (TS_START pim=%s), tavoite %.2f bar, %d riviä' % (r['kind'], r['pim_ts'], r['target'], r['n']))
    if r.get('error'):
        print('   VIRHE: %s (max %.2f bar)' % (r['error'], r['max'])); return
    print('   nousuaika pitoon %.2f s, yliampuma %+.2f bar, koko ajon maksimi %.2f bar' % (r['hold_t'], r['over'], r['max']))
    if 'hold_mean' in r:
        print('   pito %.1f s: keskiarvo %.3f bar, sd %.3f bar, suurin poikkeama %.2f bar' % (
            r['hold_s'], r['hold_mean'], r['hold_sd'], r['hold_dev']))
    kv = r['kv']
    if kv['EU_CUT']:
        c, co = kv['EU_CUT'], kv['EU_COAST']
        print('   katkaisu p=%s rate=%s coast_s=%s ennuste=%s; jälkinousu %s -> coast_s %s' % (
            c.get('p'), c.get('rate'), c.get('coast_s'), c.get('pred'), co.get('rise'), co.get('coast_s')))
    if kv['EU_END']:
        e = kv['EU_END']
        print('   iskut %s, poistettu %s, tauot 10 ms %s / 20 ms %s, late %s, miss %s' % (
            e.get('strokes'), e.get('rm'), e.get('sk10'), e.get('sk20'), e.get('late'), e.get('miss')))
        print('   kello: ikkunoita %s (heikkoja %s), opettaneita %s, hz %s, sd %s us; reason %s' % (
            e.get('windows'), e.get('win_low'), e.get('learned'), e.get('hz'), e.get('sd_us'), e.get('reason')))


def main(paths):
    rs = [parse(p) for p in paths]
    for r in rs: show(r)
    ok = [r for r in rs if 'hold_sd' in r]
    if len(ok) > 1:
        print('== vertailu (yliampuma / pidon sd)')
        for r in ok:
            print('   %-5s %+.2f bar / %.3f bar  %s' % (r['kind'], r['over'], r['hold_sd'], r['path']))
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2: sys.exit(__doc__)
    sys.exit(main(sys.argv[1:]))
