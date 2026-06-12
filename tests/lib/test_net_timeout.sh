#!/usr/bin/env bash
# Test net_run / _net_kill_tree — wrapper timeout portabile BSD/macOS (task-01)
# NB: niente 'set -e' — gli assert catturano $? di comandi che ritornano 124 di proposito.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
source "${PLUGIN_ROOT}/lib/net-timeout.sh"
PASS=0; FAIL=0
ok(){ echo "  PASS: $1"; PASS=$((PASS+1)); }
ko(){ echo "  FAIL: $1 ($2)"; FAIL=$((FAIL+1)); }

# T1 — timeout: comando lento killato entro budget, exit 124
start=$(date +%s); net_run 1 sleep 5 >/dev/null 2>&1; rc=$?; el=$(( $(date +%s) - start ))
{ [ "$rc" -eq 124 ] && [ "$el" -le 2 ]; } && ok "T1 timeout exit124 ~1s" || ko "T1" "rc=$rc el=${el}s"

# T2 — passthrough: comando veloce -> stdout + exit 0
out=$(net_run 3 echo hello); rc=$?
{ [ "$out" = "hello" ] && [ "$rc" -eq 0 ]; } && ok "T2 passthrough" || ko "T2" "out=$out rc=$rc"

# T3 — stdout parziale preservato su timeout
out=$(net_run 1 bash -c 'echo partial; sleep 5; echo never' 2>/dev/null); rc=$?
{ [ "$out" = "partial" ] && [ "$rc" -eq 124 ]; } && ok "T3 stdout parziale" || ko "T3" "out=$out rc=$rc"

# T9 — figlio diretto terminato (no orfano persistente)
marker="$(mktemp)"
net_run 1 bash -c 'sleep 10 & echo $! > "'"$marker"'"; wait' >/dev/null 2>&1 || true
child=$(cat "$marker" 2>/dev/null || echo "")
sleep 1
if [ -z "$child" ]; then ko "T9 marker vuoto" "PID figlio non catturato (test inconcludente)";
elif kill -0 "$child" 2>/dev/null; then ko "T9 figlio orfano" "pid=$child vivo"; kill -KILL "$child" 2>/dev/null || true;
else ok "T9 figlio terminato"; fi
rm -f "$marker"

# ─── NO_PROXY hardening (_devforge_no_proxy_github) ───────────────────────────

# T-NP1 — aggiunge github a NO_PROXY vuoto
( unset NO_PROXY no_proxy; _devforge_no_proxy_github
  case ",${NO_PROXY}," in *,github.com,*) exit 0 ;; *) exit 1 ;; esac )
[ $? -eq 0 ] && ok "T-NP1 github aggiunto a NO_PROXY vuoto" || ko "T-NP1" "github assente"

# T-NP2 — idempotenza: secondo invoke non duplica.
# Conta un dominio UNIVOCO del blocco (codeload.github.com): deve comparire 1 volta.
( unset NO_PROXY no_proxy; _devforge_no_proxy_github; _devforge_no_proxy_github
  n=$(grep -o 'codeload\.github\.com' <<<"$NO_PROXY" | wc -l | tr -d ' ')
  [ "$n" -eq 1 ] && exit 0 || exit 1 )
[ $? -eq 0 ] && ok "T-NP2 idempotente (no duplicati)" || ko "T-NP2" "blocco domini duplicato"

# T-NP3 — preserva i domini esistenti (es. *.siae.it)
( export NO_PROXY="localhost,*.siae.it"; _devforge_no_proxy_github
  case "$NO_PROXY" in *'*.siae.it'*) : ;; *) exit 1 ;; esac
  case "$NO_PROXY" in *github.com*) exit 0 ;; *) exit 1 ;; esac )
[ $? -eq 0 ] && ok "T-NP3 preserva domini esistenti" || ko "T-NP3" "domini persi o github assente"

# T-NP4 — export effettivo: visibile a un subprocess
( unset NO_PROXY no_proxy; _devforge_no_proxy_github
  bash -c 'case ",${NO_PROXY}," in *,github.com,*) exit 0 ;; *) exit 1 ;; esac' )
[ $? -eq 0 ] && ok "T-NP4 NO_PROXY esportato al subprocess" || ko "T-NP4" "non ereditato"

# ─── proxy autoconfig VPN-aware (_devforge_proxy_autoconfig) ──────────────────

# T-AC1 — on-net (probe ok): proxy preservato + github escluso
( export https_proxy="http://10.255.1.241:8080" HTTP_PROXY="http://10.255.1.241:8080"
  unset NO_PROXY no_proxy
  _devforge_on_siae_net() { return 0; }          # stub: rete SIAE raggiungibile
  _devforge_proxy_autoconfig
  [ -n "${https_proxy:-}" ] || exit 1            # proxy NON strippato
  case ",${NO_PROXY:-}," in *,github.com,*) exit 0 ;; *) exit 1 ;; esac )
[ $? -eq 0 ] && ok "T-AC1 on-net: proxy attivo + github DIRECT" || ko "T-AC1" "proxy strippato o github assente"

# T-AC2 — off-net (probe ko): tutte le var proxy strippate
( export https_proxy="x" http_proxy="x" HTTPS_PROXY="x" HTTP_PROXY="x" ALL_PROXY="x" all_proxy="x" NO_PROXY="x" no_proxy="x"
  _devforge_on_siae_net() { return 1; }          # stub: fuori VPN, proxy irraggiungibile
  _devforge_proxy_autoconfig
  [ -z "${https_proxy:-}${http_proxy:-}${HTTPS_PROXY:-}${HTTP_PROXY:-}${ALL_PROXY:-}${all_proxy:-}${NO_PROXY:-}${no_proxy:-}" ] && exit 0 || exit 1 )
[ $? -eq 0 ] && ok "T-AC2 off-net: tutte le var proxy strippate" || ko "T-AC2" "var proxy residue"

# T-AC3 — endpoint: parsing host:port da https_proxy (strip scheme + path)
( export https_proxy="http://10.255.1.241:8080/"
  [ "$(_devforge_proxy_endpoint)" = "10.255.1.241:8080" ] && exit 0 || exit 1 )
[ $? -eq 0 ] && ok "T-AC3 endpoint da env (scheme+path strip)" || ko "T-AC3" "parsing errato"

# T-AC4 — endpoint: fallback al proxy SIAE noto quando env vuoto
( unset https_proxy HTTPS_PROXY http_proxy HTTP_PROXY
  [ "$(_devforge_proxy_endpoint)" = "10.255.1.241:8080" ] && exit 0 || exit 1 )
[ $? -eq 0 ] && ok "T-AC4 endpoint fallback SIAE" || ko "T-AC4" "fallback assente"

echo "net_run: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
