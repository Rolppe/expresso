#!/usr/bin/env bash
# EXPRESSO-SOKKO-NOLLA: 10 tshot-ajoa sokkokorilla, TILAUS-H-purku (pvent) ennen jokaista ajoa.
# ptrig on pois sarjan ajan ja palautetaan lopuksi myos keskeytyksessa.
# Aja: bash testit/sokko-20261101/ajo-sarja.sh [ajojen maara, oletus 10]
# Pysahtyy, jos pvent ei paaty reason=ok, TS_END puuttuu tai ajossa nakyy GUARD_TRIP.
set -u
cd "$(dirname "$0")/../.." || exit 2
D=testit/sokko-20261101
N=${1:-10}
S=$D/sarja.log

say() { echo "$(date +%H:%M:%S) $*" >> "$S"; }

# Ensimmainen yhteys voi jaada mykaksi (PICO-HALLINTA.md "Ansa"), joten CMD_OK varmistetaan.
cmd_ok() {
    local c=$1 out=$D/cmd.tmp i
    for i in 1 2 3; do
        timeout 20 python3 pico_dev.py cmd "$c" 3 > "$out" 2>&1
        if grep -q "CMD_OK $c" "$out"; then
            say "CMD_OK $c (yritys $i)"
            return 0
        fi
    done
    say "EI CMD_OK: $c"
    return 1
}

palauta() {
    trap - EXIT INT TERM HUP
    cmd_ok ptrig:on || say "VIRHE: ptrig:on ei kuitattu"
    rm -f "$D/cmd.tmp"
}
trap palauta EXIT
trap 'say "KESKEYTETTY"; exit 130' INT TERM HUP

say "SARJA alkaa N=$N"
cmd_ok pcal:st || exit 3
cmd_ok ptrig:off || exit 3

for i in $(seq 1 "$N"); do
    V=$D/pvent$i.log
    A=$D/ajo$i.log
    timeout 45 python3 pico_dev.py cmd pvent 30 > "$V" 2>&1
    if ! grep -q 'PVENT_END.*reason=ok' "$V"; then
        say "ajo $i: purku ei ok: $(grep PVENT_END "$V" | tail -1)"
        exit 4
    fi
    say "ajo $i: $(grep PVENT_END "$V" | tail -1 | tr -d '\r')"
    timeout 100 python3 pico_dev.py shot 22 "$A" > /dev/null 2>&1
    rc=$?
    say "ajo $i: shot exit=$rc $(grep TS_END "$A" | tail -1 | tr -d '\r')"
    if ! grep -q TS_END "$A"; then
        say "ajo $i: TS_END puuttuu"
        exit 5
    fi
    if grep -q GUARD_TRIP "$A"; then
        say "ajo $i: GUARD_TRIP $(grep GUARD_TRIP "$A" | head -1 | tr -d '\r')"
        exit 6
    fi
done
say "SARJA valmis N=$N"
