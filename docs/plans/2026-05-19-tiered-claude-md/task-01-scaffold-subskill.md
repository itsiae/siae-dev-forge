---
task: 01
title: Scaffold sub-skill siae-codebase-map-tiered
status: PENDING
estimate_min: 15
type: scaffold
depends_on: []
---

# Task 01 — Scaffold sub-skill `siae-codebase-map-tiered`

## Obiettivo

Creare la struttura della nuova sub-skill `siae-codebase-map-tiered` con SKILL.md
e directory `scripts/` vuota. Nessuna logica implementativa in questo task —
solo scaffold testabile.

## File da creare

1. `skills/siae-codebase-map-tiered/SKILL.md` (~150 righe)
2. `skills/siae-codebase-map-tiered/scripts/` (directory)
3. `skills/siae-codebase-map-tiered/scripts/.gitkeep`

## Contenuto SKILL.md

Frontmatter YAML:

```yaml
---
name: siae-codebase-map-tiered
description: >
  Use as REQUIRED SUB-SKILL from siae-codebase-map when --tiered flag is set.
  Generates hierarchical CLAUDE.md (L1 root + L2 package + L3 child on-demand)
  from existing docs/CODEBASE_MAP.md, following Anthropic best practices for
  large codebases (load-on-demand, anti-bloat, import @ chain).
---
```

Sezioni obbligatorie:
- Tipo: Rigid · Fase SDLC: 1. Init & Setup (sub-skill)
- Header DevForge ASCII
- Prerequisiti: `docs/CODEBASE_MAP.md` deve esistere
- Step 1: Read CODEBASE_MAP.md frontmatter + module list
- Step 2: Invocazione `emit-claude-md.py` (riferimento a task 02)
- Step 3: Invocazione `anti-bloat-lint.py` (riferimento a task 03)
- Step 4: Pre-flight 🟡 MEDIO con preview path target
- Step 5: Write file CLAUDE.md L1/L2/L3
- Classificazione rischio (3 op: read map, lint, write CLAUDE.md)
- Permission denied handling (fallback testuale se Write negato)

Riferimenti pattern: vedi `skills/siae-codebase-map/SKILL.md` per format.

## Criteri di accettazione

1. ✅ Directory `skills/siae-codebase-map-tiered/` esiste
2. ✅ `SKILL.md` valido (frontmatter YAML parse OK)
3. ✅ `scripts/.gitkeep` presente per preservare directory vuota
4. ✅ Lint markdown: nessun TBD/TODO residuo
5. ✅ Description coerente con descrizione design doc

## Test

- Verifica esistenza: `test -f skills/siae-codebase-map-tiered/SKILL.md`
- Verifica frontmatter parsabile: `python3 -c "import yaml; yaml.safe_load(open('...').read().split('---')[1])"`
- Verifica nessun placeholder: `grep -E "TBD|TODO|<...>" skills/siae-codebase-map-tiered/SKILL.md && exit 1 || exit 0`

## Definition of Done

- File scaffold creati
- SKILL.md frontmatter valido
- Nessun placeholder
- Commit: `chore(skills): scaffold siae-codebase-map-tiered sub-skill`
