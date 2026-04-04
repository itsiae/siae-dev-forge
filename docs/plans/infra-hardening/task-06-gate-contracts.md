# Task 06: Gate Contract Espliciti (D6 + D6b)

**Deliverable:** D6 + D6b
**Dipendenze:** Task 01 (DEVFORGE_STATE_DIR)
**File coinvolti:** `lib/logger.sh`, `hooks/pre-commit`, `hooks/tdd-gate`, `hooks/plan-gate`, `hooks/sub-skill-gate`, `hooks/stop-gate`, `tests/run-all.sh`

---

## Step 1 — Aggiungi helper `devforge_gate_check_state` in `lib/logger.sh`

Dopo le funzioni esistenti, aggiungere:

```bash
# ─── Gate state helper ───
# Usage: devforge_gate_check_state <file> <gate_name> <behavior>
#   behavior: "fail-open" | "fail-closed"
#   Returns: 0 = proceed, 1 = block
#   Stdout: file content if exists
devforge_gate_check_state() {
    local file="$1" gate_name="$2" behavior="$3"
    if [ ! -f "$file" ]; then
        if [ "$behavior" = "fail-closed" ]; then
            devforge_log "$gate_name" "blocked" \
              "{\"reason\":\"state_file_missing\",\"file\":\"$(devforge_sanitize_json_str "$file")\"}" 2>/dev/null || true
            return 1
        fi
        return 0
    fi
    cat "$file"
}
```

## Step 2 — Aggiungi GATE CONTRACT header a ogni gate hook

Per ogni hook gate, aggiungere il header strutturato subito dopo il commento iniziale:

**`hooks/pre-commit` (git commit path):**
```bash
# ─── GATE CONTRACT ───
# Behavior:  fail-closed
# Requires:  SESSION_SKILLS_FILE (state), PLUGIN_ROOT (env)
# Reads:     ${DEVFORGE_STATE_DIR}/.devforge-session-skills
# On-missing: block commit (fail-closed)
# ─────────────────────
```

**`hooks/pre-commit` (checkout -b path):**
```bash
# ─── GATE CONTRACT ───
# Behavior:  fail-open
# Requires:  nessuno
# On-missing: proceed (branch creation senza JIRA e' legittimo)
# ─────────────────────
```

**`hooks/tdd-gate`:**
```bash
# ─── GATE CONTRACT ───
# Behavior:  fail-open
# Requires:  SESSION_SKILLS_FILE (state)
# Reads:     ${DEVFORGE_STATE_DIR}/.devforge-session-skills
# On-missing: proceed (nessun path = non e' file edit)
# ─────────────────────
```

**`hooks/plan-gate`:**
```bash
# ─── GATE CONTRACT ───
# Behavior:  fail-closed
# Requires:  SESSION_SKILLS_FILE (state)
# Reads:     ${DEVFORGE_STATE_DIR}/.devforge-session-skills
# On-missing: block (plan mode senza brainstorming = violazione)
# ─────────────────────
```

**`hooks/sub-skill-gate`:**
```bash
# ─── GATE CONTRACT ───
# Behavior:  fail-closed
# Requires:  SESSION_SKILLS_FILE (state)
# Reads:     ${DEVFORGE_STATE_DIR}/.devforge-session-skills
# On-missing: block (prerequisiti non verificabili)
# ─────────────────────
```

**`hooks/stop-gate`:**
```bash
# ─── GATE CONTRACT ───
# Behavior:  fail-open
# Requires:  SESSION_SKILLS_FILE (state), session timestamps
# On-missing: proceed (telemetria persa accettabile, bloccare stop no)
# ─────────────────────
```

## Step 3 — Refactora i gate per usare `devforge_gate_check_state`

In ogni gate hook, sostituisci la logica manuale di lettura state file con la chiamata helper. Esempio per `tdd-gate`:

```bash
# PRIMA:
SESSION_SKILLS=$(cat "${DEVFORGE_STATE_DIR}/.devforge-session-skills" 2>/dev/null || echo "")

# DOPO:
SESSION_SKILLS=$(devforge_gate_check_state \
  "${DEVFORGE_STATE_DIR}/.devforge-session-skills" "tdd-gate" "fail-open") || exit 0
```

Per gate fail-closed (plan-gate, sub-skill-gate):
```bash
SESSION_SKILLS=$(devforge_gate_check_state \
  "${DEVFORGE_STATE_DIR}/.devforge-session-skills" "plan-gate" "fail-closed") || {
    echo '{"error":"brainstorming skill not invoked"}'
    exit 1
}
```

## Step 4 — D6b: Aggiungi bypass IaC in tdd-gate

In `hooks/tdd-gate`, dopo il check estensione e prima del check SESSION_SKILLS:

```bash
# IaC config-only files: bypass TDD per SKILL.md:94
# "Config pura (.env, .yml, terraform vars) → NO — validate/plan basta"
IAC_CONFIG_BYPASS="\.tfvars$|\.auto\.tfvars$|variables\.tf$|terraform\.tfvars$"
if echo "$FILE_PATH" | grep -qE "$IAC_CONFIG_BYPASS"; then
    echo '{}'
    exit 0
fi
```

## Step 5 — Aggiungi test per bypass IaC

In `tests/run-all.sh`, nella sezione hook tests:

```bash
# D6b: TDD gate bypassa file IaC config-only
for iac_file in "vars.tfvars" "terraform.auto.tfvars" "variables.tf"; do
  iac_result=$(echo "{\"tool_input\":{\"file_path\":\"/project/${iac_file}\"}}" | \
    bash "${PLUGIN_ROOT}/hooks/tdd-gate" 2>/dev/null; echo "exit:$?")
  if echo "$iac_result" | grep -q 'exit:0'; then
    echo "  PASS  tdd-gate: bypassa ${iac_file} (IaC config-only)"
    TOTAL_PASS=$((TOTAL_PASS + 1))
  else
    echo "  FAIL  tdd-gate: non bypassa ${iac_file}"
    TOTAL_FAIL=$((TOTAL_FAIL + 1))
  fi
done
```

## Step 6 — Run test suite

```bash
tests/run-all.sh
```
Output atteso: tutti i test passano, inclusi i nuovi test IaC bypass.

## Step 7 — Commit

```bash
git add lib/logger.sh hooks/pre-commit hooks/tdd-gate hooks/plan-gate \
  hooks/sub-skill-gate hooks/stop-gate tests/run-all.sh
git commit -m "refactor(gates): add explicit GATE CONTRACT headers + check_state helper

- Add devforge_gate_check_state() to lib/logger.sh
- Each gate hook declares fail-open/fail-closed behavior
- pre-commit (commit), plan-gate, sub-skill-gate: fail-closed
- tdd-gate, stop-gate, pre-commit (checkout): fail-open
- D6b: tdd-gate bypasses .tfvars, variables.tf (IaC config-only)

Co-Authored-By: SIAE DevForge"
```
