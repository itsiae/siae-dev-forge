# Task 07 — Agent `doc-generator` Tool Whitelist

**Goal:** Whitelist tool per `agents/doc-generator.md`. Genera HLD/LLD/API doc + pubblica Confluence.

**File coinvolti:**
- `agents/doc-generator.md` (frontmatter)

## Step 1 — Leggi attuale

## Step 2 — Aggiungi tools

```yaml
tools:
  - Read
  - Bash
  - Write       # genera doc markdown
  - Edit        # itera doc generato
  - Grep
  - Glob
  - ToolSearch  # per MCP atlassian + sport-kg loading
  - mcp__atlassian__authenticate
  - mcp__atlassian__complete_authentication
  - mcp__sport-kg__describe_service       # context source
  - mcp__sport-kg__service_full_context
  - mcp__sport-kg__describe_auth_chain
  - mcp__sport-kg__describe_table
```

NB: doc-generator è l'UNICO agent con Write/Edit (deve scrivere doc). Tutti gli altri sono read-only.

NO Skill (no recursion).

## Step 3 — Edit + verifica YAML

## Step 4 — Test manuale

Dispatch doc-generator con prompt "genera HLD per servizio sport-locale-service". Verifica:
- Agent legge codice + KG context
- Agent scrive doc markdown
- Agent eventualmente pubblica su Confluence (con pre-flight card 🔴 ALTO)

## Step 5 — Commit

```bash
git add agents/doc-generator.md
git commit -m "feat(agents): doc-generator tool whitelist (Write/Edit + KG + Atlassian)

Unico agent con Write/Edit (genera HLD/LLD/API doc). ToolSearch + 4 KG tool +
2 Atlassian tool. Pre-flight card 🔴 ALTO già richiesta nel prompt agent
prima di publish Confluence."
```

## Criteri accettazione

- `tools:` array con ~13 tool inclusa Write/Edit
- YAML valido
- Test manuale: agent scrive doc + (con conferma) pubblica

## NO-REGRESSION

Pattern doc-generator già documentato. Whitelist allinea runtime.
