---
name: forge-mcp-preflight
description: Esegue il pre-flight MCP sport-kg per il task corrente — dispatcha l'agent mcp-impact-analyst (output strutturato, context-isolated) e ritorna un blocco markdown con rischio + 3 vincoli + volumi da incollare in cima al design doc. Da invocare PRIMA di brainstorming/debugging quando il task tocca un servizio SIAE mappato nel KG. Prefissi servizio (allineati con hooks/sport-task-detect — single source of truth): sport-*-service, sport-*-drools, sport-gestione-*, pop-*-service, pop-be, pae-*, ciam-*, dol-be, digital-channels-sport-*, esb-sport-*, esb-sso-*, mag-concertini-*, portal-apigateway-*, ttpp-*-bff-service.
---

# /forge-mcp-preflight

Esegue il pre-flight MCP `sport-kg` per il task corrente. Output: blocco markdown
standardizzato `## MCP Pre-flight: <service> — <feature>` da incollare in cima
al design doc generato da `siae-brainstorming` (Step 5).

## Utilizzo

```
/forge-mcp-preflight
/forge-mcp-preflight service=sport-gestione-licenze-service feature="aggiornamento profili locale alla conferma pagamento"
/forge-mcp-preflight class=PagamentoServiceImpl method=confermaPagamento
```

## Prerequisiti

- MCP server `sport-kg` connesso (verificabile con `mcp__sport-kg__graph_stats`)
- Servizio target appartiene ai prefissi mappati nel KG (sport-*/pop-*/pae-*/etc).
  Se off-domain, il comando rifiuta con `applicable: false`.

## Comportamento

Dispatcha l'agent `mcp-impact-analyst` con il contesto del task corrente. L'agent
esegue la pipeline 5-step:

1. Disambiguazione servizio target
2. Pre-flight rischio (`demand_impact`)
3. Wide scan parallelo (`service_full_context` + `service_health` + `debug_service` + `who_calls`)
4. Drill-down condizionale (`demand_impact_deep` se rischio MEDIO/ALTO)
5. Verifica empirica (`impact_with_evidence` sull'endpoint contratto)

L'agent ritorna SOLO il blocco markdown standardizzato (no chit-chat, no preambolo).

## Output

```markdown
## MCP Pre-flight: <service> — <feature>

**Rischio:** <ALTO | MEDIO | BASSO>
**Endpoint hot-path:** <path> (<req/24h>, err <%>)
**Caller dormienti (30gg ES):** <list o "nessuno">

**Top vincoli (decisione richiesta prima del codice):**
1. <vincolo concreto> — <decisione richiesta>
2. <vincolo concreto> — <decisione richiesta>
3. <vincolo concreto> — <decisione richiesta>

**Volumi stimati downstream:**
- <servizio>: +<N> req/24h (<frazione>% carico attuale)

**Ipotesi non verificate (da grep nel codice):**
- <ipotesi>

**Confidence:** <HIGH | MEDIUM | LOW>
**Data sources:** Neo4j: <OK/N/A> · ES: <OK/N/A> · Oracle: <OK/N/A>

**Tool MCP usati:** demand_impact · service_full_context · service_health · debug_service · who_calls (+ demand_impact_deep + impact_with_evidence se rischio MEDIO/ALTO)
```

## Quando usarlo

- **Stage 0 di brainstorming** su feature/refactoring/bug fix che modifica codice di un servizio mappato.
- **Pre-debugging** su bug riportato in produzione su servizio mappato.
- **Review pre-PR** quando il design doc non ha il blocco MCP pre-flight in cima.

## Quando NON usarlo

- Task off-domain (DevForge plugin, side-tools, frontend non mappato): comando rifiuta.
- Domande pure (lettura, esplorazione): non serve, e' overkill.
- Servizio non ancora indicizzato nel KG: chiamare prima `siae-microservices-map` per indicizzare.

## Note

- L'agent `mcp-impact-analyst` e' read-only sul codebase: nessuna modifica file.
- Output protetto da context window: fino a 50KB di output MCP restano nell'agent, in conversazione torna solo il blocco compatto.
- Per limiti noti del MCP sport-kg vedi `~/.claude/projects/<project>/memory/mcp_sport_kg_gaps.md`.
