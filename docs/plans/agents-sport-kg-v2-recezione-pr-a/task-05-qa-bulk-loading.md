# Task 05 — qa-investigator: estensione bulk loading Step 0

**Stato:** [PENDING]
**Dipende da:** Task 01
**Blocca:** Task 06

## Goal

Estendere il `ToolSearch select:` bulk loading di qa-investigator Step 0 con 9 nuovi tool sport-kg v2. Critico: `who_authenticates` è già in `tools:` frontmatter ma manca dal select bulk — fix di consistenza.

## File coinvolti

- `agents/qa-investigator.md` (riga 118 — comando ToolSearch select bulk)

## Step 1 — TDD test pre-modifica

```bash
grep "who_authenticates" agents/qa-investigator.md | wc -l
```
Output atteso pre-modifica: `1` (solo nel frontmatter `tools:`, NON nel select bulk Step 0).

```bash
sed -n '118p' agents/qa-investigator.md | grep -o "mcp__sport-kg__[a-z_]*" | sort -u | wc -l
```
Output atteso pre-modifica: `13` (13 tool nel select bulk).

## Step 2 — Modifica

Sostituisci la riga 118 (esatta stringa attuale):

```
ToolSearch query="select:mcp__sport-kg__list_services,mcp__sport-kg__describe_service,mcp__sport-kg__who_calls,mcp__sport-kg__endpoints_called,mcp__sport-kg__search_by_service,mcp__sport-kg__search_endpoints,mcp__sport-kg__search_tables,mcp__sport-kg__data_flow_for_method,mcp__sport-kg__refresh_external_systems,mcp__sport-kg__service_full_context,mcp__sport-kg__service_health,mcp__sport-kg__debug_service,mcp__sport-kg__impact_with_evidence"
```

con:

```
ToolSearch query="select:mcp__sport-kg__list_services,mcp__sport-kg__describe_service,mcp__sport-kg__who_calls,mcp__sport-kg__endpoints_called,mcp__sport-kg__search_by_service,mcp__sport-kg__search_endpoints,mcp__sport-kg__search_tables,mcp__sport-kg__data_flow_for_method,mcp__sport-kg__refresh_external_systems,mcp__sport-kg__service_full_context,mcp__sport-kg__service_health,mcp__sport-kg__debug_service,mcp__sport-kg__impact_with_evidence,mcp__sport-kg__who_authenticates,mcp__sport-kg__describe_auth_chain,mcp__sport-kg__describe_feign_client,mcp__sport-kg__graph_consistency_check,mcp__sport-kg__alternate_hypotheses,mcp__sport-kg__graph_staleness_report,mcp__sport-kg__find_batch_for_keyword,mcp__sport-kg__list_rules,mcp__sport-kg__describe_rule,mcp__sport-kg__answer_impact_question"
```

(13 esistenti + 10 aggiunti = 23 tool. NB: aggiunti `who_authenticates`, `describe_auth_chain`, `describe_feign_client` che erano in `tools:` frontmatter ma non nel select bulk — fix di consistenza.)

Aggiorna anche la riga sopra il bulk (~117) da:

```markdown
### Bulk loading (1 chiamata sola, all'inizio)
```

a:

```markdown
### Bulk loading (1 chiamata sola, all'inizio — 23 tool sport-kg v2: 13 base + 9 nuovi Onde 6/9/10 + D3 + 1 fix consistenza frontmatter)
```

## Step 3 — TDD verify

```bash
sed -n '118p' agents/qa-investigator.md | grep -o "mcp__sport-kg__[a-z_]*" | sort -u | wc -l
```
Output atteso post-modifica: ≥ 22 (potrebbe essere 23 con dedup, dipende dalla versione di `sort -u` su mac).

```bash
grep -c "who_authenticates" agents/qa-investigator.md
```
Output atteso post-modifica: ≥ 2 (frontmatter `tools:` + select bulk Step 0).

```bash
grep -c "graph_consistency_check\|alternate_hypotheses\|graph_staleness_report\|find_batch_for_keyword\|list_rules\|describe_rule\|answer_impact_question" agents/qa-investigator.md
```
Output atteso post-modifica: ≥ 7

## Step 4 — Commit

```bash
git add agents/qa-investigator.md
git commit -m "feat(agents): qa-investigator bulk loading +9 tool sport-kg v2 + fix consistenza

Aggiunge al ToolSearch select Step 0:
- D3: graph_consistency_check, alternate_hypotheses, graph_staleness_report
- Onda 6: list_rules, describe_rule
- Onda 9: who_authenticates (fix consistenza: era in tools frontmatter
  ma non nel select bulk - bug rilevato in spec review iter 1)
- Onda 10: find_batch_for_keyword
- Onda 7: answer_impact_question (fallback)

Aggiunti anche describe_auth_chain e describe_feign_client (gia in tools
frontmatter, ora consistenti nel select bulk).

Da 13 a 23 tool nel bulk select.

Refs: docs/plans/2026-05-03-agents-sport-kg-v2-recezione-design.md § 6.2
Refs: itsiae/sport-kg PR #23 + #21 + #18 + #17

Co-Authored-By: SIAE DevForge"
```

## Acceptance check

- [ ] who_authenticates presente sia in tools frontmatter che in select bulk
- [ ] grep dei nuovi tool ritorna ≥ 7 occorrenze nel bulk
- [ ] Commento aggiornato cita "23 tool"
- [ ] Solo riga ~117-118 modificata (verifica con `git diff HEAD~1`)
- [ ] Commit creato
