#!/usr/bin/env python3
"""diagnet_keraaja_smoke.py — keräimen (diagnet/keraaja.py) holdout-testi, EXPRESSO-DIAGNET.

Käynnistää keräimen aliprosessina satunnaisella vapaalla portilla, väliaikaisella tilahakemistolla ja
paikallisella vale-HA:lla (HTTP-palvelin); oikeaan HA:han ei koskaan oteta yhteyttä. Lähettää EXD1-paketteja
UDP:llä ja tarkistaa lokitiedostot sekä vale-HA:n saamat kutsut.

    python3 testit/diagnet_keraaja_smoke.py        RESULT: <n> failed, epänolla paluuarvo jos punaisia
"""

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

KERAAJA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'diagnet', 'keraaja.py')
sys.path.insert(0, os.path.dirname(KERAAJA))
import keraaja as K

FAILED = []
TOKEN = 'testitoken-123'


def check(name, ok):
    print(('ok   ' if ok else 'FAIL ') + name)
    if not ok:
        FAILED.append(name)


def odota(fn, t=6.0):
    """Toistaa fn:ää kunnes tosi tai aika loppuu; palauttaa viimeisen arvon."""
    loppu = time.monotonic() + t
    while True:
        v = fn()
        if v or time.monotonic() > loppu:
            return v
        time.sleep(0.05)


class ValeHA:
    def __init__(self):
        self.kutsut = []        # (polku, auth, runko)
        self.tila = 'ok'        # ok | slow | fail
        self.lukko = threading.Lock()
        ha = self

        class H(BaseHTTPRequestHandler):
            def do_POST(self):
                runko = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or b'null')
                if ha.tila == 'slow':
                    time.sleep(2)
                with ha.lukko:
                    ha.kutsut.append((self.path, self.headers.get('Authorization'), runko))
                self.send_response(500 if ha.tila == 'fail' else 200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{}')

            def log_message(self, *a):
                pass

        self.palvelin = ThreadingHTTPServer(('127.0.0.1', 0), H)
        self.palvelin.daemon_threads = True
        self.portti = self.palvelin.server_address[1]
        threading.Thread(target=self.palvelin.serve_forever, daemon=True).start()

    def lista(self):
        with self.lukko:
            return list(self.kutsut)

    def tilat(self, nimi):
        return [r for p, _, r in self.lista() if p == '/api/states/sensor.espresso_diag_' + nimi]

    def viimeinen(self, nimi):
        t = self.tilat(nimi)
        return t[-1] if t else None

    def tapahtumat(self):
        return [r for p, _, r in self.lista() if p == '/api/events/espresso_diag']

    def sulje(self):
        self.palvelin.shutdown()


def vapaa_portti():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('127.0.0.1', 0))
    p = s.getsockname()[1]
    s.close()
    return p


