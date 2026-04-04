# Task 09: Test + Eval Backbone

**Dipendenze:** Task 1-8 tutti completati
**File coinvolti:** `tests/run-all.sh`, nuovo `evals/trigger-evals/siae-review-gate.json`

---

## Step 1 — Test state machine

Aggiungere sezione in `tests/run-all.sh`:

```bash
# === SDLC Backbone Tests ===
echo ""
echo "=== SDLC Backbone Tests ==="
echo ""
backbone_ok=0
backbone_fail=0

# Test 1: stato iniziale e' idle
export DEVFORGE_STATE_DIR=$(mktemp -d)
source "${PLUGIN_ROOT}/lib/sdlc-state.sh"
STAGE=$(sdlc_get_current_stage)
if [ "$STAGE" = "idle" ]; then
    echo "  PASS  sdlc-state: initial stage is idle"
    backbone_ok=$((backbone_ok + 1))
else
    echo "  FAIL  sdlc-state: initial stage is '$STAGE', expected 'idle'"
    backbone_fail=$((backbone_fail + 1))
fi

# Test 2: advance + check
sdlc_advance_stage "brainstorming"
sdlc_advance_stage "plan"
PREREQS=$(sdlc_check_prerequisites "tdd")
if echo "$PREREQS" | grep -q "missing:execution"; then
    echo "  PASS  sdlc-state: prerequisites correctly report missing execution"
    backbone_ok=$((backbone_ok + 1))
else
    echo "  FAIL  sdlc-state: prerequisites wrong: $PREREQS"
    backbone_fail=$((backbone_fail + 1))
fi

# Test 3: all stages completed → ok
for stage in execution tdd review verification finish; do
    sdlc_advance_stage "$stage"
done
PREREQS=$(sdlc_check_prerequisites "finish")
if [ "$PREREQS" = "ok" ]; then
    echo "  PASS  sdlc-state: all stages completed, prerequisites ok"
    backbone_ok=$((backbone_ok + 1))
else
    echo "  FAIL  sdlc-state: with all stages, got: $PREREQS"
    backbone_fail=$((backbone_fail + 1))
fi

# Test 4: impl-gate blocks without backbone
rm -f "${DEVFORGE_STATE_DIR}/.devforge-sdlc-stage"
impl_result=$(echo '{"file_path":"src/UserService.java"}' | bash "${PLUGIN_ROOT}/hooks/impl-gate" 2>/dev/null)
if echo "$impl_result" | grep -q '"block"'; then
    echo "  PASS  impl-gate: blocks prod code without backbone stages"
    backbone_ok=$((backbone_ok + 1))
else
    echo "  FAIL  impl-gate: did not block without backbone"
    backbone_fail=$((backbone_fail + 1))
fi

# Test 5: impl-gate allows with backbone
sdlc_advance_stage "brainstorming"
sdlc_advance_stage "plan"
sdlc_advance_stage "execution"
sdlc_advance_stage "tdd"
impl_result=$(echo '{"file_path":"src/UserService.java"}' | bash "${PLUGIN_ROOT}/hooks/impl-gate" 2>/dev/null)
if [ "$impl_result" = "{}" ]; then
    echo "  PASS  impl-gate: allows prod code with backbone stages"
    backbone_ok=$((backbone_ok + 1))
else
    echo "  FAIL  impl-gate: blocked with backbone: $impl_result"
    backbone_fail=$((backbone_fail + 1))
fi

# Test 6: backbone skill count = 7
BACKBONE_COUNT=$(node -e "
const {findSkillsInDir} = require('${PLUGIN_ROOT}/lib/skills-core');
const skills = findSkillsInDir('${PLUGIN_ROOT}/skills');
console.log(skills.filter(s => s.backbone_role === 'backbone').length);
" 2>/dev/null)
if [ "$BACKBONE_COUNT" = "7" ]; then
    echo "  PASS  backbone: 7 backbone skills in frontmatter"
    backbone_ok=$((backbone_ok + 1))
else
    echo "  FAIL  backbone: ${BACKBONE_COUNT} backbone skills, expected 7"
    backbone_fail=$((backbone_fail + 1))
fi

rm -rf "$DEVFORGE_STATE_DIR"
export DEVFORGE_STATE_DIR="$_ORIGINAL_STATE_DIR"

echo ""
echo "  SDLC Backbone: ${backbone_ok} OK | ${backbone_fail} FAIL"
TOTAL_PASS=$((TOTAL_PASS + backbone_ok))
TOTAL_FAIL=$((TOTAL_FAIL + backbone_fail))
```

## Step 2 — Eval per siae-review-gate

Crea `evals/trigger-evals/siae-review-gate.json`:

```json
{
  "skill": "siae-review-gate",
  "threshold": { "precision": 0.7, "recall": 0.7 },
  "queries": [
    {"input": "il codice e' pronto, chiedi review", "expected": "siae-review-gate"},
    {"input": "facciamo un code review prima di mergare", "expected": "siae-review-gate"},
    {"input": "pronto per review", "expected": "siae-review-gate"},
    {"input": "rivedi il codice che ho scritto", "expected": "siae-review-gate"},
    {"input": "review del branch prima della PR", "expected": "siae-review-gate"}
  ]
}
```

## Step 3 — Run test suite

```bash
bash tests/run-all.sh
```
Output atteso: tutti i test backbone passano, zero regressioni.

## Step 4 — Commit

```bash
git add tests/run-all.sh evals/trigger-evals/siae-review-gate.json
git commit -m "test(backbone): add SDLC backbone tests + siae-review-gate eval

- 6 backbone tests: state machine, impl-gate, backbone count
- siae-review-gate trigger eval with 5 queries
- Tests verify all 3 rules madre are enforced

Co-Authored-By: SIAE DevForge"
```
