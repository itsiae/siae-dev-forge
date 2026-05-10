# Task 02 — mcp-impact-analyst: estensione bulk loading Step 0

**Stato:** [PENDING]
**Dipende da:** Task 01
**Blocca:** Task 03

## Goal

Estendere il `ToolSearch select:` bulk loading di mcp-impact-analyst Step 0 con 8 nuovi tool sport-kg v2 + promozione `answer_impact_question` (già in tools frontmatter ma assente dal select).

## File coinvolti

- `agents/mcp-impact-analyst.md` (riga 114 — comando ToolSearch select bulk)

## Step 1 — TDD test (verifica pre-modifica)

```bash
grep -c "graph_consistency_check\|alternate_hypotheses\|graph_staleness_report\|find_batch_for_keyword\|who_authenticates\|list_rules\|describe_rule\|impact_of_rule_change" agents/mcp-impact-analyst.md
```

Output atteso pre-modifica: `0` o `1-2` (qualche tool potrebbe essere già nel frontmatter `tools:` ma non nel select bulk).

Verifica specifica del select bulk:

```bash
sed -n '114p' agents/mcp-impact-analyst.md
```

Output atteso pre-modifica: select con 15 tool, NESSUNO dei 9 nuovi.

## Step 2 — Modifica

Sostituisci la riga 114 (esatta stringa attuale):

```
ToolSearch query="select:mcp__sport-kg__list_services,mcp__sport-kg__describe_service,mcp__sport-kg__demand_impact,mcp__sport-kg__demand_impact_deep,mcp__sport-kg__service_full_context,mcp__sport-kg__service_health,mcp__sport-kg__debug_service,mcp__sport-kg__who_calls,mcp__sport-kg__impact_with_evidence,mcp__sport-kg__refresh_external_systems,mcp__sport-kg__search_by_service,mcp__sport-kg__endpoints_called,mcp__sport-kg__search_endpoints,mcp__sport-kg__search_tables,mcp__sport-kg__data_flow_for_method"
```

con:

```
ToolSearch query="select:mcp__sport-kg__list_services,mcp__sport-kg__describe_service,mcp__sport-kg__demand_impact,mcp__sport-kg__demand_impact_deep,mcp__sport-kg__service_full_context,mcp__sport-kg__service_health,mcp__sport-kg__debug_service,mcp__sport-kg__who_calls,mcp__sport-kg__impact_with_evidence,mcp__sport-kg__refresh_external_systems,mcp__sport-kg__search_by_service,mcp__sport-kg__endpoints_called,mcp__sport-kg__search_endpoints,mcp__sport-kg__search_tables,mcp__sport-kg__data_flow_for_method,mcp__sport-kg__graph_consistency_check,mcp__sport-kg__alternate_hypotheses,mcp__sport-kg__graph_staleness_report,mcp__sport-kg__find_batch_for_keyword,mcp__sport-kg__who_authenticates,mcp__sport-kg__list_rules,mcp__sport-kg__describe_rule,mcp__sport-kg__impact_of_rule_change,mcp__sport-kg__answer_impact_question"
```

(15 tool esistenti + 9 nuovi = 24 tool totali, una sola riga)

Aggiungi anche un breve commento sopra il blocco bulk (riga ~112) per spiegare l'aggiunta:

```markdown
Prima di ogni altra azione, esegui (24 tool sport-kg v2: 15 base + 9 nuovi
da Onde 6/9/10 + D3, vedi design doc 2026-05-03):
```

(Il testo esistente "Prima di ogni altra azione, esegui:" va sostituito con la nuova versione che cita "24 tool sport-kg v2".)

## Step 3 — TDD verify

```bash
grep -c "graph_consistency_check\|alternate_hypotheses\|graph_staleness_report\|find_batch_for_keyword\|who_authenticates\|list_rules\|describe_rule\|impact_of_rule_change\|answer_impact_question" agents/mcp-impact-analyst.md
```

Output atteso post-modifica: ≥ `9` (i 9 nuovi tool presenti).

```bash
grep -c "mcp__sport-kg__" agents/mcp-impact-analyst.md
```

Output atteso post-modifica: ≥ 35 occorrenze (24 nel select bulk + 14 nei tools frontmatter pre-esistenti = 38, può variare).

## Step 4 — Commit

```bash
git add agents/mcp-impact-analyst.md
git commit -m "feat(agents): mcp-impact-analyst bulk loading +9 tool sport-kg v2

Aggiunge al ToolSearch select Step 0 i 9 nuovi tool sport-kg v2:
- D3: graph_consistency_check, alternate_hypotheses, graph_staleness_report
- Onda 6: list_rules, describe_rule, impact_of_rule_change
- Onda 9: who_authenticates
- Onda 10: find_batch_for_keyword
- Onda 7: answer_impact_question (promozione, gia in tools frontmatter)

Da 15 a 24 tool nel bulk select. Pattern dynamic loading (no tools frontmatter
modifiche). Backward-compatible: tool nuovi sono additivi.

Refs: docs/plans/2026-05-03-agents-sport-kg-v2-recezione-design.md § 6.1
Refs: itsiae/sport-kg PR #23 + #21 + #18 + #17

Co-Authored-By: SIAE DevForge"
```

## Acceptance check

- [ ] grep dei 9 nuovi tool ritorna ≥ 9 occorrenze
- [ ] Riga 114 contiene tutti i 24 tool nel select singolo
- [ ] Commento aggiornato cita "24 tool sport-kg v2"
- [ ] Commit creato
- [ ] Le sezioni successive (pipeline 5-step, output card, etc.) NON sono state modificate (verifica con `git diff HEAD~1 agents/mcp-impact-analyst.md` — solo righe ~112-114 modificate)
