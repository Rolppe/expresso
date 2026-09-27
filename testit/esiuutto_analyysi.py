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

Uutto (EXPRESSO-UUTTO-8BAR): bim:1 jatkaa EU-riveja vaihesarakkeella 3/4 (tavoite EB_START, pito EB_HOLD, EB_END-
kentat); bim:0 kirjaa vanhan uuttosilmukan TS-rivit (pito = ensimmainen rivi, jolla paine >= tavoite - 0,1). Molemmista
samat suureet A/B-vertailuun: nousuaika pitoon, ylitys (huippu uuton alusta pidon 1. s:n loppuun), pienin paine pidon
1. s:ssa (~1 barin pudotukset), pidon 2-5 s keskiarvo ja pidon hajonta 1 s:n jalkeen. EU-riveilta p5, TS-riveilta
yksittainen 16,7 ms keskiarvo.

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
    rows, kind, hold_t, target, p5s = [], None, None, None, []
    brew = []
    for l in lines:
        f = l.split()
        if l.startswith('PI ') and len(f) >= 6:
            kind = kind or 'pim0'
            rows.append((int(f[1]) / 1000.0, float(f[2]), float(f[3])))
        elif l.startswith('EU ') and len(f) >= 7 and f[6] in ('3', '4'):
            m5 = re.search(r' p5=(\S+)', l)
            brew.append((int(f[1]) / 1000.0, float(m5.group(1)) if m5 else float(f[2])))
        elif l.startswith('EU ') and len(f) >= 7:
            kind = 'pim1'
            m5 = re.search(r' p5=(\S+)', l)
            rows.append((int(f[1]) / 1000.0, float(f[2]), float(f[3])))
            if m5: p5s.append((int(f[1]) / 1000.0, float(m5.group(1))))
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
    for key in ('EU_CUT', 'EU_COAST', 'EU_END', 'TS_END', 'PI_END', 'EB_START', 'EB_CUT', 'EB_COAST', 'EB_HOLD', 'EB_END'):
        l = next((x for x in lines if x.startswith(key + ' ') or x.startswith(key + '2 ')), '')
        kv[key] = dict(re.findall(r'(\w+)=(\S+)', l))
        # EU_END/EB_END on jaettu kolmeen riviin (<= 255 merkkia): kentat kaikilta
        for x in lines:
            if x.startswith((key + '2 ', key[:2] + '_VV ')) and key in ('EU_END', 'EB_END'):
                for k, v in re.findall(r'(\w+)=(\S+)', x): kv[key].setdefault(k, v)
    mb = re.search(r'bim=(\d)', ts)
    r = {'path': path, 'kind': kind, 'pim_ts': m.group(1) if m else '?', 'target': target, 'n': len(rows),
         'hold_t': hold_t, 'kv': kv, 'bim_ts': mb.group(1) if mb else '?'}
    if brew:
        eh = next((x for x in lines if x.startswith('EB_HOLD')), None)
        r['brew'] = brew_stats(brew, float(kv['EB_START'].get('target', 0) or max(v for _, v in brew)),
                               int(re.search(r't_ms=(\d+)', eh).group(1)) / 1000.0 if eh else None, 'bim1 (EU 3/4, p5)')
    else:
        tsr = [(int(l.split()[1]) / 1000.0, float(l.split()[2]), float(l.split()[3])) for l in lines
               if l.startswith('TS ') and len(l.split()) >= 6]
        if tsr:
            tgt = tsr[0][2]
            th = next((t for t, p, _ in tsr if p >= tgt - 0.1), None)
            r['brew'] = brew_stats([(t, p) for t, p, _ in tsr], tgt, th, 'bim0 (TS, 16,7 ms)')
    if hold_t is None:
        r['error'] = 'pito ei alkanut'
        r['max'] = max(p for _, p, _ in rows)
        return r
    rise = [p for t, p, _ in rows if t < hold_t + OVER_S]
    hold = [p for t, p, _ in rows if t >= hold_t + OVER_S]
    r['over'] = max(rise) - target
    if p5s:
        # Firmwaren EU_END over lasketaan 5 jakson keskiarvosta; sama tassa, yksittainen jakso heiluu
        r['over5'] = max(v for t, v in p5s if t - t0 < hold_t + OVER_S) - target
    r['max'] = max(p for _, p, _ in rows)
    if len(hold) >= 2:
        r['hold_mean'] = statistics.mean(hold)
        r['hold_sd'] = statistics.pstdev(hold)
        r['hold_dev'] = max(abs(p - target) for p in hold)
        r['hold_s'] = rows[-1][0] - hold_t - OVER_S
    return r


