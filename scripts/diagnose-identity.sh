#!/usr/bin/env bash
# diagnose-identity.sh — Probe isolamento identità per-persona su macchine condivise.
#
# Uso: bash scripts/diagnose-identity.sh
#
# Output: una riga chiave=valore per ogni campo diagnostico + riga VERDICT.
# Sicurezza: oauth_account_uuid è mascherato (primi 8 char + "…"), mai file in chiaro.
# Standalone: non impatta il runtime degli hook.

set -euo pipefail

# ---------------------------------------------------------------------------
# Risoluzione interprete JSON (inline chain node→python3, senza sourciare logger.sh
# per evitare side-effect: mkdir log, DEVFORGE_LOG_FILE, etc.)
# ---------------------------------------------------------------------------
_diag_json_field() {
    local file="$1" path="$2"
    [ -f "$file" ] || { printf ''; return 0; }
    if command -v node >/dev/null 2>&1; then
        local out
        out=$(node -e '
try {
  var fs=require("fs");
  var d=JSON.parse(fs.readFileSync(process.argv[1],"utf8"));
  var v=process.argv[2].split(".").reduce(function(o,k){return (o&&o[k]!=null)?o[k]:""},d);
  process.stdout.write(String(v||""));
} catch(e) { process.exit(3); }
' "$file" "$path" 2>/dev/null) && { printf '%s' "$out"; return 0; }
    fi
    if command -v python3 >/dev/null 2>&1; then
        local out
        out=$(python3 -c '
import json,sys,functools
d=json.load(open(sys.argv[1], encoding="utf-8"))
v=functools.reduce(lambda o,k:(o.get(k,"") if isinstance(o,dict) else ""),sys.argv[2].split("."),d)
sys.stdout.write(str(v or ""))
' "$file" "$path" 2>/dev/null) && { printf '%s' "$out"; return 0; }
    fi
    printf ''
}

_diag_json_interpreter() {
    if command -v node >/dev/null 2>&1; then
        printf 'node'
    elif command -v python3 >/dev/null 2>&1; then
        printf 'python3'
    else
        printf 'none'
    fi
}

# ---------------------------------------------------------------------------
# Raccolta segnali
# ---------------------------------------------------------------------------

# HOME
home_val="${HOME:-}"
printf 'HOME=%s\n' "$home_val"

# CLAUDE_CONFIG_DIR (può essere non settata)
cfg_dir="${CLAUDE_CONFIG_DIR:-}"
printf 'CLAUDE_CONFIG_DIR=%s\n' "$cfg_dir"

# Determina il path effettivo del file .claude.json
# Priorità: DEVFORGE_CLAUDE_JSON (override test) → CLAUDE_CONFIG_DIR/.claude.json → ~/.claude.json
if [ -n "${DEVFORGE_CLAUDE_JSON:-}" ]; then
    claude_json_path="$DEVFORGE_CLAUDE_JSON"
elif [ -n "$cfg_dir" ] && [ -f "${cfg_dir}/.claude.json" ]; then
    claude_json_path="${cfg_dir}/.claude.json"
else
    claude_json_path="${home_val}/.claude.json"
fi
printf 'claude_json_path=%s\n' "$claude_json_path"

# Esistenza del file
if [ -f "$claude_json_path" ]; then
    claude_json_exists="yes"
else
    claude_json_exists="no"
fi
printf 'claude_json_exists=%s\n' "$claude_json_exists"

# Lettura campi OAuth (solo se file esiste)
oauth_email=""
oauth_account_uuid_raw=""
if [ "$claude_json_exists" = "yes" ]; then
    oauth_email=$(_diag_json_field "$claude_json_path" "oauthAccount.emailAddress" 2>/dev/null || true)
    oauth_account_uuid_raw=$(_diag_json_field "$claude_json_path" "oauthAccount.accountUuid" 2>/dev/null || true)
fi
printf 'oauth_email=%s\n' "$oauth_email"

# Mascheramento UUID: primi 8 char + "…"  (siae-security)
if [ -n "$oauth_account_uuid_raw" ]; then
    oauth_account_uuid_masked="${oauth_account_uuid_raw:0:8}…"
else
    oauth_account_uuid_masked=""
fi
printf 'oauth_account_uuid=%s\n' "$oauth_account_uuid_masked"

# OS user
os_user="${USER:-}"
if [ -z "$os_user" ]; then
    os_user=$(whoami 2>/dev/null || echo "")
fi
printf 'os_user=%s\n' "$os_user"

# host short-name
host_full=$(hostname -s 2>/dev/null || hostname 2>/dev/null || echo "")
host_short="${host_full%%.*}"
printf 'host_short=%s\n' "$host_short"

# Interprete JSON disponibile
printf 'json_interpreter=%s\n' "$(_diag_json_interpreter)"

# ---------------------------------------------------------------------------
# CLAUDE_CONFIG_DIR onorato?
# Logica: "onorato=si" se:
#   - DEVFORGE_CLAUDE_JSON è settato (modalità test, path esplicito) E coincide con cfg_dir/.claude.json, OPPURE
#   - cfg_dir è non-vuoto, il file cfg_dir/.claude.json esiste, E claude_json_path == cfg_dir/.claude.json
# ---------------------------------------------------------------------------
cfg_honored="no"
if [ -n "$cfg_dir" ]; then
    expected_cfg_path="${cfg_dir}/.claude.json"
    if [ "$claude_json_path" = "$expected_cfg_path" ] && [ -f "$expected_cfg_path" ]; then
        cfg_honored="si"
    fi
fi
printf 'CLAUDE_CONFIG_DIR onorato=%s\n' "$cfg_honored"

# ---------------------------------------------------------------------------
# VERDICT
# Precedenza: NO-AUTH → ISOLATED → SHARED-DEGENERATE
# - NO-AUTH:           oauth_email vuoto (nessuna sessione autenticata)
# - ISOLATED:          cfg_dir non-vuoto, onorato=si
# - SHARED-DEGENERATE: legge ~/.claude.json, CLAUDE_CONFIG_DIR non settato o non onorato
# ---------------------------------------------------------------------------
if [ -z "$oauth_email" ]; then
    verdict="NO-AUTH"
elif [ "$cfg_honored" = "si" ]; then
    verdict="ISOLATED"
else
    verdict="SHARED-DEGENERATE"
fi
printf 'VERDICT: %s\n' "$verdict"
