#!/usr/bin/env bash
# Käynnistää Picon diagnostiikkakeräimen, jos se ei jo ole käynnissä (EXPRESSO-DIAGNET, 20.10.2026).
# Cron ajaa tämän 5 min välein, joten keräin palaa bootin ja kaatumisen jälkeen. Ei käynnistä toista, jos
# pid elää tai UDP-portti on jo varattu. Loki: ~/.local/state/expresso-diag/keraaja.loki.
set -u
tama=$(cd "$(dirname "$0")" && pwd)
tila=${DIAGNET_TILA:-$HOME/.local/state/expresso-diag}
portti=${DIAGNET_PORTTI:-47210}
loki=${DIAGNET_LOKI:-$tila/keraaja.loki}
python=${PYTHON:-python3}

mkdir -p "$tila"
pid=$(cat "$tila/keraaja.pid" 2>/dev/null || true)
if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null && tr '\0' ' ' <"/proc/$pid/cmdline" 2>/dev/null | grep -q keraaja.py; then
  exit 0
fi
if ! "$python" -c 'import socket,sys; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.bind(("0.0.0.0", int(sys.argv[1])))' "$portti" 2>/dev/null; then
  exit 0  # portti varattu: joku muu (tai edellinen keräin ilman pid-tiedostoa) kuuntelee
fi
nohup "$python" "$tama/keraaja.py" >>"$loki" 2>&1 &
