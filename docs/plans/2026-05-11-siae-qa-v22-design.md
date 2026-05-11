# Design — siae-qa v2.2.0 Full Closure

> Promosso da `2026-05-11-siae-qa-v22-stub-design.md` (backlog) a design operativo. Scope: chiudere i **25 gap residui** trovati dalla 5-case simulation portando la skill a **Gold tier consolidato 50/50**.
>
> **Accelerated workflow**: skip iter formale di spec-review (rationale: design è derivato da 5 simulation report + stub v2.2.0 già approvato concettualmente). Single-pass design + execution parallela.

## Obiettivo

Implementare 4 nuovi ADR (008-011) per chiudere i 25 gap residui clusterizzati in 4 categorie. Bump version `2.1.0 → 2.2.0`. Re-run simulazione 5-case per verifica empirica.

## ADR Specifications

### ADR-008 — Cross-temporal / Cross-event composite rules

**Gap risolti:** G-DB-6 (cross-temporal ANTE/POST deploy), G-INT-C (cross-event state idempotency+out-of-order), G-DB-12 (state machine multi-stato).

**Spec:**

1. Aggiungere alla tabella esplosione di `SKILL.md` (post-righe 297-313 in v2.1.0) la riga:

   ```
   | **Cross-temporal / cross-event composite** | 1 POS per stato finale atteso + 1 NEG per stato finale invalido + 1 EDGE per race/replay/out-of-order | idempotency: 1 POS first-event + 1 EDGE duplicate-event + 1 EDGE out-of-order |
   ```

2. Estendere prompt Matrix Agent B con paragrafo "Temporal sequences":

   ```
   Trigger sintattici: parole chiave `ANTE/POST`, `prima/dopo`, `out-of-order`, `replay`, `event.id`, `processed_at`, `last_*_at`, `idempotency-key`, `version A→version B`, `rollback dopo write`.
   Per ogni sequenza identificata:
     - 1 POS per outcome canonico (first execution successful)
     - 1 EDGE per condizione race/replay (stesso input applicato 2 volte)
     - 1 EDGE per out-of-order (eventi B applicato prima di A nella catena)
     - 1 NEG per stato finale inconsistente (es. rollback dopo write con dati persistenti)
   Marca le righe con `source_ref="temporal_composite"`.
   ```

### ADR-009 — ETL stateful pipeline rules

**Gap risolti:** G-ETL-2 (stateful idempotency MERGE), G-ETL-3 (volume threshold eterogenei), G-ETL-4 (async side-effect CloudWatch), G-ETL-5 (cross-AC pipeline ordering), G-ETL-6 (DLQ schema), G-ETL-7 (timezone-aware vs naive).

**Spec:**

1. Aggiungere 4 righe alla tabella esplosione SKILL.md:

   ```
   | **Stateful pipeline idempotency** (MERGE/UPSERT per chiave) | POS(first run) + EDGE(rerun same key→no-op) + NEG(rerun different value→conflict resolved) | MERGE INTO bronze→silver |
   | **Volume threshold composito** (count + ratio + drift) | POS(within) + NEG(exceed each threshold) + EDGE(boundary value per threshold type) | drop_ratio > 30% |
   | **Async side-effect** (CloudWatch alarm, SNS, audit log) | POS(side-effect fired) + NEG(side-effect not fired when expected) | alarm propagation |
   | **Pipeline ordering cross-AC** (filter→dedup→null→lookup→FK) | POS(canonical order respected) + NEG(stage skipped/reordered) | medallion bronze→silver→gold |
   ```

2. Estendere question-tree ETL in `reference/question-trees.md` con domande L1/L2/L3 aggiuntive:

   - L1.3: "La pipeline è idempotente? Se sì, qual è la chiave di MERGE/UPSERT?"
   - L2.4: "Quali soglie scatenano alert? (count assoluto, ratio %, drift relativo)"
   - L2.5: "I timestamp hanno timezone esplicita (TIMESTAMPTZ) o naive (TIMESTAMP)?"
   - L3.2: "Esistono side-effect asincroni (CloudWatch alarm, SNS topic, audit log)?"

