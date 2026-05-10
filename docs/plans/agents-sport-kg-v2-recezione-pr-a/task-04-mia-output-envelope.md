# Task 04 — mcp-impact-analyst: output card envelope D1 + enum status v2

**Stato:** [PENDING]
**Dipende da:** Task 03
**Blocca:** Task 09 (smoke test)

## Goal

Estendere l'output card finale con i 3 campi envelope D1 (Freshness, Falsifiable_by, inference_type) e adottare l'enum status v2 nei vincoli.

## File coinvolti

- `agents/mcp-impact-analyst.md` (sezione "Output — REQUIRED FORMAT" riga ~200)

## Step 1 — TDD test pre-modifica

```bash
grep -c "Freshness:\|Falsifiable_by:\|inference_type" agents/mcp-impact-analyst.md
```
Output atteso pre-modifica: 0

```bash
grep -c "NOT_FOUND_IN_INDEX\|PROVEN_ABSENT_UNDER_SCOPE" agents/mcp-impact-analyst.md
```
Output atteso pre-modifica: 0

## Step 2 — Modifica template output card

Nel blocco markdown template (riga ~204-226), sostituisci la sezione esistente "Confidence + Data sources":

```markdown
**Confidence:** <HIGH | MEDIUM | LOW>
**Data sources:** Neo4j: <OK/N/A> · ES: <OK/N/A> · Oracle: <OK/N/A>
```

con:

```markdown
**Confidence:** <HIGH | MEDIUM | LOW> (inference_type=<value>)
**Freshness:** observed_at=<ISO8601> · ttl_hint=<seconds>
**Falsifiable_by:** <list signal o "n/d">
**Data sources:** Neo4j: <OK/N/A> · ES: <OK/N/A> · Oracle: <OK/N/A>
```

## Step 3 — Modifica esempio "Top vincoli"

Trova la sezione esistente:

```markdown
**Top vincoli (decisione richiesta prima del codice):**
1. <vincolo concreto> — <decisione richiesta>
2. <vincolo concreto> — <decisione richiesta>
3. <vincolo concreto> — <decisione richiesta>
```

Sostituisci con:

```markdown
**Top vincoli (decisione richiesta prima del codice):**
1. <vincolo concreto> — Status: <CONFIRMED|PARTIAL|NOT_FOUND_IN_INDEX|PROVEN_ABSENT_UNDER_SCOPE|REFUTED> · Decisione: <chi/cosa/quando>
2. <vincolo concreto> — Status: <enum v2> · Decisione: <chi/cosa/quando>
3. <vincolo concreto> — Status: <enum v2> · Decisione: <chi/cosa/quando>
```

## Step 4 — Aggiorna sezione "Vincoli del formato"

Nella sezione esistente "### Vincoli del formato" (riga ~228), aggiungi righe:

```markdown
- **Freshness/Falsifiable_by**: presi da envelope D1 della response sport-kg v2. Se il KG ritorna ancora v1 (campi assenti), ometti queste righe — non scrivere "n/d".
- **Status enum v2** (5 valori): `CONFIRMED` (2+ fonti concordi), `PARTIAL` (alcune sotto-affermazioni vere/altre n/d), `NOT_FOUND_IN_INDEX` (KG/ES non hanno la entity, scope ricerca limitato — ≠ assenza), `PROVEN_ABSENT_UNDER_SCOPE` (`*_prove_absent` ha confermato assenza), `REFUTED` (evidenze contrarie).
- **Mapping legacy v1 → v2** (per dual-format 60gg, vedi D2 § 2.3):
  - MCP ritorna `"NOT_EXISTS"` → scrivi `NOT_FOUND_IN_INDEX`
  - MCP ritorna `"REFUTED"` legacy + `scope_completeness=incomplete` → scrivi `NOT_FOUND_IN_INDEX` + nota "legacy v1 mapped"
  - MCP ritorna `"REFUTED"` legacy + `scope_completeness=full` → scrivi `REFUTED`
  - MCP ritorna valore enum sconosciuto → scrivi `PARTIAL` + nota "unknown enum value <X>"
- **inference_type**: dal campo envelope D1, valori tipici `direct_observation`, `inference`, `aggregation`. Se assente, ometti il qualifier dal Confidence.
```

## Step 5 — Aggiorna "Tool MCP usati"

Trova la riga esistente:

```markdown
**Tool MCP usati:** demand_impact · service_full_context · service_health · debug_service · who_calls (+ demand_impact_deep + impact_with_evidence se rischio MEDIO/ALTO)
```

Sostituisci con:

```markdown
**Tool MCP usati:** demand_impact · service_full_context · service_health · debug_service · who_calls · graph_consistency_check (+ demand_impact_deep + impact_with_evidence + describe_rule + impact_of_rule_change se rischio MEDIO/ALTO; + who_authenticates se task auth-touching; + list_rules se task rule-touching; + alternate_hypotheses se evidence ambigua)
```

## Step 6 — Aggiungi nota su `answer_impact_question` come fallback

Nella sezione "## Integrazione con altri agent / skill" (riga ~261), aggiungi punto:

```markdown
- **Onda 7 `answer_impact_question`** (orchestrator MCP rule-based): NON usato per default. Citato come fallback opzionale se la pipeline esplicita 5-step non si applica (es. domanda Q&A pre-design senza servizio target univoco). La pipeline esplicita resta il default per mantenere rationale spiegabile.
```

## Step 7 — TDD verify

```bash
grep -c "Freshness:\|Falsifiable_by:\|inference_type" agents/mcp-impact-analyst.md
```
Output atteso: ≥ 4 (template + vincoli format)

```bash
grep -c "NOT_FOUND_IN_INDEX\|PROVEN_ABSENT_UNDER_SCOPE" agents/mcp-impact-analyst.md
```
Output atteso: ≥ 4 (top vincoli template + vincoli format)

```bash
grep -c "answer_impact_question" agents/mcp-impact-analyst.md
```
Output atteso: ≥ 2 (select bulk + integrazione fallback)

## Step 8 — Commit

```bash
git add agents/mcp-impact-analyst.md
git commit -m "feat(agents): mcp-impact-analyst output card envelope D1 + enum status v2

Output card REQUIRED FORMAT:
- Aggiunte righe Freshness (observed_at + ttl_hint) e Falsifiable_by da
  envelope D1 sport-kg v2
- Confidence arricchito con inference_type qualifier
- Top vincoli usano enum status v2 (5 valori) invece di binario v1

Vincoli format:
- Mapping legacy v1 -> v2 esplicitato (NOT_EXISTS, REFUTED legacy, unknown)
- Omissione campi envelope D1 quando assenti (no version detection)

Tool MCP usati: aggiornata lista con condizionali per nuove fasi.

Onda 7 answer_impact_question documentato come fallback opzionale, non gateway
(vedi ADR-2 design doc).

Refs: docs/plans/2026-05-03-agents-sport-kg-v2-recezione-design.md § 6.1 + ADR-4

Co-Authored-By: SIAE DevForge"
```

## Acceptance check

- [ ] Output card template ha 3 nuove righe envelope D1
- [ ] Top vincoli usano enum v2 (5 valori esplicitati)
- [ ] Vincoli format ha mapping legacy v1→v2 completo (4 casi)
- [ ] `answer_impact_question` documentato come fallback in integrazione
- [ ] Tutti i grep check passano
- [ ] Commit creato
