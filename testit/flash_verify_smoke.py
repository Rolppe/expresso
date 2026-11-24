#!/usr/bin/env python3
"""Smoke test for pico_dev.flash post-reset verify, verify log and git guard. Mock link: no device, no network."""
import glob
import hashlib
import json
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..')))
import pico_dev  # noqa: E402

results = []


def check(name, ok):
    results.append(ok)
    print('%s %s' % ('PASS' if ok else 'FAIL', name))


tmp = tempfile.mkdtemp()
data = b'print(1)\n'
good = hashlib.sha256(data).hexdigest()
open(os.path.join(tmp, 'a.py'), 'wb').write(data)
mpath = os.path.join(tmp, 'MANIFEST.json')
json.dump([{'name': '/a.py', 'sha256': good, 'size': len(data)}], open(mpath, 'w'))

state = {'sessions': 0, 'post_hash': good}


class FakeLink:
    def __init__(self):
        state['sessions'] += 1
        self.n = state['sessions']

    def enter_devsafe(self):
        pass

    def reset(self):
        pass


def fake_sha(link, name):
    return good if link.n == 1 else state['post_hash']


pico_dev.Link = FakeLink
pico_dev.pico_sha = fake_sha
pico_dev.POST_RESET_WAIT_S = 0
pico_dev.git_flash_warnings = lambda base: ('deadbeef', [])
time.sleep(0)
before = set(glob.glob(os.path.join(HERE, 'flash-*-verify.log')))
logs_dir_before = set(glob.glob(os.path.join(HERE, 'flash-*-verify.log')))
logpath = os.path.join(HERE, 'flash-%s-verify.log' % time.strftime('%Y%m%d'))
saved = open(logpath).read() if os.path.exists(logpath) else None

check('post-reset match -> OK', pico_dev.flash(mpath) is True and state['sessions'] == 2)
state.update(sessions=0, post_hash='bad')
check('post-reset mismatch -> FAIL', pico_dev.flash(mpath) is False)
log = open(logpath).read()
check('log has head, hash, MISMATCH', 'deadbeef' in log and 'MISMATCH' in log and good in log)

pico_dev.git_flash_warnings = lambda base: ('deadbeef', ['dirty'])
state.update(sessions=0, post_hash=good)
check('warning without --force blocks before link', pico_dev.flash(mpath) is False and state['sessions'] == 0)
check('warning with --force proceeds', pico_dev.flash(mpath, True) is True)

# restore log file to its prior state
if saved is None:
    os.remove(logpath)
else:
    open(logpath, 'w').write(saved)
print('RESULT %s %d/%d' % ('PASS' if all(results) else 'FAIL', sum(results), len(results)))
sys.exit(0 if all(results) else 1)
