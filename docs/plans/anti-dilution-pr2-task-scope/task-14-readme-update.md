---
task: 14
title: README update — anti-dilution PR #1 + PR #2
size: S
depends: [13]
---

# Task 14 — README update

Aggiornare `README.md` root repo con sezione "Anti-Dilution Enforcement"
che documenta PR #1 (v1.46) e PR #2 (v1.47). Motivo esplicito nel prompt
utente: "aggiorna il readme con quello che abbiamo fatto PR1 e PR 2".

## Sezione da aggiungere/modificare

### Nuova sezione: `## Anti-Dilution Enforcement (v1.46 + v1.47)`

Contenuto:

```markdown
## Anti-Dilution Enforcement (v1.46 + v1.47)

DevForge utilizza skill + hook per rinforzare il SDLC SIAE.
Telemetria su 230 sessioni (aprile 2026) ha rivelato adoption reale
38% brainstorming, 38% TDD, 3% verification, 0% blind-review.
L'initiative anti-dilution porta l'adoption verso ≥80% per-task.

### PR #1 — v1.46.0 Foundation + Compression (2026-04-25)

- **Evidence contract** (ADR-002): ogni skill backbone dichiara
  `validates_via` nel frontmatter. 5 predicati attivi (tdd_red_green_observed,
  design_doc_produced, conventional_commit_made, verification_run_passed,
  blind_review_completed).
- **Radical SKILL.md compression** (ADR-003): backbone 2636 → 980 righe
  (-62%). Regole comportamentali preservate verbatim (Legge di Ferro,
  Hard-Gate, Checkpoint schema, Pre-Flight Card, RED-GREEN-REFACTOR).
  Centralizzazioni in `lib/{risk-taxonomy,operational-limits,permission-denied-handling,checkpoint-schema}.md`.
- **Prompt injection budget** (ADR-004): `hooks/devforge-context` fonde
  3 hook UserPromptSubmit. Budget hard-cap 2KB, diff-based dedup via
  state hash, tier-based tags (default none / IMPORTANT se gate violato /
  EXTREMELY_IMPORTANT solo hard-gate attivo).

Risultati misurati:

| Metrica | Before | After | Delta |
|---|---|---|---|
| SKILL.md backbone | 2636 righe | 980 righe | -62% |
| Context injection/turn | 2123 B | 663 B | -69% |
| Session 50-turn est. | ~150KB | ~663 B | -99.6% |
| Hook UserPromptSubmit | 4 | 2 | -50% |
| `<EXTREMELY_IMPORTANT>`/sessione | ~5 | 0 (tier-guarded) | -100% |

### PR #2 — v1.47.0 Task-Scope + Scope Cleanup (2026-04-25)

- **Task-scoped enforcement** (ADR-001): `skill_key = (task_id, skill_name)`
  invece di `(session_id, skill_name)`. Una sessione può coprire N task,
  ogni task richiede le skill valide per sé. State in
  `~/.claude/.devforge-task-skills/<task_id>/`.
  Evidence copy-forward su design doc revision (stesso branch, mtime change).
- **File taxonomy** (ADR-005): `lib/file-taxonomy.sh` centralizza
  classificazione estensioni. `.tf/.hcl` ora triggerano brainstorming-gate.
  `.sh/.bash` deny-by-default (opt-in `DEVFORGE_BASH_TDD=1`).
- **Rimozione 3 escape hatches** (ADR-006):
  - `stop-gate` 2-block auto-escape → `DEVFORGE_FORCE_STOP=1` esplicito +
    abuse tracking 3/day
  - `brainstorming-gate` `W2_DEFAULT=0` → gate sempre attivo
  - `pre-commit` regex substring `git commit` → parser primo-token
    (elimina falsi positivi su `git log | grep commit`, `echo "git commit"`)
- **Prereq map autogen** (ADR-007): `sub-skill-gate` legge
  `lib/prereq-map.generated` (39 entry da frontmatter skill) invece di
  hardcoded 7 entry.
- **Nuovi gate** (ADR-008):
  - `pr-blind-review-gate` — block `gh pr create/edit` se siae-blind-review
    non validata
  - `plan-gate-write` — block Write `docs/plans/*-design.md` senza brainstorming
  - `evidence-stop-gate` — rewrite basato su evidence event invece di
    session-skills grep
  - `coverage-force-run` — block commit se staged test + coverage stale

### Rollback

Ogni cambiamento task-scoped ha fallback session-scoped via
`DEVFORGE_USE_SESSION_SCOPE=1`. Vedi `hooks/ENV_VARS.md` per matrix completa.

### Metriche target (post-merge window)

| Dimensione | Baseline | Target 2 settimane |
|---|---|---|
| Adoption per-task brainstorming | 38% | ≥80% |
| Adoption per-task TDD | 38% | ≥80% |
| Adoption per-task verification | 3% | ≥60% |
| Adoption per-task blind-review | 0% | ≥40% |
| gate_divergence (dual-write) | N/A | <10% |

Baseline snapshot: `docs/measurements/baseline-2026-04-25/`
Design doc: `docs/plans/2026-04-25-anti-dilution-enforcement-design.md`
```

### Sezione "Env vars" (se esiste) — link a hooks/ENV_VARS.md

Aggiungere link o sezione:

```markdown
## Environment variables

Vedi [`hooks/ENV_VARS.md`](hooks/ENV_VARS.md) per la matrix completa dei
bypass/rollback env var.
```

## Acceptance

- [ ] Sezione Anti-Dilution in README
- [ ] Link a design doc + ENV_VARS.md
- [ ] Tabelle metriche (before/after PR #1 + target PR #2)
- [ ] Link a `hooks/ENV_VARS.md` (creato in task 12)

## Out of scope

- README drill-down per ogni skill modificata (già documentato in SKILL.md)
