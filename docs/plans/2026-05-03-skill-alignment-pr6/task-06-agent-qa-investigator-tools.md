# Task 06 — Agent `qa-investigator` Tool Whitelist

**Goal:** Whitelist tool per `agents/qa-investigator.md`. 3-stage investigation (KG + ES + code grep).

**File coinvolti:**
- `agents/qa-investigator.md` (frontmatter)

## Step 1 — Leggi attuale

## Step 2 — Aggiungi tools

```yaml
tools:
  - Read
  - Bash
  - Grep
  - Glob
  - ToolSearch  # CRITICO per MCP loading
  - mcp__sport-kg__list_services
  - mcp__sport-kg__describe_service
  - mcp__sport-kg__find_service_for_endpoint
  - mcp__sport-kg__find_service_for_symbol
  - mcp__sport-kg__service_full_context
  - mcp__sport-kg__service_health
  - mcp__sport-kg__who_calls
  - mcp__sport-kg__describe_auth_chain
  - mcp__sport-kg__who_authenticates
  - mcp__sport-kg__describe_feign_client
  - mcp__elasticsearch__search_by_service
  - mcp__elasticsearch__search_logs
  - mcp__elasticsearch__list_indices
```

NO Write/Edit (investigation = read-only).

## Step 3 — Edit + verifica YAML

## Step 4 — Test manuale

Dispatch qa-investigator con domanda tipo "quali sono i caller di apigateway-service-ext e che auth usano?". Verifica 3-stage pipeline KG → ES → grep funziona.

## Step 5 — Commit

```bash
git add agents/qa-investigator.md
git commit -m "feat(agents): qa-investigator tool whitelist (KG + ES + grep read-only)

3-stage Q&A pipeline. ToolSearch + 13 MCP tool. NO Write/Edit/Skill.
NO-REGRESSION sui pattern di Q&A esistenti."
```

## Criteri accettazione

- `tools:` array popolato
- ToolSearch presente
- YAML valido

## NO-REGRESSION

Pattern Q&A documentato in `agents/qa-investigator.md` preservato.
