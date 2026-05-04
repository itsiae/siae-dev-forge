# Task 02 — `siae-service-logic-map` Disambiguazione 2 Modalità

**Goal:** Distinguere le 2 modalità (build-catalog vs impact-analysis) nella description + flowchart 3 domande nel body. NON splittare in 2 skill (decisione design ADR-4).

**File coinvolti:**
- `skills/siae-service-logic-map/SKILL.md`

## Step 1 — Leggi attuale

```bash
wc -l skills/siae-service-logic-map/SKILL.md
sed -n '1,30p' skills/siae-service-logic-map/SKILL.md
```

## Step 2 — Frontmatter description con 2 modalità

Pattern target:

```yaml
---
name: siae-service-logic-map
description: >
  Use when profiling microservices for documentation OR for impact analysis.
  Two modes:
  - **Mode A (build-catalog)**: build L1+L2+L3 catalog (domain profile + workflow
    map + business rules) for a cluster of microservices. Trigger: "build catalogo
    L1/L2/L3", "lanciamo su <pattern>", "analizziamo <sistema>", "regole business
    di X", "Drools in Y".
  - **Mode B (impact-analysis)**: pre-flight MCP single-task con output
    standardizzato (rischio + 3 vincoli + volumi). Trigger: "modifica su servizio
    business-critical", "impact analysis", "blast radius", "demand impact",
    "/forge-mcp-preflight".
  Examples: "cosa fa servizio X", "impact di modifica DTO Y", "build catalogo
  cluster Z".
---
```

NB: trigger keyword già project-agnostic (post-PR-4 task 02). Se ancora presenti `sport-*/pop-*/pae-*`, rimuoverli.

## Step 3 — Aggiungi sezione "Quale modalità scegliere" nel body

Posizione: subito dopo HARD-GATE.

```markdown
## Quale modalità scegliere — Flowchart 3 domande

```text
1. Stai facendo IMPLEMENTAZIONE di una modifica specifica?
   ├── SI → Mode B (impact-analysis): /forge-mcp-preflight
   └── NO → Step 2

2. Stai facendo DOCUMENTAZIONE / onboarding di un sistema?
   ├── SI → Mode A (build-catalog): /forge-logic-build
   └── NO → Step 3

3. Stai facendo INVESTIGAZIONE Q&A su come funziona X?
   ├── SI → NEITHER. Usa siae-debugging o qa-investigator subagent
   └── NO → Stop e chiedi all'utente cosa intende
```

| Modalità | Output | Subagent | When |
|---|---|---|---|
| A. build-catalog | docs/catalog/L1+L2+L3 markdown | siae-service-logic-map.md (forge-logic-build) | Documentation, onboarding nuovo cluster |
| B. impact-analysis | Pre-flight card (rischio + 3 vincoli + volumi) | mcp-impact-analyst | Pre-design di task implementativo |
```

## Step 4 — Verifica skill ancora <250 righe

```bash
wc -l skills/siae-service-logic-map/SKILL.md
```

(Se attualmente ~166-200 e aggiungiamo flowchart, può salire a ~220. OK fino a 250 per skill specialistica con 2 modalità.)

## Step 5 — Smoke test no-regression

Prompt:
- "build catalogo per cluster X" → siae-service-logic-map (Mode A)
- "impact di modifica DTO Y" → siae-service-logic-map (Mode B)
- "regole business di servizio Z" → siae-service-logic-map (Mode A)
- "blast radius di modifica X" → siae-service-logic-map (Mode B)

Tutti devono attivare la skill.

## Step 6 — Commit

```bash
git add skills/siae-service-logic-map/SKILL.md
git commit -m "refactor(skills): siae-service-logic-map disambiguazione 2 modalità (A build / B impact)

Description distingue trigger Mode A (build-catalog) e Mode B (impact-analysis)
con esempi separati. Body aggiunge flowchart 3 domande per scegliere modalità.
Decisione design ADR-4: NO split in 2 skill (cost > beneficio).
NO-REGRESSION 4 smoke OK."
```

## Criteri accettazione

- Description distingue 2 modalità con trigger separati
- Sezione "Quale modalità scegliere" con flowchart presente
- 4 smoke prompt attivano skill
- Wc -l <250

## NO-REGRESSION

Skill è singola — entrambe le modalità mantengono attivazione su prompt esistenti. Disambiguazione interna è AGGIUNTA, non sottrazione di copertura.
