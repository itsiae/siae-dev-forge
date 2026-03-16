# SIAE Service Logic Map — Template e Esempi Output

## Table of Contents

- [Template Cluster Output](#template-cluster-output)
- [Template clusters.yaml](#template-clustersyaml)
- [Pre-fetch Dati per Cluster](#pre-fetch-dati-per-cluster)
- [Istruzione Critica Agenti](#istruzione-critica-agenti)
- [Esempio Query Output](#esempio-query-output)

---

## Template Cluster Output

**`docs/logic-catalog/cluster-{nome}.md`** — documento tecnico-funzionale del cluster:

```markdown
# Cluster: {nome}

Servizi: {lista repo}
Dominio: {dominio funzionale} [CONFIRMED] docs/SYSTEM_MAP.md

## {repo-1}

### L1 — Domain Profile
- Domain: {nome dominio} [CONFIRMED] {Entity.java:riga}
- Entities: {ClassName1}, {ClassName2} [CONFIRMED] {Entity.java:riga}
- Exposes: {/api/v1/...} [CONFIRMED] {openapi.yaml:riga}

### L2 — Workflow Map
- {nomeMetodo}(): trigger=REST [CONFIRMED] {Service.java:riga}
- {nomeScheduled}(): trigger=SCHEDULED [CONFIRMED] {Scheduler.java:riga}

### L3 — Business Rules
- {nomeMetodo}(): regola={condizione dominio} [CONFIRMED] {Service.java:riga}
- Drools: KieSession.fireAllRules() [CONFIRMED] {Service.java:riga} → {rules.drl}
- {NomeRepository}: @Query("...") [CONFIRMED] {Repository.java:riga}

## {repo-2}
...

## Gap Report
- [FILE_NOT_FOUND] {repo}: Service.java non trovato
```

---

## Template clusters.yaml

Il parent scrive `docs/logic-catalog/clusters.yaml`:

```yaml
generated_at: YYYY-MM-DDTHH:MM:SSZ
source: docs/SYSTEM_MAP.md
clusters:
  - name: "{cluster-name}"
    services: ["{repo1}", "{repo2}"]
    domain: "{dominio funzionale — da cluster-{nome}.md}"
    confidence: CONFIRMED | INFERRED
```

E `docs/logic-catalog/system-overview.md` con la visione d'insieme di tutti i cluster.

---

## Pre-fetch Dati per Cluster

Per ogni cluster, pre-fetcha i dati di TUTTI i repo del cluster prima di dispatchar l'agente:

```bash
# Per ogni repo nel cluster:

# 1. File tree per trovare *Service.java, *Entity.java, openapi*.yaml
gh api "/repos/itsiae/{repo}/git/trees/HEAD?recursive=1" \
  --jq '[.tree[].path | select(test("Service\\.java$|Entity\\.java$|Controller\\.java$|openapi.*\\.ya?ml$|Scheduler\\.java$"))] | .[0:20]'

# 2. Per ogni *Service.java: solo metodi public (firme, non body)
gh api /repos/itsiae/{repo}/contents/{path} --jq '.content' | base64 -d \
  | grep -E "^\s+(public|@Transactional|@Scheduled|@KafkaListener)"

# 3. openapi*.yaml (se esiste): prime 100 righe
gh api /repos/itsiae/{repo}/contents/{openapi-path} --jq '.content' | base64 -d | head -100

# 4. Pre-fetch L3 — Business Rules (per ogni *Service.java)
#    Grep snippet: KieSession/Drools, condizioni dominio, @Query
gh api /repos/itsiae/{repo}/contents/{ServiceFile} --jq '.content' | base64 -d \
  | grep -n "KieSession\|fireAllRules\|@Query\|@NamedQuery\|if.*[Ss]tato\|if.*[Tt]ipo\|if.*[Cc]ategoria" -A3 -B1

# 5. Pre-fetch L3 — Repository e DRL files (se esistono nel tree scan)
gh api /repos/itsiae/{repo}/contents/{RepositoryFile} --jq '.content' | base64 -d \
  | grep -n "@Query\|@NamedQuery\|@EntityGraph" -A2
```

**Regola critica:** il parent pre-fetcha SEMPRE via Bash. Gli agenti ricevono i dati inline — non hanno permesso di usare Bash autonomamente.

---

## Istruzione Critica Agenti

**ISTRUZIONE CRITICA DA INCLUDERE IN OGNI AGENTE:**

```
Hai tutti i dati nel prompt per il cluster {nome} ({lista servizi}).
NON usare Bash. Usa SOLO il Write tool.
1. Analizza i dati e compila la doc L1+L2+L3 per ogni servizio del cluster
   - L3 usa i snippet grep ricevuti inline: sezione "Business Rules"
   - Se snippet grep vuoto per un repo → [UNVERIFIED] nessun pattern L3 trovato
   (formato: reference/logic-catalog-template.yaml)
2. Scrivi in: docs/logic-catalog/cluster-{nome}.md
3. Rispondi con UNA SOLA RIGA: "OK cluster-{nome} salvato"
4. NON includere Markdown nel corpo della risposta
```

---

## Esempio Query Output

Output atteso dal comando `/forge-logic-search`:

Tabella con colonne `cluster | servizio | layer | campo | valore | source`

| cluster | servizio | layer | campo | valore | source |
|---------|----------|-------|-------|--------|--------|
| cluster-abbonamenti | sport-gestione-abbonamento | l2.workflow | name | calcolaPreventivo | `[CONFIRMED]` GestioneAbbonamentoService.java:45 |
| cluster-abbonamenti | sport-contabilita | l2.workflow | name | elaboraPreventivo | `[CONFIRMED]` ContabilitaService.java:12 |
