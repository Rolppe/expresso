#!/usr/bin/env python3
"""OHJEVAHTI — PreToolUse-koukku.
Estää pico_dev.py-laiteajon, joka poikkeaa käyttäjän ohjekirjaan (OHJEKIRJA.json) kirjatusta
ohjeesta, ja näyttää ohjeen lainauksen muille laiteajoille. Spec: paketit/OHJEVAHTI.spec.md.
"""
import json
import os
import re
import shlex
import sys
import time
HERE = os.path.dirname(os.path.abspath(__file__))
KIRJA_POLKU = os.environ.get('OHJEVAHTI_KIRJA', os.path.join(HERE, 'OHJEKIRJA.json'))
TILA_POLKU = os.environ.get('OHJEVAHTI_TILA', os.path.join(HERE, '.ohjevahti-tila.json'))
EROTIN_RE = re.compile(r'\|\||&&|;|\||\n')
NIMI_ARVO_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*=')
# op -> (laitekomento, kenttien nimet järjestyksessä)
OP_TAULU = {
    'pgap': ('pgap', ['bar', 'n', 'spacing_ms', 'len_ms', 'phases', 'lo_us', 'hi_us']),
    'pstep': ('pstep', ['bar', 'hold_ms', 'tail_ms']),
    'plen': ('plen', ['bar', 'reps']),
    'pcap': ('pcap', ['ms', 'bar', 'phase_us']),
    'psweep': ('psweep', ['ms', 'bar', 'n', 'mult']),
    'phold': ('phold', ['s']),
    'shot': ('tshot', ['s']),
}
LAPI_ILMAN_TULOSTETTA = {'verify', 'capture', 'safe', 'watchdog', 'watchdog_test'}
# laitekomennon nimi -> kenttien nimet (cmd-op:n taulukkohaku)
KOMENTO_KENTAT = {laite: kentat for laite, kentat in OP_TAULU.values()}
KOMENTO_KENTAT['mcal'] = ['ms']
KYSY_ENSIN = 'Kysy käyttäjältä ennen ajoa. Älä muuta komentoa tai ohjekirjaa ilman hänen vastaustaan.'
OHJEKIRJA_TYHJA = 'ohjekirja tyhjä — käyttäjän ohjeita ei ole kirjattu'

def fmt(x):
    if isinstance(x, float) and x == int(x):
        return str(int(x))
    return str(x)

def _on_ensimmainen_sana(sanat, i):
    """Onko sanat[i] osan ensimmainen sana, kun edeltavat NIMI=arvo-sanat ja
    'timeout <luku>' ohitetaan ensimmaista sanaa etsittaessa?"""
    j = 0
    while j < i:
        sana = sanat[j]
        if NIMI_ARVO_RE.match(sana):
            j += 1
            continue
        if sana == 'timeout' and j + 1 < len(sanat):
            try:
                float(sanat[j + 1])
                j += 2
                continue
            except ValueError:
                pass
        break
    return j == i

def loyda_kaikki(command):
    """Palauttaa listan (op, arg) jokaiselle pico_dev.py-ajolle komennossa."""
    tulos = []
    for osa in EROTIN_RE.split(command):
        osa = osa.strip()
        if not osa:
            continue
        try:
            sanat = shlex.split(osa)
        except ValueError:
            continue
        for i, sana in enumerate(sanat):
            if not sana.endswith('pico_dev.py'):
                continue
            ensimmainen = _on_ensimmainen_sana(sanat, i)
            edeltaja_python = i > 0 and os.path.basename(sanat[i - 1]).startswith('python')
            if not (ensimmainen or edeltaja_python):
                continue
            if i + 1 >= len(sanat):
                continue
            op = sanat[i + 1]
            arg = sanat[i + 2] if i + 2 < len(sanat) else ''
            tulos.append((op, arg))
            break
    return tulos

def kasittele(op, arg):
    """Palauttaa (komento, kentat-dict) tai None jos op/arg ei ole tarkistettava laiteajo."""
    if op in LAPI_ILMAN_TULOSTETTA:
        return None
    if op == 'cmd' and arg == 'dev:safe':
        return None
    if op == 'cmd':
        osat = arg.split(':') if arg else ['']
        komento = osat[0]
        kentta_arvot = osat[1:]
        kentta_nimet = KOMENTO_KENTAT.get(komento, [])
    elif op in OP_TAULU:
        komento, kentta_nimet = OP_TAULU[op]
        kentta_arvot = arg.split(':') if arg else []
    else:
        komento = op
        kentta_nimet = []
        kentta_arvot = arg.split(':') if arg else []
    if kentta_arvot and kentta_arvot[0] == 'stop':
        return None
    kentat = {}
    for nimi, arvo in zip(kentta_nimet, kentta_arvot):
        kentat[nimi] = float(arvo)
    return komento, kentat

