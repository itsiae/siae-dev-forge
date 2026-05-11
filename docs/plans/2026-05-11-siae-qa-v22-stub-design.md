# Design Stub — siae-qa v2.2.0 (backlog post 5-case simulation)

> **Stato:** BACKLOG / STUB — non implementare in questa sessione. Da promuovere a design completo via `siae-brainstorming` quando si decide di pianificare v2.2.0.

## Origine

Simulazione end-to-end di siae-qa v2.0.0 su **5 nuove fixture archetipo** (`frontend_form`, `etl_bronze_silver`, `database_migration`, `integration_webhook`, `api_pagination` — output in `evals/workspace/siae-qa-sim-5case/`) ha confermato l'efficacia dei 7 ADR del piano v2.1.0 (43→48/50 scorecard atteso post-v2.1.0) e identificato **25 nuovi gap** non coperti distribuiti su 4 categorie.

## Categorie Gap Residui

### Categoria 1 — Cross-temporal / Cross-event composite (PRIORITÀ ALTA)

Sintomi su `database_migration` (G-DB-6) e `integration_webhook` (G-INT-C):
- Regole composite che dipendono da **sequenza temporale ordinata di stati** (ANTE deploy v1 → migration → POST deploy v2 → write → rollback) — Matrix B v2.1.0 tratta solo prodotto cartesiano sincrono.
- Idempotency cross-event (`event.id IN webhook_events`) e out-of-order (`event.created < last_event_at`) — stato cross-event, non cross-field.

**ADR-008 candidato (v2.2.0):** estendere Matrix Agent B con primitive "temporal sequence" e "cross-event state". Trigger sintattico: presenza di parole chiave `ANTE/POST`, `prima/dopo`, `out-of-order`, `replay`, `event.id`, `processed_at`, `last_*_at`.

### Categoria 2 — Stateful ETL pipeline rules (PRIORITÀ ALTA)

Sintomi su `etl_bronze_silver` (G-ETL-2/3/4/5/6/7):
- Stateful idempotency (MERGE INTO con same period) cross-run cross-time.
- Volume threshold con soglie eterogenee (count assoluto / ratio / drift) — no regola esplosione composita unificata.
- Side-effect asincroni (CloudWatch alarm propagation) non coperti da ADR-005 multi-step.
- Pipeline ordering cross-AC (filter → dedup → null → lookup → FK).
- DLQ schema (motivo drop, run_id correlation).
- Timezone-aware vs naive timestamp.

**ADR-009 candidato:** ETL-specific stateful explosion rules. Trigger: `REQ_TYPE=ETL/Data Pipeline` + parole chiave `bronze/silver/gold`, `MERGE INTO`, `DLQ`, `quarantine`, `idempotent rerun`, `partition`, `timezone`.

### Categoria 3 — Multi-sessione TC concorrenti (PRIORITÀ MEDIA)

Sintomo su `database_migration` (G-DB-7):
- TC con observer step: `pg_locks` sampling in sessione parallela mentre ALTER/CREATE INDEX gira in sessione principale.
- Phase 4b v2.1.0 prescrive solo step sequenziali action+verification.

**ADR-010 candidato:** template step `[SESSION A] action / [SESSION B] observe` con assertion sui side-channel. Trigger: parole chiave `pg_locks`, `sessione parallela`, `concurrent`, `lock-free`, `monitor durante`.

### Categoria 4 — Conflict resolution su regole sovrapposte (PRIORITÀ MEDIA)

Sintomo su `frontend_form` (G-FE-1):
- Boolean + valore fisso business (`consensoPrivacy DEVE essere true`): A-037 (POS false) e A-039 (NEG false) semanticamente sovrapposti, generati da regole boolean+valore_fisso indipendenti.

Sintomi minori: UI states (loading/empty/error) come righe matrix implicit (G-FE-2); REST "200 empty list vs 404" non catturato (G-API-4); SQL injection EDGE-security vs EDGE-boundary indistinti (G-API-3); duration/interval type (G-INT-A); prosa "valore→outcome" non in test sintattico ADR-007 #1 (G-INT-D); performance NFR (G-API-1); cache header categoria ortogonale (G-API-2); doc-as-testable-artifact (G-DB-11); measurement-bound vs input-bound (G-DB-10); policy-dependent constraint (G-DB-9); idempotency rollback category (G-DB-8).

**ADR-011 candidato:** regole di priorità deterministica quando due categorie di esplosione si sovrappongono. Es. boolean + valore_fisso → priorità valore_fisso → POS(true) + NEG(false) + NEG(non-parseable).

**ADR-012/013/014:** ognuno per cluster gap secondari (UI states, REST patterns, performance NFR).

## Roadmap (proposta)

| Sprint | Scope | SP stimati |
|--------|-------|-----------:|
| Sprint 1 | ADR-008 cross-temporal/cross-event + ADR-009 ETL stateful (top-2 HIGH) | 12 Umano / 5 Augmented |
| Sprint 2 | ADR-010 multi-sessione + ADR-011 priority rules | 6 Umano / 3 Augmented |
| Sprint 3 | ADR-012/013/014 cluster gap secondari + 2 nuove fixture golden (etl_pipeline, integration_async) | 8 Umano / 3 Augmented |

**Totale stima v2.2.0:** ~26 Umano / 11 Augmented.

## Pre-requisiti per design completo

1. Aggiungere 2 nuove golden fixture (`etl_pipeline` + `integration_async`) come baseline misurabile per i criteri di accettazione delle nuove ADR.
2. Estendere `validate_outputs.py` con check semantici per le nuove categorie (es. `check_temporal_composite_has_sequence`, `check_etl_stateful_has_merge_clause`).
3. Aggiornare scorecard target da 50/50 a includere dimensione "Cross-domain expressiveness".

## Out of scope v2.2.0

- Refactor a DSL formale (BNF grammar per regole esplosione) — backlog v3.0.0.
- IDE plugin per autocomplete su Matrix Agent prompts — backlog v3.0.0.

---

**Note di tracciabilità:** durante l'esecuzione del piano v2.1.0 si è verificata una race condition tra Agent A (Task 03 SKILL.md) e Agent C (Task 11 schema regex): le modifiche di Task 11 (`m_final.schema.json` + `validate_outputs.py` regex `[ABC]→[A-Z]`) sono state assorbite nel commit `0860650 ADR-005 Phase 4b multi-step` invece che in commit dedicato. Codice in tree corretto; tracciabilità git parzialmente persa ma documentata in commit `e6494d4 docs(plans): aggiungi task-11`.

**Validator post-v2.1.0 (verifica empirica):**
- enumerative_spec: 6/6 PASS (incluso ADR-006 check `NEG numeric strict has EDGE low`)
- functional_be: 5/5 PASS + 3 WARN ADR-006 (gap pre-esistenti correttamente rilevati: autore_id/opera_id/body NEG senza EDGE)
- role_based: 6/6 PASS

ADR-006 funziona come progettato: emette WARN su stderr, exit code 0 (non bloccante).
