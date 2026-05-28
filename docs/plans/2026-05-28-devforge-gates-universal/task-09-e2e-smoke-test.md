# Task 09 — E2E smoke test su repo non-itsiae locale

> **REQUIRED SUB-SKILL:** `siae-verification` (verifica end-to-end pre-merge)
> **Dipendenza:** task 1-8 completati

**Goal:** Smoke test E2E su working dir reale fuori `itsiae/*` verifica che tutti e 5 i gate scattino con default universal, e che `DEVFORGE_GATE_SCOPE=itsiae` ripristini il vecchio behavior.

**File coinvolti:**
- Crea: `tests/e2e/smoke_universal.test.sh`
- Eventuale fix di residui post-test (no nuovi file plan/skill)

---

## Step 1 — Scrivi lo smoke test E2E

Crea `tests/e2e/smoke_universal.test.sh`:

```bash
#!/usr/bin/env bash
# E2E smoke: i 5 gate scattano su repo non-itsiae con default universal
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

PASS=0
FAIL=0
DETAILS=""

# Setup repo non-itsiae
mkdir -p "$TMPDIR/myproject"
cd "$TMPDIR/myproject"
git init -q
git remote add origin "git@github.com:acme/myproject.git"

# Cleanup state
rm -f "${HOME}/.claude/.devforge-session-skills"
unset DEVFORGE_GATE_SCOPE

# Per ogni gate, costruisci input hook appropriato e attendi block
check_block() {
    local hook_name="$1" input_json="$2"
    local output
    output=$(echo "$input_json" | bash "${REPO_ROOT}/hooks/$hook_name" 2>/dev/null)
    if echo "$output" | grep -q '"decision"[[:space:]]*:[[:space:]]*"block"'; then
        PASS=$((PASS+1)); printf "  [PASS] universal: %s blocks on acme repo\n" "$hook_name"
    else
        FAIL=$((FAIL+1))
        DETAILS="${DETAILS}\n  [FAIL] universal: $hook_name did NOT block on acme repo. Output: $output"
    fi
}

check_passes() {
    local hook_name="$1" input_json="$2"
    local output
    output=$(echo "$input_json" | bash "${REPO_ROOT}/hooks/$hook_name" 2>/dev/null)
    if echo "$output" | grep -q '"decision"[[:space:]]*:[[:space:]]*"block"'; then
        FAIL=$((FAIL+1))
        DETAILS="${DETAILS}\n  [FAIL] itsiae scope: $hook_name blocked on acme (expected no-op rollback)"
    else
        PASS=$((PASS+1)); printf "  [PASS] itsiae scope: %s no-op on acme repo (rollback)\n" "$hook_name"
    fi
}

# Universal default — tutti i 5 gate devono BLOCK
check_block "pr-premortem-gate"   '{"tool_input":{"command":"gh pr create"}}'
check_block "pr-blind-review-gate" '{"tool_input":{"command":"gh pr create"}}'
check_block "tdd-gate"             '{"tool_input":{"file_path":"src/main.java","new_string":"x"}}'
check_block "brainstorming-gate"   '{"tool_input":{"file_path":"src/main.java","new_string":"x"}}'
check_block "plan-gate-write"      "{\"tool_input\":{\"file_path\":\"$TMPDIR/myproject/docs/plans/foo/task-01.md\",\"new_string\":\"x\"}}"

# Rollback itsiae — tutti i 5 gate devono PASS (no-op)
export DEVFORGE_GATE_SCOPE=itsiae
check_passes "pr-premortem-gate"   '{"tool_input":{"command":"gh pr create"}}'
check_passes "pr-blind-review-gate" '{"tool_input":{"command":"gh pr create"}}'
check_passes "tdd-gate"             '{"tool_input":{"file_path":"src/main.java","new_string":"x"}}'
check_passes "brainstorming-gate"   '{"tool_input":{"file_path":"src/main.java","new_string":"x"}}'
check_passes "plan-gate-write"      "{\"tool_input\":{\"file_path\":\"$TMPDIR/myproject/docs/plans/foo/task-01.md\",\"new_string\":\"x\"}}"

unset DEVFORGE_GATE_SCOPE

echo
echo "smoke_universal.test.sh — PASS: $PASS / 10 — FAIL: $FAIL / 10"
[ -n "$DETAILS" ] && echo -e "$DETAILS"
[ "$FAIL" -eq 0 ] || exit 1
```

## Step 2 — Esegui e verifica

Pre-condizione: tutti i task 1-8 completati. Se task 6 (brainstorming) o altri non sono completi, alcuni `check_block` falliranno → segnale per fixare il task incompleto.

```bash
bash tests/e2e/smoke_universal.test.sh
```

Atteso post task 1-8: `PASS: 10 / 10`, exit 0.

## Step 3 — Verifiche globali post-smoke

Crea `tests/e2e/global_grep.test.sh` per asserire exit code esplicito su ogni grep:

