# Automated-Only Coverage Notes — RTD-108 Magic Link

> 21 righe della Coverage Matrix M_FINAL sono state classificate come **non eseguibili
> da QA manuale** (R1-R3) e quindi non incluse nel CSV Xray. Coprire ognuna con il
> tipo di test automatico suggerito. Questo file e' per lo sviluppatore — NON viene
> importato in Xray.

**Conteggio per regola:**

| Regola | Descrizione                                                  | Conteggio |
|--------|--------------------------------------------------------------|-----------|
| R1     | System Mutation (template, config, SMTP, CDN, feature flag)  | 8         |
| R2     | DB Direct Action (SELECT/INSERT/UPDATE come Action o setup)  | 6         |
| R3     | Fault Injection (servizio down, mock stub, race, rollback)   | 7         |

---

## R1 — System Mutation

### A-006 — Sender address non conforme
- entita': `MAGIC_LINK_EMAIL` · campo: `sender_address`
- condizione originale: `SMTP config con sender_address="info@siae.it"`
- motivo: la modifica del sender e' configurazione SMTP, non producibile dal QA manuale
- coprire con: **contract test SMTP config** + **snapshot test header From** dell'email generata

### A-010 — URL HTTP con token non-UUID
- entita': `MAGIC_LINK_EMAIL` · campo: `button_href`
- condizione originale: `href="http://host/it/magicLink/abc"`
- motivo: forzare HTTP+token non-UUID nell'href richiede modifica del template engine
- coprire con: **snapshot test del template HTML** con golden file + **integration test** che verifichi che il builder produca solo HTTPS+UUID

### A-014 — Body in plain text
- entita': `MAGIC_LINK_EMAIL` · campo: `body_format`
- condizione originale: template impostato come plain text
- motivo: rendering plain text richiede flag di template config, non esposto al QA
- coprire con: **unit test render mode** + assert Content-Type=`text/html` o `multipart/alternative`

### A-016 — Locale "en" non supportato
- entita': `MAGIC_LINK_EMAIL` · campo: `locale`
- condizione originale: render con locale="en"
- motivo: forzare locale "en" richiede modifica config i18n
- coprire con: **unit test sul resolver locale** + assert fallback a "it" per locali non supportati

### A-017 — Subject mandatory mancante
- entita': `MAGIC_LINK_EMAIL` · campo: `subject`
- condizione originale: `subject=null` nel template
- motivo: richiede modifica della source bundle del template
- coprire con: **build-time test** che fallisce se subject mandatory mancante nel resource bundle

### A-036 — user_id esposto in URL come query
- entita': `MAGIC_LINK_TOKEN` · campo: `user_id`
- condizione originale: template include `?uid=U-123` nell'URL del bottone
- motivo: richiede modifica del template del link
- coprire con: **snapshot test template** + assert assenza di query string user-bound nell'URL

### A-055 — 200 JSON invece di 302
- entita': `ENDPOINT_CONSUME` · campo: `response_success`
- condizione originale: response 200 JSON senza redirect/login
- motivo: richiede configurazione errata del controller
- coprire con: **contract test integration**: assert status code 302 + header `Location` + `Set-Cookie`

### A-057 — Messaggi errore differenziati
- entita': `ENDPOINT_CONSUME` · campo: `response_error`
- condizione originale: messaggi diversi per scaduto/usato/rotato
- motivo: richiede implementazione errata (information disclosure)
- coprire con: **integration test** che assert testo errore identico per `expired`, `used`, `rotated`, `not-found`

---

## R2 — DB Direct Action

### A-022 — generated_at malformato in DB
- entita': `MAGIC_LINK_TOKEN` · campo: `generated_at`
- condizione originale: `generated_at="2026-13-45T99:99:99"` (data invalida)
- motivo: richiede INSERT SQL diretto con dato corrotto come precondizione
- coprire con: **unit test sul parser timestamp** con input fuzzato (property-based test, es. Hypothesis/jqwik)

### A-028 — used = "yes" (non-boolean)
- entita': `MAGIC_LINK_TOKEN` · campo: `used`
- condizione originale: `used="yes"` (stringa invece di boolean)
- motivo: richiede UPDATE DB con tipo errato
- coprire con: **integration test** sullo schema constraint (CHECK / typed enum / BOOLEAN NOT NULL)

