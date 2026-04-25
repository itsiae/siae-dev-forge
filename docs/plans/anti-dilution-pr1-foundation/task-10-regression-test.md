# Task 10 — Creare tests/compression-regression/ + improvement tests

**Stato:** [PENDING]
**Execution:** in-session (TDD stretto)
**Dipendenze:** nessuna (il test è scritto PRIMA delle compression)
**Durata stimata:** 20 min

## Goal — duplice

1. **Non-regression**: garantire che post-compression le skill compresse conservino ogni regola comportamentale (Legge di Ferro, checkpoint, hard-gate, regole di ferro specifiche).
2. **Improvement tests**: dimostrare che l'obiettivo di compressione (–62%, ≤1000 righe) **E** l'obiettivo di anti-dilution (budget injection, hook fusion) sono stati **effettivamente raggiunti**. Non solo accettati — verificati.

## Architettura del testing

```
tests/compression-regression/
├── assert_behavioral_invariants.sh     # (a) non-regression — DEVE passare post-compression
├── assert_compression_targets.sh       # (b) improvement: wc -l target verificati
├── assert_injection_reduction.sh       # (b) improvement: hook devforge-context emette <30KB
├── assert_baseline_preserved.sh        # (b) improvement: 168 PASS / 6 FAIL preserved o migliorato
└── README.md                           # come lanciare la suite
```

## Test 1 — Behavioral invariants (non-regression)

File: `tests/compression-regression/assert_behavioral_invariants.sh`

```bash
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
```

## Test 2 — Compression target improvements

File: `tests/compression-regression/assert_compression_targets.sh`

```bash
#!/usr/bin/env bash
# Improvement: verifica che i target di compressione siano raggiunti.
set -eu
PASS=0; FAIL=0
cd "$(git rev-parse --show-toplevel)"

_assert_le() {
    local name="$1"; local actual="$2"; local limit="$3"
    if [ "$actual" -le "$limit" ]; then
        echo "  PASS  $name (actual=$actual <= $limit)"; PASS=$((PASS+1))
    else
        echo "  FAIL  $name (actual=$actual > $limit)"; FAIL=$((FAIL+1))
    fi
}

echo "=== Per-skill compression targets ==="
_assert_le "using-devforge <= 90"     "$(wc -l < skills/using-devforge/SKILL.md)" 90
_assert_le "siae-brainstorming <= 220" "$(wc -l < skills/siae-brainstorming/SKILL.md)" 220
_assert_le "siae-tdd <= 180"          "$(wc -l < skills/siae-tdd/SKILL.md)" 180
_assert_le "siae-git-workflow <= 220" "$(wc -l < skills/siae-git-workflow/SKILL.md)" 220
_assert_le "siae-verification <= 180" "$(wc -l < skills/siae-verification/SKILL.md)" 180
_assert_le "siae-blind-review <= 110" "$(wc -l < skills/siae-blind-review/SKILL.md)" 110

echo ""
TOTAL=$(wc -l < skills/using-devforge/SKILL.md)
for s in siae-brainstorming siae-tdd siae-git-workflow siae-verification siae-blind-review; do
    TOTAL=$((TOTAL + $(wc -l < skills/$s/SKILL.md)))
done
_assert_le "TOTAL backbone <= 1000" "$TOTAL" 1000

echo ""
echo "=== Improvement vs baseline (2636 lines) ==="
BASELINE=2636
REDUCTION=$(( (BASELINE - TOTAL) * 100 / BASELINE ))
if [ "$REDUCTION" -ge 50 ]; then
    echo "  PASS  Reduction >= 50% (actual=$REDUCTION%, target=62%)"; PASS=$((PASS+1))
else
    echo "  FAIL  Reduction < 50% (actual=$REDUCTION%)"; FAIL=$((FAIL+1))
fi

echo ""
echo "=== Centralizations present ==="
for f in risk-taxonomy.md operational-limits.md permission-denied-handling.md checkpoint-schema.md; do
    if [ -f "lib/$f" ]; then echo "  PASS  lib/$f exists"; PASS=$((PASS+1))
    else echo "  FAIL  lib/$f missing"; FAIL=$((FAIL+1)); fi
done

echo ""
echo "Total: $((PASS+FAIL)) — PASS: $PASS — FAIL: $FAIL"
exit $FAIL
```

