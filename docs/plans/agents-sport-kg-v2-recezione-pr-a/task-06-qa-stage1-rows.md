# Task 06 — qa-investigator: Stage 1 nuove righe domanda-tipo

**Stato:** [PENDING]
**Dipende da:** Task 05
**Blocca:** Task 07

## Goal

Aggiungere 3 nuove righe alla tabella domanda-tipo dello Stage 1 per coprire batch discovery, rule discovery, e auth chain primario via `who_authenticates`.

## File coinvolti

- `agents/qa-investigator.md` (sezione "### Stage 1 — KG topology" tabella riga ~152)

## Step 1 — TDD test pre-modifica

```bash
grep -c "find_batch_for_keyword\|list_rules\|who_authenticates" agents/qa-investigator.md
```
Output atteso pre-modifica (post Task 05): `find_batch_for_keyword` + `list_rules` solo nel select bulk (1 ciascuno); `who_authenticates` in 2 posti (frontmatter + bulk). Totale ≥ 4.

## Step 2 — Modifica tabella domanda-tipo

Trova la tabella esistente (riga ~152-159):

```markdown
| Domanda tipo | Tool primario | Tool secondario |
|---|---|---|
| "Chi chiama X?" | `who_calls(X)` | `describe_service(X)` |
| "X chi chiama?" | `endpoints_called(X)` | `service_full_context(X)` |
| "Esiste un servizio che fa Y?" | `list_services(filter=*Y*)` + `search_endpoints(keyword=Y)` | `search_by_service(Y)` |
| "Dove e' scritta la tabella T?" | `search_tables(T)` | `data_flow_for_method` se trovi metodo |
| "Chi e' l'IdP di X?" | `describe_service(X)` + `refresh_external_systems(X)` | `who_calls(ciam-*)` |
```

Sostituisci con:

```markdown
| Domanda tipo | Tool primario | Tool secondario |
|---|---|---|
| "Chi chiama X?" | `who_calls(X)` | `describe_service(X)` |
| "X chi chiama?" | `endpoints_called(X)` | `service_full_context(X)` |
| "Esiste un servizio che fa Y?" | `list_services(filter=*Y*)` + `search_endpoints(keyword=Y)` | `search_by_service(Y)` |
| "Dove e' scritta la tabella T?" | `search_tables(T)` | `data_flow_for_method` se trovi metodo |
| "Chi e' l'IdP di X?" | `who_authenticates(X)` (Onda 9 — primario) | `describe_service(X)` + `refresh_external_systems(X)` |
| "Esiste un batch per Z?" | `find_batch_for_keyword(Z)` (Onda 10) | `service_full_context(<host>)` per cron schedule |
| "Quale regola Drools governa W?" | `list_rules(filter=W)` (Onda 6) | `describe_rule(rule_id)` per drill-down |
| "Quale auth filter chain usa X?" | `describe_auth_chain(X)` | `describe_feign_client(X)` per outbound auth |
```

(5 righe esistenti aggiornate o lasciate + 3 nuove righe + 1 riga "Chi è l'IdP" promossa a `who_authenticates` primario)

## Step 3 — Aggiungi sotto-sezione "Priors check freshness"

Sotto la tabella esistente, prima di "**Fail-fast**:", aggiungi:

```markdown
#### Priors check freshness (opzionale)

Se la domanda riguarda dati storici >30gg (es. "chi era il caller a inizio 2025?"),
chiama prima `mcp__sport-kg__graph_staleness_report()` per verificare se i nodi
rilevanti sono entro TTL. Se HIGH staleness, annota nel report:

```
⚠️ Staleness: KG ultimo refresh <observed_at>, TTL hint <ttl_hint_seconds>s
   I claim possono riflettere stato passato.
```

Non bloccare l'investigazione, solo qualificare confidence.
```

## Step 4 — Aggiungi BatchJob/BusinessRule estrazione

Trova la sezione esistente (riga ~158, dopo la tabella):

```markdown
**Fail-fast**: se Stage 1 risponde completamente alla domanda con confidence
HIGH (es. who_calls ritorna 1 caller con 100% match), salta Stage 2 e 3.
```

Sostituisci con:

```markdown
#### Estrazione nodi v2 da Stage 1

Quando chiami `describe_service` o `service_full_context`, estrai esplicitamente
(se presenti):

- **`batch_jobs[]`** — BatchJob (@Scheduled) hostati dal servizio. Usa per Q&A "chi triggera Z?", "quale batch elabora W?"
- **`business_rules[]`** — BusinessRule (Drools/Kogito) hostate. Usa per Q&A "quale regola applica logica X?"
- **`external_systems[]`** — ExternalSystem M2M caller con `<userId>_<sourceSystem>`. Usa per Q&A "chi sono i clienti M2M di X?"

**Fail-fast**: se Stage 1 risponde completamente alla domanda con confidence
HIGH (es. who_calls ritorna 1 caller con 100% match), salta Stage 2 e 3.
```

## Step 5 — TDD verify

```bash
grep -c "find_batch_for_keyword\|list_rules\|who_authenticates\|graph_staleness_report\|describe_rule\|describe_auth_chain" agents/qa-investigator.md
```
Output atteso post-modifica: ≥ 8 (select bulk + tabella + freshness + estrazione).

```bash
grep -c "batch_jobs\[\]\|business_rules\[\]\|external_systems\[\]" agents/qa-investigator.md
```
Output atteso post-modifica: ≥ 3.

## Step 6 — Commit

```bash
git add agents/qa-investigator.md
git commit -m "feat(agents): qa-investigator Stage 1 + nodi v2 + freshness priors

Stage 1 tabella domanda-tipo:
- 3 nuove righe: batch (find_batch_for_keyword), rule (list_rules + describe_rule),
  auth chain (describe_auth_chain + describe_feign_client)
- 'Chi e l IdP di X' promossa a who_authenticates primario (Onda 9)

Nuova sotto-sezione 'Priors check freshness':
- Uso opzionale graph_staleness_report per Q&A storiche >30gg
- Annotazione confidence senza bloccare investigazione

Estrazione esplicita nodi v2 da describe_service/service_full_context:
- batch_jobs[], business_rules[], external_systems[]

Refs: docs/plans/2026-05-03-agents-sport-kg-v2-recezione-design.md § 6.2

Co-Authored-By: SIAE DevForge"
```

## Acceptance check

- [ ] Tabella domanda-tipo ha 8 righe (5 esistenti + 3 nuove)
- [ ] who_authenticates è primario per "Chi è l'IdP"
- [ ] Sotto-sezione "Priors check freshness" presente
- [ ] Estrazione nodi v2 (batch_jobs, business_rules, external_systems) documentata
- [ ] grep checks passano
- [ ] Commit creato
