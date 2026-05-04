# Task 07 — Description Audit Batch 1 (skill 1-13)

**Goal:** Audit + rewrite description in pattern "Use when X" per skill 1-13. Backbone già fatte in PR-4 (verifica), questo batch include skill domain non-backbone.

**Skill coperte (batch 1)**:
1. siae-architecture
2. siae-automation
3. siae-autoresearch
4. siae-blind-review
5. siae-branching-strategy-check
6. siae-code-standards
7. siae-codebase-map
8. siae-data-engineering
9. siae-debugging (verify post-PR-4)
10. siae-dev-analytics
11. siae-documentation
12. siae-executing-plans (verify post-PR-4)
13. siae-finishing-branch (verify post-PR-4)

## Step 1 — Verifica baseline pre-modifica (Task 06 deve essere DONE)

```bash
ls tests/skill-activation/baseline-2026-05-03.md  # deve esistere
```

## Step 2 — Per ogni skill del batch

Per ogni skill `X` in lista:

### 2.1 Leggi description attuale

```bash
sed -n '1,15p' skills/X/SKILL.md
```

### 2.2 Verifica conformità pattern

Pattern target: `Use when <trigger>. <Cosa fa>. Examples: "<esempio1>", "<esempio2>".`

Check:
- Inizia con "Use when"? (terza persona, "pushy")
- Trigger keyword 5-12?
- Description ≤1024 char?
- Esempi concreti?
- No SIAE-specifics non necessari?

### 2.3 Rewrite se non conforme

Esempio prima/dopo `siae-architecture`:

**Prima**:
```yaml
description: |
  Analizza architettura di sistemi software: C4 model, HLD, bounded context, CQRS,
  event-driven, microservizi vs monolite, resilienza, accoppiamento tra servizi.
  Invoca quando l'utente chiede di VALUTARE, SCEGLIERE o ANALIZZARE pattern...
```

**Dopo**:
```yaml
description: >
  Use when evaluating, choosing, or analyzing architectural patterns for an
  existing or new system. Covers C4 model, HLD, bounded context, CQRS,
  event-driven, microservizi vs monolite, resilienza, coupling. Best after:
  siae-brainstorming Step 4 (options proposed). Examples: "valutiamo CQRS",
  "microservizi o monolite?", "crea il C4", "definisci bounded context".
```

### 2.4 Edit con tool Edit

Usa Edit tool con `old_string` e `new_string` esatti. Preserva indentazione YAML.

### 2.5 Verifica YAML

```bash
python3 -c "import yaml; yaml.safe_load(open('skills/X/SKILL.md').read().split('---')[1])"
```

## Step 3 — Tracking progressivo

Dopo ogni skill modificata, aggiungi entry in `docs/measurements/skill-description-audit-2026-05-03.md`:

```markdown
## skill-name

- Status: REWRITTEN | OK_AS_IS
- Length before: N char
- Length after: N char
- Pattern compliance: YES (Use when X)
- Trigger keyword count: N
- Notes: <eventuale>
```

## Step 4 — Smoke test attivazione (ogni skill)

Per ogni skill rewritten, prompt smoke test (almeno 1 prompt rappresentativo):
- siae-architecture: "valutiamo CQRS per il sistema X"
- siae-data-engineering: "scrivo Glue job PySpark"
- siae-debugging: "ho un bug NPE" (verify post-PR-4)
- ...

Verifica skill ancora si attiva. Se NO → rollback granulare quella skill, fix description, retry.

## Step 5 — Commit batch

```bash
git add skills/siae-{architecture,automation,autoresearch,blind-review,branching-strategy-check,code-standards,codebase-map,data-engineering,debugging,dev-analytics,documentation,executing-plans,finishing-branch}/SKILL.md docs/measurements/skill-description-audit-2026-05-03.md
git commit -m "refactor(skills): description audit batch 1 (13 skill, 'Use when X' pattern)

Skill toccate: architecture, automation, autoresearch, blind-review,
branching-strategy-check, code-standards, codebase-map, data-engineering,
debugging (verify), dev-analytics, documentation, executing-plans (verify),
finishing-branch (verify).
NO-REGRESSION: smoke test per ognuna verificato OK."
```

## Criteri accettazione

- 13/13 skill description in pattern "Use when X"
- 13/13 YAML valido
- 13/13 smoke test OK
- audit log committato

## NO-REGRESSION

Per ogni skill toccata, prompt che pre-modifica attivava la skill DEVE continuare a farlo. Se 1+ skill regredisce, rollback solo quella + fix mirato.
