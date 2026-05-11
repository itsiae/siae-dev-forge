# Task 02 — doc-generator: estensione bulk loading Step 0

**Stato:** [PENDING]
**Dipende da:** Task 01
**Blocca:** Task 03

## Goal

Estendere il `ToolSearch select:` bulk loading di doc-generator Step 0 con 4 nuovi tool sport-kg v2 indispensabili per HLD: `who_authenticates`, `list_rules`, `find_batch_for_keyword`, `graph_staleness_report`.

## File coinvolti

- `agents/doc-generator.md` (riga 134 — comando ToolSearch select bulk)

## Step 1 — TDD test pre-modifica

```bash
sed -n '134p' agents/doc-generator.md | grep -o "mcp__sport-kg__[a-z_]*" | sort -u | wc -l
```
Output atteso pre-modifica: `7` (7 tool nel select bulk).

```bash
grep -c "who_authenticates\|list_rules\|find_batch_for_keyword\|graph_staleness_report" agents/doc-generator.md
```
Output atteso pre-modifica: 0

## Step 2 — Modifica

Sostituisci la riga 134 (esatta stringa attuale):

```
ToolSearch query="select:mcp__sport-kg__describe_service,mcp__sport-kg__service_full_context,mcp__sport-kg__who_calls,mcp__sport-kg__endpoints_called,mcp__sport-kg__refresh_external_systems,mcp__sport-kg__search_endpoints,mcp__sport-kg__search_tables"
```

con:

```
ToolSearch query="select:mcp__sport-kg__describe_service,mcp__sport-kg__service_full_context,mcp__sport-kg__who_calls,mcp__sport-kg__endpoints_called,mcp__sport-kg__refresh_external_systems,mcp__sport-kg__search_endpoints,mcp__sport-kg__search_tables,mcp__sport-kg__who_authenticates,mcp__sport-kg__list_rules,mcp__sport-kg__find_batch_for_keyword,mcp__sport-kg__graph_staleness_report"
```

(7 esistenti + 4 nuovi = 11 tool. Una sola riga.)

## Step 3 — Aggiorna nota sopra il bulk

Trova la riga ~130 (sopra il blocco code del bulk):

```markdown
I tool MCP appaiono come "deferred" nei subagent — devi caricarli con
`ToolSearch` PRIMA di chiamarli:
```

Sostituisci con:

```markdown
I tool MCP appaiono come "deferred" nei subagent — devi caricarli con
`ToolSearch` PRIMA di chiamarli (11 tool sport-kg v2: 7 base topology + 4 nuovi
HLD-specific da Onde 6/9/10 + D3):
```

## Step 4 — TDD verify

```bash
sed -n '134p' agents/doc-generator.md | grep -o "mcp__sport-kg__[a-z_]*" | sort -u | wc -l
```
Output atteso post-modifica: ≥ 11

```bash
grep -c "who_authenticates\|list_rules\|find_batch_for_keyword\|graph_staleness_report" agents/doc-generator.md
```
Output atteso post-modifica: ≥ 4

## Step 5 — Commit

```bash
git add agents/doc-generator.md
git commit -m "feat(agents): doc-generator bulk loading +4 tool sport-kg v2 per HLD

Aggiunge al ToolSearch select Step 0:
- who_authenticates (Onda 9): per Authentication chain in HLD security
- list_rules (Onda 6): per Domain rules section in HLD
- find_batch_for_keyword (Onda 10): per Batch Schedulers swim lane
- graph_staleness_report (D3): per footer freshness HLD

Da 7 a 11 tool nel bulk select. Scope minimal HLD-specific (no suite completa
come mcp-impact-analyst, vedi ADR-3 design doc).

Refs: docs/plans/2026-05-03-agents-sport-kg-v2-recezione-design.md § 6.3

Co-Authored-By: SIAE DevForge"
```

## Acceptance check

- [ ] 4 nuovi tool nel select bulk
- [ ] Nota sopra cita "11 tool"
- [ ] Solo riga ~130-134 modificata
- [ ] Commit creato