3. Aggiungere a XRAY-TEMPLATES.md sezione "Pattern DLQ (Dead Letter Queue) per ETL":

   ```
   DLQ schema standard:
   - run_id (UUID, FK to job_log.id)
   - source_record_id (string)
   - reason (enum: NULL_KEY, INVALID_LOOKUP, FK_MISS, FORMAT_ERROR, QUARANTINE_THRESHOLD)
   - source_payload (JSON, original record)
   - quarantine_timestamp (TIMESTAMPTZ)
   ```

### ADR-010 — Multi-session TC concorrenti

**Gap risolti:** G-DB-7 (pg_locks sampling sessione parallela), G-INT-async (CloudWatch alarm timing).

**Spec:**

1. Estendere Phase 4b di SKILL.md con sezione "Multi-session TC pattern":

   ```
   Per TC che richiedono osservazione concorrente (lock-free verification, async side-effect):
     - Step naming: `[SESSION A] action` / `[SESSION B] observe`
     - Session B = monitor passivo, NON deve influenzare Session A
     - Timing window esplicita: "entro X secondi dall'azione" / "dopo X secondi"
     - Cleanup: ogni sessione chiude connessioni/timer alla fine del TC
   ```

2. Aggiungere esempio in XRAY-TEMPLATES.md:

   ```
   [POS] CREATE INDEX CONCURRENTLY su tabella grande — verifica lock-free
   Step 1 [SESSION A]: psql -c "CREATE INDEX CONCURRENTLY idx_email_secondaria ON autori(email_secondaria)"
   Step 2 [SESSION B] (in parallelo entro 500ms): psql -c "SELECT mode, granted FROM pg_locks WHERE relation='autori'::regclass AND mode='AccessExclusiveLock'"
   Step 3 [SESSION B] Expected: query restituisce 0 rows (no AccessExclusiveLock) per > 1 secondo durante CREATE INDEX
   Step 4 [SESSION A]: aspettare completamento CREATE INDEX
   Step 5 [SESSION A]: SELECT indexname FROM pg_indexes WHERE indexname='idx_email_secondaria' → 1 row
   ```

### ADR-011 — Conflict resolution su regole sovrapposte

**Gap risolti:** G-FE-1 (boolean + valore_fisso priority), G-FE-2 (UI states explicit category), G-API-3 (SQL injection EDGE-security vs EDGE-boundary), G-API-4 (REST 200 empty vs 404), G-INT-A (duration type), G-INT-D (prosa "valore→outcome"), G-API-1 (performance NFR), G-API-2 (cache header), G-DB-8/9/10/11 (idempotency rollback, policy-dependent, measurement-bound, doc-as-artifact).

**Spec:**

Aggiungere sezione "Priorità Regole su Conflitto" a SKILL.md (dopo tabella esplosione):

