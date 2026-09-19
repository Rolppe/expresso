#!/usr/bin/env python3
"""build_set.py — rakentaa uuden firmware-setin puhelimeen vanhan setin päälle.

Kopioi pohjasetin puhelimen yksityisessä tallennuksessa (``run-as ... cp -r``), työntää
muuttuneet tiedostot ``/data/local/tmp/``:n kautta ja todentaa jokaisen paikallisen SHA-256:n
puhelimen ``sha256sum``-tulostetta vasten. Lopuksi laskee ``MANIFEST.json``:in puhelimen omasta
``sha256sum``- ja ``stat``-tulosteesta koko uudelle setille ja todentaa sen samalla tavalla.
Katso Infra/iot/expresso/PICO-HALLINTA.md luku 6.

Käyttö:
  build_set.py <uusi> [--from <pohja>] [tiedosto...]
  build_set.py --check <uusi> [--from <pohja>] [tiedosto...]   # ei yhtään muuttavaa komentoa

Ilman ``--from`` pohja on uusin setti (``ls -1t``). Ilman tiedostolistaa: ``pico/*.py``,
``pico/scale_cal.json``, ``pico/lib/*.py`` (paikallisesta Infra/iot/expresso/pico/-hakemistosta).
Adb valitaan ympäristöstä kuten pico_dev.py:ssä: ``PICO_ADB``, muuten
``~/.local/share/platform-tools/adb``.
"""
import argparse
import glob
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PICO_DIR = os.path.join(HERE, 'pico')
ADB = os.environ.get('PICO_ADB') or os.path.expanduser('~/.local/share/platform-tools/adb')
PHONE = '192.0.2.11:5555'
APP = 'com.example.silvia_pico_ui'
SETS_DIR = 'files/firmware_backup'
MIN_BATTERY = 20


def adb(*args, check=True):
    return subprocess.run([ADB, '-s', PHONE] + list(args), capture_output=True, text=True, check=check)


def run_as(shell_cmd, check=True):
    return adb('shell', 'run-as', APP, 'sh', '-c', shell_cmd, check=check)


def default_files():
    names = []
    for pattern in ('*.py', 'scale_cal.json', 'lib/*.py'):
        for path in sorted(glob.glob(os.path.join(PICO_DIR, pattern))):
            names.append(os.path.relpath(path, PICO_DIR))
    return names


def local_sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def _strip_common_prefix(paths):
    prefix = os.path.commonprefix(paths)
    if '/' in prefix:
        return prefix[:prefix.rfind('/') + 1]
    return ''


def parse_sha256sum(text):
    """`sha256sum`-tulosteen jäsennys: pilkkoo hash+polku-rivit ja lyhentää rivien yhteisen
    alkuosan pois niin että avaimet ovat '/tiedosto'-muotoisia setin juuren suhteen."""
    entries = []
    for line in text.strip('\n').split('\n'):
        line = line.rstrip('\r')
        if not line.strip():
            continue
        h, path = line.split('  ', 1)
        entries.append((h, path))
    rows = {}
    if not entries:
        return rows
    prefix = _strip_common_prefix([p for _, p in entries])
    for h, path in entries:
        name = path[len(prefix):] if path.startswith(prefix) else path
        if not name.startswith('/'):
            name = '/' + name
        rows[name] = h
    return rows


def parse_stat_sizes(text):
    """`stat -c '%n %s'`-tulosteen jäsennys samalla yhteisen alkuosan lyhennyksellä kuin
    parse_sha256sum."""
    entries = []
    for line in text.strip('\n').split('\n'):
        line = line.rstrip('\r')
        if not line.strip():
            continue
        path, size = line.rsplit(' ', 1)
        entries.append((path, int(size)))
    sizes = {}
    if not entries:
        return sizes
    prefix = _strip_common_prefix([p for p, _ in entries])
    for path, size in entries:
        name = path[len(prefix):] if path.startswith(prefix) else path
        if not name.startswith('/'):
            name = '/' + name
        sizes[name] = size
    return sizes


def build_manifest(rows, sizes):
    """Manifesti on JSON-lista {'name','size','sha256'}; MANIFEST.json itse ei ole listassa.
    Jokaisella merkinnällä on oltava kokonaislukukoko — puuttuva koko (esim. stat epäonnistui) on
    virhe, joka keskeyttää ajon ennen manifestin työntämistä."""
    man = []
    missing = []
    for name, sha in sorted(rows.items()):
        if name == '/MANIFEST.json':
            continue
        size = sizes.get(name)
        if size is None:
            missing.append(name)
        man.append({'name': name, 'size': size, 'sha256': sha})
    if missing:
        raise RuntimeError('koko puuttuu manifestista: %s' % ', '.join(missing))
    return man


def list_remote_files(dir_path):
    """Tiedostojen suhteelliset nimet `dir_path`:n alla (`find <dir> -type f`)."""
    r = run_as('find %s -type f' % dir_path)
    if r.returncode != 0:
        raise RuntimeError('tiedostolistaus epäonnistui: %s: %s' % (dir_path, r.stderr.strip()))
    prefix = dir_path.rstrip('/') + '/'
    names = set()
    for line in r.stdout.strip('\n').split('\n'):
        if not line.strip():
            continue
        names.add(line[len(prefix):] if line.startswith(prefix) else line)
    return names


def list_sets():
    r = run_as('ls -1t %s' % SETS_DIR, check=False)
    if r.returncode != 0:
        return []
    return [l for l in r.stdout.strip('\n').split('\n') if l.strip()]