```bash
#!/usr/bin/env bash
# Global grep checks — no residual itsiae coupling
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

PASS=0; FAIL=0

assert_grep_no_match() {
    local desc="$1" pattern="$2" path="$3"
    # Exclude docs/plans (contains historical design discussions) and .git
    if grep -qrE "$pattern" "$path" \
        --exclude-dir=docs/plans --exclude-dir=.git --exclude-dir=node_modules 2>/dev/null; then
        FAIL=$((FAIL+1))
        printf "  [FAIL] %s — match found:\n" "$desc"
        grep -rnE "$pattern" "$path" --exclude-dir=docs/plans --exclude-dir=.git 2>/dev/null | head -5
    else
        PASS=$((PASS+1))
        printf "  [PASS] %s\n" "$desc"
    fi
}

# 5 hook: nessun residuo grep itsiae inline
for hook in brainstorming-gate plan-gate-write tdd-gate pr-blind-review-gate pr-premortem-gate; do
    if grep -qE 'grep -qE "\[/:\]itsiae/"' "${REPO_ROOT}/hooks/${hook}" 2>/dev/null; then
        FAIL=$((FAIL+1)); printf "  [FAIL] hooks/%s still has inline grep itsiae\n" "$hook"
    else
        PASS=$((PASS+1)); printf "  [PASS] hooks/%s — no inline grep itsiae\n" "$hook"
    fi
done

# Path errato hooks/lib/scope (canonical è lib/scope)
assert_grep_no_match "no 'hooks/lib/scope' references anywhere" "hooks/lib/scope" "${REPO_ROOT}"

# SKILL premortem: nessun ref itsiae/* nel scope (mantenute solo le stat citations)
if grep -qE 'on itsiae/\* repos|prima di .gh pr create. su .itsiae' "${REPO_ROOT}/skills/siae-premortem/SKILL.md"; then
    FAIL=$((FAIL+1)); printf "  [FAIL] siae-premortem SKILL still has itsiae scope ref\n"
else
    PASS=$((PASS+1)); printf "  [PASS] siae-premortem SKILL — no scope itsiae ref\n"
fi

# Plugin version dual source aligned
PV=$(grep -oE '"version":[[:space:]]*"[^"]*"' "${REPO_ROOT}/.claude-plugin/plugin.json" | head -1 | sed 's/.*"\([^"]*\)"$/\1/')
MV=$(grep -oE '"version":[[:space:]]*"[^"]*"' "${REPO_ROOT}/.claude-plugin/marketplace.json" | head -1 | sed 's/.*"\([^"]*\)"$/\1/')
if [ "$PV" = "1.69.0" ] && [ "$MV" = "1.69.0" ]; then
    PASS=$((PASS+1)); printf "  [PASS] plugin.json + marketplace.json aligned at 1.69.0\n"
else
    FAIL=$((FAIL+1)); printf "  [FAIL] version mismatch: plugin=%s marketplace=%s\n" "$PV" "$MV"
fi

echo
echo "global_grep.test.sh — PASS: $PASS / 8 — FAIL: $FAIL / 8"
[ "$FAIL" -eq 0 ] || exit 1
```

Esegui tutti i test in sequenza con exit code esplicito:

```bash
set -e
bash tests/scope_check.test.sh
bash tests/integration/pr_premortem_gate.test.sh
bash tests/integration/tdd_gate.test.sh
bash tests/integration/pr_blind_review_gate.test.sh
bash tests/integration/plan_gate_write.test.sh
bash tests/integration/brainstorming_gate.test.sh
bash tests/skill_premortem_generalized.test.sh
bash tests/docs_and_version.test.sh
bash tests/e2e/smoke_universal.test.sh
bash tests/e2e/global_grep.test.sh
echo "ALL TESTS PASSED"
```

Atteso: `ALL TESTS PASSED` con exit 0. Se uno qualsiasi fallisce, `set -e` interrompe e exit != 0 (memory `feedback_test_verify_via_exit_code`).

## Step 4 — Verifica iCloud edge case (opzionale, manuale)

```bash
# Smoke su path con spazi (simula iCloud)
TMPSPACES=$(mktemp -d -t "test space.XXX")
cd "$TMPSPACES" && git init -q && git remote add origin git@github.com:acme/x.git
echo '{"tool_input":{"command":"gh pr create"}}' | bash "${REPO_ROOT}/hooks/pr-premortem-gate"
# Atteso: decision: block (gate funziona anche con path che ha spazi)
rm -rf "$TMPSPACES"
```

## Step 5 — Commit finale

```bash
git add tests/e2e/smoke_universal.test.sh
git commit -m "test(e2e): smoke universal gate enforcement on non-itsiae repo

Verifies that all 5 workflow gates (brainstorming, plan-gate-write, tdd,
pr-blind-review, pr-premortem) block on a fresh acme git repo with default
DEVFORGE_GATE_SCOPE=universal, and no-op when set to itsiae (rollback).
10 E2E checks PASS.

Co-Authored-By: SIAE DevForge"
```

---

## Criteri di accettazione

- [ ] `bash tests/e2e/smoke_universal.test.sh` exit 0 con `PASS: 10 / 10`
- [ ] `grep -rn "hooks/lib/scope" .` ritorna 0 match
- [ ] `grep -cE 'grep -qE "\[/:\]itsiae/"' hooks/{brainstorming,plan-gate-write,tdd,pr-blind-review,pr-premortem}-gate` ritorna 5 zeri (uno per file)
- [ ] Tutti i 9 test del piano (1+2+3+4+5+6+7+8+9) exit 0 in sequenza
- [ ] Smoke su path con spazi (iCloud-like) verifica gate funzionante
