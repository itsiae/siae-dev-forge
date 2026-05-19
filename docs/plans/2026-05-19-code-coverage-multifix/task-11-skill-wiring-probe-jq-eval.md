# Task 11 — SKILL.md wiring: probe-first + drop jq + eval hardening

**Fix-group:** G7, G9, G11
**ADR riferito:** ADR-7 (probe-first), ADR-9 (drop jq), ADR-11 (eval hardening)
**Stato:** [PENDING]
**Dipendenze:** Task 09 (SKILL.md compaction prima)

## File modificati

- `skills/code-coverage/SKILL.md`
- `skills/code-coverage/lib/phase6-coverage.sh` (modifiche definitive)

## Implementazione

### G7 — Phase 5b Coverage Probe

In SKILL.md WORKFLOW, dopo Phase 4 inserisci:

```markdown
### Phase 5b — Coverage Probe (conditional)

**Trigger:** `stack.existing_test_frameworks != []` AND `stack.module_coverage == []`

```bash
bash skills/code-coverage/lib/phase6-coverage.sh <repo>  # PROBE run
python3 skills/code-coverage/scripts/parse_coverage.py \
  "$FORMAT" "<repo>/$REPORT_PATH" > .code-coverage/coverage-report.json
# Re-walk module_coverage; D1 attivera' TIER-FIRST nel Phase 5 successivo
```
```

### G9 — Drop jq

In Phase 0:
```bash
# PRIMA:
for tool in python3 jq; do ... done
# DOPO:
command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 required" >&2; exit 1; }
```

In Phase 6 (e nel lib/phase6-coverage.sh creato in Task 09):
```bash
# PRIMA:
COV_CMD=$(echo "$SEL" | jq -r '.cov_cmd')
# DOPO:
COV_CMD=$(printf '%s' "$SEL" | python3 -c "import json,sys; print(json.load(sys.stdin).get('cov_cmd', ''))")
```
Idem per `report_path`, `format`, `error`, `manifest_root`.

### G11 — eval hardening

In `lib/phase6-coverage.sh`:
```bash
# PRIMA:
cd "<repo>" && eval "$COV_CMD" 2>&1 | tee .code-coverage/coverage-stdout.log
# DOPO:
REPO_QUOTED=$(printf '%q' "$REPO")
MANIFEST_QUOTED=$(printf '%q' "$MANIFEST_ROOT")
TARGET_DIR="$REPO"
if [ "$MANIFEST_ROOT" != "." ]; then
  TARGET_DIR="$REPO/$MANIFEST_ROOT"
fi
( cd "$TARGET_DIR" && bash -c "$COV_CMD" ) 2>&1 | tee "$REPO/.code-coverage/coverage-stdout.log"
```

## Criterio di accettazione

- Zero `jq` references in SKILL.md (verifica con `grep -c jq SKILL.md` → 0)
- Zero `eval` references in `lib/phase6-coverage.sh` (verifica con `grep -c eval lib/phase6-coverage.sh` → 0)
- SKILL.md WORKFLOW include Phase 5b Coverage Probe
- E2E: su repo con test esistenti, Phase 5b si attiva e popola module_coverage prima di Phase 5
