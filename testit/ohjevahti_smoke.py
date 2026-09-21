"""Holdout for EXPRESSO-OHJEVAHTI (paketit/OHJEVAHTI.md, spec OHJEVAHTI.spec.md).

Feeds ohjevahti.py the 20.9.2026 deviations (OHJEPOIKKEAMAT-20260920.konteksti.md) as PreToolUse
stdin and checks the decision. Planner-owned: the executor must not edit this file.
"""
import json
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(HERE, '..', 'ohjevahti.py')
TMP = tempfile.mkdtemp(prefix='ohjevahti-')
KIRJA = os.path.join(TMP, 'OHJEKIRJA.json')
TILA = os.path.join(TMP, 'tila.json')

O1 = {'id': 'O-1', 'pvm': '2026-09-20', 'lahde': '1f997ae0:1176', 'tila': 'voimassa',
      'lainaus': 'aja 20 taukoa samalla 5ms viiveellä', 'tyyppi': 'arvo',
      'komento': 'pgap', 'kentta': 'n', 'arvo': 20}
O2 = {'id': 'O-2', 'pvm': '2026-09-20', 'lahde': '1f997ae0:1232', 'tila': 'voimassa',
      'lainaus': 'älä huolehdi paineesta nyt', 'tyyppi': 'kielto', 'komento': 'mcal'}
O3 = {'id': 'O-3', 'pvm': '2026-09-20', 'lahde': '1f997ae0:1560', 'tila': 'voimassa',
      'lainaus': 'kaukalo pitää tyhjentää ajojen välissä', 'tyyppi': 'valivaihe',
      'komento': 'pgap', 'vaihe': 'kaukalon tyhjennys', 'kuitattu_klo': None}
O4 = dict(O1, id='O-4', arvo=40, tila='korvattu')

fails = []


def write_kirja(rows, raw=None):
    with open(KIRJA, 'w') as f:
        f.write(raw if raw is not None else json.dumps({'ohjeet': rows}, ensure_ascii=False))


def reset_tila():
    if os.path.exists(TILA):
        os.remove(TILA)


def run(command, env_kirja=True):
    env = dict(os.environ, OHJEVAHTI_TILA=TILA)
    env['OHJEVAHTI_KIRJA'] = KIRJA if env_kirja else os.path.join(TMP, 'puuttuu.json')
    stdin = json.dumps({'hook_event_name': 'PreToolUse', 'tool_name': 'Bash',
                        'tool_input': {'command': command}})
    p = subprocess.run([sys.executable, HOOK], input=stdin, capture_output=True, text=True,
                       env=env, timeout=20)
    if p.returncode != 0:
        return 'EXIT%d' % p.returncode, p.stdout + p.stderr
    if not p.stdout.strip():
        return None, ''
    out = json.loads(p.stdout)['hookSpecificOutput']
    return out['permissionDecision'], out.get('permissionDecisionReason', '')


def expect(name, command, decision, must=(), must_not=(), env_kirja=True):
    got, reason = run(command, env_kirja)
    ok = got == decision and all(m in reason for m in must) and not any(m in reason for m in must_not)
    print('%-4s %-44s %s' % ('OK' if ok else 'FAIL', name, got))
    if not ok:
        fails.append(name)
        print('     reason: %r' % reason[:400])


D = 'python3 Infra/iot/expresso/pico_dev.py '

write_kirja([O1, O2, O4])
reset_tila()
expect('1 ei laitekomento', 'git status --short', None)
expect('2 pgap n=40 vs O-1 n=20', D + 'pgap 7.0:40:350:5:20 out.log', 'deny', ('ERO', 'O-1', '20'))
expect('3 pgap n=20 ohjeen mukaan', D + 'pgap 7.0:20:350:5:20', 'ask',
       ('O-1', 'aja 20 taukoa'), ('ERO', 'KIELTO'))
expect('4 pgap n puuttuu', D + 'pgap 7.0', 'deny', ('ERO', 'O-1'))
expect('5 mcal kiellon aikana', D + 'cmd mcal:500', 'deny', ('KIELTO', 'O-2', 'älä huolehdi'))
expect('6 mcal:stop pääsee', D + 'cmd mcal:stop', None)
expect('7 ketjutettu komento', 'cd /x && ' + D + 'cmd pgap:7.0:40', 'deny', ('ERO',))
expect('8 verify ja safe pääsevät', D + 'verify m.json; ' + D + 'safe', None)
expect('9 korvattu rivi ohitetaan', D + 'pgap 7.0:20', 'ask', ('O-1',), ('O-4', 'ERO'))

write_kirja([O3])
reset_tila()
expect('10 ensimmäinen ajo', D + 'pgap 7.0:20', 'ask', ('O-3',))
expect('11 toinen ajo ilman tyhjennystä', D + 'pgap 7.0:20', 'deny', ('VÄLIVAIHE', 'kaukalon tyhjennys'))
time.sleep(1.1)
write_kirja([dict(O3, kuitattu_klo=time.time())])
expect('12 kuittauksen jälkeen', D + 'pgap 7.0:20', 'ask', ('O-3',), ('VÄLIVAIHE',))
expect('13 heti perään uudestaan', D + 'pgap 7.0:20', 'deny', ('VÄLIVAIHE',))

time.sleep(1.1)
write_kirja([dict(O3, kuitattu_klo=time.time())])
time.sleep(1.1)
expect('13b grep lukee pico_dev.py:tä', 'grep -n pgap Infra/iot/expresso/pico_dev.py', None)
expect('13c sed lukee pico_dev.py:tä', 'sed -n 1,5p pico_dev.py | head', None)
expect('13d luku ei kirjannut ajoa', D + 'pgap 7.0:20', 'ask', ('O-3',), ('VÄLIVAIHE',))

reset_tila()
expect('14 ohjekirja puuttuu', D + 'pgap 7.0:20', 'ask', ('ohjekirja tyhjä',), env_kirja=False)
write_kirja(None, raw='{rikki')
expect('15 rikkinäinen ohjekirja', D + 'pgap 7.0:20', 'deny', ('OHJEKIRJA',))

print('OHJEVAHTI_SMOKE %s (%d virhettä)' % ('PASS' if not fails else 'FAIL', len(fails)))
sys.exit(1 if fails else 0)
