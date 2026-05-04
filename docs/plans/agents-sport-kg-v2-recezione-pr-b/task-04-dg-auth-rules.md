# Task 04 — doc-generator: HLD Authentication chain + Domain rules section

**Stato:** [PENDING]
**Dipende da:** Task 03
**Blocca:** Task 07 (smoke test)

## Goal

Aggiungere alle istruzioni HLD due sezioni nuove: "Authentication chain" (security section, da `who_authenticates`) e "Domain rules" (sezione dedicata, da `list_rules`).

## File coinvolti

- `agents/doc-generator.md`

## Step 1 — TDD test pre-modifica

```bash
grep -c "Authentication chain\|who_authenticates" agents/doc-generator.md
```
Output atteso pre-modifica (post Task 02-03): 1 (solo nel select bulk).

```bash
grep -c "Domain rules\|list_rules" agents/doc-generator.md
```
Output atteso pre-modifica: 1 (solo nel select bulk).

## Step 2 — Aggiungi istruzioni "Authentication chain"

Aggiungi nelle istruzioni operative dell'agent (vicino agli step HLD generation di Task 03), il seguente blocco. Queste sono istruzioni che dicono all'agent come arricchire la sezione "Security" dell'HLD generato (NON modifichiamo un HLD esistente — istruiamo l'agent a generare contenuto aggiuntivo nella sezione Security del template):

```markdown
#### Authentication chain (Onda 9)

Nella sezione "Security" dell'HLD, aggiungi un blocco "Authentication chain"
con dati da `who_authenticates`.

**Discovery**:
```
mcp__sport-kg__who_authenticates(service=<target-service>)
```

**Output template** (markdown da inserire in HLD):

```markdown
##### Authentication chain

| Categoria | Valore |
|---|---|
| **IdP primary** | <idp_primary o "n/d"> |
| **Additional IdP** | <list o "nessuno"> |
| **Registered M2M callers** | <list di userId+sourceSystem o "nessuno"> |
| **Confidence** | <HIGH/MEDIUM/LOW> |
| **Observed at** | <ISO8601 da envelope D1> |
```

**Note**:
- Se `who_authenticates` ritorna `applicable=false` (servizio non auth-aware),
  **OMETTI** il blocco intero. Non scrivere "nessuna auth" — è informazione
  fuorviante.
- "Registered M2M callers" deduplicare per userId (può apparire con sourceSystem
  multipli — es. `OPCON_M2M_CONC` e `OPCON_M2M_DIGITAL`).
```

## Step 3 — Aggiungi istruzioni "Domain rules"

Aggiungi nelle istruzioni operative dell'agent un nuovo blocco di istruzioni che dice all'agent di generare una sezione "Domain rules" nell'HLD prodotto (posizione consigliata nel template: dopo "Domain model" o prima di "Security"):

```markdown
#### Domain rules (Onda 6)

Se il servizio ospita BusinessRule (Drools/Kogito), genera una sezione dedicata.

**Discovery**:
```
mcp__sport-kg__list_rules(service_filter=<target-service>)
```

**Output template** (markdown da inserire in HLD):

```markdown
##### Domain rules

| Package | Rule name | Activation pattern | Salience |
|---|---|---|---|
| <package> | <rule_name> | <when_summary> | <salience> |
| ... (top 10 più rilevanti) | | | |

*Totale rules: <count>. Per drill-down completo, consultare
`mcp__sport-kg__describe_rule(<rule_id>)` o repo `<service-name>` directory
`src/main/resources/rules/`.*
```

**Note**:
- Limita a top 10 per package o per salience desc (HLD non è il posto per
  dump di 22.257 rules — link al repo è sufficiente per tail)
- Se `list_rules` ritorna 0 rules per il servizio, **OMETTI** la sezione
- Se `list_rules` non disponibile (Onda 6 non installata), aggiungi nota
  "Rules: vedi `<service-name>/src/main/resources/rules/` (introspection KG
  non disponibile)"
```

## Step 4 — TDD verify

```bash
grep -c "Authentication chain" agents/doc-generator.md
```
Output atteso: ≥ 2

```bash
grep -c "Domain rules\|list_rules" agents/doc-generator.md
```
Output atteso: ≥ 4 (select bulk + sezione + Note + Discovery)

```bash
grep -c "who_authenticates" agents/doc-generator.md
```
Output atteso: ≥ 3 (select bulk + sezione + Discovery)

## Step 5 — Commit

```bash
git add agents/doc-generator.md
git commit -m "feat(agents): doc-generator HLD Authentication chain + Domain rules

HLD Security section:
- Nuovo blocco 'Authentication chain' da who_authenticates (Onda 9)
- Tabella IdP primary + additional + M2M registered + Confidence + observed_at
- Dedup userId per sourceSystem multipli (es. OPCON_M2M_CONC vs DIGITAL)
- Omissione se applicable=false (no rumore)

HLD Domain rules section (NEW):
- Nuova sezione da list_rules (Onda 6)
- Top 10 rules per package o salience
- Link al repo per tail (no dump 22k+ rules)
- Fallback a directory rules/ se list_rules non disponibile

Refs: docs/plans/2026-05-03-agents-sport-kg-v2-recezione-design.md § 6.3

Co-Authored-By: SIAE DevForge"
```

## Acceptance check

- [ ] Sezione "Authentication chain" con tabella + Note presente
- [ ] Sezione "Domain rules" con tabella + Note presente
- [ ] Omissione esplicita per casi vuoti
- [ ] Fallback documentato
- [ ] grep checks passano
- [ ] Commit creato
