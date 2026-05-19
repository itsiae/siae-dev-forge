# Task 09 — SKILL.md compaction + extract refs

**Fix-group:** G5
**ADR riferito:** ADR-5 (230→~90 LOC)
**Stato:** [PENDING]
**Dipendenze:** Task 02, 03, 04, 05 (schema fields nuovi referenziati)

## File modificati

- `skills/code-coverage/SKILL.md` (compaction)
- `skills/code-coverage/lib/phase1-discover.sh` (NEW)
- `skills/code-coverage/lib/phase6-coverage.sh` (NEW)
- `skills/code-coverage/references/phase-2-strategy.md` (NEW)
- `skills/code-coverage/references/phase-7-repair.md` (NEW)
- `skills/code-coverage/references/index.md` (NEW)

## Implementazione

**STEP 0 — Locate boundaries:**
```bash
cd /Users/mazzacuv/Git/siae-dev-forge/skills/code-coverage
grep -n '^### Phase' SKILL.md  # localizza range exact delle Phase
wc -l SKILL.md                  # baseline LOC
```
Le linee `SKILL.md:81-97`, `148-171`, `206-230` indicate sotto sono baseline. Verifica empirica.

### `lib/phase1-discover.sh` (NEW)
Estrae il blocco inline `Phase 1 - Discovery` da SKILL.md (verifica linee via `grep -n` step 0; baseline ~L57-97 con parallel runner + cache check + fail-fast). Espone funzione `phase1_discover <repo_path>`.

### `lib/phase6-coverage.sh` (NEW)
Estrae il blocco inline `Phase 6 — Coverage` da SKILL.md:148-171. Sostituisce `jq` con `python3 -c` (G9), `eval` con `bash -c` shlex-quoted (G11). Espone funzione `phase6_coverage <repo_path>`.

### `references/phase-2-strategy.md` (NEW)
Estrae Phase-2 markdown (decision tree Vitest-first, stack matrix lookup).

### `references/phase-7-repair.md` (NEW)
Estrae Phase-7 algorithm (categorize_failure + progress guard + early-abort).

### `references/index.md` (NEW)
Sposta la tabella SUPPORTING FILES (SKILL.md:206-230).

### `SKILL.md` compaction
Target ≤100 LOC. Mantieni:
- Frontmatter (name/description) — 7 LOC
- Activation note — 1 LOC
- INPUT MODE — 12 LOC
- GLOBAL EXECUTION PRINCIPLES (compresso a 7 bullet 1-line each) — 8 LOC
- WORKFLOW table-of-contents:
  ```
  ### Phase 0 (init)
  `bash skills/code-coverage/lib/cache-helper.sh; init_workdir <repo>`

  ### Phase 1 — Discovery
  `bash skills/code-coverage/lib/phase1-discover.sh <repo>`
  Gates: orchestration_only → Block 4 + END; pre_existing≥70 → Block 8 + END.

  ### Phase 2 — Strategy
  See `references/phase-2-strategy.md`.

  ### Phase 3 — Sizing (REF if LARGE)
  ### Phase 4 — Environment (REF)
  ### Phase 5 — Generation (REF)
  ### Phase 5b — Coverage Probe (if existing tests)
  ### Phase 6 — Coverage
  `bash skills/code-coverage/lib/phase6-coverage.sh <repo>`
  ### Phase 7 — Repair
  See `references/phase-7-repair.md`.
  ```
- OUTPUT — Conditional Blocks (preservato)
- 1-line pointer a `references/index.md`

## Criterio di accettazione

- `wc -l SKILL.md` ≤ 100
- Zero comparse di `jq` in SKILL.md
- Tutti i bash inline → estratti in `lib/phase{1,6}-*.sh`
- `bash lib/phase1-discover.sh /tmp/test-repo` esegue lo stesso flow di prima
