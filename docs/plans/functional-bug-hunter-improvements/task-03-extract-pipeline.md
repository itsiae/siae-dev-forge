# Task 03 — Extract Phase narrative → references/pipeline_internals.md

**Stato**: [COMPLETED] · **Effort**: 1h · **File toccati**: 2

## Goal

Estrarre la narrativa prose-heavy di Phase 0..8 (incluse sub-Phase 2.5
e 7.5) da `SKILL.md` (~1800 token eager) in un reference on-demand, e
sostituirla in `SKILL.md` con una tabella riassuntiva 11-righe.

## Acceptance

- `references/pipeline_internals.md` esiste e contiene la narrativa
  completa di Phase 0..8 + 2.5 + 7.5.
- `SKILL.md` `## Pipeline overview` contiene solo: 1 paragrafo intro + 1
  tabella 11-righe (Phase | Purpose | Canonical artifacts | Empty-input
  branch) + sub-section compatta "Oracle rank" (Phase 2.5 table) +
  sub-section "Hallucination guard" 1-line pointer.
- Saving eager: ~1600 token (target).
- `references/pipeline_internals.md` dichiara nel preambolo che è
  load-on-demand.

## Implementation

1. Write nuovo file `references/pipeline_internals.md` con tutto il
   contenuto Phase 0..8 estratto.
2. Edit `SKILL.md` rimuovendo le sezioni `### Phase NN` originali e
   sostituendole con la tabella riassuntiva.

## Why on-demand

Il dettaglio implementativo di ogni Phase (rc codes, tree-sitter depth,
Grep budget, lock file format) serve all'operator che debug-a o estende
la pipeline. Il subagent / orchestrator che invoca la skill ha bisogno
solo del contratto (artifacts + empty-input branch) — quello sta nella
tabella eager.
