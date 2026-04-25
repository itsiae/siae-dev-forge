#!/usr/bin/env bash
# Behavioral non-regression: post-compression le skill mantengono le regole cardine.
set -eu
PASS=0; FAIL=0
cd "$(git rev-parse --show-toplevel)"

_assert() {
    local name="$1"; local cmd="$2"
    if eval "$cmd" >/dev/null 2>&1; then echo "  PASS  $name"; PASS=$((PASS+1))
    else echo "  FAIL  $name (cmd: $cmd)"; FAIL=$((FAIL+1)); fi
}

echo "=== K invariants — Legge di Ferro ==="
for s in siae-brainstorming siae-tdd siae-git-workflow siae-verification; do
    _assert "$s has LA LEGGE DI FERRO" "grep -q '## LA LEGGE DI FERRO' skills/$s/SKILL.md"
done

echo ""
echo "=== K invariants — HARD-GATE / EXTREMELY-IMPORTANT tags ==="
_assert "brainstorming HARD-GATE"  "grep -q '## HARD-GATE' skills/siae-brainstorming/SKILL.md"
_assert "git-workflow PRE-FLIGHT CARD" "grep -q 'PRE-FLIGHT CARD' skills/siae-git-workflow/SKILL.md"
_assert "git-workflow SCOPE GUARD"   "grep -q 'SCOPE GUARD' skills/siae-git-workflow/SKILL.md"
_assert "git-workflow force-push blocco assoluto" "grep -qE 'BLOCCO ASSOLUTO.*force' skills/siae-git-workflow/SKILL.md"

echo ""
echo "=== K invariants — Checkpoint schema preservation ==="
for cp in INTAKE SCOPE DESIGN SPEC-REVIEW GATE; do
    _assert "brainstorming has [BRAINSTORM:$cp]" "grep -q 'BRAINSTORM:$cp' skills/siae-brainstorming/SKILL.md"
done
for cp in RED GREEN REFACTOR COMMIT; do
    _assert "tdd has [TDD:$cp]" "grep -q 'TDD:$cp' skills/siae-tdd/SKILL.md"
done

echo ""
echo "=== K invariants — Specific rules ==="
_assert "tdd RED-GREEN-REFACTOR workflow" "grep -qE 'RED.?GREEN.?REFACTOR' skills/siae-tdd/SKILL.md"
_assert "tdd Red Flags section"           "grep -q '## Red Flags' skills/siae-tdd/SKILL.md"
_assert "verification 5 step present"     "grep -cE 'Step [0-9]+' skills/siae-verification/SKILL.md | awk '{exit (\$1>=5)?0:1}'"
_assert "verification Cosa NON Conta"     "grep -q 'Cosa NON Conta' skills/siae-verification/SKILL.md"
_assert "verification Context-First Rule" "grep -q 'Context-First Rule' skills/siae-verification/SKILL.md"
_assert "git-workflow Conventional Commits" "grep -q 'Conventional Commits' skills/siae-git-workflow/SKILL.md"
_assert "using-devforge Backbone Core"    "grep -q 'Backbone Core' skills/using-devforge/SKILL.md"
_assert "using-devforge La Regola 1%"     "grep -qE '1%.*probabilit' skills/using-devforge/SKILL.md"

echo ""
echo "=== Frontmatter invariants — name + description + validates_via ==="
for s in siae-tdd siae-brainstorming siae-git-workflow siae-verification siae-blind-review; do
    _assert "$s frontmatter has name+description" \
        "head -20 skills/$s/SKILL.md | grep -cE '^name:|^description:' | awk '{exit (\$1>=2)?0:1}'"
    _assert "$s frontmatter has validates_via" \
        "head -30 skills/$s/SKILL.md | grep -q 'validates_via:'"
done

echo ""
echo "=== Catalog integrity — skills-core.js genera catalog valido ==="
_assert "skills-core.js generates catalog without errors" \
    "node lib/skills-core.js \"\$(pwd)\" 2>&1 | grep -q 'siae-tdd'"

echo ""
echo "Total: $((PASS+FAIL)) — PASS: $PASS — FAIL: $FAIL"
exit $FAIL