def lue_kirja():
    if not os.path.exists(KIRJA_POLKU):
        return []
    with open(KIRJA_POLKU) as f:
        data = json.load(f)
    rivit = data['ohjeet']
    if not isinstance(rivit, list):
        raise ValueError('ohjeet ei ole lista')
    return rivit

def lue_tila():
    if not os.path.exists(TILA_POLKU):
        return {}
    try:
        with open(TILA_POLKU) as f:
            return json.load(f)
    except Exception:
        return {}

def kirjoita_tila():
    with open(TILA_POLKU, 'w') as f:
        json.dump({'viimeisin_ajo': time.time()}, f)

def arvioi(komento, kentat, rivit_kirja, tila):
    osuvat = [r for r in rivit_kirja
              if r.get('tila') == 'voimassa' and r.get('komento') in (komento, '*')]
    deny_rivit = []
    for r in osuvat:
        tyyppi = r.get('tyyppi')
        if tyyppi == 'arvo':
            nimi = r.get('kentta')
            arvo = r.get('arvo')
            annettu = kentat.get(nimi)
            if annettu is None or abs(annettu - arvo) > 1e-9:
                nayta = fmt(annettu) if annettu is not None else 'puuttuu'
                deny_rivit.append('ERO %s: %s %s=%s, ohje %s — "%s"' %
                                   (r['id'], komento, nimi, nayta, fmt(arvo), r['lainaus']))
        elif tyyppi == 'kielto':
            deny_rivit.append('KIELTO %s: %s — "%s"' % (r['id'], komento, r['lainaus']))
        elif tyyppi == 'valivaihe':
            viimeisin = tila.get('viimeisin_ajo')
            kuitattu = r.get('kuitattu_klo')
            if viimeisin is not None and (kuitattu is None or kuitattu < viimeisin):
                deny_rivit.append('VÄLIVAIHE %s: %s kuittaamatta edellisen ajon jälkeen — "%s"' %
                                   (r['id'], r['vaihe'], r['lainaus']))
    if deny_rivit:
        return 'deny', deny_rivit
    kentta_teksti = ' '.join('%s=%s' % (k, fmt(v)) for k, v in kentat.items())
    otsikko = ('Laiteajo: %s %s' % (komento, kentta_teksti)) if kentta_teksti else ('Laiteajo: %s' % komento)
    ask_rivit = [otsikko]
    for r in osuvat:
        ask_rivit.append('%s: "%s"' % (r['id'], r['lainaus']))
    if not rivit_kirja:
        ask_rivit.append(OHJEKIRJA_TYHJA)
    return 'ask', ask_rivit

def tulosta(paatos, syy):
    print(json.dumps({'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'permissionDecision': paatos,
        'permissionDecisionReason': syy,
    }}, ensure_ascii=False))

def main():
    try:
        data = json.loads(sys.stdin.read())
    except Exception:
        return
    command = data.get('tool_input', {}).get('command')
    if not isinstance(command, str):
        return
    pico_ajot = loyda_kaikki(command)
    if not pico_ajot:
        return
    try:
        arvioitavat = []
        for op, arg in pico_ajot:
            kasittely = kasittele(op, arg)
            if kasittely is not None:
                arvioitavat.append(kasittely)
        if not arvioitavat:
            return
        try:
            rivit_kirja = lue_kirja()
        except Exception as e:
            tulosta('deny', 'OHJEKIRJA rikki: %s' % e)
            return
        tila = lue_tila()
        tulokset = [arvioi(komento, kentat, rivit_kirja, tila) for komento, kentat in arvioitavat]
        if any(paatos == 'deny' for paatos, _ in tulokset):
            rivit = []
            for paatos, r in tulokset:
                if paatos == 'deny':
                    rivit.extend(r)
            rivit.append(KYSY_ENSIN)
            tulosta('deny', '\n'.join(rivit))
        else:
            rivit = []
            for _, r in tulokset:
                rivit.extend(r)
            tulosta('ask', '\n'.join(rivit))
            kirjoita_tila()
    except Exception as e:
        tulosta('deny', 'OHJEVAHTI VIRHE: %s' % e)


if __name__ == '__main__':
    main()