## Test 3 — Injection reduction

File: `tests/compression-regression/assert_injection_reduction.sh`

```bash
#!/usr/bin/env bash
# Improvement: verifica che devforge-context rispetti il budget di iniezione.
set -eu
PASS=0; FAIL=0
cd "$(git rev-parse --show-toplevel)"

# Requires: devforge-context hook exists (T11)
if [ ! -f hooks/devforge-context ]; then
    echo "SKIP — hooks/devforge-context not yet created (T11 pending)"
    exit 0
fi

_assert() {
    local name="$1"; shift
    if "$@" >/dev/null 2>&1; then echo "  PASS  $name"; PASS=$((PASS+1))
    else echo "  FAIL  $name"; FAIL=$((FAIL+1)); fi
}

echo "=== Budget: first injection <= 2048 bytes ==="
# Fresh state: no .devforge-last-injection-hash → first-time injection
TMPHOME=$(mktemp -d)
OUTPUT=$(HOME=$TMPHOME echo '{}' | bash hooks/devforge-context 2>/dev/null || true)
SIZE=$(printf '%s' "$OUTPUT" | wc -c | tr -d ' ')
if [ "$SIZE" -le 2048 ]; then
    echo "  PASS  first injection <= 2KB (actual=$SIZE)"; PASS=$((PASS+1))
else
    echo "  FAIL  first injection > 2KB (actual=$SIZE)"; FAIL=$((FAIL+1))
fi

echo ""
echo "=== Diff-based: second invocation with same state returns {} ==="
# Run twice with same env → second must be empty (no diff)
SECOND=$(HOME=$TMPHOME echo '{}' | bash hooks/devforge-context 2>/dev/null || true)
SECOND_SIZE=$(printf '%s' "$SECOND" | wc -c | tr -d ' ')
if [ "$SECOND_SIZE" -le 20 ]; then  # empty JSON or zero
    echo "  PASS  second injection zero/minimal (actual=$SECOND_SIZE)"; PASS=$((PASS+1))
else
    echo "  FAIL  second injection not deduped (actual=$SECOND_SIZE)"; FAIL=$((FAIL+1))
fi

echo ""
echo "=== Tier policy: default output NO EXTREMELY_IMPORTANT ==="
if echo "$OUTPUT" | grep -q "EXTREMELY_IMPORTANT"; then
    echo "  FAIL  default output contains EXTREMELY_IMPORTANT (should be tier-guarded)"; FAIL=$((FAIL+1))
else
    echo "  PASS  default output has no EXTREMELY_IMPORTANT"; PASS=$((PASS+1))
fi

rm -rf "$TMPHOME"
echo ""
echo "Total: $((PASS+FAIL)) — PASS: $PASS — FAIL: $FAIL"
exit $FAIL
```

## Test 4 — Baseline test suite preservation

File: `tests/compression-regression/assert_baseline_preserved.sh`

```bash
#!/usr/bin/env bash
# Improvement: la test suite esistente non regredisce.
# Baseline pre-PR-1: 168 PASS / 6 FAIL / 1 SKIP.
set -eu
cd "$(git rev-parse --show-toplevel)"

echo "=== Run full baseline suite ==="
OUTPUT_FILE=$(mktemp)
bash tests/run-all.sh > "$OUTPUT_FILE" 2>&1 || true

PASS_COUNT=$(grep -oE '✅ PASS: `[0-9]+`' "$OUTPUT_FILE" | grep -oE '[0-9]+' | head -1 || echo 0)
FAIL_COUNT=$(grep -oE '❌ FAIL: `[0-9]+`' "$OUTPUT_FILE" | grep -oE '[0-9]+' | head -1 || echo 0)

echo "Current run: PASS=$PASS_COUNT  FAIL=$FAIL_COUNT"

BASELINE_PASS=168
BASELINE_FAIL=6

if [ "$PASS_COUNT" -ge "$BASELINE_PASS" ]; then
    echo "  PASS  PASS count preserved ($PASS_COUNT >= $BASELINE_PASS)"
    P=0
else
    echo "  FAIL  PASS regression ($PASS_COUNT < $BASELINE_PASS)"
    P=1
fi

if [ "$FAIL_COUNT" -le "$BASELINE_FAIL" ]; then
    echo "  PASS  FAIL count no worse ($FAIL_COUNT <= $BASELINE_FAIL)"
    F=0
else
    echo "  FAIL  FAIL regression ($FAIL_COUNT > $BASELINE_FAIL)"
    F=1
fi

# Bonus: log delta vs baseline
echo ""
echo "Delta: ΔPASS=+$((PASS_COUNT - BASELINE_PASS))  ΔFAIL=$((FAIL_COUNT - BASELINE_FAIL))"

rm -f "$OUTPUT_FILE"
exit $((P + F))
```

