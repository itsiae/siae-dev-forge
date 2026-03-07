---
name: forge-logic-build
description: Costruisce il catalogo L1+L2 (domain profile + workflow map) per tutti i microservizi del sistema. Invoca siae-service-logic-map in modalita' BUILD. Salva un file YAML per repo in docs/logic-catalog/.
---

# /forge-logic-build

Invoca la skill `siae-service-logic-map` per costruire il catalogo domain profile (L1)
e workflow map (L2) di tutti i microservizi del sistema.

## Utilizzo

```
/forge-logic-build
/forge-logic-build org=itsiae pattern=sport-*
```

## Comportamento

Esegue il workflow completo della skill `siae-service-logic-map`:

1. **PRE-FLIGHT** — Verifica accesso GitHub (`gh auth status`)
2. **ENUMERATE** — Lista tutti i repo con il pattern specificato
3. **PRE-FETCH** — Il parent fetcha i dati rilevanti per ogni repo via `gh api`:
   - File tree → identifica `*Service.java`, `*Entity.java`, `openapi*.yaml`
   - Contenuto file → firma metodi public, @Transactional, @Scheduled, @KafkaListener
4. **PILOT TEST** — Verifica il pattern con 2 repo prima del full run
5. **DISPATCH** — Agenti paralleli (1 per repo) con dati inline, usano solo Write tool
6. **COLLECT** — Verifica file YAML scritti, re-dispatcha mancanti

## Output

- `docs/logic-catalog/sport-{service}.yaml` per ogni repo analizzato
- Report finale: N repo processati, gap per servizio

## Prerequisiti

- `gh auth status` deve passare
- Accesso all'organizzazione GitHub

## Note

- Pilot test obbligatorio con 2 repo — non saltarlo
- Gli agenti usano SOLO il Write tool (il parent fetcha i dati via Bash)
- Per aggiornare un singolo servizio: ri-esegui passando la lista con 1 solo repo
- Il catalogo puo' diventare stale — ri-esegui dopo modifiche significative ai repo
