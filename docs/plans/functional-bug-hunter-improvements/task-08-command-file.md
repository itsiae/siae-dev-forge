# Task 08 — Register commands/siae-functional-bug-hunter.md

**Stato**: [PENDING] · **Effort**: 30min · **File toccati**: 1

## Goal

Onorare il claim nello SKILL.md "Invocation is manual only, via the
explicit slash command `/siae-functional-bug-hunter`" creando il file
slash-command che fact-check ha mostrato essere assente. Pattern
canonico: `commands/forge-*.md`.

## Acceptance

- `commands/siae-functional-bug-hunter.md` esiste.
- Frontmatter contiene almeno `description:` (≤500 char) + `argument-hint:`.
- Body contiene: invocation example JSON, link a SKILL.md.
- Stile allineato a `commands/forge-*.md` esistenti.

## Implementation

1. Read `commands/forge-mcp-preflight.md` per format reference.
2. Write `commands/siae-functional-bug-hunter.md` con frontmatter + body.
3. Verifica: nessun frontmatter campo extra non documentato.