## Step TDD

### Step 1 — Crea i 4 script + README + test runner

```bash
mkdir -p tests/compression-regression
# Scrivi i 4 file sopra
# README.md
cat > tests/compression-regression/README.md <<'EOF'
# Compression Regression Suite

Verifica che la compressione SKILL.md (PR #1 anti-dilution) non introduca regressioni E raggiunga i target di miglioramento.

## Run full suite

```bash
bash tests/compression-regression/run-all.sh
```

## Singoli test

- `assert_behavioral_invariants.sh` — K sections preserved
- `assert_compression_targets.sh` — wc -l targets achieved
- `assert_injection_reduction.sh` — devforge-context budget respected
- `assert_baseline_preserved.sh` — 168 PASS / 6 FAIL baseline preserved

Ogni script exit 0 = PASS, exit >0 = FAIL con dettaglio.
EOF

# run-all.sh
cat > tests/compression-regression/run-all.sh <<'EOF'
#!/usr/bin/env bash
set +e
cd "$(dirname "$0")"
TOTAL_FAIL=0
for script in assert_behavioral_invariants.sh assert_compression_targets.sh assert_injection_reduction.sh assert_baseline_preserved.sh; do
    echo "━━━ $script ━━━"
    bash "$script"
    RC=$?
    TOTAL_FAIL=$((TOTAL_FAIL + RC))
    echo ""
done
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Suite result: $([ $TOTAL_FAIL -eq 0 ] && echo PASS || echo FAIL)"
exit $TOTAL_FAIL
EOF
chmod +x tests/compression-regression/*.sh
```

### Step 2 — Verifica RED (scritto PRIMA delle compression)

```bash
bash tests/compression-regression/run-all.sh
echo "EXIT=$?"
```
Output atteso pre-compression: molti FAIL su `assert_compression_targets.sh` (wc -l ancora 2636), `assert_injection_reduction.sh` SKIP (T11 pending), `assert_baseline_preserved.sh` PASS (non ancora toccato nulla), `assert_behavioral_invariants.sh` PASS (pre-compression le sezioni ci sono tutte).

Questo è il RED atteso: il **gap tra stato attuale e target** è il delta che le compression devono chiudere.

### Step 3 — GREEN dopo compression

Dopo T03-T08 completi:

```bash
bash tests/compression-regression/run-all.sh
```
Output atteso: tutti PASS.

### Step 4 — Commit

```bash
git add tests/compression-regression/
git commit -m "test(compression): add regression + improvement suite

Part of PR #1 anti-dilution (ADR-003).
4 scripts + README + runner:
- behavioral_invariants: K sections preserved
- compression_targets: wc -l targets achieved (<=1000 total)
- injection_reduction: devforge-context budget <=2KB + diff-based dedup
- baseline_preserved: 168 PASS / 6 FAIL base no regression

Run: bash tests/compression-regression/run-all.sh"
```

## Acceptance

- [ ] 4 script + README + runner creati
- [ ] Pre-compression: `assert_compression_targets.sh` FAIL atteso (RED corretto)
- [ ] Post-compression: tutti 4 script PASS
- [ ] Commit `test(compression):`

## Nota sul principio di improvement

Questi test non dimostrano solo "non ho rotto nulla" — dimostrano **che il design ha ottenuto il risultato promesso**:
- ≥50% riduzione righe (target 62%)
- Injection ≤2KB prima invocazione
- Dedup attivo per invocazioni successive
- Tag EXTREMELY_IMPORTANT non emesso in default state
- Baseline test suite preservata o migliorata

Un design accettato che non passa questi test = design non implementato.
