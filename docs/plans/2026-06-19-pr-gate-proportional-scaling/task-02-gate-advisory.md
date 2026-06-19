# Task 02 — Downgrade advisory nei gate PR

**Goal:** `pr-premortem-gate` e `pr-blind-review-gate`: se la skill NON è validata MA il
diff è `risk=low`, emettere advisory (no `decision:block`) + log `pr_gate_scaled`. Su
`risk=code` il block resta invariato.

**File:** modifica `hooks/pr-premortem-gate` + `hooks/pr-blind-review-gate`; crea
`tests/hooks/test_pr_gate_scaling.sh`. **Copre AC:** AC-7, AC-8, AC-9, AC-10. **Dipende da:** Task 01.

---

## Step 1 — Test fallente

Crea `tests/hooks/test_pr_gate_scaling.sh`:

```bash
#!/usr/bin/env bash
# test_pr_gate_scaling.sh — i gate PR scalano ad advisory su diff risk=low.
set -eu
PASS=0; FAIL=0
REPO_ROOT="$(git rev-parse --show-toplevel)"

# Invoca un gate con un comando 'gh pr create' e un classifier finto che stampa $RISK.
# Stub: PATH-prepend di una dir con uno script 'devforge_classify_diff_risk'? No — il
# classifier è una funzione sourced. Usiamo un repo reale + branch per pilotare il diff.
_mkrepo() {
    local td; td=$(mktemp -d)
    ( cd "$td" && git init -q && git config user.email t@t && git config user.name t \
      && echo s > s.txt && git add -A && git commit -qm s && git branch -m main \
      && git remote add origin https://github.com/itsiae/fake.git \
      && git checkout -qb work ) >/dev/null 2>&1
    echo "$td"
}
# $1=hook-name $2=repodir → stdout del gate
# NB: il gate classifica vs 'origin/main'. Il repo temp non fa fetch, quindi creiamo
# il ref remote-tracking origin/main puntando a main (BLOCK-1 plan-review): senza, il
# classifier fallirebbe git diff → code → AC-7/9 mai GREEN.
_run_gate() {
    git -C "$2" update-ref refs/remotes/origin/main "$(git -C "$2" rev-parse main)" >/dev/null 2>&1
    printf '{"tool_input":{"command":"gh pr create --base main"}}' \
      | ( cd "$2" && HOME="$2/home" DEVFORGE_USE_SESSION_SCOPE=1 \
          bash "${REPO_ROOT}/hooks/$1" 2>/dev/null )
}

for GATE in pr-premortem-gate pr-blind-review-gate; do
  echo "=== $GATE AC-7/9: diff doc-only + skill NON validata → advisory (no block) ==="
  TD=$(_mkrepo); mkdir -p "$TD/home/.claude"; : > "$TD/home/.claude/.devforge-session-skills"
  ( cd "$TD" && echo x > a.md && git add -A && git commit -qm m ) >/dev/null 2>&1
  OUT=$(_run_gate "$GATE" "$TD")
  if ! echo "$OUT" | grep -q '"decision": "block"'; then echo "  PASS"; PASS=$((PASS+1)); else echo "  FAIL: $OUT"; FAIL=$((FAIL+1)); fi
  rm -rf "$TD"

  echo "=== $GATE AC-8/9: diff con hooks/ + skill NON validata → block (no-regression) ==="
  TD=$(_mkrepo); mkdir -p "$TD/home/.claude"; : > "$TD/home/.claude/.devforge-session-skills"
  ( cd "$TD" && mkdir -p hooks && echo y > hooks/foo && git add -A && git commit -qm m ) >/dev/null 2>&1
  OUT=$(_run_gate "$GATE" "$TD")
  if echo "$OUT" | grep -q '"decision": "block"'; then echo "  PASS"; PASS=$((PASS+1)); else echo "  FAIL: $OUT"; FAIL=$((FAIL+1)); fi
  rm -rf "$TD"
done

echo "=== AC-10: floor security — pre-commit NON modificato da questo task ==="
if git -C "$REPO_ROOT" diff origin/main...HEAD --name-only 2>/dev/null | grep -qx 'hooks/pre-commit'; then
  echo "  FAIL: pre-commit modificato"; FAIL=$((FAIL+1))
else
  echo "  PASS: pre-commit intatto"; PASS=$((PASS+1))
fi

echo ""; echo "RESULT: PASS=$PASS FAIL=$FAIL"; [ "$FAIL" -eq 0 ]
```

## Step 2 — Esegui (RED)
Run: `bash tests/hooks/test_pr_gate_scaling.sh`
Atteso: i casi AC-7/AC-9 FAIL (oggi i gate bloccano sempre se skill non validata, ignorano il diff).

## Step 3 — Implementa (entrambi i gate, modifica IDENTICA per struttura)

In `hooks/pr-premortem-gate`, tra il check `VALIDATED=1 → echo '{}'; exit 0` (riga 103-106)
e il blocco (riga 108 `# Block`), inserisci:

```bash
# Proportional scaling: su diff risk=low (doc/manifest) il gate è advisory, non block.
# Floor security/secret invariato (pre-commit non toccato). Design ADR-3.
RISK=code
if source "${PLUGIN_ROOT}/lib/diff-risk-classifier.sh" 2>/dev/null \
   && command -v devforge_classify_diff_risk >/dev/null 2>&1; then
    RISK=$(devforge_classify_diff_risk "origin/main" 2>/dev/null || echo code)
fi
if [ "$RISK" = "low" ]; then
    devforge_log "pr_gate_scaled" "info" "{\"gate\":\"pr-premortem-gate\",\"risk\":\"low\"}" 2>/dev/null || true
    cat <<EOF
{
  "additional_context": "<IMPORTANT>\\nDevForge Premortem Gate scalato ad ADVISORY: diff a basso rischio (doc-only/manifest plugin). siae-premortem consigliato ma NON obbligatorio per questo diff. Floor security invariato.\\n</IMPORTANT>"
}
EOF
    exit 0
fi
```

In `hooks/pr-blind-review-gate` inserisci il blocco equivalente nello stesso punto
(dopo il `VALIDATED=1 → exit 0`, prima del `# Block`), sostituendo le stringhe
`pr-premortem-gate`→`pr-blind-review-gate` e `siae-premortem`→`siae-blind-review` e il
testo "Premortem Gate"→"Blind Review Gate".

> Nota: `PLUGIN_ROOT` è già definito in entrambi i gate (header setup). Verificalo con
> `grep -n 'PLUGIN_ROOT=' hooks/pr-premortem-gate`.

## Step 4 — Esegui (GREEN)
Run: `bash tests/hooks/test_pr_gate_scaling.sh` → `RESULT: PASS=5 FAIL=0`.
Run no-regression: `bash -n hooks/pr-premortem-gate && bash -n hooks/pr-blind-review-gate` → OK.

## Step 5 — Commit
```bash
git add hooks/pr-premortem-gate hooks/pr-blind-review-gate tests/hooks/test_pr_gate_scaling.sh
git commit -m "feat(hooks): gate PR advisory su diff risk=low (task-02)"
```

## Criteri di accettazione
- [ ] Diff doc-only + skill non validata → entrambi i gate emettono advisory, NO block (AC-7/9).
- [ ] Diff con `hooks/` → block invariato (AC-8/9 no-regression).
- [ ] Evento `pr_gate_scaled` loggato sul downgrade.
- [ ] `pre-commit` non modificato (AC-10 floor).
- [ ] `test_pr_gate_scaling.sh` → PASS=5 FAIL=0; `bash -n` OK su entrambi i gate.
