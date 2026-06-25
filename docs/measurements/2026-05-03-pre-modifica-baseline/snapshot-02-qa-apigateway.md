# Snapshot 2 — qa-investigator pre-modifica

**Data:** 2026-05-03
**Branch:** feat/agents-sport-kg-v2-recezione
**Agent commit pre-mod:** dea5240 (design doc) — agents/qa-investigator.md non ancora modificato
**Dispatch prompt:** "Quali sono i clienti che eseguono chiamate dei MS SPORT contattando apigateway-service-ext e che tipo di auth usano?"

---

## Q&A: Quali clienti M2M chiamano i microservizi SPORT via apigateway-service-ext e con quale auth?

**Risposta sintetica**: I clienti M2M osservati sono `TTPP_M2M` (TicketOne Pubblici Spettacoli), `POP_M2M` (Punto Operatore Pop / Frontend POP), `SAP_PI` (SAP ECC bus), `ACC_M2M` (Accentramenti), `CONCERTINI_M2M` (Concertini frontend) e `MULE_M2M` (ESB AnypointStudio interno). Tutti si autenticano con un **token opaque AAS-M2M** (formato `<UUID>@<ISO8601>`) emesso da `aasm2m.siae.it/api/aasm2m/` e validato in ingresso da `AasSecurityFilter` (Mule custom security filter) — NON e' JWT, NON e' OAuth2 standard.

**Confidence**: HIGH (3 fonti concordi: codice + KG auth-chain + ES sample storici)
**Stato hint utente**: n/d (utente non ha fornito ipotesi)

### Evidenze per claim

| # | Claim | Confidence | Evidence type | Fonte |
|---|---|---|---|---|
| 1 | `apigateway-service-ext` e' una deployment k8s separata dell'immagine `sport-apigateway-service` (stessa repo, profilo M2M) | HIGH | code | `sport-apigateway-service/conf/M2M/application.yml`:160 (`spring.application.name=apigateway-service`) + scratchpad 2026-04-29 (`image ghcr.io/itsiae/sport-apigateway-service:prod-latest`, k8s name `apigateway-service-ext`) |
| 2 | Pool caller M2M: TTPP_M2M, POP_M2M, SAP_PI, ACC_M2M, CONCERTINI_M2M | HIGH | ES-runtime | scratchpad 2026-04-29 (200 hit sample 30gg userName=POP_M2M dominant, TTPP_M2M 5 hit confermati su /api/licenze/fp/{id}) + 2026-04-30 G2 (CONCERTINI_M2M 151/200, sourceSystem=CONC) |
| 3 | Caller MULE_M2M (ESB Anypoint interno) | MEDIUM | ES-runtime | scratchpad 2026-04-30 — 6/200 hit sample su /api/contabilita/notificaMovimento |
| 4 | DIGITAL_M2M NON e' caller attivo (repo `digital-channels-sport-integration-be` dormant) | MEDIUM | ES-runtime | scratchpad 2026-04-30 G2 — 0 hit in 30gg |
| 5 | Auth provider: AAS-M2M legacy SIAE (`https://aasm2m.siae.it/api/aasm2m/` in prod) | HIGH | code | `conf/M2M/application.yml`:238 (`spring.aas.url`) + `WSClientAAS.java`:84 (`authenticateRest`) |
| 6 | Token format: opaque `<UUID>@<ISO8601>` con header `X-Auth-Token` + `userId` + `sourceSystem` | HIGH | code + ES-runtime | `AasSecurityFilter.java`:58-60 (legge `X-Auth-Token` + `userId`) + `mule-config.xml`:82,89,92 (passthrough header userId/sourceSystem) + scratchpad 2026-04-29 |
| 7 | Filter Mule applicato a quasi tutti gli endpoint (organizzatore, locali, legacy, dashboard, contabilita, eccetera) | HIGH | code | `conf/M2M/mule-config.xml`:286,326,344 (`<custom-security-filter class="it.siae.authentication.AasSecurityFilter"/>`) |
| 8 | KG `sport-apigateway-service` IdP inbound = `sso-mule` (Mule SSO) — coerente con AAS via Mule filter | HIGH | KG | `describe_auth_chain(sport-apigateway-service)` → inbound `sso-mule` SSO Mule, source manual confidence HIGH |
| 9 | Esiste fallback "service account" via env var (System.getenv(userID)==token) per legacy services | MEDIUM | code | `AasSecurityFilter.java`:69-78 |
| 10 | Esiste bypass hard-coded token `cd4c3fb5-...` → userName=SUN | LOW | code | `AasSecurityFilter.java`:79,156 — possibile residuo dev/debug, da confermare in produzione |

### Dettagli

`apigateway-service-ext` e' la deployment k8s del servizio `sport-apigateway-service` configurata col profilo `M2M` (`conf/M2M/application.yml` + `conf/M2M/mule-config.xml`). Il KG MCP non lo indicizza separatamente (Gap #21 noto), ma la repo Git e l'immagine Docker sono identiche al `sport-apigateway-service` standard.

