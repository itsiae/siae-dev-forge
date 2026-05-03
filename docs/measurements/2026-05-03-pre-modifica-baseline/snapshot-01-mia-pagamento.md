# Snapshot 1 — mcp-impact-analyst pre-modifica

**Data:** 2026-05-03
**Branch:** feat/agents-sport-kg-v2-recezione
**Agent commit pre-mod:** dea5240 (design doc) — agents/mcp-impact-analyst.md non ancora modificato
**Dispatch prompt:** "Devo aggiungere arricchimento profili locale alla conferma pagamento in PagamentoServiceImpl di sport-gestione-licenze-service. Esegui pre-flight."

---

```markdown
## MCP Pre-flight: sport-gestione-licenze-service — arricchimento profili locale su conferma pagamento (PagamentoServiceImpl)

**Rischio:** MEDIO
**Endpoint hot-path:** n/d (servizio espone 237 endpoint, KG non riporta req/24h per endpoint; ES 24h: 0 log totali sul servizio target — anomalia, vedi vincolo #3)
**Caller dormienti (30gg ES):** tutti i 7 caller statici risultano dormienti su ES 30gg (no traffic in 1h/24h/7d/30d) — sport-contabilita-service, sport-corrispettivi-service, pop-permessi-service, sport-batch-service, ttpp-cbe-bff-service, sport-accertamenti-autorali-service, self-callers interni

**Top vincoli (decisione richiesta prima del codice):**
1. **Arricchimento profili locale → invocazione `sport-locale-service` su path di conferma pagamento.** sport-locale-service è già callee dichiarato di sport-gestione-licenze-service (Neo4j confidence medium) e ha 41 endpoint candidati per "profilo" (es. POST `/locali/profilo`, `/localiMedesimoIndirizzo/profilo`, `/localiMedesimoIndirizzo/spazio/profilo`). — **Decisione richiesta:** chi (tech lead sport-licenze + owner sport-locale-service) decide quale endpoint specifico usare e se l'arricchimento è sincrono in-line con la conferma pagamento (rischio latenza + cascade failure) o asincrono post-commit (rischio inconsistenza temporale). Quando: prima dello Stage 1 brainstorming.
2. **Blast radius DB writes su PagamentoServiceImpl.** Il servizio scrive su `licpermesso (W)`, `modello340 (W)`, `sede (W)`, `genere_locale (W)` — un arricchimento profilo locale potrebbe toccare `genere_locale` (già in write set sport-licenze) e collidere con `profilo_locale (W)` lato sport-locale-service. Doppia ownership del profilo locale = rischio race/inconsistenza. — **Decisione richiesta:** chi (DBA + 2 service owner) decide se sport-licenze deve scrivere il profilo locale direttamente in DB o esclusivamente via API verso sport-locale-service (single source of truth). Quando: prima della scelta endpoint al vincolo #1.
3. **Transazionalità conferma pagamento + chiamata REST esterna.** sport-gestione-licenze-service usa Hystrix (spring-cloud-starter-netflix-hystrix presente come dipendenza interna nei callee), ma non è verificato sul Feign client verso sport-locale-service. Aggiungere una chiamata REST dentro la transazione di conferma pagamento espone a (a) timeout che fallano il pagamento già autorizzato, (b) rollback DB lasciando profilo locale aggiornato. — **Decisione richiesta:** chi (architect + tech lead) decide pattern: outbox + retry asincrono, oppure chiamata sincrona con Hystrix circuit-breaker + compensazione esplicita su failure. Quando: prima del piano implementativo.

**Volumi stimati downstream:**
- sport-locale-service: +N req/24h pari al numero di conferme pagamento/24h su sport-gestione-licenze-service — n/d (ES 24h ritorna 0 log per il servizio target, KG non espone metriche req/24h per endpoint; richiede misurazione empirica via ES su path conferma pagamento o via APM SIAE)
- Caller upstream impattati transitivamente da rallentamento conferma pagamento (Neo4j): sport-contabilita-service, sport-corrispettivi-service, pop-permessi-service, sport-batch-service, ttpp-cbe-bff-service, sport-accertamenti-autorali-service — frazione carico n/d

**Ipotesi non verificate (da grep nel codice):**
- Esistenza e signature di `PagamentoServiceImpl.confermaPagamento` (o nome equivalente) in sport-gestione-licenze-service (find_service_for_symbol ES non trova il simbolo nelle ultime 24h — classe silente o no traffic)
- Quale Feign client viene già usato da PagamentoServiceImpl verso sport-locale-service (oppure se va creato ex novo)
- Presenza di `@Transactional` sul metodo confermaPagamento e sua propagazione
- Configurazione Hystrix (timeout, fallback) sul Feign client verso sport-locale-service in sport-gestione-licenze-service
- Esistenza di un meccanismo outbox/eventi già attivo per arricchimenti post-pagamento (Kafka non mappato nel grafo per sport-gestione-licenze-service)
- Path concreto del metodo "conferma pagamento" tra i 237 endpoint esposti (no metadata per disambiguare)
- Schema del payload ProfiloLocale richiesto da sport-locale-service (POST `/locali/profilo` vs `/localiMedesimoIndirizzo/profilo`)

**Confidence:** MEDIUM
**Data sources:** Neo4j: OK · ES: degraded (sport-gestione-licenze-service ritorna 0 log/24h e find_service_for_symbol errore ES — possibile gap indicizzazione) · Oracle: N/A

**Tool MCP usati:** demand_impact · service_full_context · service_health · debug_service · find_service_for_symbol · describe_service (sport-locale-service) · who_calls — demand_impact_deep saltato per limite tool (change_type=feature non supportato)
```

---

## Note baseline

- **Output card pre-modifica**: NESSUNO dei nuovi campi v2 presente: niente `Freshness:`, niente `Falsifiable_by:`, niente sezione `Batch jobs:`/`Business rules:`/`External callers M2M:`/`Drift signals:`. Status nei vincoli usa testo libero (es. "Decisione richiesta:" inline).
- **Tool usati**: pipeline 5-stage standard (no `graph_consistency_check`, no `who_authenticates`, no `list_rules`).
- Questo snapshot è il **target del diff post-modifica** in PR-A Task 09.
