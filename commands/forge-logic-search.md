---
name: forge-logic-search
description: Cerca un concetto o workflow nel catalogo L1+L2 costruito da forge-logic-build. Risponde a "quali servizi gestiscono X?" e "cosa fa sport-Y?". Richiede che forge-logic-build sia stato eseguito almeno una volta.
---

# /forge-logic-search

Cerca nel catalogo `docs/logic-catalog/` costruito da `/forge-logic-build`.

## Utilizzo

```
/forge-logic-search preventivo
/forge-logic-search "calcolo abbonamento"
/forge-logic-search sport-gestione-abbonamento
/forge-logic-search rinnovo
```

## Comportamento

1. Verifica che `docs/logic-catalog/` esista e contenga file YAML
2. Cerca il keyword nel catalogo (case-insensitive, su tutti i campi)
3. Per ogni match: mostra repo, layer (l1/l2), campo, valore, source
4. Ordina per rilevanza (match in l2.workflows.name > l1.domain > altri campi)

## Output esempio

```
Keyword: "preventivo"

| Servizio | Layer | Campo | Valore | Source |
|---|---|---|---|---|
| sport-gestione-abbonamento | l2.workflow | name | calcolaPreventivo | GestioneAbbonamentoService.java:45 |
| sport-contabilita | l2.workflow | name | elaboraPreventivo | ContabilitaService.java:12 |
| sport-gestione-abbonamento | l1.exposes | path | /api/mda/accentramento/calcolaPreventivo | openapi/sport-gestione-abbonamento.yaml:8 |

3 servizi trovati per "preventivo"
```

## Se il catalogo non esiste

```
Il catalogo docs/logic-catalog/ non esiste o e' vuoto.
Esegui prima: /forge-logic-build
```

## Note

- La ricerca e' sul catalogo locale — puo' essere stale se i repo sono cambiati
- Per cercare un singolo servizio: `/forge-logic-search sport-{nome-servizio}`
- Per cercare un concetto di dominio: `/forge-logic-search {keyword-italiano}`
- I risultati mostrano confidence tag: [CONFIRMED] / [INFERRED] / [UNVERIFIED]
