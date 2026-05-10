# Task 03 — Agent `code-reviewer` Tool Whitelist

**Goal:** Aggiungere `tools:` array nel frontmatter di `agents/code-reviewer.md`. Read-only review = no Write/Edit.

**File coinvolti:**
- `agents/code-reviewer.md` (frontmatter)

## Step 1 — Leggi frontmatter attuale

```bash
sed -n '1,30p' agents/code-reviewer.md
```

Verifica struttura YAML (eventuali campi esistenti: name, description, model, etc.).

## Step 2 — Aggiungi tools array

Inserisci nel frontmatter:

```yaml
tools:
  - Read
  - Bash
  - Grep
  - Glob
  - WebFetch  # per consultare standard SIAE / docs esterne se necessario
```

NON includere: `Write`, `Edit`, `NotebookEdit` (review è read-only).
NON includere: `Skill` (review NON invoca skill ricorsivamente).
NON includere: `Agent` (review è invocata DA controller, non orchestrate).

## Step 3 — Edit con tool Edit

## Step 4 — Verifica YAML

```bash
python3 -c "import yaml; data=yaml.safe_load(open('agents/code-reviewer.md').read().split('---')[1]); print(data.get('tools'))"
```

Output atteso: lista 5 tool.

## Step 5 — Test invocazione (manuale)

In una sessione, dispatch Agent code-reviewer su test review. Verifica:
- Agent NON tenta Write/Edit (verrebbe denied)
- Agent completa review usando solo Read/Bash/Grep/Glob/WebFetch

## Step 6 — Commit

```bash
git add agents/code-reviewer.md
git commit -m "feat(agents): code-reviewer tool whitelist (read-only review)

Tools: Read, Bash, Grep, Glob, WebFetch. NO Write/Edit (review = read-only).
Anti-dilution: tool list ristretto riduce blast radius e context bloat in
agent invocation."
```

## Criteri accettazione

- `tools:` array presente
- 5 tool specifici, no Write/Edit
- YAML valido
- Test manuale: agent non tenta scrittura

## NO-REGRESSION

Agent code-reviewer non doveva mai scrivere file. Whitelist enforcement allinea il behaviour atteso al runtime.