Tutti gli endpoint inbound sono Mule HTTP listener su path `/api/*` (`mule-config.xml`:256). Quasi ogni flow ha un `<custom-security-filter class="it.siae.authentication.AasSecurityFilter"/>` che:

1. legge `X-Auth-Token` (token opaque) e `userId` dagli header inbound (`AasSecurityFilter.java`:58-60);
2. controlla cache locale `LocalTokenCache` per evitare hit ad AAS ad ogni request (riga 81, 121);
3. se cache miss, chiama `aasAuthenticationService.authenticate(token, clientAddress, "SNS")` che fa POST a `https://aasm2m.siae.it/api/aasm2m/` (prod profile) restituendo `userName` (riga 98);
4. propaga `userName` come invocation property + inbound property `userID` per i flussi a valle.

Il pool caller M2M osservato nei sample ES (30gg, scratchpad sessioni 2026-04-29 e 2026-04-30) e':

| Caller userId | sourceSystem | Sistema esterno | Volume relativo (sample) |
|---|---|---|---|
| `POP_M2M` | POP | Frontend Punto Operatore POP | dominante |
| `CONCERTINI_M2M` (anche `Concertini_M2M` 15%) | CONC | Frontend Concertini | alto (151/200 sample contabilita) |
| `TTPP_M2M` | TTPP | TicketOne / TPP frontend | medio (5+ hit /api/licenze/fp) |
| `ACC_M2M` | ACC | Sport Accentramenti | basso |
| `SAP_PI` | SAP | SAP ECC bus integration (PI) | basso |
| `MULE_M2M` | n/d | ESB AnypointStudio interno | 6/200 |

Tutti usano lo stesso schema header (`X-Auth-Token`, `userId`, `sourceSystem`, `seprag`, `transactionid`) — token opaque emesso dal sottosistema AAS-M2M, NON JWT/OAuth2.

Esistono due bypass nel filtro:
- **Service-account legacy** (`AasSecurityFilter.java`:69-78): se `userID` matcha una env var, il valore della env var fa da password — usato per legacy services iniettati via k8s ConfigMap;
- **Token hard-coded** `cd4c3fb5-...` (riga 79, valore mascherato) → userName forzato a `SUN`. Confidence LOW: potrebbe essere legacy debug, va verificato che non sia attivo in prod. ⚠️ Token di bypass auth reale nel sorgente di `sport-apigateway-service` — da rimuovere e ruotare in quel repo.

### Gap residui

- ES MCP timeout questa sessione: non posso aggiornare i volumi 30gg in real-time. Pool basato su sample 2026-04-29/30 (max 200 hit/query — sample-based, non aggregato).
- `apigateway-service-ext` non indicizzato nel KG (Gap #21 known) → who_calls / refresh_external_systems non eseguibili sul nome diretto.
- ES MCP cap 200 ed assenza di `aggs.terms` impediscono il computo esatto di volume per caller — da chiudere con query Kibana diretta.
- Lista env-var legacy bypass (claim 9) non enumerata: richiederebbe lettura del k8s ConfigMap `sport-prod/apigateway-service-ext`.
- Token `cd4c3fb5-...` bypass (claim 10): da verificare se ancora attivo o rimosso post-deploy — richiede ES query su `userName: SUN`.

### Tool usati

- KG: `list_services(filter=apigateway)`, `describe_service(apigateway-service-ext)` (not found), `describe_service(sport-apigateway-service)`, `describe_auth_chain(apigateway-service-ext)` (empty), `describe_auth_chain(sport-apigateway-service)`, `who_authenticates(apigateway-service-ext)` (empty), `who_authenticates(sport-apigateway-service)`, `refresh_external_systems(apigateway-service-ext)` (ES timeout)
- ES: `search_by_service(apigateway-service-ext)`, `search_logs("apigateway-service-ext userName")` — entrambi timeout questa sessione, fallback su scratchpad 2026-04-29/30
- Code: grep su `sport-apigateway-service` clonato — letti `conf/M2M/application.yml`, `conf/M2M/mule-config.xml` (porzioni), `src/main/java/it/siae/authentication/AasSecurityFilter.java`, riferimenti `WSClientAAS.java`
- Scratchpad: `/tmp/qa-investigator-session-default.md` (entry 2026-04-29 task-pr3, 2026-04-30 G2/G3, 2026-05-03 caller pool consolidated)

---

## Note baseline

- **Status enum pre-mod**: usa vocabolario v1 (`Confidence: HIGH | MEDIUM | LOW`, `Stato hint utente: n/d`). Niente `NOT_FOUND_IN_INDEX` né `PROVEN_ABSENT_UNDER_SCOPE`.
- **Niente sezione Mapping legacy v1→v2** né `scope_completeness`.
- **Niente sezione "Disambiguazione evidence ambigua"** (alternate_hypotheses).
- **Tool usati**: l'agent ha già chiamato `who_authenticates` + `describe_auth_chain` (sono già nel `tools:` frontmatter), ma il bulk loading select Step 0 NON include `who_authenticates` (verifica con grep — fix di consistenza in Task 05).
- Questo snapshot è il **target del diff post-modifica** in PR-A Task 09.