### A-033 — status = "purple" fuori lookup
- entita': `MAGIC_LINK_TOKEN` · campo: `status`
- condizione originale: `status="purple"` (fuori da {valid, expired, consumed, rotated})
- motivo: richiede UPDATE DB con valore arbitrario
- coprire con: **integration test** con `CHECK constraint` o `ENUM type` sulla colonna status

### A-044 — side_effect_rotate non parseable
- entita': `ENDPOINT_REQUEST` · campo: `side_effect_rotate`
- condizione originale: valore non boolean forzato in DB
- motivo: richiede UPDATE DB con tipo invalido
- coprire con: **integration test** sullo schema constraint del campo

### A-060 — side_effect_consume = "n/a"
- entita': `ENDPOINT_CONSUME` · campo: `side_effect_consume`
- condizione originale: `used="n/a"` (non boolean)
- motivo: richiede UPDATE DB diretto con tipo invalido
- coprire con: **integration test** sullo schema BOOLEAN NOT NULL + default false

### B-013 — INSERT UUID duplicato
- entita': `MAGIC_LINK_TOKEN` · campo: `token_value`
- condizione originale: INSERT forzato di UUID gia' presente
- motivo: richiede INSERT SQL diretto con violazione PK
- coprire con: **integration test** su UNIQUE constraint del `token_value`

---

## R3 — Fault Injection

### A-025 — Boundary now == expires_at
- entita': `MAGIC_LINK_TOKEN` · campo: `expires_at`
- condizione originale: `now=T0+5min00s000ms` esatto (regola strict `>`)
- motivo: il boundary millisecondo-preciso richiede clock-freeze, non producibile manualmente
- coprire con: **unit test su `isExpired()`** con clock injectable (Clock di JDK Time API o Freezegun in Python)

### A-041 — DB/SMTP down -> 500/503
- entita': `ENDPOINT_REQUEST` · campo: `response_code`
- condizione originale: simulazione DB offline o SMTP service down
- motivo: fault injection sui servizi infrastrutturali
- coprire con: **integration test con Toxiproxy** o **WireMock fail rule** per simulare timeout/disconnect

### A-046 — Retry pending (primo SMTP fail)
- entita': `ENDPOINT_REQUEST` · campo: `email_send_outcome`
- condizione originale: primo tentativo SMTP fallisce, retry queue attiva
- motivo: richiede primo tentativo SMTP forzato a fail
- coprire con: **integration test** con SMTP mock fail-then-pass (es. GreenMail con scripted failure)

### A-047 — Retry failed alert (GAP G-A3)
- entita': `ENDPOINT_REQUEST` · campo: `email_send_outcome`
- condizione originale: tutti i retry SMTP falliscono
- motivo: richiede SMTP unavailable per tutta la retry window
- coprire con: **chaos test** SMTP unavailable for retry window + **assert presenza alert** in monitoring; sollevare al PO la **policy alert non definita** (GAP MEDIUM)

### A-048 — Outcome SMTP unknown
- entita': `ENDPOINT_REQUEST` · campo: `email_send_outcome`
- condizione originale: SMTP service ritorna outcome non in lookup
- motivo: richiede stub SMTP con valore inventato
- coprire con: **unit test sul mapper SMTP outcome** con valori non-canonici

### B-008 — Boundary now == T0+5min exactly
- entita': `MAGIC_LINK_TOKEN` · campo: `generated_at`
- condizione originale: clock freezato a T0+5min00s000ms
- motivo: time-freeze richiesto (regola strict `>`)
- coprire con: **unit test** equivalente a A-025 con clock injectable

### B-012 — Fallimento a meta' transazione DB
- entita': `CROSS` · campo: `transaction_partial`
- condizione originale: INSERT magic_link_tokens riuscito, UPDATE users.last_login fallito
- motivo: richiede stub applicativo per fail middleware
- coprire con: **integration test con `@Transactional` rollback test** + assert no record orfani in magic_link_tokens

### B-014 — Race condition retry queue
- entita': `CROSS` · campo: `retry_queue_race`
- condizione originale: 2 worker della retry queue prendono lo stesso job
- motivo: race condition non producibile manualmente
- coprire con: **load test concorrente** + assert idempotency-key (max 1 email per token)

---

## Riepilogo per il developer

- [ ] R1 — 8 test automatici (5 snapshot + 2 integration + 1 build-time)
- [ ] R2 — 6 test automatici (5 integration schema + 1 unit fuzzed)
- [ ] R3 — 7 test automatici (3 unit clock-injectable + 3 integration mock + 1 load test)

**Totale: 21 test automatici** che coprono il blast radius non manualmente eseguibile.
