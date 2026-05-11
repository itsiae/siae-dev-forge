#!/usr/bin/env bash
# tools/benchmark-skill.sh — misura metriche skill code-coverage
# Usage: ./tools/benchmark-skill.sh <repo-path> <run-label> [out-file]
#
# Output: appende un'entry JSON al file specificato (default
# docs/plans/2026-05-09-code-coverage-optimization/baseline-metrics.json).
# Misura 8 metriche dal contenuto di <repo-path>/.code-coverage/ popolato
# dall'esecuzione precedente della skill code-coverage.

set -euo pipefail

REPO_PATH="${1:?repo path required}"
RUN_LABEL="${2:?run label required (es. baseline | post-pr1 | final)}"
OUT_FILE="${3:-docs/plans/2026-05-09-code-coverage-optimization/baseline-metrics.json}"

if [ ! -d "$REPO_PATH" ]; then
  echo "ERROR: repo path '$REPO_PATH' does not exist" >&2
  exit 1
fi

START_TS=$(date +%s)

# 1. Conta approval gate triggers nel decisions.log (manuale per baseline)
GATE_COUNT=0

# 2. Conta full coverage runs (pattern coverage runner nel decisions.log)
COVERAGE_RUNS=$(grep -cE '(vitest run --coverage|pytest --cov|mvn test|gradle test|cargo tarpaulin|go test -cover|jest --coverage)' \
  "$REPO_PATH/.code-coverage/decisions.log" 2>/dev/null || echo 0)

# 3. Misura iter Phase 7 (cerca "iteration" nel decisions.log)
PHASE7_ITER=$(grep -cE 'iteration [0-9]+' "$REPO_PATH/.code-coverage/decisions.log" 2>/dev/null || echo 0)

# 4. Conta reference file load (cerca "phase-N-...md" nel log)
REF_LOADS=$(grep -cE 'phase-[1-7]-.+\.md' "$REPO_PATH/.code-coverage/decisions.log" 2>/dev/null || echo 0)

# 5. Coverage finale (parse coverage-report.json se esiste, altrimenti coverage-output.txt)
GLOBAL_PCT=0
P1_PCT=0
if [ -f "$REPO_PATH/.code-coverage/coverage-report.json" ]; then
  GLOBAL_PCT=$(python3 -c "import json; d=json.load(open('$REPO_PATH/.code-coverage/coverage-report.json')); print(d.get('global_pct', 0))" 2>/dev/null || echo 0)
  P1_PCT=$(python3 -c "import json; d=json.load(open('$REPO_PATH/.code-coverage/coverage-report.json')); p1=[m for m in d.get('modules', []) if m.get('priority')=='P1']; print(min((m['lines_pct'] for m in p1), default=0))" 2>/dev/null || echo 0)
elif [ -f "$REPO_PATH/.code-coverage/coverage-output.txt" ]; then
  GLOBAL_PCT=$(grep -oE 'All files.*?[0-9]+\.[0-9]+' "$REPO_PATH/.code-coverage/coverage-output.txt" 2>/dev/null | head -1 | grep -oE '[0-9]+\.[0-9]+' | head -1 || echo 0)
fi

# 6. Wall-clock — placeholder per misurazione baseline manuale
END_TS=$(date +%s)
WALL_CLOCK=$((END_TS - START_TS))

# 7. Placeholder leakage (grep su test files generati)
PLACEHOLDER_LEAK=$(grep -rE '\{\{[A-Z_]+\}\}' "$REPO_PATH" --include='*.test.*' --include='*test_*.py' 2>/dev/null | wc -l | tr -d ' ' || echo 0)

# 8. Emit JSON entry
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
REPO_NAME=$(basename "$REPO_PATH")
REPO_SHA=$(git -C "$REPO_PATH" rev-parse --short HEAD 2>/dev/null || echo "unknown")

OUT_FILE_ABS="$OUT_FILE" \
TIMESTAMP="$TIMESTAMP" \
RUN_LABEL="$RUN_LABEL" \
REPO_NAME="$REPO_NAME" \
REPO_PATH="$REPO_PATH" \
REPO_SHA="$REPO_SHA" \
GATE_COUNT="$GATE_COUNT" \
COVERAGE_RUNS="$COVERAGE_RUNS" \
PHASE7_ITER="$PHASE7_ITER" \
REF_LOADS="$REF_LOADS" \
GLOBAL_PCT="$GLOBAL_PCT" \
P1_PCT="$P1_PCT" \
WALL_CLOCK="$WALL_CLOCK" \
PLACEHOLDER_LEAK="$PLACEHOLDER_LEAK" \
python3 - <<'PYEOF'
import json
import os

def to_num(s, fallback=0):
    s = (s or "").strip()
    if not s:
        return fallback
    try:
        if "." in s:
            return float(s)
        return int(s)
    except ValueError:
        return fallback

out_path = os.environ["OUT_FILE_ABS"]

entry = {
    "timestamp": os.environ["TIMESTAMP"],
    "run_label": os.environ["RUN_LABEL"],
    "repo_name": os.environ["REPO_NAME"],
    "repo_path": os.environ["REPO_PATH"],
    "repo_sha": os.environ["REPO_SHA"],
    "metrics": {
        "user_round_trips": to_num(os.environ["GATE_COUNT"]),
        "full_coverage_runs": to_num(os.environ["COVERAGE_RUNS"]),
        "phase7_iterations": to_num(os.environ["PHASE7_ITER"]),
        "reference_loads": to_num(os.environ["REF_LOADS"]),
        "global_coverage_pct": to_num(os.environ["GLOBAL_PCT"]),
        "p1_min_coverage_pct": to_num(os.environ["P1_PCT"]),
        "wall_clock_seconds": to_num(os.environ["WALL_CLOCK"]),
        "placeholder_leakage": to_num(os.environ["PLACEHOLDER_LEAK"]),
    },
    "transcript_tokens": None,
}

os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

# Output schema: { repo_pinning: {...}, metric_collection_status: {...}, runs: [entry, ...] }
# Backward-compat: se file e' una lista, viene migrato a {"runs": [...]} preservando le entry.
doc = {"runs": []}
if os.path.exists(out_path):
    try:
        with open(out_path) as f:
            loaded = json.load(f)
        if isinstance(loaded, list):
            doc = {"runs": loaded}
        elif isinstance(loaded, dict):
            doc = loaded
            doc.setdefault("runs", [])
    except (json.JSONDecodeError, OSError):
        pass

doc["runs"].append(entry)
with open(out_path, "w") as f:
    json.dump(doc, f, indent=2)
    f.write("\n")
print(f"Appended baseline entry for {entry['repo_name']} ({entry['run_label']})")
PYEOF
