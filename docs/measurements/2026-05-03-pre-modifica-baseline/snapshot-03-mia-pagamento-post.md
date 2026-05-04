# Snapshot 3 — mcp-impact-analyst post-modifica (PR-A)

**Data:** 2026-05-03
**Branch:** feat/agents-sport-kg-v2-recezione (HEAD post-Task 08: 3044a0b)
**Agent commit post-mod:** mcp-impact-analyst.md a 310 righe (post Task 02+03+04)
**Dispatch prompt:** stessa di Snapshot 1

**MCP server status:** DEGRADED — tutti i tool `mcp__sport-kg__*` ritornano `MCP error -32602: Invalid request parameters`. Recovery server-side richiesto (pkill processo Python sport-kg).

---

```markdown
## MCP Pre-flight: sport-gestione-licenze-service — arricchimento profili locale conferma pagamento (PagamentoServiceImpl)

**Stato:** BLOCKED — MCP sport-kg non risponde

**Errore osservato:**
- Tutti i tool `mcp__sport-kg__*` (incluso `list_services` senza parametri e `graph_stats`) ritornano `MCP error -32602: Invalid request parameters`.
- Schemi tool correttamente caricati via `ToolSearch select:` (Step 0 OK), quindi non e' un problema di registry client-side.
- Il codice di errore JSON-RPC `-32602` con stesso sintomo su tool senza parametri richiesti indica un wrapper/proxy server-side che rigetta le richieste a monte (handler MCP non in stato pronto, oppure container/processo del server in stato anomalo).

**Recovery suggerito (lato utente, una volta sola):**
1. Identificare il processo Python del server MCP sport-kg: `ps aux | grep -i sport-kg`.
2. `pkill -f sport-kg` (NON `docker restart` del container — rompe il registry tool della sessione corrente, vedi feedback memory `feedback_mcp_tool_registry_boot_snapshot.md`). Il supervisord lo ririscrive in pochi secondi.
3. Attendere 10-15s, ri-eseguire `/forge-mcp-preflight` o ridispatchare `mcp-impact-analyst`.
4. Se persiste: `curl -fsS http://<mcp-host>:<port>/health` per verificare lo stato Neo4j/ES/Oracle backend.

**Quanto e' stato verificato in questa run:**
- Step 0 ToolSearch: OK (15 tool sport-kg caricati).
- Step 1-5 pipeline: NON eseguiti perche' Step 2 (`demand_impact`) e Step 3 (`describe_service`, `list_services`) bloccati dal server.
- Nessun fallback a grep su repo locali tentato (richiede autorizzazione esplicita utente o variabile `SPORT_KG_REPOS_DIR` configurata).

**Rischio (stima preliminare senza dati MCP, da confermare dopo recovery):**
- `PagamentoServiceImpl` di `sport-gestione-licenze-service` e' tipicamente nel hot-path di confermaPagamento → coordinata con sport-contabilita-service (SAP↔SPORT bidirezionale, vedi memory `project_session_2026-04-28_contabilita_caller_audit.md`). Aggiungere arricchimento profili locale al payment confirm tocca probabilmente: contratto evento Kafka, transazionalita' della conferma, idempotenza retry. Stima preliminare: **MEDIO/ALTO** — da rivalutare dopo demand_impact reale.

**Confidence:** LOW (1 source su 3 disponibile e per giunta in errore)
**Data sources:** Neo4j: ERROR · ES: not attempted (bloccato a monte) · Oracle: not attempted

**Tool MCP usati:** find_service_for_symbol (ERROR) · demand_impact (ERROR) · describe_service (ERROR) · list_services (ERROR) · graph_stats (ERROR)

**Azione richiesta utente:** eseguire recovery sopra e ridispatchare il pre-flight. Senza dati MCP non posso produrre il blocco standard 3-vincoli con confidence accettabile.
```

```json
{"applicable": true, "blocked": "mcp_unavailable", "error_code": "-32602", "tools_failed": ["list_services", "describe_service", "find_service_for_symbol", "demand_impact", "graph_stats"], "recovery": "pkill -f sport-kg (NOT docker restart) then re-dispatch"}
```

---

## Note post-mod

- L'agent ha **correttamente identificato MCP degraded** e ritornato formato `BLOCKED` documentato (consistente con sezione "Anti-razionalizzazione" e workaround).
- **NON è stato possibile testare** in questa sessione le novità v2 introdotte da PR-A:
  - Envelope D1 (Freshness, Falsifiable_by, inference_type) — richiede MCP up per popolare i campi
  - Sezioni nuove (Batch jobs, Business rules, External callers M2M, Drift signals) — richiede `service_full_context` + `who_calls` + `graph_consistency_check` live
  - Status enum v2 nei vincoli — richiede MCP che ritorni response v2 per emergere
- **Behavior verificato**: in caso MCP degraded, l'agent ritorna correttamente formato BLOCKED con istruzioni recovery — questo è no-regression rispetto al comportamento pre-mod (Snapshot 1 aveva MCP UP, output completo).