def device_ready():
    r = adb('devices', check=False)
    if r.returncode != 0:
        return False
    for line in r.stdout.strip('\n').split('\n')[1:]:
        if line.startswith(PHONE) and line.split('\t')[-1].strip() == 'device':
            return True
    return False


def battery_pct():
    r = adb('shell', 'dumpsys', 'battery', check=False)
    if r.returncode != 0:
        return None
    for line in r.stdout.split('\n'):
        line = line.strip()
        if line.startswith('level:'):
            try:
                return int(line.split(':', 1)[1].strip())
            except ValueError:
                return None
    return None


def preflight(new_name, base, files):
    """Ei yhtään muuttavaa komentoa. Palauttaa (preflight-rivi, estosyyt, pohjasetin nimi)."""
    reasons = []
    ready = device_ready()
    if not ready:
        reasons.append('adb ei vastaa')
    pct = battery_pct() if ready else None
    if ready and (pct is None or pct < MIN_BATTERY):
        reasons.append('akku alle %d %%' % MIN_BATTERY)
    sets = list_sets() if ready else []
    resolved_base = base or (sets[0] if sets else None)
    if ready and (resolved_base is None or resolved_base not in sets):
        reasons.append('pohjasettia ei ole')
    if ready and new_name in sets:
        reasons.append('uusi setti on jo olemassa')
    line = ('preflight: adb=%s device=%s battery=%s%% base=%s push=%d'
            % ('ok' if ready else 'unreachable',
               'device' if ready else 'unknown',
               pct if pct is not None else '?',
               resolved_base or '?',
               len(files)))
    return line, reasons, resolved_base


def push_and_verify(local_path, remote_name, new_dir):
    tmp_name = '/data/local/tmp/%s' % remote_name.replace('/', '_')
    local_hash = local_sha256(local_path)
    r = adb('push', local_path, tmp_name)
    if r.returncode != 0:
        raise RuntimeError('push epäonnistui: %s: %s' % (local_path, r.stderr.strip()))
    dest = '%s/%s' % (new_dir, remote_name)
    dest_parent = os.path.dirname(dest)
    if dest_parent:
        run_as('mkdir -p %s' % dest_parent)
    run_as('cp %s %s' % (tmp_name, dest))
    r = run_as('sha256sum %s' % dest)
    remote_hash = r.stdout.split()[0] if r.stdout.strip() else ''
    if remote_hash != local_hash:
        raise RuntimeError('SHA-256-ristiriita: %s paikallinen=%s puhelin=%s'
                            % (remote_name, local_hash, remote_hash))


def build(new_name, base, files):
    new_dir = '%s/%s' % (SETS_DIR, new_name)
    base_dir = '%s/%s' % (SETS_DIR, base)
    r = run_as('cp -r %s %s' % (base_dir, new_dir))
    if r.returncode != 0:
        raise RuntimeError('pohjan kopiointi epäonnistui: %s' % r.stderr.strip())

    # `adb shell` ei kaikissa versioissa välitä etäkomennon paluuarvoa, joten epäonnistunut
    # `cp -r` voi näyttää onnistuneelta — todenna listaamalla molemmat puolet.
    base_files = list_remote_files(base_dir)
    new_files = list_remote_files(new_dir)
    print('base=%d new=%d' % (len(base_files), len(new_files)))
    missing_from_copy = sorted(base_files - new_files)
    if missing_from_copy:
        raise RuntimeError('pohjan kopiointi jätti puuttumaan: %s' % ', '.join(missing_from_copy))

    for name in files:
        push_and_verify(os.path.join(PICO_DIR, name), name, new_dir)

    r = run_as("find %s -type f ! -name MANIFEST.json -exec sha256sum {} \\;" % new_dir)
    if r.returncode != 0:
        raise RuntimeError('sha256sum-ajo epäonnistui: %s' % r.stderr.strip())
    rows = parse_sha256sum(r.stdout)
    r = run_as("find %s -type f ! -name MANIFEST.json -exec stat -c '%%n %%s' {} \\;" % new_dir)
    if r.returncode != 0:
        raise RuntimeError('stat-ajo epäonnistui: %s' % r.stderr.strip())
    sizes = parse_stat_sizes(r.stdout)
    manifest = build_manifest(rows, sizes)

    manifest_local = os.path.join(HERE, '.manifest_tmp.json')
    with open(manifest_local, 'w') as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
        f.write('\n')
    try:
        push_and_verify(manifest_local, 'MANIFEST.json', new_dir)
    finally:
        os.remove(manifest_local)

    restore_cmd = ('%s -s %s shell am start -n %s/.MainActivity --es espressopico_restore_backup %s'
                   % (ADB, PHONE, APP, new_name))
    print('Setti %s valmis (%d tiedostoa + MANIFEST.json).' % (new_name, len(files)))
    print('Palautuskomento:')
    print('  %s' % restore_cmd)
    print('ÄLÄ KOSKE SARJALINKKIIN ENNEN RESTORE_OK-RIVIÄ.')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('new_name')
    ap.add_argument('--from', dest='base', default=None)
    ap.add_argument('--check', action='store_true')
    ap.add_argument('files', nargs='*')
    args = ap.parse_args(argv)

    files = args.files or default_files()
    line, reasons, resolved_base = preflight(args.new_name, args.base, files)
    print(line)

    if args.check:
        if reasons:
            print('preflight-esto: ' + ', '.join(reasons))
        return 1 if reasons else 0

    if reasons:
        print('preflight-esto: ' + ', '.join(reasons), file=sys.stderr)
        return 1

    build(args.new_name, resolved_base, files)
    return 0


if __name__ == '__main__':
    sys.exit(main())
