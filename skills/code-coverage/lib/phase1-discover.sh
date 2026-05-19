#!/usr/bin/env bash
# phase1-discover.sh — Parallel discovery runner per Phase 1 di /code-coverage.
#
# Esegue in parallelo (skip se cache valida via is_cache_valid) i 3 detector
# Python:
#   - detect_stack.py     → stack.json
#   - estimate_size.py    → size.json
#   - validate_env.py     → env.json
#
# Fail-fast: se UNO dei subprocess esce con codice != 0, abort dell'intera Phase 1
# (no parsing parziale, no stack.json mezzo-scritto).
#
# Uso:
#   bash skills/code-coverage/lib/phase1-discover.sh <repo_path>
#
# Pre-condizione: init_workdir <repo_path> deve essere stato chiamato (Phase 0).

set -e
set -o pipefail

REPO="${1:?usage: phase1-discover.sh <repo_path>}"

if [ ! -d "$REPO" ]; then
  echo "ERROR: repo path not found: $REPO" >&2
  exit 1
fi

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=cache-helper.sh
source "$SKILL_DIR/lib/cache-helper.sh"

# Pinnacle file: il primo manifest trovato in root sancisce la mtime di cache.
STACK_PINNACLE=""
for f in package.json pom.xml Cargo.toml pyproject.toml build.gradle build.gradle.kts pubspec.yaml go.mod; do
  if [ -f "$REPO/$f" ]; then
    STACK_PINNACLE="$REPO/$f"
    break
  fi
done

PIDS=()

if is_cache_valid "$REPO/.code-coverage/stack.json" "$STACK_PINNACLE"; then
  echo "[cache] stack.json hit"
else
  python3 "$SKILL_DIR/scripts/detect_stack.py" "$REPO" \
    > "$REPO/.code-coverage/stack.json" &
  PIDS+=($!)
fi

if is_cache_valid "$REPO/.code-coverage/size.json" "$STACK_PINNACLE"; then
  echo "[cache] size.json hit"
else
  python3 "$SKILL_DIR/scripts/estimate_size.py" "$REPO" \
    --file-list \
    --with-coverage "$REPO/.code-coverage/coverage-report.json" \
    > "$REPO/.code-coverage/size.json" &
  PIDS+=($!)
fi

if is_cache_valid "$REPO/.code-coverage/env.json" "$STACK_PINNACLE"; then
  echo "[cache] env.json hit"
else
  python3 "$SKILL_DIR/scripts/validate_env.py" "$REPO" \
    > "$REPO/.code-coverage/env.json" &
  PIDS+=($!)
fi

# Fail-fast: aspetta tutti i PID e propaga il primo errore.
for pid in "${PIDS[@]}"; do
  if ! wait "$pid"; then
    echo "ERROR: Phase 1 subprocess pid=$pid failed" >&2
    exit 1
  fi
done

echo "[phase1] discovery complete: stack.json size.json env.json"
