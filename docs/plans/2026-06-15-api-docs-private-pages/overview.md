---
title: Piano — API docs browsable su GitHub Pages privato (Redoc)
design: ../2026-06-15-api-docs-private-pages-design.md
REQUIRED SUB-SKILL: siae-executing-plans
status: PENDING
created: 2026-06-15
---

# Piano — API contract come GitHub Pages PRIVATO (Redoc)

## Contesto
Pubblica l'OpenAPI insights (`docs/plans/2026-06-14-devforge-telemetry-insights-api.openapi.yaml`)
come documentazione navigabile Redoc su **GitHub Pages con visibility private** (org itsiae = Enterprise →
members-only, niente esposizione pubblica). Complessità bassa. Branch nuovo da `origin/main` (9b245df).

## Task
- [x] task-01 — docs/api/index.html (Redoc) + copia spec same-origin + test (same-origin + no-drift) [DONE — 15/15 assert]
- [x] task-02 — .github/workflows/pages.yml (upload+deploy Pages) + validazione YAML [DONE]
- [x] task-03 — abilitazione Pages via gh api (build_type=workflow) + visibility private + verifica members-only [DONE — public=false confermato, sito https://redesigned-bassoon-7pmn8pw.pages.github.io/ members-only, no fallback necessario]
- [x] task-04 — link README alla URL Pages + no-regression suite esistente [DONE — version-match preservato]

## Dipendenze
- task-01 → task-02 (il workflow pubblica docs/api/ prodotta da task-01).
- task-02 → task-03 (Pages build_type=workflow presuppone il workflow).
- task-04 dopo task-03 (la URL Pages è nota dopo l'abilitazione).

## Criteri di accettazione
I 7 AC del design (sez. Criteri di accettazione). task-04 verifica no-regression.

## Note esecuzione
Branch da `origin/main` aggiornato. L'abilitazione Pages (task-03) richiede admin repo → tentata via gh api;
se la policy org nega private Pages → STOP e fallback markdown nativo (AC-7 design), NON pubblicare pubblico.
