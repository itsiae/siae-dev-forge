# Task 04 — Dedup hallucination guard → references/hallucination_guard.md

**Stato**: [COMPLETED] · **Effort**: 20min · **File toccati**: 2

## Goal

Eliminare la duplicazione del contenuto "Hallucination Guard" e
"Grounding policy" presente in `SKILL.md` (sezioni 309-322 + 390-422
post-T1/T2), estraendo entrambe in `references/hallucination_guard.md` e
lasciando in `SKILL.md` un pointer compatto.

## Acceptance

- `references/hallucination_guard.md` esiste, contiene HG-01..05 + invocation
  + grounding policy.
- `SKILL.md` ha solo sezione `## Hallucination guard` di 4-5 righe con
  pointer al reference.
- Saving eager: ~520 token (target).

## Implementation

1. Write nuovo file `references/hallucination_guard.md`.
2. Edit `SKILL.md` rimuovendo sezioni duplicate, sostituendole con pointer
   compatto.
