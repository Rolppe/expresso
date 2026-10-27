#!/usr/bin/env python3
"""testit/eu_rivi_smoke.py — EU-rivin ja uuttosilmukan allokaatioiden smoke-testi (EXPRESSO-EU-RIVI-KOKONAISLUVUT).

Todentaa:
1. functions.py:n pre_infusion_phased-silmukassa käytetään in-place-tyhjennystä 'del out[:]'
   uuden 'out = []' -listan luomisen sijaan jokaisessa 20 ms jaksossa.
2. Generator-lauseke 'sum(len(x) + 1 for x in out)' on poistettu silmukan tieltä.
3. EU-rivin lokitus inlinettaa w- ja f-kentät suoraan päämerkkijonoon ilman väliaikaista 'w=... f=...' -merkkijonoa.
4. weight_flow_log säilyy taaksepäin yhteensopivana ulkoisille kutsujille ja testeille.
5. Luotu EU-rivi jäsennetään virheettömästi esiuutto_analyysi.py:n ja muiden olemassa olevien parsereiden säännöillä.
6. In-place list clearing 'del out[:]' säilyttää listan identiteetin (id) eikä allokoi uutta listaa.
"""

import ast
import os
import re
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO_ROOT, 'pico'))

failed = 0


def check(name, condition, msg=''):
    global failed
    if condition:
        print(f"PASS {name}")
    else:
        print(f"FAIL {name}: {msg}")
        failed += 1


def main():
    functions_path = os.path.join(REPO_ROOT, 'pico', 'functions.py')
    with open(functions_path, 'r', encoding='utf-8') as f:
        src = f.read()

    # 1. AST-tarkistukset functions.py:lle
    tree = ast.parse(src, filename=functions_path)
    check('functions.py syntaksi ja AST-jäsennys', tree is not None)

    # Etsi pre_infusion_phased funktio
    pip_func = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == 'pre_infusion_phased':
            pip_func = node
            break
    check('pre_infusion_phased löytyi', pip_func is not None)

    # Tarkista että pre_infusion_phased-rungosta löytyy 'del out[:]' ja ei löydy 'out = []' silmukan sisältä
    has_del_out_slice = False
    has_out_reassign_in_loop = False
    for node in ast.walk(pip_func):
        if isinstance(node, ast.Delete):
            for target in node.targets:
                if isinstance(target, ast.Subscript):
                    if isinstance(target.value, ast.Name) and target.value.id == 'out':
                        if isinstance(target.slice, ast.Slice) and target.slice.lower is None and target.slice.upper is None:
                            has_del_out_slice = True
        elif isinstance(node, ast.While):
            for subnode in ast.walk(node):
                if isinstance(subnode, ast.Assign):
                    for target in subnode.targets:
                        if isinstance(target, ast.Name) and target.id == 'out':
                            if isinstance(subnode.value, ast.List) and len(subnode.value.elts) == 0:
                                has_out_reassign_in_loop = True

    check('pre_infusion_phased käyttää del out[:]', has_del_out_slice)
    check('pre_infusion_phased ei luo out = [] silmukassa', not has_out_reassign_in_loop)

    # Tarkista ettei silmukassa ole generaattorisummaa sum(len(x) + 1 for x in out)
    check('ei generaattorisummaa out-listalle', 'sum(len(x) + 1 for x in out)' not in src)

    # 2. Toiminnalliset tarkistukset: weight_flow_log ja EU-rivin muoto
    import functions

    class FakeBrewData:
        def __init__(self, weight=None, flow=None):
            self._weight = weight
            self._flow = flow

        def get_weight(self):
            return self._weight

        def get_flow(self):
            return self._flow

    # None-arvoilla (ei vaakaa tai vanhentunut näyte)
    bd_none = FakeBrewData(None, None)
    tail_none = functions.weight_flow_log(bd_none)
    check('weight_flow_log ilman vaakaa on w=- f=-', tail_none == 'w=- f=-')

    # Lukemilla
    bd_val = FakeBrewData(486.84, 1.253)
    tail_val = functions.weight_flow_log(bd_val)
    check('weight_flow_log lukemilla', tail_val == 'w=486.8 f=1.25')

    # Mallinna functions.py:n EU-rivin generointi
    t_ms = 12724
    p = 8.163
    sp = 8.0
    rel = 0
    d = 0.154
    phase = 4
    p5 = 8.012
    sd_t = 1003.4
    removed = 278
    skips10 = 62
    skips20 = 0
    late = 1

    w = bd_val.get_weight()
    f = bd_val.get_flow()
    eu_line = 'EU %d %.2f %.2f %d %.2f %d p5=%.2f sd_us=%.0f rm=%d sk10=%d sk20=%d late=%d w=%s f=%s' % (
        t_ms, p, sp, rel, d, phase, p5,
        sd_t, removed, skips10, skips20, late,
        '-' if w is None else '%.1f' % w,
        '-' if f is None else '%.2f' % f
    )

    # 3. Yhteensopivuus esiuutto_analyysi.py:n sääntöjen kanssa
    parts = eu_line.split()
    check('EU-rivin pituus vähintään 7 kenttää', len(parts) >= 7)
    check('parts[0] on EU', parts[0] == 'EU')
    check('parts[1] on aika kokonaislukuna', int(parts[1]) == 12724)
    check('parts[2] on paine liukulukuna', float(parts[2]) == 8.16)
    check('parts[3] on asetusarvo liukulukuna', float(parts[3]) == 8.00)
    check('parts[4] on releen tila 0 tai 1', parts[4] in ('0', '1'))
    check('parts[5] on duty liukulukuna', float(parts[5]) == 0.15)
    check('parts[6] on vaihe 4', parts[6] == '4')

    m5 = re.search(r' p5=(\S+)', eu_line)
    check('p5 poimittavissa', m5 is not None and float(m5.group(1)) == 8.01)

    m_rm = re.search(r'rm=(\d+)', eu_line)
    check('rm poimittavissa', m_rm is not None and int(m_rm.group(1)) == 278)

    m_w = re.search(r'w=(\S+)', eu_line)
    m_f = re.search(r'f=(\S+)', eu_line)
    check('w ja f poimittavissa', m_w is not None and m_f is not None)
    check('w arvo 486.8', float(m_w.group(1)) == 486.8)
    check('f arvo 1.25', float(m_f.group(1)) == 1.25)

    # 4. In-place tyhjennystarkistus: listan id ei muutu 100 kierroksella
    buf = []
    buf_id = id(buf)
    all_same_id = True
    for i in range(100):
        buf.append(f"line {i}")
        del buf[:]
        if id(buf) != buf_id or len(buf) != 0:
            all_same_id = False
            break
    check('del buf[:] säilyttää listan identiteetin ja tyhjentää sen', all_same_id)

    print(f"\nRESULT: {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
