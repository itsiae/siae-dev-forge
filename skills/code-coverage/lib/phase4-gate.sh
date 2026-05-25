#!/usr/bin/env bash
# phase4-gate.sh — HARD-WARN consumer gate per Task 03 (jdk-lombok-compat).
#
# Closes consumer-side gap della skill code-coverage: env.json.jdk_compat.severity
# può essere OK | WARN | HARD-WARN. Quando HARD-WARN (es. Lombok 1.18.16 + JDK 25),
# la skill consumer DEVE abortire il primo mvn run e suggerire il fix
# (suggested_fix contiene il comando `export JAVA_HOME=...`).
#
# Senza questo gate, la skill prosegue e brucia 1 ciclo mvn (~30s test-compile +
# crittico error message). Phase 4 deve invocare questo gate PRIMA di lanciare mvn.
#
# Usage:
#   # Sourceable
#   source skills/code-coverage/lib/phase4-gate.sh
#   check_jdk_compat_gate /path/to/repo
#
#   # Standalone CLI
#   bash skills/code-coverage/lib/phase4-gate.sh /path/to/repo
#
# Exit codes:
#   0 = OK | WARN | env.json missing | parse error (fail-open)
#   2 = HARD-WARN (consumer MUST abort mvn run)

# Public function — sourceable
check_jdk_compat_gate() {
    local repo="${1:-.}"
    local env_json="$repo/.code-coverage/env.json"

    # 1. Verifica .code-coverage/env.json esiste (fail-open se mancante)
    if [ ! -f "$env_json" ]; then
        return 0
    fi

    # 2. Estrae jdk_compat.{severity,reason,suggested_fix} via python3 stdlib
    local parsed
    parsed=$(python3 - "$env_json" <<'PY' 2>/dev/null
import json
import sys

path = sys.argv[1]
try:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
except (OSError, json.JSONDecodeError):
    sys.exit(0)

jdk = data.get("jdk_compat") or {}
severity = jdk.get("severity") or ""
reason = jdk.get("reason") or ""
fix = jdk.get("suggested_fix") or ""

# Pipe-separated payload (severity has fixed alphabet, never contains '|')
print(f"{severity}|{reason}|{fix}")
PY
)

    # Errore parsing JSON / file vuoto / chiave assente → fail-open
    if [ -z "$parsed" ]; then
        return 0
    fi

    local severity="${parsed%%|*}"
    local rest="${parsed#*|}"
    local reason="${rest%%|*}"
    local suggested_fix="${rest#*|}"

    # 3. Comportamento per severity
    case "$severity" in
        OK)
            # Silent, return 0
            return 0
            ;;
        WARN)
            echo "[phase4] WARN: ${reason}" >&2
            return 0
            ;;
        HARD-WARN)
            echo "[phase4] BLOCKED: ${reason}" >&2
            echo "[phase4] Suggested fix: ${suggested_fix}" >&2
            echo "[phase4] Override: re-run validate_env.py --ignore-jdk-mismatch" >&2
            return 2
            ;;
        *)
            # Valori sconosciuti / vuoti → fail-open per non bloccare run legittimi
            return 0
            ;;
    esac
}

# Standalone CLI: detection sourcing vs exec
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    check_jdk_compat_gate "${1:-.}"
    exit $?
fi
