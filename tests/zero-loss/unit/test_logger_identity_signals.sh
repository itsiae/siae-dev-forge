#!/usr/bin/env bash
# Task-02/03/04 — segnali identità locali cross-platform (Capability A).
# Verifica: funzioni OS + tools, wiring nel bundle, best-effort (mai abort sotto set -euo pipefail),
# normalizzazione (undefined npm), determinismo SSH, opt-in gh, JSON valido.
# Piano: docs/plans/2026-06-18-telemetry-identity-rotation-crossplatform/task-02..04
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
PASS=0; FAIL=0
ok(){ PASS=$((PASS+1)); echo "  PASS  $1"; }
ko(){ FAIL=$((FAIL+1)); echo "  FAIL  $1"; }
jq_valid(){ /usr/bin/python3 -c 'import json,sys; json.load(sys.stdin)' 2>/dev/null; }

# ---- Parte OS (task-02) ----
T1="$(mktemp -d)"
out=$(HOME="$T1" PR="$PLUGIN_ROOT" bash -c '
  source "$PR/lib/logger.sh" 2>/dev/null || true
  _devforge_local_identity_signals_os' 2>/dev/null || echo "")
# output è TSV: full_name \t login \t domain
login=$(printf '%s' "$out" | awk -F'\t' '{print $2}')
[ -n "$login" ] && ok "OS: os_login non vuoto (fallback whoami): '$login'" || ko "OS: os_login vuoto"

# set -u safe con USERDOMAIN unset
sub=$(HOME="$T1" PR="$PLUGIN_ROOT" bash -c '
  set -euo pipefail
  unset USERDOMAIN 2>/dev/null || true
  source "$PR/lib/logger.sh" 2>/dev/null || true
  _devforge_local_identity_signals_os >/dev/null 2>&1 && echo OK' 2>/dev/null || echo "")
[ "$sub" = "OK" ] && ok "OS: nessun abort sotto set -u con USERDOMAIN unset" || ko "OS: abort sotto set -u"
rm -rf "$T1"

# ---- Parte tools (task-03) ----
# npm che ritorna 'undefined' → normalizzato a vuoto
T2="$(mktemp -d)"; mkdir -p "$T2/bin"
for d in $(echo "$PATH" | tr ':' ' '); do [ -d "$d" ] && ln -sf "$d"/* "$T2/bin/" 2>/dev/null || true; done
cat > "$T2/bin/npm" <<'EOF'
#!/usr/bin/env bash
[ "$1" = "config" ] && { echo "undefined"; exit 0; }
EOF
chmod +x "$T2/bin/npm"
out=$(HOME="$T2" PATH="$T2/bin" PR="$PLUGIN_ROOT" bash -c '
  source "$PR/lib/logger.sh" 2>/dev/null || true
  _devforge_local_identity_signals_tools' 2>/dev/null || echo "")
npme=$(printf '%s' "$out" | awk -F'\t' '{print $2}')
[ -z "$npme" ] && ok "tools: npm 'undefined' normalizzato a vuoto" || ko "tools: npm_email='$npme' (atteso vuoto)"

# gh opt-in OFF → gh NON invocato (marker assente)
rm -f "$T2/.gh-called"
cat > "$T2/bin/gh" <<EOF
#!/usr/bin/env bash
touch "$T2/.gh-called"; echo '{"email":"x@y.z"}'
EOF
chmod +x "$T2/bin/gh"
HOME="$T2" PATH="$T2/bin" PR="$PLUGIN_ROOT" bash -c '
  source "$PR/lib/logger.sh" 2>/dev/null || true
  _devforge_local_identity_signals_tools >/dev/null 2>&1' 2>/dev/null || true
[ ! -f "$T2/.gh-called" ] && ok "tools: gh NON invocato senza DEVFORGE_IDENTITY_GH=1 (no rete)" || ko "tools: gh invocato (rete non opt-in!)"
rm -rf "$T2"

# SSH determinismo: 2 chiavi REALI → stesso fingerprint su 2 chiamate (prima per sort)
T3="$(mktemp -d)"; mkdir -p "$T3/.ssh"
if command -v ssh-keygen >/dev/null 2>&1; then
  ssh-keygen -t ed25519 -N '' -C 'a@b' -f "$T3/.ssh/id_a" >/dev/null 2>&1
  ssh-keygen -t ed25519 -N '' -C 'c@d' -f "$T3/.ssh/id_b" >/dev/null 2>&1
  f1=$(HOME="$T3" PR="$PLUGIN_ROOT" bash -c 'source "$PR/lib/logger.sh" 2>/dev/null||true; _devforge_local_identity_signals_tools' 2>/dev/null | awk -F'\t' '{print $1}')
  f2=$(HOME="$T3" PR="$PLUGIN_ROOT" bash -c 'source "$PR/lib/logger.sh" 2>/dev/null||true; _devforge_local_identity_signals_tools' 2>/dev/null | awk -F'\t' '{print $1}')
  [ -n "$f1" ] && [ "$f1" = "$f2" ] && ok "tools: ssh_fingerprint deterministico ('$f1')" || ko "tools: ssh_fp non deterministico ('$f1' vs '$f2')"
else
  ok "tools: ssh_fingerprint SKIP (ssh-keygen assente)"
fi

# SSH 0 chiavi → vuoto, nessun abort
T4="$(mktemp -d)"; mkdir -p "$T4/.ssh"
sub=$(HOME="$T4" PR="$PLUGIN_ROOT" bash -c 'set -euo pipefail; source "$PR/lib/logger.sh" 2>/dev/null||true; _devforge_local_identity_signals_tools >/dev/null 2>&1 && echo OK' 2>/dev/null||echo "")
[ "$sub" = "OK" ] && ok "tools: SSH 0 chiavi → nessun abort" || ko "tools: abort con 0 chiavi SSH"
rm -rf "$T3" "$T4"

# ---- Parte bundle (task-04) ----
T5="$(mktemp -d)"
printf '{"oauthAccount":{"emailAddress":"lorenzo.detomasi@siae.it","accountUuid":"u1","organizationUuid":"o1","organizationName":"SIAE"}}' > "$T5/.claude.json"
bundle=$(HOME="$T5" DEVFORGE_CLAUDE_JSON="$T5/.claude.json" PR="$PLUGIN_ROOT" bash -c '
  source "$PR/lib/logger.sh" 2>/dev/null || true
  devforge_identity_bundle' 2>/dev/null || echo "")
printf '%s' "$bundle" | jq_valid && ok "bundle: JSON valido" || ko "bundle: JSON NON valido"
for k in git_local_email auth_email os_full_name os_login os_domain ssh_fingerprint npm_email gh_email; do
  printf '%s' "$bundle" | grep -q "\"$k\":" && : || { ko "bundle: campo '$k' assente"; continue; }
done
printf '%s' "$bundle" | grep -q '"os_login":' && printf '%s' "$bundle" | grep -q '"gh_email":' && ok "bundle: 6 nuovi campi presenti" || ko "bundle: campi nuovi mancanti"
printf '%s' "$bundle" | grep -q '"auth_email":"lorenzo.detomasi@siae.it"' && ok "bundle: auth_email esistente preservato (additivo)" || ko "bundle: auth_email perso (regressione)"
rm -rf "$T5"

# Unicode/quote nel nome OS → bundle resta JSON valido
T6="$(mktemp -d)"; mkdir -p "$T6/bin"
for d in $(echo "$PATH" | tr ':' ' '); do [ -d "$d" ] && ln -sf "$d"/* "$T6/bin/" 2>/dev/null || true; done
# shim id che ritorna nome con apostrofo+quote+unicode (simula id -F)
cat > "$T6/bin/id" <<'EOF'
#!/usr/bin/env bash
[ "$1" = "-F" ] && { printf 'O%sBrien "Jörg"\n' "'"; exit 0; }
exec /usr/bin/id "$@"
EOF
chmod +x "$T6/bin/id"
bundle=$(HOME="$T6" PATH="$T6/bin" PR="$PLUGIN_ROOT" bash -c 'source "$PR/lib/logger.sh" 2>/dev/null||true; devforge_identity_bundle' 2>/dev/null||echo "")
printf '%s' "$bundle" | jq_valid && ok "bundle: nome con quote/apostrofo/unicode → JSON valido (sanitize)" || ko "bundle: JSON rotto da nome con caratteri speciali"
rm -rf "$T6"

echo "  TOTALE: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
