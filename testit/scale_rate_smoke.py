#!/usr/bin/env python3
"""scale_rate_smoke.py — suunnittelijan holdout vaa'an lukutahdille (SCALE-POLL, 19.9.2026).

Vaa'an lukutahti ei ole vapaa luku: se on sidottu `scale.py`:n virtausvakioihin ja
`functions.py`:n kaukalovahtiin. Ehto eli tähän asti vain kommenteissa, ja juuri sellainen ehto
katosi kerran jo (`paketit/TURVAKATO.md`). Tämä testi lukee vakiot kolmesta tiedostosta tekstinä
— `scale.py` ja `main.py` eivät ole tuotavissa CPythonilla (`import machine`) — ja tarkistaa
invariantit.

    python3 testit/scale_rate_smoke.py       RESULT: <n> failed, epänolla paluuarvo jos punaisia

Toteuttaja ei muokkaa tätä tiedostoa (brief: must not).
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PICO = os.path.join(HERE, '..', 'pico')

# Mitattu näytteenottotaajuus, scale.py:n oma kommentti (rivi 7): "at 11.6 samples/s".
SAMPLE_INTERVAL_MS = 1000.0 / 11.6


def const(path, name):
    src = open(os.path.join(PICO, path), encoding='utf-8').read()
    m = re.search(r'^%s\s*=\s*([0-9]+)' % re.escape(name), src, re.M)
    return int(m.group(1)) if m else None


def main():
    fails = []

    def check(name, cond, extra=''):
        if not cond:
            fails.append(name)
            print('FAIL ' + name + (' — ' + extra if extra else ''))

    poll = const('main.py', 'SCALE_POLL_MS')
    win = const('scale.py', 'FLOW_WINDOW_MS')
    pts = const('scale.py', 'FLOW_MIN_POINTS')
    stale = const('scale.py', 'FLOW_STALE_MS')
    tray = const('functions.py', 'TRAY_STALE_MS')

    check('main.py määrittelee SCALE_POLL_MS', poll is not None,
          'vakiota ei löytynyt — tahti on yhä literaali sleep_ms-kutsussa')
    for n, v in (('FLOW_WINDOW_MS', win), ('FLOW_MIN_POINTS', pts), ('FLOW_STALE_MS', stale),
                 ('TRAY_STALE_MS', tray)):
        check('%s luettavissa' % n, v is not None)
    if None in (poll, win, pts, stale, tray):
        print('RESULT: %d failed' % len(fails))
        return 1

    check('SCALE_POLL_MS on käyttäjän päättämä 50', poll == 50, 'on %d' % poll)

    # 1. Jokainen anturin näyte on saatava kiinni: tahti ei saa ylittää näyteväliä.
    check('tahti nappaa jokaisen näytteen (<= %.0f ms)' % SAMPLE_INTERVAL_MS,
          poll <= SAMPLE_INTERVAL_MS, '%d ms vs näyteväli %.0f ms' % (poll, SAMPLE_INTERVAL_MS))

    # 2. Virtausikkunaan on mahduttava FLOW_MIN_POINTS näytettä kaksinkertaisella marginaalilla.
    check('virtausikkunaan mahtuu %d näytettä marginaalilla' % pts,
          poll * pts <= win / 2, '%d*%d = %d > %d' % (poll, pts, poll * pts, win // 2))

    # 3. Yksi väliin jäänyt luenta ei saa vanhentaa virtausta.
    check('yksi väliin jäänyt luenta ei vanhenna virtausta',
          poll * 2 <= stale, '2*%d = %d > %d' % (poll, poll * 2, stale))

    # 4. Kaukalovahdin on ehdittävä nähdä kaksi näytettä ennen kuin lukema on sen mielestä vanha
    #    — sen katkaisusääntö vaatii kaksi peräkkäistä vaakanäytettä.
    check('kaukalovahti ehtii nähdä kaksi näytettä',
          poll * 2 < tray, '2*%d = %d >= %d' % (poll, poll * 2, tray))

    print('RESULT: %d failed' % len(fails))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
