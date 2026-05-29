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

# Phase 2 pre-compute: detect_jest_incompat runs in parallel with other
# detectors so Phase 2 can read jest-compat.json without an extra wait.
# Bug-fix 2026-05-28: Vitest-first decision lives here (closed list I1..I10).
mkdir -p "$REPO/.code-coverage"
if find "$REPO" -maxdepth 4 -name package.json -not -path '*/node_modules/*' -print -quit 2>/dev/null | grep -q .; then
  if is_cache_valid "$REPO/.code-coverage/jest-compat.json" "$STACK_PINNACLE"; then
    echo "[cache] jest-compat.json hit"
  else
    python3 "$SKILL_DIR/scripts/detect_jest_incompat.py" "$REPO" \
      > "$REPO/.code-coverage/jest-compat.json" 2>/dev/null &
    PIDS+=($!)
  fi
fi

if is_cache_valid "$REPO/.code-coverage/ci-thresholds.json" "$STACK_PINNACLE"; then
  echo "[cache] ci-thresholds.json hit"
else
  python3 "$SKILL_DIR/scripts/detect_ci_thresholds.py" "$REPO" \
    > "$REPO/.code-coverage/ci-thresholds.json" 2>/dev/null &
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

# ─── C3 fix: Phase 5b probe trigger (idempotent, bash-side) ────────────────
# Sposta la decisione "serve coverage probe" da LLM-side a bash-side per
# eliminare 1 round-trip Phase 5b. Idempotente: skip se coverage-report.json
# è già presente.
PROBE_STATE="not_needed"
if [ -f "$REPO/.code-coverage/coverage-report.json" ]; then
  echo "[phase1] phase5b probe skipped: coverage-report.json already present"
  PROBE_STATE="skipped"
else
  NEED_PROBE=$(python3 - "$REPO" <<'PYEOF'
import json, sys
repo = sys.argv[1]
try:
    d = json.load(open(f"{repo}/.code-coverage/stack.json"))
except Exception:
    print('no')
else:
    efs = d.get('existing_test_frameworks', [])
    tfc = d.get('test_infrastructure', {}).get('test_files_count', 0)
    mc = d.get('module_coverage', [])
    print('yes' if (efs and tfc > 0 and not mc) else 'no')
PYEOF
)
  if [ "$NEED_PROBE" = "yes" ]; then
    echo "[phase1] phase5b probe auto-triggered"
    if bash "$SKILL_DIR/lib/phase6-coverage.sh" "$REPO" --probe; then
      PROBE_STATE="ran"
    else
      echo "[phase1] phase5b probe failed (non-fatal)"
      PROBE_STATE="ran"
    fi
  fi
fi

# ─── C4b fix: emit discovery-summary.json (≤2k tok) ────────────────────────
# Compatta i 3 JSON discovery in 1 summary essenziale per LLM decision-making.
python3 - "$REPO" "$PROBE_STATE" <<'PYEOF' > "$REPO/.code-coverage/discovery-summary.json"
import json, sys
from pathlib import Path
repo = Path(sys.argv[1])
probe_state = sys.argv[2]
cov_dir = repo / ".code-coverage"

def safe_load(name):
    p = cov_dir / name
    if not p.exists():
        return {}
    try:
        return json.load(open(p))
    except Exception:
        return {}

stack = safe_load("stack.json")
size = safe_load("size.json")
env = safe_load("env.json")

summary = {
    "stack": {
        "languages": stack.get("languages", []),
        "primary": stack.get("primary_language") or (stack.get("languages") or [None])[0],
        "monorepo": stack.get("monorepo", False),
        "monorepo_workspaces": stack.get("monorepo_workspaces", []),
        "manifest_root": stack.get("manifest_root", "."),
    },
    "maven_aggregator": stack.get("maven_aggregator"),  # Task 01
    "size": {
        "class": size.get("class") or size.get("size_class"),
        "loc_total": size.get("loc") or size.get("loc_total"),
        "file_count_test_target": size.get("file_count") or size.get("file_count_test_target"),
    },
    "env": {
        "missing_frameworks": env.get("missing", env.get("missing_frameworks", [])),
        "install_required": bool(env.get("blocking", env.get("install_required", False))),
    },
    "phase5b_probe": probe_state,
}
print(json.dumps(summary, indent=2))
PYEOF

echo "[phase1] discovery-summary.json emitted (phase5b_probe=$PROBE_STATE)"

# ─── Task 01: WARN se Java stack ma nessun aggregator pom rilevato ─────────
# Lasciare che il phase 4 gate gestisca required_framework=unknown; questo è
# advisory per troubleshooting (l'operatore può creare overrides.json).
if grep -q '"primary": "java"' "$REPO/.code-coverage/discovery-summary.json" 2>/dev/null \
   && grep -q '"maven_aggregator": null' "$REPO/.code-coverage/discovery-summary.json" 2>/dev/null; then
    echo "[phase1] WARN: Java stack but no aggregator pom found within CC_POM_MAXDEPTH (default 4)." >&2
    echo "[phase1] WARN: Create .code-coverage/overrides.json with {\"manifest_root\": \"...\", \"aggregator_pom\": \"...\"} to override." >&2
fi

