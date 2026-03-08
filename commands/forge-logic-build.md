---
name: forge-logic-build
description: Costruisce il catalogo L1+L2+L3 (domain profile + workflow map + business rules) per cluster di microservizi. Flusso automatico a comando singolo — trova o genera SYSTEM_MAP.md, detecta cluster, pre-fetcha dati L1+L2+L3, dispatcha agenti, esegue siae-documentation post-build. Prerequisiti: gh auth; pattern repo GitHub.
---

# /forge-logic-build

Invoca la skill `siae-service-logic-map` per costruire il catalogo domain profile (L1),
workflow map (L2) e business rules (L3) di tutti i microservizi, organizzati per cluster funzionale.

## Utilizzo

```
/forge-logic-build
/forge-logic-build org=itsiae pattern=sport-*
```

## Prerequisiti

- `gh auth status` deve passare
- Accesso all'organizzazione GitHub
- `docs/SYSTEM_MAP.md` — se non esiste viene generato automaticamente

## Comportamento

Flusso automatico a comando singolo — non serve eseguire `/forge-sysmap` prima:

1. **SYSTEM_MAP.md DISCOVERY** — Cerca il file in `docs/`, `docs/systems/*/`, `/tmp/siae-sysmap-*/`
   - Trovato → usa quello piu' recente
   - Non trovato → esegue `siae-microservices-map` automaticamente sul pattern specificato,
     poi continua senza commit intermedio
2. **PRE-FLIGHT** — Verifica accesso GitHub (`gh auth status`)
3. **ENUMERATE** — Lista tutti i repo con il pattern (con disambiguazione se nome semantico)
4. **CLUSTER DETECTION** — Legge SYSTEM_MAP.md, estrae cluster dal grafo,
   propone cluster all'utente per conferma prima di procedere
5. **PRE-FETCH** — Il parent fetcha i dati di tutti i repo per cluster via `gh api`:
   - File tree → identifica `*Service.java`, `*Entity.java`, `openapi*.yaml`
   - Contenuto file → firma metodi public, @Transactional, @Scheduled, @KafkaListener
   - Snippet L3 → grep KieSession, fireAllRules, @Query, condizioni if di dominio
6. **PILOT TEST** — Verifica il pattern con 1 cluster (il piu' piccolo) prima del full run
7. **DISPATCH** — Agenti paralleli (1 per cluster) con dati inline, usano solo Write tool
8. **COLLECT** — Verifica file cluster scritti, genera `clusters.yaml` e `system-overview.md`
9. **POST-BUILD** — Esegue siae-documentation sui cluster-*.md generati (step obbligatorio, non opzionale)

## Output

- `docs/logic-catalog/cluster-{nome}.md` per ogni cluster — doc tecnica L1+L2
- Ogni cluster-{nome}.md include sezione L3 — Business Rules (Drools, @Query, condizioni dominio)
- `docs/logic-catalog/clusters.yaml` — indice dei cluster con metadata
- `docs/logic-catalog/system-overview.md` — visione d'insieme del sistema

## Note

- Pilot test obbligatorio con 1 cluster — non saltarlo
- Gli agenti usano SOLO il Write tool (il parent fetcha i dati via Bash)
- La conferma cluster e' obbligatoria — i cluster vengono mostrati prima del build
- Per aggiornare un singolo cluster: ri-esegui indicando il cluster specifico
- Il catalogo puo' diventare stale — ri-esegui dopo modifiche significative ai repo
- Se SYSTEM_MAP.md e' stale: ri-esegui `/forge-sysmap` prima di questo comando
