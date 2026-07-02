#!/usr/bin/env bash
# test_reconcile_zero_eccezioni.sh — guard: "zero eccezioni" riconciliato con
# lo scaling trivial (Lite-present, REQ-DF-04, design 2026-07-01).
# La PROFONDITA' scala sempre; il gate non forza il processo sui trivial;
# l'enforcement resta assoluto sui complessi/IaC/multi-repo.
set -eu
PASS=0; FAIL=0
cd "$(git rev-parse --show-toplevel)"

_assert() {
    local name="$1"; local cmd="$2"
    if eval "$cmd" >/dev/null 2>&1; then echo "  PASS  $name"; PASS=$((PASS+1))
    else echo "  FAIL  $name (cmd: $cmd)"; FAIL=$((FAIL+1)); fi
}

echo "=== skills/siae-brainstorming/SKILL.md — carve-out trivial presente ==="
_assert "menziona 'trivial' nella sezione Scaling" \
    "grep -qi 'trivial' skills/siae-brainstorming/SKILL.md"
_assert "NON asserisce più 'si eseguono SEMPRE' senza carve-out" \
    "! grep -q 'I 7 step si eseguono SEMPRE' skills/siae-brainstorming/SKILL.md"
_assert "la profondità scala esplicitamente" \
    "grep -qi 'la.*PROFONDIT.*scala' skills/siae-brainstorming/SKILL.md"
_assert "HARD-GATE ancora presente (invariante non rimossa)" \
    "grep -q '## HARD-GATE' skills/siae-brainstorming/SKILL.md"

echo ""
echo "=== lib/skills-core.js — riga disambiguation qualificata ==="
_assert "NON asserisce più 'zero eccezioni'" \
    "! grep -q 'zero eccezioni' lib/skills-core.js"
_assert "menziona 'trivial' o soglia nella riga disambiguation" \
    "grep 'siae-brainstorming\` ' lib/skills-core.js | grep -qi 'trivial\|soglia\|complessi'"

echo ""
echo "=== tests/skill-activation/cases.yml — commento allineato ==="
_assert "commento feature-config-change non cita più 'zero eccezioni'" \
    "! grep -A2 'id: feature-config-change' tests/skill-activation/cases.yml | grep -q 'zero eccezioni'"

echo ""
echo "=== hooks/ENV_VARS.md — sezione brainstorming complexity documentata ==="
_assert "DEVFORGE_BRAINSTORM_COMPLEXITY documentato" \
    "grep -q 'DEVFORGE_BRAINSTORM_COMPLEXITY' hooks/ENV_VARS.md"
_assert "DEVFORGE_BRAINSTORM_TRIVIAL_MAX_LINES documentato" \
    "grep -q 'DEVFORGE_BRAINSTORM_TRIVIAL_MAX_LINES' hooks/ENV_VARS.md"

echo ""
echo "Total: $((PASS+FAIL)) — PASS: $PASS — FAIL: $FAIL"
exit $FAIL
