# Task 03 — mcp-impact-analyst: Stage 3 5° check parallelo + sezioni nodi

**Stato:** [PENDING]
**Dipende da:** Task 02
**Blocca:** Task 04

## Goal

Aggiungere allo Stage 3 (wide scan parallelo) il 5° check `graph_consistency_check`. Documentare l'estrazione di BatchJob/BusinessRule/ExternalSystem dall'output `service_full_context`/`describe_service`.

## File coinvolti

- `agents/mcp-impact-analyst.md` (sezione "### Step 3 — Wide scan (parallelo, sempre)" righe ~169-180)

## Step 1 — TDD test pre-modifica

```bash
grep -n "graph_consistency_check\|Batch jobs\|Business rules\|External callers M2M" agents/mcp-impact-analyst.md
```

Output atteso pre-modifica: `graph_consistency_check` solo nel select bulk (1 occorrenza dal Task 02). `Batch jobs`/`Business rules`/`External callers M2M` zero occorrenze.

## Step 2 — Modifica Stage 3

Trova la sezione Step 3 esistente (riga ~170-180 dopo Task 02):

```markdown
### Step 3 — Wide scan (parallelo, sempre)

Esegui in PARALLELO (singolo messaggio, multipli tool call):

- `mcp__sport-kg__service_full_context(service, hours=24)` — topology + DB + health
- `mcp__sport-kg__service_health(service, hours=24)` — error rate per livello
- `mcp__sport-kg__debug_service(service, hours=24, keyword=<topic>)` — top eccezioni
- `mcp__sport-kg__who_calls(service, identifier_type=endpoint|class, identifier=...)` — caller statici + ES

Estrai dai risultati: top 3 endpoint hot, error rate, top eccezioni, caller dormienti
(0 traffico 30gg), Kafka producers/consumers, tabelle DB toccate.
```

Sostituisci con:

```markdown
### Step 3 — Wide scan (parallelo, sempre)

Esegui in PARALLELO (singolo messaggio, multipli tool call):

- `mcp__sport-kg__service_full_context(service, hours=24)` — topology + DB + health (include `batch_jobs[]`, `business_rules[]` se presenti — sport-kg v2)
- `mcp__sport-kg__service_health(service, hours=24)` — error rate per livello
- `mcp__sport-kg__debug_service(service, hours=24, keyword=<topic>)` — top eccezioni
- `mcp__sport-kg__who_calls(service, identifier_type=endpoint|class, identifier=...)` — caller statici + ES (include `ExternalSystem` M2M con `<userId>_<sourceSystem>` — Onda 10)
- `mcp__sport-kg__graph_consistency_check(service)` — drift KG↔ES (auth/DTO/schedule). Se ritorna `INCONSISTENT`, listare i mismatch nei vincoli. Se MCP non disponibile, skip silenzioso.

Estrai dai risultati: top 3 endpoint hot, error rate, top eccezioni, caller dormienti
(0 traffico 30gg), Kafka producers/consumers, tabelle DB toccate, **BatchJob attivi**
(da `service_full_context.batch_jobs[]`), **BusinessRule attive** (da
`service_full_context.business_rules[]`), **ExternalSystem M2M caller**
(da `who_calls` con `discovered_via=inbound_principal`), **drift signals**
(da `graph_consistency_check`).

#### Condizionale: task auth-touching

Se la modifica tocca autenticazione/autorizzazione (es. modifica filtro Spring Security,
nuovo header auth, integrazione IdP), aggiungi al wide scan:

- `mcp__sport-kg__who_authenticates(service)` — IdP primary + additional + M2M registrati (Onda 9)

#### Condizionale: task business-rule-touching

Se la modifica tocca regole Drools/Kogito (file `.drl`, `KieSession`, package rule),
aggiungi al wide scan:

- `mcp__sport-kg__list_rules(service_filter=<service>)` — enumera BusinessRule (Onda 6)
```

## Step 3 — Aggiunta sezione output supplementare

Trova la sezione "Output — REQUIRED FORMAT" (riga ~204) e nel template del blocco markdown, dopo la sezione "Volumi stimati downstream" e prima di "Ipotesi non verificate", inserisci:

```markdown
**Batch jobs:** <list di BatchJob con name + cron + last_seen, o "nessuno">
**Business rules:** <list di BusinessRule con package + activation_count, o "nessuna">
**External callers M2M:** <list di ExternalSystem userId+sourceSystem, o "nessuno">
**Drift signals (KG↔ES):** <list mismatch da graph_consistency_check, o "consistent">
```

Aggiungi nei "Vincoli del formato" (sezione esistente sotto):

```markdown
- "Batch jobs/Business rules/External callers M2M" → ometti la riga se la lista è vuota e il servizio non ha mai avuto questi nodi (evita "nessuno" se confonde). Scrivi "nessuno" SOLO se il KG ha esplicitamente cercato e non trovato.
- "Drift signals" → "consistent" se graph_consistency_check ritorna OK; lista mismatch se INCONSISTENT; "n/d" se MCP non ha risposto.
```

## Step 4 — Aggiungi workaround riga in tabella

Nella sezione "Workaround tool MCP noti" (riga ~239), aggiungi righe:

```markdown
| `graph_consistency_check` ritorna `INCONSISTENT` | Listare mismatch nei vincoli; non auto-risolvere — è human-decision |
| Servizio mappato in v2 ma client v1 | Envelope D1 additive: leggi i campi se presenti, ometti sezioni se assenti |
| Blast-radius richiede prova di assenza (no false negative) | Preferire `*_prove_absent` variants invece di default tool |
```

## Step 5 — TDD verify

```bash
grep -c "graph_consistency_check" agents/mcp-impact-analyst.md
```
Output atteso: ≥ 4 (1 select bulk + 1 Step 3 + 1 output template + 1 workaround)

```bash
grep -c "Batch jobs\|Business rules\|External callers M2M\|Drift signals" agents/mcp-impact-analyst.md
```
Output atteso: ≥ 5

```bash
grep -c "who_authenticates\|list_rules" agents/mcp-impact-analyst.md
```
Output atteso: ≥ 4 (almeno 2 per ogni tool: select bulk + condizionale Step 3)

## Step 6 — Commit

```bash
git add agents/mcp-impact-analyst.md
git commit -m "feat(agents): mcp-impact-analyst Stage 3 + output supplementare nodi v2

Stage 3 (wide scan parallelo):
- 5 check parallelo aggiunto: graph_consistency_check (drift KG vs ES)
- Condizionale auth-touching: who_authenticates
- Condizionale rule-touching: list_rules
- Estrazione esplicita BatchJob/BusinessRule/ExternalSystem da
  service_full_context e who_calls

Output card REQUIRED FORMAT:
- Nuove sezioni: Batch jobs, Business rules, External callers M2M, Drift signals
- Vincoli format aggiornati (omissione vs nessuno semantica)

Workaround tool MCP noti:
- graph_consistency_check INCONSISTENT handling
- Envelope D1 additive (KG v1 vs v2)
- *_prove_absent variants per blast-radius assenza

Refs: docs/plans/2026-05-03-agents-sport-kg-v2-recezione-design.md § 6.1

Co-Authored-By: SIAE DevForge"
```

## Acceptance check

- [ ] Stage 3 ha 5 check parallelo (incluso graph_consistency_check)
- [ ] Output template ha 4 nuove righe (Batch jobs, Business rules, External callers M2M, Drift signals)
- [ ] Workaround tabella ha 3 righe nuove
- [ ] grep checks tutti passano
- [ ] Commit creato
