# Task 10 — Add BP-026 + BP-027 in stacks/data-platform.md

**Stato**: [PENDING] · **Effort**: 2h · **File toccati**: 1

## Goal

Chiudere il gap A4 #2 (PySpark recall 50%): aggiungere 2 pattern Data
Engineering correctness che un QA umano troverebbe.

## Acceptance

- `references/stacks/data-platform.md` contiene:
  - **BP-026 nullable-join-key-loss**: pattern per `join` con chiave
    nullable che causa duplicati o record persi silenziosi.
    Trigger: `\.join\(.*on\s*=` con colonna nullable; absence di
    `coalesce()` o filter `isNotNull` upstream.
  - **BP-027 window-missing-partition-by**: pattern per
    `Window.orderBy(...)` senza `partitionBy` esplicito → calcolo
    globale errato.
    Trigger: `Window\.orderBy` non preceduto da `\.partitionBy`.
- Ogni BP ha format canonico (vedi task-09).
- Allineamento stilistico.

## Implementation

1. Read `references/stacks/data-platform.md` per stile inline.
2. Edit appendendo le 2 nuove BP.
