#!/usr/bin/env python3
"""Picon diagnostiikkavirran keräin (EXPRESSO-DIAGNET, käyttäjä 20.10.2026). Spec: paketit/DIAGNET.md.

Kuuntelee UDP-paketteja (versio EXD1: `EXD1 <boot> <seq> <up_ms> <drop>\\n<data>`), kokoaa Picon tekstivirran
riveiksi, kirjoittaa jokaisen rivin `<tila>/YYYY-MM-DD.log`-tiedostoon (`<ISO-aika> <boot> <rivi>`; uutto
`DIAG_SHOT start`…`end` lisäksi tiedostoon `shot-<aika>-<boot>.log`) ja vie tilan Home Assistantiin REST:llä
(sensor.espresso_diag_* ja tapahtuma espresso_diag). HA-kutsut ovat omassa säikeessään: hidas tai kaatunut
HA ei pysäytä UDP-vastaanottoa.

Käyttö: keraaja.py [--portti N] [--osoite A] [--tila HAKEMISTO] [--ha-url URL] [--token TIEDOSTO]
                   [--offline-s S] [--rate-s S] [--shot-rate-s S]
Ympäristö: DIAGNET_PORTTI, DIAGNET_OSOITE, DIAGNET_TILA, HA_URL, HA_TOKEN_FILE (kuten oneplus-ha.py).
Loki (stdout): kaynnista.sh ohjaa tiedostoon ~/.local/state/expresso-diag/keraaja.loki.
"""
import argparse
import collections
import datetime
import fcntl
import json
import os
import re
import signal
import socket
import sys
import threading
import time
import urllib.request

PORTTI = 47210
OFFLINE_S = 150        # ei paketteja näin kauan -> status offline
RATE_S = 5             # sensorin päivitys korkeintaan kerran näin monessa sekunnissa entiteettiä kohti
SHOT_RATE_S = 1        # uuton aikaiset shot_*-sensorit: ≤ 1 Hz (DIAGNET.md)
HA_AIKAKATKAISU_S = 5
PUSKURI_MAX = 8192     # rivi ilman rivinvaihtoa tämän yli -> liuotetaan riviksi
TAPAHTUMAJONO_MAX = 1000
EI_EXD1_LOKI_VALI = 100
TILA_OLETUS = os.path.expanduser("~/.local/state/expresso-diag")
TAPAHTUMA = "espresso_diag"
PREFIX = "sensor.espresso_diag_"

OTSIKKO = re.compile(r"^EXD1 ([0-9a-f]{8}) (\d+) (\d+) (\d+)$")
AVAIN_ARVO = re.compile(r"(\w+)=(\S*)")
LOPPU = re.compile(r"^[A-Za-z][A-Za-z0-9_]*_END\b")

# nimi -> (friendly_name, yksikkö, ikoni)
SENSORIT = {
    "status": ("Espresso Pico yhteys", None, "mdi:connection"),
    "uptime": ("Espresso Pico käyntiaika", "s", "mdi:timer-outline"),
    "mem_free": ("Espresso Pico vapaa muisti", "B", "mdi:memory"),
    "drop": ("Espresso Pico pudotetut tavut", "B", "mdi:package-down"),
    "rssi": ("Espresso Pico Wi-Fi RSSI", "dBm", "mdi:wifi"),
    "reset_cause": ("Espresso Pico nollaussyy", None, "mdi:restart-alert"),
    "boots": ("Espresso Pico käynnistykset", None, "mdi:counter"),
    "last_end": ("Espresso Pico viimeisin loppu", None, "mdi:flag-checkered"),
    "max_loop_ms": ("Espresso Pico pisin silmukka", "ms", "mdi:timer-sand"),
    "last_guard_trip": ("Espresso Pico viimeisin vartiolaukaisu", None, "mdi:shield-alert"),
    "stalls": ("Espresso Pico EU_STALL-määrä", None, "mdi:alert-circle-outline"),
    "shot_pressure": ("Espresso uuton paine", "bar", "mdi:gauge"),
    "shot_temp": ("Espresso uuton lämpötila", "°C", "mdi:thermometer"),
    "shot_flow": ("Espresso uuton virtaus", "g/s", "mdi:water"),
    # DIAG_MIN (käyttäjä 20.10.2026): minuuttikooste, HA:n historiaan ja pitkäaikaistilastoihin
    "heater_on_s": ("Espresso lämmitin päällä / min", "s", "mdi:radiator"),
    "pump_on_s": ("Espresso pumppu päällä / min", "s", "mdi:pump"),
    "pressure_avg": ("Espresso paine keskiarvo / min", "bar", "mdi:gauge"),
    "pressure_min": ("Espresso paine minimi / min", "bar", "mdi:gauge-low"),
    "pressure_max": ("Espresso paine maksimi / min", "bar", "mdi:gauge-full"),
    "boiler_temp": ("Espresso kattilan lämpötila", "°C", "mdi:thermometer"),
}


