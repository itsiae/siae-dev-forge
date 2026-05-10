# Task 04 — Agent `spec-reviewer` Tool Whitelist

**Goal:** Whitelist tool per `agents/spec-reviewer.md`. Confronta spec vs codice → read-only.

**File coinvolti:**
- `agents/spec-reviewer.md` (frontmatter)

## Step 1 — Leggi attuale

```bash
sed -n '1,30p' agents/spec-reviewer.md
```

## Step 2 — Aggiungi tools

```yaml
tools:
  - Read
  - Bash
  - Grep
  - Glob
```

NO Write/Edit (review). NO WebFetch (interno, no fetch esterni). NO Skill (boundary critico — vedi prompt design-reviewer-prompt.md).

## Step 3 — Edit + verifica YAML

```bash
python3 -c "import yaml; data=yaml.safe_load(open('agents/spec-reviewer.md').read().split('---')[1]); print(data.get('tools'))"
```

## Step 4 — Test manuale

Dispatch spec-reviewer su un design doc test. Verifica agent completa review con solo Read/Bash/Grep/Glob.

## Step 5 — Commit

```bash
git add agents/spec-reviewer.md
git commit -m "feat(agents): spec-reviewer tool whitelist (read-only design/spec review)

Tools: Read, Bash, Grep, Glob. NO Write/Edit, NO Skill (boundary critico).
NO WebFetch (review è interna)."
```

## Criteri accettazione

- `tools:` array con 4 tool
- YAML valido
- Test manuale OK

## NO-REGRESSION

Allinea runtime al boundary già documentato in prompt skill.