```
Quando due regole di esplosione si applicano allo stesso campo, applicare priorità deterministica:

1. **Boolean + valore fisso business** → priorità valore fisso. Esplosione: POS(true) + NEG(false) + NEG(non-parseable). NO duplicazione POS(false).
2. **String length/encoding + valore fisso** → priorità valore fisso (length/encoding già implicito nel valore). POS(=valore) + NEG(≠valore).
3. **Strict-bound numerico + valore fisso** → priorità valore fisso.

Categorie aggiuntive (extension v2.2.0):

| Categoria | Pattern esplosione | Esempio |
|-----------|---------------------|---------|
| **UI state** (loading/empty/error/disabled) | 1 POS per stato osservabile + 1 NEG per fallimento transition | form button: enabled(valid form) + disabled(invalid form) + loading(submit clicked) + error(API 5xx) |
| **REST pagination/empty-set** | 200 con `content: []` (NON 404). 1 POS empty result + 1 POS first-page + 1 POS last-page + 1 EDGE page-overflow | GET /api/opere?titolo=NOMATCH → 200 + empty content |
| **Security boundary** (SQL inj, XSS, path traversal) | NEG per ogni vettore noto, status 400 o sanitized 200 | `'; DROP TABLE`, `<script>`, `../etc/passwd` |
| **Type duration/interval** | Estensione ADR-001 type-aware: `> 5 min` → EDGE `5 min + 1s` (timestamp granularity) | signature timestamp validity |
| **Performance NFR** (latency, throughput, P95) | Marca come `source_ref="nfr_perf"` — non genera TC funzionale standard ma annotazione per test suite separata (k6/JMeter) | P95 < 500ms |
| **Cache header** (Cache-Control, ETag) | 1 POS header presente + 1 NEG header mancante quando expected | max-age=60 con filtri assenti |
| **Documentation artifact** (runbook, ADR, README) | source_ref="doc_artifact" + TC con step "verifica presenza file X" | recovery runbook esiste |
| **Policy-dependent constraint** | source_ref="policy_dependent" + nota "verify policy in place" — non NEG ambiguo | DROP COLUMN dopo write |
| **Measurement-bound** (tempo, RAM, latency misurati) | EDGE con tolerance range invece di valore fisso | duration < 35 min ± 10% |
```

### ADR-012 — Schema regex deep extension

Estendere regex `matrix_row_id` (già `[A-Z]-\d{3}` da G-DB-5 fix) per supportare suffix tematici opzionali: `[A-Z]-\d{3}(-[a-z]+)?` per consentire `A-001-nfr`, `B-005-temporal`, etc. (utile per source_ref structured).

## Componenti Toccati

| File | Modifica | Effort |
|------|----------|--------|
| `skills/siae-qa/SKILL.md` | Riga ADR-008 + 4 righe ADR-009 + sezione ADR-010 multi-session + sezione ADR-011 conflict + tabelle extension + version 2.1→2.2 + changelog | L |
| `skills/siae-qa/XRAY-TEMPLATES.md` | Sezione DLQ schema + sezione Multi-session pattern + esempi UI/REST/Security | M |
| `skills/siae-qa/reference/question-trees.md` | 4 nuove domande ETL (L1/L2/L3) | S |
| `skills/siae-qa/reference/scripts/validate_outputs.py` | Nuovi check semantici: `check_temporal_composite_has_sequence`, `check_etl_stateful_has_merge_clause`, `check_multi_session_has_session_tags` | M |
| `skills/siae-qa/reference/schemas/m_final.schema.json` | Pattern matrix_row_id esteso a `[A-Z]-\d{3}(-[a-z]+)?` (ADR-012) | XS |

## Out of Scope v2.2.0

- DSL formale (BNF grammar) — backlog v3.0.0.
- 2 nuove golden fixture (`etl_pipeline_full`, `integration_async_full`) — backlog (richiede design completo).
- Re-eseguire spec-reviewer iter su questo design — accelerated path.

## SP Stimati

- ADR-008: 3 Umano / 1 Augmented
- ADR-009: 5 Umano / 2 Augmented (più ampio: tabella + question-trees + DLQ template)
- ADR-010: 2 Umano / 1 Augmented
- ADR-011: 4 Umano / 1.5 Augmented (cluster gap, sezione lunga)
- ADR-012: 0.5 Umano / 0 Augmented
- Validator extension: 2 Umano / 0.5 Augmented
- Version bump + changelog v2.2.0: 0.5 Umano
- Re-run simulazione 5-case verifica: 1 Umano

**Totale:** 18 Umano / 6 Augmented.

## Criteri di Accettazione

1. `version: 2.2.0` nel frontmatter SKILL.md.
2. Changelog inline cita ADR-008/009/010/011/012.
3. Tabella esplosione SKILL.md ha 16+ righe (8 baseline + 3 v2.1.0 + 5 v2.2.0).
4. XRAY-TEMPLATES.md ha sezioni "DLQ Schema Pattern" e "Multi-Session TC Pattern".
5. question-trees.md sezione ETL ha 4+ domande estese (L1/L2/L3).
6. Validator ha 3+ nuovi check semantici con livello WARN.
7. Re-run simulazione 5-case post-v2.2.0: per ogni fixture, almeno 1 gap chiuso (delta validator warning -X vs v2.1.0 baseline).
8. Scorecard: 48→50/50 atteso.

## Roadmap esecuzione

| Phase | Owner | Output |
|-------|-------|--------|
| 1. Dispatch parallelo 3 agent (SKILL.md / XRAY+question-trees / validator+schema) | parallel agents | 4-6 commit |
| 2. Version bump 2.2.0 + changelog | main agent | 1 commit |
| 3. Re-run simulazione 5-case | parallel agents (5 fixture) | report consolidato |
| 4. Push + PR (riprendere `siae-finishing-branch`) | main agent | PR open |
