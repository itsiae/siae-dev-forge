# Task 05 — Agent `mcp-impact-analyst` Tool Whitelist

**Goal:** Whitelist tool per `agents/mcp-impact-analyst.md`. KG queries + grep, no Write.

**File coinvolti:**
- `agents/mcp-impact-analyst.md` (frontmatter)

## Step 1 — Leggi attuale

```bash
sed -n '1,30p' agents/mcp-impact-analyst.md
```

## Step 2 — Aggiungi tools

```yaml
tools:
  - Read
  - Bash
  - Grep
  - Glob
  - ToolSearch  # CRITICO: agent fa Step 0 ToolSearch select bulk per MCP
  - mcp__sport-kg__answer_impact_question
  - mcp__sport-kg__demand_impact
  - mcp__sport-kg__demand_impact_deep
  - mcp__sport-kg__describe_service
  - mcp__sport-kg__find_service_for_endpoint
  - mcp__sport-kg__find_service_for_symbol
  - mcp__sport-kg__impact_of_dto_change
  - mcp__sport-kg__impact_of_endpoint_change
  - mcp__sport-kg__impact_with_evidence
  - mcp__sport-kg__list_services
  - mcp__sport-kg__service_full_context
  - mcp__sport-kg__service_health
  - mcp__sport-kg__who_calls
  - mcp__elasticsearch__search_by_service
  - mcp__elasticsearch__search_logs
```

NB: lista MCP tool basata sul prompt `agents/mcp-impact-analyst.md` (5-step pipeline).
NO Write/Edit (analyst non scrive doc).
NO Skill (no recursion).

NB rischio: ToolSearch è critico per evitare il bug noto "MCP non disponibile" nei subagent (memory `feedback_subagent_mcp_tool_loading`). DEVE essere nel whitelist.

## Step 3 — Edit + verifica YAML

```bash
python3 -c "import yaml; print(len(yaml.safe_load(open('agents/mcp-impact-analyst.md').read().split('---')[1])['tools']))"
```

Output atteso: ~17 tool.

## Step 4 — Test manuale

Dispatch mcp-impact-analyst con una query (es. "impact of DichiarazioneEventoDTO change"). Verifica:
- Agent fa ToolSearch select bulk all'inizio
- Agent invoca mcp__sport-kg__* tool senza errore "tool not available"
- Agent completa pipeline 5-step e produce output strutturato

## Step 5 — Commit

```bash
git add agents/mcp-impact-analyst.md
git commit -m "feat(agents): mcp-impact-analyst tool whitelist (KG + ES + grep, no Write)

Whitelist include ToolSearch (critico per workaround MCP injection issue),
17 tool sport-kg + ES essenziali per pipeline 5-step. NO Write/Edit/Skill.
Allinea runtime al pattern documentato nel prompt agent."
```

## Criteri accettazione

- `tools:` array con ~17 tool
- ToolSearch presente
- YAML valido
- Test manuale OK

## NO-REGRESSION

Whitelist non rimuove tool che agent usava con successo. Allinea al pattern documentato.
