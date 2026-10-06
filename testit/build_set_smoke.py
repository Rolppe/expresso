#!/usr/bin/env python3
"""build_set_smoke.py — build_set.py kirjoittaa puhelimeen työnnetyn manifestin myös repon pico/MANIFEST.json:iin.

Valeadb: run_as, list_remote_files ja push_and_verify korvataan, PICO_DIR osoittaa väliaikaishakemistoon.

    python3 testit/build_set_smoke.py      RESULT: <n> failed, epänolla paluuarvo jos punaisia

Tapaukset: (a) onnistunut ajo -> repon manifesti = puhelimen manifesti, väliaikaistiedosto poistettu;
(b) manifestin työntö epäonnistuu -> repon vanha manifesti ennallaan, väliaikaistiedosto poistettu.
"""
import json, os, sys, tempfile, types
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import build_set as b
fail = 0
def setup():
    d = tempfile.mkdtemp(); os.mkdir(os.path.join(d, 'pico'))
    open(os.path.join(d, 'pico', 'MANIFEST.json'), 'w').write('OLD\n')
    b.HERE = d; b.PICO_DIR = os.path.join(d, 'pico'); return d
def run_as(cmd, check=True):
    out = ''
    if 'sha256sum' in cmd: out = 'aa  files/x/new/a.py\nbb  files/x/new/lib/c.py\n'
    elif 'stat' in cmd: out = 'files/x/new/a.py 10\nfiles/x/new/lib/c.py 20\n'
    return types.SimpleNamespace(returncode=0, stdout=out, stderr='')
b.run_as = run_as
b.list_remote_files = lambda d: {'a.py'}
# success
d = setup(); b.push_and_verify = lambda *a: None
b.build('new', 'old', [])
m = json.load(open(os.path.join(d, 'pico', 'MANIFEST.json')))
ok = m == [{'name': '/a.py', 'sha256': 'aa', 'size': 10}, {'name': '/lib/c.py', 'sha256': 'bb', 'size': 20}] and not os.path.exists(os.path.join(d, '.manifest_tmp.json'))
print('success repo manifest:', 'ok' if ok else 'FAIL %r' % m); fail += not ok
# push failure keeps old repo manifest
d = setup()
def bad(local, name, nd):
    if name == 'MANIFEST.json': raise RuntimeError('SHA-256-ristiriita')
b.push_and_verify = bad
try: b.build('new', 'old', []); print('FAIL no raise'); fail += 1
except RuntimeError: pass
ok = open(os.path.join(d, 'pico', 'MANIFEST.json')).read() == 'OLD\n' and not os.path.exists(os.path.join(d, '.manifest_tmp.json'))
print('push failure keeps old:', 'ok' if ok else 'FAIL'); fail += not ok
print('RESULT: %d failed' % fail); sys.exit(fail)