def brew_stats(rows, target, hold_t, kind):
    """Uuton suureet riveista [(t s, p)]: uuton alku = ensimmainen rivi."""
    b = {'kind': kind, 'target': target, 'n': len(rows)}
    if hold_t is None:
        b['error'] = 'pito ei alkanut (max %.2f)' % max(p for _, p in rows)
        return b
    t0 = rows[0][0]
    b['t_hold'] = hold_t - t0
    b['over'] = max(p for t, p in rows if t <= hold_t + OVER_S) - target
    first = [p for t, p in rows if hold_t <= t <= hold_t + OVER_S]
    b['drop'] = min(first) - target if first else float('nan')
    h25 = [p for t, p in rows if hold_t + 2.0 <= t < hold_t + 5.0]
    b['m25'] = statistics.mean(h25) - target if h25 else float('nan')
    hold = [p for t, p in rows if t >= hold_t + OVER_S]
    if len(hold) >= 2:
        b['hold_mean'], b['hold_sd'], b['hold_s'] = statistics.mean(hold), statistics.pstdev(hold), rows[-1][0] - hold_t
    return b


def show(r):
    print('== %s' % r['path'])
    if 'kind' not in r:
        print('   VIRHE: %s' % r['error']); return
    print('   tapa %s (TS_START pim=%s), tavoite %.2f bar, %d riviä' % (r['kind'], r['pim_ts'], r['target'], r['n']))
    if r.get('error'):
        print('   VIRHE: %s (max %.2f bar)' % (r['error'], r['max'])); return
    print('   nousuaika pitoon %.2f s, yliampuma %+.2f bar%s, koko ajon maksimi %.2f bar' % (
        r['hold_t'], r['over'], (' (p5 %+.2f)' % r['over5']) if 'over5' in r else '', r['max']))
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
    b = r.get('brew')
    if b:
        print('   UUTTO %s (TS_START bim=%s), tavoite %.2f bar, %d riviä' % (b['kind'], r['bim_ts'], b['target'], b['n']))
        if b.get('error'):
            print('   VIRHE: %s' % b['error'])
        else:
            print('   pitoon %.2f s, ylitys %+.2f bar, pienin pidon 1. s:ssa %+.2f bar, pidon 2-5 s ka %+.3f bar' % (
                b['t_hold'], b['over'], b['drop'], b['m25']))
            if 'hold_mean' in b:
                print('   pito %.1f s (1 s:n jälkeen): keskiarvo %.3f bar, sd %.3f bar' % (b['hold_s'], b['hold_mean'], b['hold_sd']))
        e, c = kv.get('EB_END') or {}, kv.get('EB_CUT') or {}
        if e:
            print('   EB: katkaisu p=%s rate=%s g=%s ff=%s tau=%s; ylitys (p5) %s, iskut %s, poistot %s, 10/20 ms %s/%s, '
                  'late %s, miss %s' % (c.get('p'), c.get('rate'), c.get('g'), c.get('ff'), c.get('tau'), e.get('over'),
                                        e.get('strokes'), e.get('rm'), e.get('sk10'), e.get('sk20'), e.get('late'), e.get('miss')))
            print('   EB: kello ikkunoita %s, opettaneita %s, sd %s us; opittu eb_ff %s eb_x %s eb_g %s eb_tau %s coast_s %s' % (
                e.get('windows'), e.get('learned'), e.get('sd_us'), e.get('eb_ff'), e.get('eb_x'), e.get('eb_g'),
                e.get('eb_tau'), e.get('coast_s')))


def main(paths):
    rs = [parse(p) for p in paths]
    for r in rs: show(r)
    ok = [r for r in rs if 'hold_sd' in r]
    if len(ok) > 1:
        print('== vertailu (yliampuma / pidon sd)')
        for r in ok:
            print('   %-5s %+.2f bar / %.3f bar  %s' % (r['kind'], r['over'], r['hold_sd'], r['path']))
    ub = [r for r in rs if r.get('brew') and 'm25' in r['brew']]
    if len(ub) > 1:
        print('== uuton vertailu (pitoon s / ylitys / pienin 1. s / 2-5 s ka)')
        for r in ub:
            b = r['brew']
            print('   %-20s %.2f / %+.2f / %+.2f / %+.3f  %s' % (b['kind'], b['t_hold'], b['over'], b['drop'], b['m25'], r['path']))
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2: sys.exit(__doc__)
    sys.exit(main(sys.argv[1:]))
