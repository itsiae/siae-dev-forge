# Snapshot 4 — qa-investigator post-modifica (PR-A)

**Data:** 2026-05-03
**Branch:** feat/agents-sport-kg-v2-recezione (HEAD post-Task 08: 3044a0b)
**Agent commit post-mod:** qa-investigator.md a 424 righe (post Task 05+06+07+08)
**Dispatch prompt:** stessa di Snapshot 2

**MCP server status:** DEGRADED — sport-kg `-32602` errors. ES MCP timeout. Agent in modalità code-grep + memoria episodica fallback.

---

## Q&A: Quali clienti chiamano i MS SPORT via apigateway-service-ext e con quale auth?

**Risposta sintetica (1-2 frasi)**: I MS SPORT esposti esternamente sono raggiunti tramite il profilo **M2M** dello stesso binario `sport-apigateway-service` (3 profili conf: M2M/TEST/PRODUCTION). I client sono **sistemi tecnici machine-to-machine** (es. **SAP_PI**, **ACC_M2M**, e altri user tecnici pattern `*_PI`/`*_M2M`/`*_BATCH`/`*_SAP`) che si autenticano contro **AAS (Authentication Service SIAE)** in due modalità: **token opaco SIAE in header `X-Auth-Token`** (filter primario `AasSecurityFilter`) oppure **Basic auth `X-Username`/`X-Password`** convertita da AAS in token via `loginSSO` (filter secondario `AasSecurityUsernamePasswordFilter`); esistono anche bypass per "legacy users" autenticati via env var del pod.

**Confidence**: MEDIUM (high sul meccanismo auth da codice, medium sulla lista caller perché ES offline → riuso memoria episodica 5gg)
**Stato hint utente**: n/d (nessuna ipotesi nel prompt)

### Evidenze per claim

| # | Claim | Confidence | Evidence type | Fonte |
|---|---|---|---|---|
| 1 | apigateway-service-ext = profilo M2M dello stesso `sport-apigateway-service` (binario unico, 3 conf separate) | HIGH | code | `sport-apigateway-service/conf/{M2M,TEST,PRODUCTION}/mule-config.xml` |
| 2 | Auth INBOUND primaria = AAS via header `X-Auth-Token` | HIGH | code | `AasSecurityFilter.java:55-100` |
| 3 | AAS è un SOAP/REST service esterno (`aasws.test.siae`) — non OAuth/JWT | HIGH | code | `WSClientAAS.java:60-66` |
| 4 | Auth INBOUND secondaria = Basic auth `X-Username`/`X-Password` → AAS `loginSSO` | HIGH | code | `AasSecurityUsernamePasswordFilter.java:53-75` |
| 5 | Custom security filter agganciato per ogni flow Mule del profilo M2M | HIGH | code | `mule-config.xml:286,326,344,362` |
| 6 | Bypass "legacy" via env var | HIGH | code | `AasSecurityFilter.java:69-77` |
| 7 | Caller M2M registrati: SAP_PI (78 hit/24h IP 10.125.17.162 / VPC 172.31.1.210), ACC_M2M (38 hit/24h IP 10.125.27.169) | MEDIUM | ES-runtime (memoria 2026-04-28) | scratchpad + `project_session_2026-04-28_contabilita_caller_audit.md` |
| 8 | Pattern userId tecnici: `^[A-Z][A-Z0-9_]*_(PI\|M2M\|BATCH\|ESB\|SAP\|JOB\|CRON)$` | MEDIUM | KG description | tool description metadata |
| 9 | userName ricevuto da AAS in MDC e in `data.userId` filebeat → ES | HIGH | code | `WSClientAAS.java:65-74` + `AasSecurityFilter.java:75` |
| 10 | Endpoint contabilità via apigateway-ext: `/api/contabilita/notificaMovimento`, `/anteprimaProposta` | MEDIUM | inference + ES (memoria) | `mule-config.xml` listener `/contabilita/*` + memoria 2026-04-28 |
| 11 | Token bypass dev hardcoded `cd4c3fb5-...` in produzione | HIGH | code | `AasSecurityFilter.java:80` |

### Dettagli

[...output completo, abbreviato per leggibilità snapshot...]

### Gap residui

- **Lista esaustiva caller M2M attivi 30d**: ES MCP timeout → impossibile aggregare. Si chiude con `search_by_service(apigateway-service-ext, 30d)`.
- **Mapping userId tecnico → sistema sorgente**: SAP_PI ↔ SAP confermato; ACC_M2M ↔ Accentramenti; resta TTPP_M2M, POP_M2M, *_BATCH.
- **MCP sport-kg `-32602`** persistente — gap operativo non risolvibile in-session.
- **AAS lato server**: follow-up su `aas-channelbackend` o `pae-auth-be`.

### Tool usati

- KG: `list_services`, `describe_service` (5+3 tentativi, tutti `-32602`)
- ES: `search_by_service`, `search_logs`, `list_indices` (tutti timeout)
- Code: grep su `sport-apigateway-service/conf/` + `src/main/java/it/siae/authentication/`
- Memoria: `project_session_2026-04-28_contabilita_caller_audit.md`
- Scratchpad: `/tmp/qa-investigator-session-20260503.md`

---

## Note post-mod (verifica novità v2)

**Cosa è osservabile:**
- ✅ **Status enum v1 ancora compatibile**: l'agent usa `Confidence: MEDIUM` + `Stato hint utente: n/d` (formato pre-mod ancora valido).
- ❌ **Enum v2 (NOT_FOUND_IN_INDEX, PROVEN_ABSENT_UNDER_SCOPE)**: NON emerge in questa run perché MCP degraded — il mapping legacy v1→v2 si applica solo se `scope_completeness` è presente nella response MCP, e MCP non risponde.
- ❌ **Mapping legacy v1→v2**: stessa cosa — feature dormiente in modalità code-grep fallback.
- ❌ **Sotto-sezione "Disambiguazione evidence ambigua" (alternate_hypotheses)**: NON applicabile in questa run perché MCP non disponibile.
- ✅ **Fallback memoria + grep funzionano**: l'agent produce report comunque utilizzabile con confidence calibrata (MEDIUM, motivata da ES offline).
- ✅ **No-regression**: il formato e la struttura del report sono compatibili con baseline (Snapshot 2). 11 claim con evidence_type code/ES-runtime/inference, gap residui esplicitati, tool usati documentati.

**Cosa NON è verificabile in questa sessione:**
- L'emergere effettivo di `NOT_FOUND_IN_INDEX` o `PROVEN_ABSENT_UNDER_SCOPE` in output reale richiede una run con MCP UP che ritorni `scope_completeness=incomplete` o invocazione di `*_prove_absent` variants.
- Le 3 nuove righe Stage 1 (find_batch_for_keyword, list_rules, describe_auth_chain) richiedono dispatch su domande mirate (es. "esiste un batch per X?") + MCP UP.
