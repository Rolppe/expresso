#!/usr/bin/env bash
# OnePlus 7T Pro (eXpresso-keittimen kehityspuhelin) — akku- ja tavoitettavuusvahti.
#
# Miksi: OTG-hostina puhelin syöttää Picolle virtaa eikä lataudu; akku loppui 11.8. ja 10.9.2026,
# ja sammunut puhelin katkaisi kehitysyhteyden. Vahti hälyttää iPhoneen ennen kuin akku loppuu.
#
# Ajo: palvelimen cron 10 min välein (Infra/linux/palvelin/cron.d-palvelin,
# PUHELIN=127.0.0.1:5555 = puhelimen oma root-adbd, 26.9.2026); aiemmin systemd --user -ajastin
# palvelimella osoitteeseen 192.0.2.11:5555. Ilmoitus HA:n kautta (Infra/iot/ha/ha.sh →
# notify.mobile_app_iphone). Puhelimella ajettuna EI_VASTAA ei voi laueta (sammunut puhelin ei aja
# cronia), joten sammumista vastaan suojaa vain akkuhälytys.
#
# Hälytykset (kukin kerran, kunnes tila palautuu):
#   AKKU_MATALA   akku < VAROITUS_PCT (30) eikä lataa
#   AKKU_KRIITTINEN akku < KRIITTINEN_PCT (15) eikä lataa
#   EI_VASTAA     adb ei saa yhteyttä PERÄKKÄISET (2) ajoa peräkkäin (= 20 min)
#   PALAUTUI      puhelin vastaa taas EI_VASTAA-hälytyksen jälkeen
#
# Käyttö: oneplus-akkuvahti.sh [--dry-run]   (--dry-run tulostaa ilmoituksen lähettämättä)
set -uo pipefail

PUHELIN="${PUHELIN:-192.0.2.11:5555}"
ADB="${ADB:-$HOME/.local/share/platform-tools/adb}"
HA_SH="${HA_SH:-/srv/work/Infra/iot/ha/ha.sh}"
PALVELU="${PALVELU:-notify.mobile_app_iphone}"
VAROITUS_PCT="${VAROITUS_PCT:-30}"
KRIITTINEN_PCT="${KRIITTINEN_PCT:-15}"
PERAKKAISET="${PERAKKAISET:-2}"
TILA="${TILA:-$HOME/.local/state/oneplus-akkuvahti/tila}"
DRY=0
[[ "${1:-}" == "--dry-run" ]] && DRY=1

# Rajat säädetään HA:n OnePlus-välilehdeltä (input_number.oneplus_akku_*, Infra/iot/ha/oneplus-nakyma.py,
# käyttäjä 5.10.2026); jos HA ei vastaa, pätevät yllä olevat oletukset.
lue_raja() {
  local arvo
  arvo=$(bash "$HA_SH" tilat "input_number.$1" 2>/dev/null | jq -r '.tila // empty' 2>/dev/null)
  [[ "$arvo" =~ ^[0-9]+(\.[0-9]+)?$ ]] && printf '%d\n' "${arvo%.*}"
}
raja=$(lue_raja oneplus_akku_varoitus || true); VAROITUS_PCT="${raja:-$VAROITUS_PCT}"
raja=$(lue_raja oneplus_akku_kriittinen || true); KRIITTINEN_PCT="${raja:-$KRIITTINEN_PCT}"

mkdir -p "$(dirname "$TILA")"
# Tila: hälytetty=<AKKU_MATALA|AKKU_KRIITTINEN|->, ei_vastaa_laskuri=<n>, ei_vastaa_halytetty=<0|1>
halytetty="-"; laskuri=0; ei_vastaa_halytetty=0
# shellcheck disable=SC1090
[[ -f "$TILA" ]] && source "$TILA"

tallenna() {
  printf 'halytetty=%q\nlaskuri=%q\nei_vastaa_halytetty=%q\n' "$halytetty" "$laskuri" "$ei_vastaa_halytetty" > "$TILA"
}

ilmoita() {
  local otsikko="$1" viesti="$2"
  echo "ILMOITUS: $otsikko — $viesti"
  [[ "$DRY" == 1 ]] && return 0
  local json
  json=$(python3 -c 'import json,sys; print(json.dumps({"title": sys.argv[1], "message": sys.argv[2]}))' "$otsikko" "$viesti")
  bash "$HA_SH" palvelu "$PALVELU" "$json" >/dev/null || echo "VIRHE: HA-ilmoitus epäonnistui" >&2
}

timeout 15 "$ADB" connect "$PUHELIN" >/dev/null 2>&1
akku=$(timeout 15 "$ADB" -s "$PUHELIN" shell dumpsys battery 2>/dev/null | tr -d '\r')
taso=$(awk -F': ' '/^  level:/{print $2; exit}' <<<"$akku")

if [[ -z "$taso" ]]; then
  laskuri=$((laskuri + 1))
  echo "EI_VASTAA: $PUHELIN ($laskuri/$PERAKKAISET)"
  if (( laskuri >= PERAKKAISET && ei_vastaa_halytetty == 0 )); then
    ilmoita "OnePlus ei vastaa" "eXpresso-kehityspuhelin $PUHELIN ei ole vastannut adb:hen $((laskuri * 10)) minuuttiin. Akku loppu tai puhelin sammunut? Kytke laturi ja käynnistä."
    ei_vastaa_halytetty=1
  fi
  tallenna
  exit 0
fi

if (( ei_vastaa_halytetty == 1 )); then
  ilmoita "OnePlus vastaa taas" "eXpresso-kehityspuhelin on taas tavoitettavissa, akku $taso %."
fi
laskuri=0; ei_vastaa_halytetty=0

# status 2 = lataa, 5 = täynnä. "AC powered: true" ei riitä: virrallinen hubi näyttää sen, vaikka
# akku purkautuu (status 3, 26.9.2026), jolloin vahti ei hälyttäisi koskaan.
lataa=false
grep -qE '^  status: (2|5)$' <<<"$akku" && lataa=true
echo "AKKU: $taso % lataa=$lataa rajat=$VAROITUS_PCT/$KRIITTINEN_PCT (hälytetty=$halytetty)"

if [[ "$lataa" == true ]] || (( taso >= VAROITUS_PCT + 5 )); then
  halytetty="-"
elif (( taso < KRIITTINEN_PCT )) && [[ "$halytetty" != AKKU_KRIITTINEN ]]; then
  ilmoita "OnePlus akku KRIITTINEN $taso %" "eXpresso-kehityspuhelin ei lataudu (Pico OTG:ssa). Kytke laturi tai irrota Pico nyt, muuten puhelin sammuu ja kehitysyhteys katkeaa."
  halytetty=AKKU_KRIITTINEN
elif (( taso < VAROITUS_PCT )) && [[ "$halytetty" == "-" ]]; then
  ilmoita "OnePlus akku $taso %" "eXpresso-kehityspuhelin ei lataudu (Pico OTG:ssa). Lataa puhelin tai käytä virrallista USB-C-hubia."
  halytetty=AKKU_MATALA
fi
tallenna