def loki(viesti):
    print("%s %s" % (time.strftime("%F %T"), viesti), flush=True)


def avaimet(rivi):
    return dict(AVAIN_ARVO.findall(rivi))


def luku(teksti, jakaja=1):
    try:
        return round(float(teksti) / jakaja, 2)
    except (TypeError, ValueError):
        return None


class Julkaisija(threading.Thread):
    """HA-kutsut omassa säikeessään. Sensorit: uusin arvo per entiteetti, lähtee kun rate-väli on täynnä;
    tapahtumat lähtevät heti jonosta."""

    def __init__(self, url, token_tiedosto, rate_s=RATE_S, shot_rate_s=SHOT_RATE_S, tikki=None):
        super().__init__(daemon=True, name="ha-julkaisija")
        self.url, self.token_tiedosto = url.rstrip("/"), token_tiedosto
        self.rate_s, self.shot_rate_s, self.tikki = rate_s, shot_rate_s, tikki
        self.lukko = threading.Lock()
        self.odottavat = {}                      # entiteetti -> (state, attribuutit)
        self.viimeksi = {}                       # entiteetti -> monotonic viimeisimmän lähetyksen alku
        self.tapahtumat = collections.deque()
        self.herate = threading.Event()
        self.lopeta = threading.Event()
        self.pudotetut_tapahtumat = 0

    def sensori(self, nimi, state, attribuutit=None):
        attr = {"friendly_name": SENSORIT[nimi][0], "icon": SENSORIT[nimi][2]}
        if SENSORIT[nimi][1]:
            attr["unit_of_measurement"] = SENSORIT[nimi][1]
        attr.update(attribuutit or {})
        with self.lukko:
            self.odottavat[PREFIX + nimi] = (state, attr)

    def tapahtuma(self, laji, rivi, boot):
        with self.lukko:
            if len(self.tapahtumat) >= TAPAHTUMAJONO_MAX:
                self.tapahtumat.popleft()
                self.pudotetut_tapahtumat += 1
            self.tapahtumat.append({"kind": laji, "line": rivi, "boot": boot})
        self.herate.set()

    def _rate(self, entiteetti):
        return self.shot_rate_s if entiteetti.startswith(PREFIX + "shot_") else self.rate_s

    def _kutsu(self, polku, data):
        try:
            token = open(self.token_tiedosto).read().strip()
            req = urllib.request.Request(self.url + polku, method="POST", data=json.dumps(data).encode(),
                                         headers={"Authorization": "Bearer " + token,
                                                  "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=HA_AIKAKATKAISU_S) as r:
                r.read()
        except Exception as e:  # HA tai token poissa: kirjataan, ei koskaan nosteta UDP-puolelle
            loki("HA-VIRHE %s: %s" % (polku, e))

    def laheta(self):
        with self.lukko:
            tapahtumat = list(self.tapahtumat)
            self.tapahtumat.clear()
        for t in tapahtumat:
            self._kutsu("/api/events/" + TAPAHTUMA, t)
        nyt = time.monotonic()
        with self.lukko:
            erapaivat = [(e, v) for e, v in self.odottavat.items()
                         if nyt - self.viimeksi.get(e, -1e9) >= self._rate(e)]
            for e, _ in erapaivat:
                del self.odottavat[e]
                self.viimeksi[e] = nyt
        for e, (state, attr) in erapaivat:
            self._kutsu("/api/states/" + e, {"state": str(state), "attributes": attr})

    def run(self):
        while not self.lopeta.is_set():
            self.herate.wait(0.2)
            self.herate.clear()
            try:
                if self.tikki:
                    self.tikki()
                self.laheta()
            except Exception as e:
                loki("JULKAISIJA-VIRHE: %s" % e)


class Keraaja:
    def __init__(self, tila, ha, offline_s=OFFLINE_S):
        self.tila, self.ha, self.offline_s = tila, ha, offline_s
        self.lukko = threading.RLock()
        self.boot = self.seq = None
        self.puskuri = b""
        self.drop = 0
        self.boots = 0
        self.ei_exd1 = 0
        self.stalls = 0
        self.status = None                      # None (ei pakettia vielä) | online | offline
        self.viimeinen = None                   # monotonic viimeisimmän EXD1-paketin saapuminen
        self.hb = {}
        self.paiva = self.paivatiedosto = self.shot = None

    # --- lokitiedostot -------------------------------------------------------------------------
    def _avaa(self, polku):
        os.makedirs(self.tila, exist_ok=True)
        return open(os.path.join(self.tila, polku), "a", encoding="utf-8")

    def _kirjoita(self, boot, rivi):
        nyt = datetime.datetime.now().astimezone()
        teksti = "%s %s %s\n" % (nyt.isoformat(timespec="milliseconds"), boot, rivi)
        try:
            paiva = nyt.strftime("%Y-%m-%d")
            if paiva != self.paiva:
                if self.paivatiedosto:
                    self.paivatiedosto.close()
                self.paivatiedosto, self.paiva = self._avaa(paiva + ".log"), paiva
            if rivi.startswith("DIAG_SHOT start"):
                self._sulje_shot()
                self.shot = self._avaa("shot-%s-%s.log" % (nyt.strftime("%Y%m%d-%H%M%S"), boot))
            for f in (self.paivatiedosto, self.shot):
                if f:
                    f.write(teksti)
                    f.flush()
            if rivi.startswith("DIAG_SHOT end"):
                self._sulje_shot()
        except OSError as e:
            loki("TIEDOSTOVIRHE: %s" % e)
        return nyt.isoformat(timespec="seconds")

    def _sulje_shot(self):
        if self.shot:
            self.shot.close()
            self.shot = None

    # --- paketit -------------------------------------------------------------------------------
    def paketti(self, data):
        with self.lukko:
            alku, erotin, runko = data.partition(b"\n")
            m = OTSIKKO.match(alku.decode("ascii", "replace")) if erotin else None
            if not m:
                self.ei_exd1 += 1
                if self.ei_exd1 == 1 or self.ei_exd1 % EI_EXD1_LOKI_VALI == 0:
                    loki("ei-EXD1-paketti #%d (%d B): %r" % (self.ei_exd1, len(data), data[:40]))
                return
            boot, seq, self.drop = m.group(1), int(m.group(2)), int(m.group(4))
            self.viimeinen = time.monotonic()
            if boot != self.boot:                      # uusi boot: vanhan osittainen rivi ulos, kokoaminen alusta
                self._tyhjenna()
                self._sulje_shot()
                self.boot, self.seq = boot, None
            if self.seq is not None and seq <= self.seq:
                return                                 # kaksoiskappale tai myöhästynyt
            odotettu = 0 if self.seq is None else self.seq + 1
            if seq > odotettu:
                self._tyhjenna()
                self._kirjoita(boot, "[LOST %d]" % (seq - odotettu))
            self.seq = seq
            if self.status != "online":
                self.status = "online"
                self._status()
            self.puskuri += runko
            *rivit, self.puskuri = self.puskuri.split(b"\n")
            for r in rivit:
                self._rivi(boot, r)
            if len(self.puskuri) > PUSKURI_MAX:
                self._tyhjenna()

    def _tyhjenna(self):
        if self.puskuri and self.boot:
            self._rivi(self.boot, self.puskuri)
        self.puskuri = b""

    def _rivi(self, boot, raaka):
        rivi = raaka.decode("utf-8", "replace").rstrip("\r")
        if not rivi.strip():
            return
        aika = self._kirjoita(boot, rivi)
        self._kasittele(boot, rivi, aika)

    def lopeta(self):
        with self.lukko:
            self._tyhjenna()
            self._sulje_shot()
            if self.paivatiedosto:
                self.paivatiedosto.close()

    # --- tila ja HA ----------------------------------------------------------------------------
    def tikki(self):
        with self.lukko:
            if self.status == "online" and time.monotonic() - self.viimeinen > self.offline_s:
                self.status = "offline"
                self._status()

    def _status(self):
        attr = dict(self.hb)
        attr.update({"boot": self.boot, "ei_exd1": self.ei_exd1,
                     "viimeinen_paketti": datetime.datetime.now().astimezone().isoformat(timespec="seconds")})
        self.ha.sensori("status", self.status, attr)

    def _kasittele(self, boot, rivi, aika):
        ha = self.ha
        if rivi.startswith("DIAG_BOOT"):
            kv = avaimet(rivi)
            self.boots += 1
            ha.sensori("reset_cause", kv.get("rc", "?"), {"rc": kv.get("rc"), "fw": kv.get("fw"),
                                                           "mac": kv.get("mac"), "aika": aika, "boot": boot})
            ha.sensori("boots", self.boots)
            ha.tapahtuma("BOOT", rivi, boot)
        elif rivi.startswith("DIAG_HB"):
            self.hb = avaimet(rivi)
            for nimi, avain in (("uptime", "up_s"), ("mem_free", "free"), ("drop", "drop"), ("rssi", "rssi")):
                if avain in self.hb:
                    ha.sensori(nimi, self.hb[avain])
            self._status()
        elif rivi.startswith("DIAG_MIN"):
            kv = avaimet(rivi)
            win = luku(kv.get("win_ms"))
            mitta = {"state_class": "measurement", "aika": aika, "boot": boot}
            if win:
                # Sekuntia minuutissa: ikkuna venyy, jos Picon tehtävä myöhästyy, joten skaalataan 60 s:iin
                for nimi, avain in (("heater_on_s", "heat_ms"), ("pump_on_s", "pump_ms")):
                    ms = luku(kv.get(avain))
                    if ms is not None:
                        ha.sensori(nimi, round(ms * 60.0 / win, 1),
                                   dict(mitta, ms=int(ms), win_ms=int(win), osuus_pct=round(100.0 * ms / win, 1)))
            for nimi, avain in (("pressure_avg", "p_avg"), ("pressure_min", "p_min"), ("pressure_max", "p_max"),
                                ("boiler_temp", "T")):
                arvo = luku(kv.get(avain))
                if arvo is not None:
                    ha.sensori(nimi, arvo, dict(mitta, p_n=kv.get("p_n"), target=kv.get("target")))
        elif rivi.startswith("DIAG_S "):
            kv = avaimet(rivi)
            for nimi, avain, jakaja in (("shot_temp", "T", 10), ("shot_pressure", "p", 100), ("shot_flow", "f", 100)):
                arvo = luku(kv.get(avain), jakaja)
                if arvo is not None:
                    ha.sensori(nimi, arvo, {"t_ms": kv.get("t"), "boot": boot})
        elif rivi.startswith("DIAG_SHOT start"):
            self.stalls = 0
            ha.sensori("stalls", 0, {"aika": aika})
        elif rivi.startswith("GUARD_TRIP"):
            ha.sensori("last_guard_trip", rivi[:255], {"rivi": rivi, "aika": aika, "boot": boot})
            ha.tapahtuma("GUARD_TRIP", rivi, boot)
        elif LOPPU.match(rivi):
            kv = avaimet(rivi)
            ha.sensori("last_end", kv.get("reason", "end")[:255], dict(kv, rivi=rivi, aika=aika, boot=boot))
            if "max_loop_ms" in kv:
                ha.sensori("max_loop_ms", kv["max_loop_ms"], {"rivi": rivi, "aika": aika})
            ha.tapahtuma("END", rivi, boot)
        elif rivi.startswith("EU_STALL"):
            self.stalls += 1
            ha.sensori("stalls", self.stalls, {"aika": aika})
        elif rivi.startswith("DEVSAFE"):
            ha.tapahtuma("DEVSAFE", rivi, boot)
        elif rivi.startswith("Traceback"):
            ha.tapahtuma("TRACEBACK", rivi, boot)
        elif "MemoryError" in rivi:
            ha.tapahtuma("MEMORYERROR", rivi, boot)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--portti", type=int, default=int(os.environ.get("DIAGNET_PORTTI", PORTTI)))
    p.add_argument("--osoite", default=os.environ.get("DIAGNET_OSOITE", "0.0.0.0"))
    p.add_argument("--tila", default=os.environ.get("DIAGNET_TILA", TILA_OLETUS))
    p.add_argument("--ha-url", default=os.environ.get("HA_URL", "http://192.0.2.12:8123"))
    p.add_argument("--token", default=os.environ.get("HA_TOKEN_FILE", os.path.expanduser("~/.config/ha/token")))
    p.add_argument("--offline-s", type=float, default=OFFLINE_S)
    p.add_argument("--rate-s", type=float, default=RATE_S)
    p.add_argument("--shot-rate-s", type=float, default=SHOT_RATE_S)
    a = p.parse_args(argv)

    os.makedirs(a.tila, exist_ok=True)
    lukko = open(os.path.join(a.tila, "keraaja.lukko"), "w")
    try:
        fcntl.flock(lukko, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        loki("toinen keräin on jo käynnissä (lukko %s)" % lukko.name)
        return 0
    sok = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sok.bind((a.osoite, a.portti))
    except OSError as e:
        loki("portti %s:%d varattu: %s" % (a.osoite, a.portti, e))
        return 1
    sok.settimeout(0.5)
    sok.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1 << 20)
    with open(os.path.join(a.tila, "keraaja.pid"), "w") as f:
        f.write("%d\n" % os.getpid())

    kerain = Keraaja(a.tila, None, a.offline_s)
    ha = Julkaisija(a.ha_url, a.token, a.rate_s, a.shot_rate_s, tikki=kerain.tikki)
    kerain.ha = ha
    ha.start()
    pysayta = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: pysayta.set())
    loki("kuuntelee %s:%d tila=%s ha=%s" % (a.osoite, a.portti, a.tila, a.ha_url))
    while not pysayta.is_set():
        try:
            data, _ = sok.recvfrom(65535)
        except socket.timeout:
            continue
        except OSError as e:
            loki("RECV-VIRHE: %s" % e)
            continue
        try:
            kerain.paketti(data)
        except Exception as e:  # yksi huono paketti ei kaada keräintä
            loki("PAKETTIVIRHE: %r %s" % (e, data[:60]))
    kerain.lopeta()
    ha.lopeta.set()
    loki("pysäytetty")
    return 0


if __name__ == "__main__":
    sys.exit(main())
