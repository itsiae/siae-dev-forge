---
name: forge-logic-build
description: Costruisce il catalogo L1+L2 (domain profile + workflow map) per cluster di microservizi. Invoca siae-service-logic-map in modalita' BUILD. Richiede docs/SYSTEM_MAP.md (eseguire /forge-sysmap prima).
---

# /forge-logic-build

Invoca la skill `siae-service-logic-map` per costruire il catalogo domain profile (L1)
e workflow map (L2) di tutti i microservizi, organizzati per cluster funzionale.

## Utilizzo

```
/forge-logic-build
/forge-logic-build org=itsiae pattern=sport-*
```

## Prerequisiti

- `docs/SYSTEM_MAP.md` deve esistere — esegui `/forge-sysmap` prima
- `gh auth status` deve passare
- Accesso all'organizzazione GitHub

## Comportamento

Esegue il workflow completo della skill `siae-service-logic-map`:

1. **PRE-FLIGHT** — Verifica accesso GitHub (`gh auth status`)
2. **ENUMERATE** — Lista tutti i repo con il pattern specificato
3. **CLUSTER DETECTION** — Legge `docs/SYSTEM_MAP.md`, estrae cluster dal grafo,
   propone cluster all'utente per conferma prima di procedere
4. **PRE-FETCH** — Il parent fetcha i dati di tutti i repo per cluster via `gh api`:
   - File tree → identifica `*Service.java`, `*Entity.java`, `openapi*.yaml`
   - Contenuto file → firma metodi public, @Transactional, @Scheduled, @KafkaListener
5. **PILOT TEST** — Verifica il pattern con 1 cluster (il piu' piccolo) prima del full run
6. **DISPATCH** — Agenti paralleli (1 per cluster) con dati inline, usano solo Write tool
7. **COLLECT** — Verifica file cluster scritti, genera `clusters.yaml` e `system-overview.md`

## Output

- `docs/logic-catalog/cluster-{nome}.md` per ogni cluster — doc tecnica L1+L2
- `docs/logic-catalog/clusters.yaml` — indice dei cluster con metadata
- `docs/logic-catalog/system-overview.md` — visione d'insieme del sistema

## Note

- Pilot test obbligatorio con 1 cluster — non saltarlo
- Gli agenti usano SOLO il Write tool (il parent fetcha i dati via Bash)
- La conferma cluster e' obbligatoria — i cluster vengono mostrati prima del build
- Per aggiornare un singolo cluster: ri-esegui indicando il cluster specifico
- Il catalogo puo' diventare stale — ri-esegui dopo modifiche significative ai repo
- Se SYSTEM_MAP.md e' stale: ri-esegui `/forge-sysmap` prima di questo comando
