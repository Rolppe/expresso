#!/usr/bin/env python3
"""uutto_first_drop_capture.py — Tallentaa ja analysoi käyttäjän kuristintesti-uoton.

Odottaa uuton käynnistymistä kytkimestä (PB / EU_START),
tallentaa jokaisen 10 Hz telemetriarivin ja vaa'an lukeman,
havaitsee käyttäjän kytkimen sulkemisen (PB_END),
tallentaa 4 sekuntia asettumista uuton jälkeen ja
tulostaa analyysin pumpun tärinästä ja ensimmäisen pisaran signaalista.
"""
import socket
import sys
import time
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import localenv  # noqa: E402,F401  local.env -> os.environ (README: Local configuration)

HOST = os.environ.get('PICO_ZERO', '192.0.2.10')
PORT = 2217
LOG_FILE = os.path.join(os.path.dirname(__file__), 'first_drop_shot_20261025_run2.log')

def main():
    print(f"Yhdistetään Picoon {HOST}:{PORT}...")
    try:
        s = socket.create_connection((HOST, PORT), timeout=5)
    except Exception as e:
        print(f"Virhe yhdistettäessä {HOST}:{PORT}: {e}")
        sys.exit(1)

    s.settimeout(0.5)
    print(f"Yhteys auki. Tallennetaan tiedostoon: {LOG_FILE}")
    print(">>> VALMIINA: Laita kuristimellinen kahva ja kuppi paikoilleen.")
    print(">>> Käännä uuttokytkin PÄÄLLE ja heti ensimmäisen pisaran tullessa POIS PÄÄLTÄ.")
    print("Odotetaan uuttoa...")

    shot_active = False
    shot_ended = False
    t_end_wait = None
    all_lines = []
    t_idle_limit = time.time() + 300.0  # 5 min odotusaika uuton aloitukselle

    with open(LOG_FILE, 'w', buffering=1) as f_out:
        buf = ""
        while True:
            try:
                data = s.recv(4096)
                if not data:
                    print("Socket sulkeutui.")
                    break
                text = data.decode('utf-8', errors='replace')
                buf += text
                while '\n' in buf:
                    line, buf = buf.split('\n', 1)
                    line = line.strip('\r')
                    f_out.write(line + '\n')
                    all_lines.append(line)

                    # Näytetään olennaiset rivit konsoliin
                    if any(line.startswith(k) for k in ('EU', 'PB', 'TS', 'BREW_LOG', 'TARE', 'CMD', 'VKELLO', 'FIRST_DROP')):
                        print(line)

                    if 'EU_START' in line or 'BREW_LOG start' in line or line.startswith('PB '):
                        if not shot_active:
                            shot_active = True
                            print("\n*** UUTTO ALKOI! PUMPPU KÄY ***\n")

                    if shot_active and ('PB_END' in line or 'TS_END' in line or 'log_stop' in line):
                        if not shot_ended:
                            shot_ended = True
                            t_end_wait = time.time() + 4.0
                            print("\n*** UUTTO PYSÄYTETTY (KYTKIN KÄÄNNETTY POIS)! Tallennetaan jälkiasettuminen (4s)... ***\n")

            except socket.timeout:
                pass
            except KeyboardInterrupt:
                print("\nKäyttäjä keskeytti tallennuksen.")
                break

            if not shot_active and time.time() >= t_idle_limit:
                print("5 min aikakatkaisu: uuttoa ei käynnistetty.")
                break

            if shot_ended and time.time() >= t_end_wait:
                print("Jälkiasettuminen tallennettu. Suljetaan yhteys ja analysoidaan.")
                break

    s.close()
    print(f"\nKaikki tallennettu tiedostoon {LOG_FILE} ({len(all_lines)} riviä).")

if __name__ == '__main__':
    main()
