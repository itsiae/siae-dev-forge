# Task 41 — siae-finishing-branch + open PR

**Stato:** [PENDING]
**SP:** 1 Human / 0.5 Augmented
**Dipendenze:** task-40 (full test suite green)

## Goal

Eseguire `siae-finishing-branch` per pre-flight pre-PR, blind-review gate, e poi aprire la PR `feat/siae-release-risk → main`.

## File coinvolti

- N/A (orchestration via siae-finishing-branch skill)

## Step

### Step 1 — Verifica stato branch

```bash
git status                                            # clean (committed)
git log origin/main..HEAD --oneline | wc -l           # 40+ commit (1 per task)
git branch --show-current                              # feat/siae-release-risk o feat/mutation-testing-runners
```

### Step 2 — REQUIRED SUB-SKILL siae-finishing-branch

Invoke siae-finishing-branch via Skill tool. Sequenza 6-step:
- Step 0b: parent_branch detection (main)
- Step 1: status clean
- Step 2: pre-flight test card (re-run pytest)
- Step 3: revisione diff (no debug logs, no API key, no .env)
- Step 4: commit history (conventional commits)
- Step 4b: plan completion gate — verifica `docs/plans/2026-05-14-siae-release-risk/overview.md` task TUTTI [DONE]
- Step 4c: REQUIRED SUB-SKILL siae-blind-review — review cieca contro design doc
- Step 5: gh pr create con pre-flight card 🔴 ALTO + attesa conferma

### Step 3 — Open PR

Dopo conferma utente:
```bash
git push origin HEAD
gh pr create --base main --title "feat(release-risk): siae-release-risk skill + hook + 18 criteri + integrazioni" --body-file - <<'EOF'
## Cosa fa questa PR

Aggiunge skill DevForge `siae-release-risk` per pre-deploy risk assessment release branch.

**Highlights:**
- 18 criteri (15 originali + 3 nuovi Lore: regression delta, security state HEAD-only, genesis check)
- Score 0-36, level LOW/MEDIUM/HIGH/CRITICAL, decision GO/POSTPONE/NO_GO
- Hook `pr-release-gate` PostToolUse Bash advisory-only su `gh pr create --base main` con head `release/**`
- Cache 3-key `(branch, diff-hash, baseline-main-sha)` + idempotency
- Output versionato `docs/releases/<date>-<service>-<branch>.md` + PR comment auto
- MCP sport-kg lookup per Criterion 5 (critical service)
- Reuse `lib/review_evidence/baseline_cache.py` (Criterion 16) + runners (Criterion 17)
- Activity ledger event via `devforge_log`

**Plugin manifest:** bump 1.56.0 → 1.57.0 + count audit (42 skill / 17 cmd / 5 agent / 24 hook).

## Come testare

1. `git checkout feat/siae-release-risk`
2. `pytest tests/test_release_risk_*.py -v` → tutti PASS
3. `python3 -m lib.evals.runner evals/release-risk/disambiguation.yaml` → 10/10 PASS
4. Smoke test su release branch:
   ```bash
   git checkout release/X  # qualsiasi release branch esistente
   /forge-release-risk     # esegui skill manualmente
   cat docs/releases/<date>-<service>-<branch>.md  # verifica scorecard
   ```
5. Verifica hook auto: simula `gh pr create --base main` su release/** (in repo test isolato)

## Design & Plan

- Design doc: `docs/plans/2026-05-14-siae-release-risk-design.md` (13 ADR, spec-review iter 3 PASS)
- Plan: `docs/plans/2026-05-14-siae-release-risk/` (42 task bite-sized)

## Acceptance criteria

- [x] Test coverage ≥85% su `lib/release_risk/`
- [x] Mutation score ≥60%
- [x] Eval disambiguation 10/10 PASS
- [x] Lint 0 errors (ruff + shellcheck)
- [x] review-evidence v2 PASS (non BLOCK)
- [x] No regressioni su skill esistenti (siae-finishing-branch, siae-branching-strategy-check, forge-evidence)
- [x] Plugin manifest count audit (42/17/5/24)

## Out of scope (backlog futuro)

Vedi design doc sez. 12. Top items:
- Criterion 17 delta vs baseline (v2.x — richiede extension schema EvidenceV2)
- Maven security runner
- Dashboard release-risk in siae-dev-analytics

Co-Authored-By: SIAE DevForge
EOF
```

### Step 4 — REQUIRED SUB-SKILL siae-requesting-review

Dopo PR aperta, invoke siae-requesting-review per:
- Aggiunta description completa (se non già nel body)
- Assegna reviewer (mario-siae o equivalente)
- Trigger review formale

### Step 5 — Aggiorna overview.md

Edit `docs/plans/2026-05-14-siae-release-risk/overview.md`:
- Marca tutti i task come `[DONE]`
- Aggiungi `Status piano: COMPLETED — PR #N aperta YYYY-MM-DD`

### Step 6 — Final commit

```bash
git add docs/plans/2026-05-14-siae-release-risk/overview.md
git commit -m "docs(release-risk): mark plan COMPLETED post PR open"
git push origin HEAD
```

## Criteri di accettazione

- [ ] siae-finishing-branch completato (6 step + 2 gate PASS)
- [ ] siae-blind-review gate PASS
- [ ] PR aperta verso main con body completo
- [ ] siae-requesting-review eseguita (reviewer assegnato)
- [ ] overview.md aggiornato (tutti task [DONE])
- [ ] Final commit pushed