class Instanssi:
    def __init__(self, ha, tmp, *lisa):
        self.tmp = tmp
        self.tila = os.path.join(tmp, 'tila')
        self.portti = vapaa_portti()
        self.lokitiedosto = os.path.join(tmp, 'keraaja.loki')
        token = os.path.join(tmp, 'token')
        with open(token, 'w') as f:
            f.write(TOKEN + '\n')
        self.loki = open(self.lokitiedosto, 'w')
        self.proc = subprocess.Popen(
            [sys.executable, KERAAJA, '--osoite', '127.0.0.1', '--portti', str(self.portti), '--tila', self.tila,
             '--ha-url', 'http://127.0.0.1:%d' % ha.portti, '--token', token] + list(lisa),
            stdout=self.loki, stderr=subprocess.STDOUT)
        self.sok = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.valmis = odota(lambda: 'kuuntelee' in self.lokiteksti(), 5)

    def lokiteksti(self):
        return open(self.lokitiedosto).read()

    def laheta(self, boot, seq, data, up_ms=1000, drop=0):
        if isinstance(data, str):
            data = data.encode()
        self.sok.sendto(('EXD1 %s %d %d %d\n' % (boot, seq, up_ms, drop)).encode() + data, ('127.0.0.1', self.portti))

    def raaka(self, data):
        self.sok.sendto(data, ('127.0.0.1', self.portti))

    def paivarivit(self):
        """Päivälokin rivit: (aika, boot, rivi)."""
        rivit = []
        try:
            tiedostot = [f for f in os.listdir(self.tila) if re.fullmatch(r'\d{4}-\d\d-\d\d\.log', f)]
        except OSError:
            return rivit
        for f in sorted(tiedostot):
            for r in open(os.path.join(self.tila, f), encoding='utf-8').read().splitlines():
                m = re.fullmatch(r'(\S+) ([0-9a-f]{8}) (.*)', r)
                rivit.append(m.groups() if m else (None, None, r))
        return rivit

    def tekstit(self):
        return [r for _, _, r in self.paivarivit()]

    def sulje(self):
        self.proc.terminate()
        try:
            self.proc.wait(5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self.loki.close()


HB = 'DIAG_HB up_s=%s free=%s alloc=5000 drop=%s txp=3 txerr=0 smax_us=900 rssi=-60 brew=0 pend=0\n'


def main():
    # K0 oletusarvot spekin mukaan
    check('K0 portti 47210, offline 150 s, rate 5 s', (K.PORTTI, K.OFFLINE_S, K.RATE_S) == (47210, 150, 5))

    # K0b offline 150 s oikealla oletuksella ilman odotusta (in-process, valejulkaisija)
    class Valejulkaisija:
        def __init__(self):
            self.s = []

        def sensori(self, nimi, state, attr=None):
            self.s.append((nimi, state))

        def tapahtuma(self, *a):
            pass
    tmp0 = tempfile.mkdtemp(prefix='diagnet-k0-')
    vj = Valejulkaisija()
    k = K.Keraaja(tmp0, vj, K.OFFLINE_S)
    k.paketti(b'EXD1 aaaaaaaa 0 1 0\nx\n')
    k.viimeinen -= 149
    k.tikki()
    check('K0b 149 s hiljaisuutta: ei vielä offline', ('status', 'offline') not in vj.s)
    k.viimeinen -= 2
    k.tikki()
    check('K0b 151 s hiljaisuutta: offline', ('status', 'offline') in vj.s)
    k.lopeta()
    shutil.rmtree(tmp0, ignore_errors=True)

    ha = ValeHA()
    tmp = tempfile.mkdtemp(prefix='diagnet-smoke-')
    ins = Instanssi(ha, tmp, '--rate-s', '1.5', '--shot-rate-s', '1.5')
    try:
        check('K1 keräin käynnistyi ja kuuntelee', ins.valmis)
        if not ins.valmis:
            print(ins.lokiteksti())
            print('RESULT: %d failed' % len(FAILED))
            return 1
        A, B = 'aaaa0001', 'bbbb0002'

        # K2 rivi jakautuu kahteen pakettiin, DIAG_BOOT, HB
        ins.laheta(A, 0, 'DIAG_BOOT rc=1 fw=t1 mac=aabbccddeeff\nHALKAISTU_RI')
        ins.laheta(A, 1, 'VI x=1\n' + HB % (60, 123456, 0))
        r = odota(lambda: 'HALKAISTU_RIVI x=1' in ins.tekstit() and any(t.startswith('DIAG_HB') for t in ins.tekstit()))
        check('K2 jaettu rivi liitetty yhteen', r)
        rivit = ins.paivarivit()
        check('K2 rivimuoto "<ISO-aika> <boot> <rivi>"',
              bool(rivit) and all(re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}[+-]\d\d:\d\d', a or '') and b == A
                                  for a, b, _ in rivit))
        check('K2 DIAG_BOOT-rivi lokissa', 'DIAG_BOOT rc=1 fw=t1 mac=aabbccddeeff' in ins.tekstit())

        # K3 HA: tila, sensorit, tapahtuma, token
        check('K3 status online', odota(lambda: (ha.viimeinen('status') or {}).get('state') == 'online'))
        check('K3 uptime 60', odota(lambda: (ha.viimeinen('uptime') or {}).get('state') == '60'))
        check('K3 mem_free ja rssi', odota(lambda: (ha.viimeinen('mem_free') or {}).get('state') == '123456'
                                           and (ha.viimeinen('rssi') or {}).get('state') == '-60'))
        rc = odota(lambda: ha.viimeinen('reset_cause'))
        check('K3 reset_cause state 1, attribuutit rc/fw', bool(rc) and rc['state'] == '1'
              and rc['attributes']['rc'] == '1' and rc['attributes']['fw'] == 't1')
        check('K3 boots == 1', odota(lambda: (ha.viimeinen('boots') or {}).get('state') == '1'))
        ev = odota(lambda: [e for e in ha.tapahtumat() if e.get('kind') == 'BOOT'])
        check('K3 BOOT-tapahtuma {kind,line,boot}', bool(ev) and ev[0]['boot'] == A and ev[0]['line'].startswith('DIAG_BOOT')
              and set(ev[0]) == {'kind', 'line', 'boot'})
        check('K3 Authorization: Bearer <token>', ha.lista() and all(a == 'Bearer ' + TOKEN for _, a, _ in ha.lista()))

        # K4 seq-aukko -> [LOST n]
        ins.laheta(A, 2, 'ENNEN_AUKKOA\n')
        ins.laheta(A, 5, 'AUKON_JALKEEN\n')
        check('K4 seq 2 -> 5: [LOST 2] ennen jatkoa', odota(lambda: 'AUKON_JALKEEN' in ins.tekstit()))
        t = ins.tekstit()
        check('K4 järjestys ENNEN_AUKKOA, [LOST 2], AUKON_JALKEEN',
              'ENNEN_AUKKOA' in t and '[LOST 2]' in t and t.index('ENNEN_AUKKOA') < t.index('[LOST 2]') < t.index('AUKON_JALKEEN'))
        ins.laheta(A, 5, 'KAKSOIS\n')
        ins.laheta(A, 6, 'SEURAAVA\n')
        odota(lambda: 'SEURAAVA' in ins.tekstit())
        t = ins.tekstit()
        check('K4 kaksoiskappale (sama seq) ohitetaan', 'KAKSOIS' not in t and t.count('[LOST 2]') == 1 and '[LOST 1]' not in t)

        # K5 ei-EXD1-paketit ohitetaan ja lasketaan
        ins.raaka(b'hei maailma')
        ins.raaka(b'EXD2 aaaa0001 7 1 0\nVAARA_VERSIO\n')
        ins.raaka(b'EXD1 EIHEKSA 7 1 0\nVAARA_BOOT\n')
        ins.laheta(A, 7, HB % (61, 1, 0))
        check('K5 ei-EXD1 ei lokiin', odota(lambda: any(x.startswith('DIAG_HB up_s=61') for x in ins.tekstit()))
              and not any(w in ' '.join(ins.tekstit()) for w in ('hei maailma', 'VAARA_VERSIO', 'VAARA_BOOT')))
        check('K5 ei-EXD1 laskettu (status ei_exd1 == 3)',
              odota(lambda: ((ha.viimeinen('status') or {}).get('attributes') or {}).get('ei_exd1') == 3))
        check('K5 ei-EXD1 kirjattu keräimen lokiin', 'ei-EXD1' in ins.lokiteksti())

        # K6 uusi boot: osittainen rivi ulos vanhana bootina, kokoaminen alusta, ei LOST-väärinhälytystä
        ins.laheta(A, 8, 'OSITTAINEN_ILMAN_RIVINVAIHTOA')
        ins.laheta(B, 0, 'DIAG_BOOT rc=0 fw=t2 mac=aabbccddeeff\nUUSI_BOOT_RIVI\n')
        r = odota(lambda: 'UUSI_BOOT_RIVI' in ins.tekstit())
        pr = ins.paivarivit()
        check('K6 osittainen rivi liuotettu vanhan bootin rivinä',
              r and ('OSITTAINEN_ILMAN_RIVINVAIHTOA' in [x for a, b, x in pr if b == A]))
        check('K6 uuden bootin rivit kantavat uutta boot-id:tä ja osittainen ei liity niihin',
              [x for a, b, x in pr if b == B][:2] == ['DIAG_BOOT rc=0 fw=t2 mac=aabbccddeeff', 'UUSI_BOOT_RIVI']
              and not any('OSITTAINEN_ILMAN_RIVINVAIHTOADIAG' in x for x in ins.tekstit()))
        check('K6 uusi boot seq 0: ei [LOST]-riviä sen jälkeen', ins.tekstit().count('[LOST 2]') == 1
              and not any(x.startswith('[LOST') and b == B for a, b, x in pr))
        check('K6 boots == 2 ja reset_cause rc 0',
              odota(lambda: (ha.viimeinen('boots') or {}).get('state') == '2'
                    and (ha.viimeinen('reset_cause') or {}).get('state') == '0'))

        # K7 END / GUARD_TRIP / DEVSAFE / Traceback / MemoryError: tapahtuma heti, sensorit
        time.sleep(1.6)  # rate-ikkuna auki, jotta tapahtumien ei tarvitse odottaa sitä
        n0 = len(ha.tapahtumat())
        t0 = time.monotonic()
        ins.laheta(B, 1, 'PB_END loops=100 max_loop_ms=45 reason=done\nGUARD_TRIP pump reason=overtemp\n'
                         'GUARD_TRIP heater reason=dry\nDEVSAFE x=1\nTraceback (most recent call last):\n'
                         '  File "main.py", line 1\nMemoryError: boom\n')
        kuvat = odota(lambda: len(ha.tapahtumat()) - n0 >= 6, 1.0)
        dt = time.monotonic() - t0
        uudet = ha.tapahtumat()[n0:]
        check('K7 6 tapahtumaa alle 1 s:ssa, ei rate-rajoitusta (2 GUARD_TRIP peräkkäin)', kuvat and dt < 1.2)
        check('K7 tapahtumalajit', sorted(e['kind'] for e in uudet) ==
              sorted(['END', 'GUARD_TRIP', 'GUARD_TRIP', 'DEVSAFE', 'TRACEBACK', 'MEMORYERROR']))
        check('K7 tapahtuman line ja boot', any(e['kind'] == 'END' and e['line'] == 'PB_END loops=100 max_loop_ms=45 reason=done'
                                                and e['boot'] == B for e in uudet))
        le = odota(lambda: ha.viimeinen('last_end'))
        check('K7 last_end state = reason, attribuutit key=value',
              bool(le) and le['state'] == 'done' and le['attributes']['loops'] == '100'
              and le['attributes']['max_loop_ms'] == '45')
        check('K7 max_loop_ms sensori', odota(lambda: (ha.viimeinen('max_loop_ms') or {}).get('state') == '45'))
        lg = odota(lambda: ha.viimeinen('last_guard_trip'))
        check('K7 last_guard_trip sisältää rivin ja ajan', bool(lg) and lg['state'].startswith('GUARD_TRIP')
              and 'aika' in lg['attributes'])

        # K8 uutto: shot-tiedosto, DIAG_S-sensorit, EU_STALL-laskuri
        time.sleep(1.6)
        ins.laheta(B, 2, 'ENNEN_UUTTOA\nDIAG_SHOT start\nDIAG_S t=0 T=930 p=100 f=0 w=0 r=1\n')
        ins.laheta(B, 3, 'EU_STALL x=1\nDIAG_S t=100 T=931 p=250 f=150 w=5 r=1\nDIAG_SHOT end reason=done n=2\nUUTON_JALKEEN\n')
        odota(lambda: 'UUTON_JALKEEN' in ins.tekstit())
        shotit = [f for f in os.listdir(ins.tila) if re.fullmatch(r'shot-\d{8}-\d{6}-%s\.log' % B, f)]
        check('K8 shot-<aika>-<boot>.log luotu', len(shotit) == 1)
        sisalto = open(os.path.join(ins.tila, shotit[0])).read() if shotit else ''
        check('K8 shot-tiedostossa start..end, ei ennen/jälkeen',
              'DIAG_SHOT start' in sisalto and 'DIAG_SHOT end reason=done n=2' in sisalto and 'EU_STALL' in sisalto
              and 'ENNEN_UUTTOA' not in sisalto and 'UUTON_JALKEEN' not in sisalto)
        check('K8 päivälokissa kaikki rivit', all(x in ins.tekstit() for x in ('ENNEN_UUTTOA', 'DIAG_SHOT start', 'UUTON_JALKEEN')))
        # kaksi DIAG_S-riviä samassa rate-ikkunassa: viimeisin (p=250 T=931 f=150) voittaa; yksiköt p/100, T/10, f/100
        check('K8 shot_pressure 2.5 bar (p/100)', odota(lambda: (ha.viimeinen('shot_pressure') or {}).get('state') == '2.5'))
        check('K8 shot_temp 93.1, shot_flow 1.5', odota(lambda: (ha.viimeinen('shot_temp') or {}).get('state') == '93.1'
              and (ha.viimeinen('shot_flow') or {}).get('state') == '1.5'))
        check('K8 stalls == 1 uutossa', odota(lambda: (ha.viimeinen('stalls') or {}).get('state') == '1'))
        n = len(ha.tilat('shot_pressure'))
        for i in range(10):
            ins.laheta(B, 4 + i, 'DIAG_S t=%d T=930 p=%d f=0 w=0 r=1\n' % (200 + i * 100, 300 + i))
        time.sleep(0.5)
        check('K8 shot_pressure ≤ 1 päivitys 0,5 s:ssa 10 näytteestä', len(ha.tilat('shot_pressure')) - n <= 1)

        # K9 rate-raja 1,5 s per entiteetti: välissä tulleet arvot yhdistyvät, viimeisin lähtee ikkunan jälkeen
        time.sleep(1.7)
        ins.laheta(B, 20, HB % (1000, 1, 0))
        odota(lambda: (ha.viimeinen('uptime') or {}).get('state') == '1000')
        ins.laheta(B, 21, HB % (1001, 1, 0))
        ins.laheta(B, 22, HB % (1002, 1, 0))
        time.sleep(0.6)
        check('K9 uptime ei päivity ikkunan sisällä', (ha.viimeinen('uptime') or {}).get('state') == '1000')
        check('K9 viimeisin arvo (1002) lähtee ikkunan jälkeen, 1001 ei koskaan',
              odota(lambda: (ha.viimeinen('uptime') or {}).get('state') == '1002', 3)
              and '1001' not in [r['state'] for r in ha.tilat('uptime')])

        # K10 hidas HA ei estä UDP-vastaanottoa eikä tiedostokirjausta
        ha.tila = 'slow'
        time.sleep(1.6)
        ins.laheta(B, 23, 'GUARD_TRIP pump reason=hidas_ha\n')   # tapahtuma jää jumiin hitaaseen HA:han (2 s / kutsu)
        time.sleep(0.2)
        t0 = time.monotonic()
        for i in range(30):
            ins.laheta(B, 24 + i, 'HIDAS_%d\n' % i)
        kaikki = odota(lambda: all(('HIDAS_%d' % i) in ins.tekstit() for i in range(30)), 1.5)
        check('K10 30 riviä lokissa <1,5 s:ssa vaikka HA vastaa 2 s:ssa', kaikki and time.monotonic() - t0 < 1.5)
        ha.tila = 'ok'
        odota(lambda: any(e['line'].endswith('hidas_ha') for e in ha.tapahtumat()), 6)

        # K11 HA-virhe kirjataan, tiedostokirjaus jatkuu
        ha.tila = 'fail'
        ins.laheta(B, 54, 'GUARD_TRIP pump reason=ha_500\n')
        check('K11 HA 500 -> HA-VIRHE keräimen lokiin', odota(lambda: 'HA-VIRHE' in ins.lokiteksti() and '500' in ins.lokiteksti()))
        check('K11 rivi silti lokitiedostossa', 'GUARD_TRIP pump reason=ha_500' in ins.tekstit())
        ha.tila = 'ok'
        ins.laheta(B, 55, 'JATKUU_VIRHEEN_JALKEEN\n')
        check('K11 keräin jatkaa virheen jälkeen', odota(lambda: 'JATKUU_VIRHEEN_JALKEEN' in ins.tekstit()))
        check('K11 keräin yhä hengissä', ins.proc.poll() is None)

        # K15 DIAG_MIN: lämmittimen ja pumpun päälläolo sekunteina minuutissa (venynyt ikkuna skaalataan 60 s:iin),
        # paineen keskiarvo/minimi/maksimi ja kattilan lämpö, state_class measurement (käyttäjä 20.10.2026)
        time.sleep(1.6)
        ins.laheta(B, 56, 'DIAG_MIN win_ms=90000 heat_ms=45000 pump_ms=3000 p_n=900 p_avg=1.25 p_min=-0.10 '
                          'p_max=9.40 T=99.80 target=100.00\n')
        hs = odota(lambda: ha.viimeinen('heater_on_s'))
        check('K15 heater_on_s skaalattu 60 s:iin', bool(hs) and float(hs['state']) == 30.0
              and hs['attributes']['ms'] == 45000 and hs['attributes']['osuus_pct'] == 50.0
              and hs['attributes']['state_class'] == 'measurement' and hs['attributes']['unit_of_measurement'] == 's')
        check('K15 pump_on_s', float((odota(lambda: ha.viimeinen('pump_on_s')) or {}).get('state', -1)) == 2.0)
        check('K15 paine avg/min/max ja lämpö', all(
            float((odota(lambda n=n: ha.viimeinen(n)) or {}).get('state', -99)) == v
            for n, v in (('pressure_avg', 1.25), ('pressure_min', -0.1), ('pressure_max', 9.4), ('boiler_temp', 99.8))))
        check('K15 rivi lokitiedostossa', any(t.startswith('DIAG_MIN win_ms=90000') for t in ins.tekstit()))
        ins.laheta(B, 57, 'DIAG_MIN win_ms=60000 heat_ms=0 pump_ms=0 p_n=0 p_avg=- p_min=- p_max=- T=- target=-\n')
        check('K15 tyhjä ikkuna ei kaada', odota(lambda: ins.proc.poll() is None and
                                                any(t.startswith('DIAG_MIN win_ms=60000') for t in ins.tekstit())))
    finally:
        ins.sulje()

    # K12 offline-ilmaisu oikeassa säikeessä (lyhennetty raja 1,5 s), takaisin online kun paketti tulee
    tmp2 = tempfile.mkdtemp(prefix='diagnet-smoke2-')
    ins2 = Instanssi(ha, tmp2, '--offline-s', '1.5', '--rate-s', '0.2')
    try:
        ha.kutsut.clear()
        ins2.laheta('cccc0003', 0, HB % (5, 1, 0))
        check('K12 online ensimmäisestä paketista', odota(lambda: (ha.viimeinen('status') or {}).get('state') == 'online'))
        check('K12 offline ilman paketteja (raja 1,5 s)', odota(lambda: (ha.viimeinen('status') or {}).get('state') == 'offline', 6))
        ins2.laheta('cccc0003', 1, HB % (6, 1, 0))
        check('K12 uusi paketti -> online', odota(lambda: (ha.viimeinen('status') or {}).get('state') == 'online'))
    finally:
        ins2.sulje()

    # K13 keräin sammuu SIGTERMillä siististi
    check('K13 SIGTERM -> paluukoodi 0 ja "pysäytetty"', ins.proc.returncode == 0 and 'pysäytetty' in open(ins.lokitiedosto).read())
    # K14 toinen keräin samalla tilahakemistolla: lukko estää, paluu 0
    tmp3 = tempfile.mkdtemp(prefix='diagnet-smoke3-')
    a = Instanssi(ha, tmp3)
    try:
        r = subprocess.run([sys.executable, KERAAJA, '--osoite', '127.0.0.1', '--portti', str(vapaa_portti()), '--tila', a.tila],
                           capture_output=True, text=True, timeout=10)
        check('K14 toinen keräin samaan tilaan: ei käynnisty (lukko), rc 0', r.returncode == 0 and 'jo käynnissä' in r.stdout)
        r = subprocess.run([sys.executable, KERAAJA, '--osoite', '127.0.0.1', '--portti', str(a.portti), '--tila', os.path.join(tmp3, 'toinen')],
                           capture_output=True, text=True, timeout=10)
        check('K14 varattu portti: rc 1 ja viesti', r.returncode == 1 and 'varattu' in r.stdout)
    finally:
        a.sulje()

    ha.sulje()
    for d in (tmp, tmp2, tmp3):
        shutil.rmtree(d, ignore_errors=True)
    print('RESULT: %d failed' % len(FAILED))
    return 1 if FAILED else 0


if __name__ == '__main__':
    sys.exit(main())
