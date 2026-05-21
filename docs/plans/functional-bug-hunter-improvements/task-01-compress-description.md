# Task 01 — Compress description ≤1024 char

**Stato**: [COMPLETED] · **Effort**: 15min · **File toccati**: 1

## Goal

Comprimere il blocco `description: >` nel frontmatter di
`skills/siae-functional-bug-hunter/SKILL.md` da 1209 a ≤1024 char
(vincolo Anthropic Agent Skills frontmatter) e spostare l'elenco stack
estesi in una sezione body dedicata (vedi task-02).

## Acceptance

- `description: >` cleaned char count ≤1024.
- Trigger keyword preservati: "static, multi-repo, cross-stack", "manual",
  "slash command", "deterministic", "ISTQB", "interactive/strict/report-only".
- Stack list di dettaglio rimossa dalla description.

## Implementation

Edit `skills/siae-functional-bug-hunter/SKILL.md:3-19`. Output verificato
via Python char count.

## Verification

```bash
python3 -c "
import re
content = open('skills/siae-functional-bug-hunter/SKILL.md').read()
m = re.search(r'description: >\n((?:  .*\n)+)', content)
desc = ' '.join(line.strip() for line in m.group(1).strip().split('\n'))
assert len(desc) <= 1024, f'{len(desc)} > 1024'
print(f'OK: {len(desc)} chars')
"
```

Risultato: **854 chars** (era 1209, −355).
