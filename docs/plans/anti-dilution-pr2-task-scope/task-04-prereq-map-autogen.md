---
task: 04
title: lib/generate-prereq-map.sh + prereq-map.generated (ADR-007)
size: M
blocks: [09]
---

# Task 4 — `lib/generate-prereq-map.sh`

Autogen di `PREREQ_MAP` da frontmatter delle 39 skill. Oggi hardcoded 7
entry in `sub-skill-gate`. Target: 39 entry autogenerate, sub-skill-gate
legge il file.

## Fonte dati

Ogni SKILL.md può dichiarare:

```yaml
---
name: siae-XXX
description: ...
prerequisites:
  - siae-brainstorming
  - siae-writing-plans
---
```

Se il frontmatter non ha `prerequisites:`, fallback: ricerca `REQUIRED SUB-SKILL`
o `## Prerequisites` nel body del SKILL.md (come documentato nel design doc).

## API

```bash
# lib/generate-prereq-map.sh
# Uso: bash lib/generate-prereq-map.sh
# Output: scrive lib/prereq-map.generated
#
# Formato output (identico al PREREQ_MAP attuale per drop-in):
#   siae-git-workflow=siae-git-env
#   siae-finishing-branch=siae-git-env,siae-git-workflow
#   ...
```

## Algoritmo

1. `for skill in skills/*/SKILL.md`
2. Parse frontmatter: estrarre `name:` e `prerequisites:` (lista YAML)
3. Se `prerequisites:` presente → emit `<name>=<prereq1>,<prereq2>`
4. Se assente → fallback: grep `REQUIRED SUB-SKILL:` nel body (optional, opt-in step)
5. Se nessun prereq trovato → skip (non emit riga, sub-skill-gate tratterà come no-prereq)
6. Sort deterministico, write atomic

## Skill → prereq attesi (da design doc + audit manuale)

Mapping completo (39 skill, ~20 con prereq):

```
siae-git-workflow=siae-git-env
siae-finishing-branch=siae-git-env,siae-git-workflow
siae-git-worktrees=siae-git-env
siae-service-logic-map=siae-microservices-map
siae-writing-plans=siae-brainstorming
siae-executing-plans=siae-writing-plans
siae-requesting-review=siae-finishing-branch
siae-receiving-review=siae-git-workflow
siae-subagent-development=siae-writing-plans
siae-blind-review=siae-finishing-branch
siae-qa=siae-brainstorming
siae-documentation=siae-brainstorming
siae-tdd=siae-brainstorming
siae-iac=siae-brainstorming
siae-data-engineering=siae-brainstorming
siae-frontend=siae-brainstorming
siae-flutter=siae-brainstorming
siae-robot-framework=siae-brainstorming
siae-automation=siae-brainstorming
siae-nr-test-flows=siae-brainstorming
```

Nota: non tutti i mapping sono obbligatori — dipende da cosa dichiara ogni
SKILL.md. Lo script è source of truth, questa lista è audit baseline.

## Step di rollout

1. Scrivere lo script generator
2. Audit manuale: verificare frontmatter su 39 skill. Dove `prerequisites:` manca
   ma la skill ha un prereq implicito (da SKILL.md body), aggiungerlo al frontmatter
3. Run generator, committare `prereq-map.generated`
4. (Task 9) Modificare `sub-skill-gate` per leggere da `prereq-map.generated`

## Acceptance

- [ ] `lib/generate-prereq-map.sh` creato
- [ ] `lib/prereq-map.generated` committato con ≥20 entry (target: 39, minimo 20 critiche)
- [ ] Frontmatter `prerequisites:` aggiunto dove manca (su skill con dep documentato)
- [ ] Idempotente: re-run stesso output
- [ ] Test: ogni entry di `prereq-map.generated` rispecchia frontmatter sorgente
- [ ] Fallback: generator robusto a skill senza frontmatter valido (warn, skip)

## Out of scope

- sub-skill-gate integration → task 9
- Hook di rigenerazione automatica (CI) → PR #3 observability (deferred)
