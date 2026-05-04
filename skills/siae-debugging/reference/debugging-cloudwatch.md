# siae-debugging — Integration con observability

> Reference linked da `../SKILL.md`. Esempio AWS CloudWatch (contesto SIAE) + pattern generale per qualsiasi observability stack.

## AWS CloudWatch — Lambda / Glue (esempio SIAE)

```bash
# Filtra errori Lambda negli ultimi 30 minuti
aws logs filter-log-events \
  --log-group-name "/aws/lambda/NOME_FUNZIONE" \
  --start-time $(date -d '30 minutes ago' +%s000) \
  --filter-pattern "ERROR"

# Filtra errori Glue Job
aws logs filter-log-events \
  --log-group-name "/aws-glue/jobs/NOME_JOB" \
  --filter-pattern "?ERROR ?Exception ?Traceback"

# Cerca pattern specifico
aws logs filter-log-events \
  --log-group-name "/aws/lambda/NOME_FUNZIONE" \
  --filter-pattern '{ $.level = "ERROR" }'
```

## Qodana — Scan Statico

- Esegui scan Qodana per trovare pattern sospetti correlati al bug
- Controlla i risultati per code smells nella zona del bug
- Usa i finding come input per la Fase 2 (Pattern Analysis)

## Google Analytics — Error Tracking Frontend

- Controlla eventi di errore (5xx, 4xx, network errors)
- Verifica se il problema e' correlato a browser/dispositivo specifico
- Controlla la timeline degli errori per capire quando e' iniziato

## JIRA — Collegamento Ticket

- Cerca issue correlate via MCP Atlassian (`searchJiraIssuesUsingJql`)
- Collega il bug al ticket se disponibile
- Aggiorna lo stato del ticket durante l'investigazione
- Documenta la root cause nel ticket

## Generalizzazione

Pattern applicabile a qualsiasi observability stack: errori di integrazione
(compute, data pipeline, API, frontend) richiedono correlazione tra log
applicativi e metriche di sistema. Sostituisci i comandi `aws logs` con il
client del tuo stack (`gcloud logging`, `az monitor`, `kubectl logs`, Kibana,
Grafana Loki, etc.) mantenendo la stessa logica:

1. Restringi la finestra temporale all'incidente
2. Filtra per livello (`ERROR`, `WARN`)
3. Cerca pattern specifici (eccezioni, codici di errore)
4. Correla con eventi upstream/downstream tramite trace ID o correlation ID
