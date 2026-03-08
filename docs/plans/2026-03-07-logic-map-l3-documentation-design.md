# Logic Map L3 + Documentation Integration — Design

> **Stato:** Approvato
> **Data:** 2026-03-07
> **Branch:** feature/service-logic-map-skill (PR #46)

## Contesto

`siae-service-logic-map` genera attualmente L1 (domain profile) e L2 (workflow map)
per cluster di microservizi. Il catalogo si ferma alle firme dei metodi pubblici.

Due gap da colmare:
1. L3 mancante — nessuna visibilità su regole business, Drools, query DB
2. Il catalogo generato non viene ulteriormente elaborato in documentazione formale

## Goal

Aggiungere L3 al flusso `/forge-logic-build` (sempre incluso, non opzionale)
e aggiungere un Step 5 che esegue automaticamente `siae-documentation` sui
cluster-*.md generati.

## Decisioni

- **L3 sempre incluso**: non flag opzionale — `/forge-logic-build` produce sempre L1+L2+L3
- **Pattern focused per L3**: grep su pattern specifici (non body completo) per rispettare
  l'anti-context-overflow. Il parent pre-fetcha snippet, non file interi.
- **siae-documentation automatico**: non proposto, eseguito come Step 5 obbligatorio

## Architettura

### L3 — Business Rules (aggiunto al Step 4)

Il parent pre-fetcha un quarto blocco dati per ogni repo:

```bash
# File target L3
gh api repos/itsiae/{repo}/git/trees/HEAD --recursive \
  | jq '[.[] | .path | select(test("Repository\\.java$|\\.drl$|Rule\\.java$"))]'

# Snippet business rules da Service.java (grep con contesto)
# Pattern: KieSession, fireAllRules, if.*stato/tipo/categoria, @Query, @NamedQuery
gh api repos/itsiae/{repo}/contents/{ServiceFile} \
  | jq -r '.content | @base64d' \
  | grep -n "KieSession\|fireAllRules\|@Query\|if.*stato\|if.*tipo\|if.*categoria" -A3 -B1
```

Gli agenti scrivono una sezione L3 nel cluster-*.md:

```markdown
### L3 — Business Rules

- {nomeMetodo}(): regola={if statoFascicolo == DIFFIDA → inviaNotifica()}
  [CONFIRMED] FascicoloService.java:142
- Drools: KieSession.fireAllRules() [CONFIRMED] FascicoloService.java:87
  → resources/rules/tariffe.drl [CONFIRMED] tree scan
- {EntityRepository}: @Query("SELECT f FROM Fascicolo f WHERE f.stato = :stato")
  [CONFIRMED] FascicoloRepository.java:34
```

### Step 5 — POST-BUILD: siae-documentation (nuovo)

Dopo COLLECT (verifica cluster-*.md scritti), il flusso esegue:

```
REQUIRED SUB-SKILL: siae-documentation
Input: docs/logic-catalog/cluster-*.md + clusters.yaml
Scope: documentazione tecnica del sistema (system-overview enriched, API guide per cluster)
```

Non viene proposto all'utente — è parte obbligatoria del build.

### Flusso completo aggiornato

```
Step 0 → Discovery SYSTEM_MAP.md (o auto-generate via siae-microservices-map)
Step 1 → PRE-FLIGHT (gh auth status)
Step 2 → ENUMERATE + disambiguazione semantica
Step 3 → CLUSTER DETECTION dal grafo + conferma utente
Step 4 → PRE-FETCH L1+L2+L3 → PILOT (1 cluster) → DISPATCH → COLLECT
Step 5 → siae-documentation su docs/logic-catalog/  ← NUOVO
```

## Template cluster-*.md aggiornato

```markdown
## {repo}

### L1 — Domain Profile
- Domain: ... [CONFIRMED] Entity.java:N
- Entities: ... [CONFIRMED] Entity.java:N
- Exposes: ... [CONFIRMED] openapi.yaml:N

### L2 — Workflow Map
- {metodo}(): trigger=REST|KAFKA|SCHEDULED [CONFIRMED] Service.java:N

### L3 — Business Rules
- {metodo}(): regola={condizione} [CONFIRMED] Service.java:N
- Drools: ... [CONFIRMED] Service.java:N → rules/*.drl
- {Repository}: @Query(...) [CONFIRMED] Repository.java:N

### Gap Report
- [FILE_NOT_FOUND] se Repository.java non trovato
- [UNVERIFIED] se nessun pattern L3 trovato
```

## File da modificare

- `skills/siae-service-logic-map/SKILL.md` — aggiungere pre-fetch L3 in Step 4, Step 5 post-build
- `skills/siae-service-logic-map/reference/logic-catalog-template.yaml` — aggiungere sezione L3
- `commands/forge-logic-build.md` — aggiornare comportamento con Step 5

## Stima SP

**SP: 3** — Moderato. Le modifiche sono localizzate e il pattern è già consolidato.
Rischio: i grep L3 potrebbero restituire 0 risultati su servizi senza Drools (gestito con Gap Report).

## Criteri di Accettazione

- [ ] `/forge-logic-build` produce sempre sezione L3 nei cluster-*.md
- [ ] L3 contiene almeno uno tra: regole Drools, condizioni if di dominio, @Query
- [ ] Se nessun pattern L3 trovato, il Gap Report riporta `[UNVERIFIED] nessun pattern L3 trovato`
- [ ] Dopo COLLECT, siae-documentation viene eseguito automaticamente
- [ ] Il template `logic-catalog-template.yaml` include la sezione L3
