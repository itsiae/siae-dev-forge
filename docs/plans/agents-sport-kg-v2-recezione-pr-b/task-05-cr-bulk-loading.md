# Task 05 — code-reviewer: estensione bulk loading Step 0

**Stato:** [PENDING]
**Dipende da:** Task 01
**Blocca:** Task 06

## Goal

Estendere il `ToolSearch select:` bulk loading di code-reviewer Step 0 con 1 nuovo tool: `graph_consistency_check` (per Point 4 drift KG↔codice).

## File coinvolti

- `agents/code-reviewer.md` (riga 101 — comando ToolSearch select bulk)

## Step 1 — TDD test pre-modifica

```bash
sed -n '101p' agents/code-reviewer.md | grep -o "mcp__sport-kg__[a-z_]*" | sort -u | wc -l
```
Output atteso pre-modifica: `5` (5 tool nel select bulk).

```bash
grep -c "graph_consistency_check" agents/code-reviewer.md
```
Output atteso pre-modifica: 0

## Step 2 — Modifica

Sostituisci la riga 101 (esatta stringa attuale):

```
ToolSearch query="select:mcp__sport-kg__describe_service,mcp__sport-kg__who_calls,mcp__sport-kg__impact_with_evidence,mcp__sport-kg__service_full_context,mcp__sport-kg__service_health"
```

con:

```
ToolSearch query="select:mcp__sport-kg__describe_service,mcp__sport-kg__who_calls,mcp__sport-kg__impact_with_evidence,mcp__sport-kg__service_full_context,mcp__sport-kg__service_health,mcp__sport-kg__graph_consistency_check"
```

(5 esistenti + 1 nuovo = 6 tool. Una sola riga.)

## Step 3 — Aggiorna nota sopra il bulk

Trova la riga ~97 (sopra il blocco code del bulk):

```markdown
I tool MCP appaiono come "deferred" nei subagent — devi caricarli con
`ToolSearch` PRIMA di chiamarli, altrimenti `InputValidationError`.
```

Sostituisci con:

```markdown
I tool MCP appaiono come "deferred" nei subagent — devi caricarli con
`ToolSearch` PRIMA di chiamarli, altrimenti `InputValidationError`. Set minimal:
6 tool sport-kg per cross-check architetturale (5 base topology + graph_consistency_check D3 per drift KG↔codice).
```

## Step 4 — TDD verify

```bash
sed -n '101p' agents/code-reviewer.md | grep -o "mcp__sport-kg__[a-z_]*" | sort -u | wc -l
```
Output atteso post-modifica: `6`

```bash
grep -c "graph_consistency_check" agents/code-reviewer.md
```
Output atteso post-modifica: ≥ 1

## Step 5 — Commit

```bash
git add agents/code-reviewer.md
git commit -m "feat(agents): code-reviewer bulk loading +1 tool sport-kg v2 (graph_consistency_check)

Aggiunge al ToolSearch select Step 0:
- graph_consistency_check (D3): per Point 4 (Architettura) drift KG vs codice

Da 5 a 6 tool nel bulk select. Scope minimal (review puo continuare anche
senza MCP, fallback gia esistente).

Refs: docs/plans/2026-05-03-agents-sport-kg-v2-recezione-design.md § 6.4

Co-Authored-By: SIAE DevForge"
```

## Acceptance check

- [ ] graph_consistency_check nel select bulk
- [ ] Nota sopra cita "6 tool"
- [ ] Solo riga ~97-101 modificata
- [ ] Commit creato
