# SIAE Microservices Map — Template e Esempi Output

## Table of Contents

- [Scheda Evidenza YAML](#scheda-evidenza-yaml)
- [Istruzione Critica Subagent](#istruzione-critica-subagent)
- [Protocollo Bias da Conferma](#protocollo-bias-da-conferma)
- [Pre-fetch Dati per Repo](#pre-fetch-dati-per-repo)
- [Pilot Test Procedura](#pilot-test-procedura)
- [Template Dispatch Subagent](#template-dispatch-subagent)
- [Sezioni Obbligatorie SYSTEM_MAP.md](#sezioni-obbligatorie-system_mapmd)

---

## Scheda Evidenza YAML

Ogni subagent produce una scheda evidenza strutturata per il suo repo:

```yaml
repo: sport-anagrafe
stack: java-spring-boot        # rilevato da manifest
confidence: CONFIRMED          # almeno Tier 1 trovato, oppure INFERRED/FILE_NOT_FOUND

exposes:
  - path: /api/v1/autori
    method: GET
    source: openapi.yaml:12    # SEMPRE file:riga

calls:
  - target_url: "http://sport-diritti/api/v1/diritti"
    type: REST
    client: FeignClient
    source: src/main/java/.../DirittiClient.java:8
    confidence: CONFIRMED
  - target_url: "${sport.gestione.url}/eventi"
    type: REST
    client: RestTemplate
    source: application.yml:sport.gestione.url
    confidence: INFERRED       # URL in variabile, non hardcoded

events:
  publishes:
    - topic: autori.creato
      source: AutoreService.java:45
      confidence: CONFIRMED
  consumes:
    - topic: diritti.aggiornato
      source: application.yml:spring.kafka.consumer.topics
      confidence: CONFIRMED

databases:
  - type: PostgreSQL
    name: sport_anagrafe_db
    source: application.yml:spring.datasource.url
    confidence: INFERRED

gaps:
  - "Nessun file k8s trovato — deployment topology sconosciuta"
  - "application-prod.yml non accessibile — config prod non verificata"
```

---

## Istruzione Critica Subagent

**ISTRUZIONE CRITICA DA INCLUDERE IN OGNI SUBAGENT (copia verbatim):**

```
Hai gia' tutti i dati necessari nel prompt. NON usare Bash. NON usare gh api. Usa SOLO il Write tool.

  1. Analizza i dati forniti e compila la scheda evidenza YAML (formato sotto).
  2. Applica il protocollo bias da conferma per ogni edge: quale file? quale riga?
     Se non puoi rispondere → confidence: INFERRED o UNVERIFIED.
  3. Scrivi la scheda in: {OUTPUT_DIR}/{repo-name}.yaml  (usa il Write tool)
  4. Rispondi con UNA SOLA RIGA: "OK {repo-name} salvato in {OUTPUT_DIR}/{repo-name}.yaml"
  5. NON includere il contenuto YAML nel tuo output testuale.
     Il YAML va SOLO nel file — mai nel corpo della risposta.
```

Il parent non ingestisce l'analisi: riceve solo la riga di conferma (~50 token).
Con 42 agenti: 42 x 50 token = 2.1k token nel parent (invece di ~210k → context overflow).

---

## Protocollo Bias da Conferma

Ogni subagent DEVE rispondere prima di scrivere un edge:
1. Quale file contiene questa evidenza?
2. Ho letto quel file, o sto assumendo che esista?
3. L'evidenza e' diretta (codice) o indiretta (config → URL)?

Se non si risponde alla domanda 1 con un path preciso → `[UNVERIFIED]`.

---

## Pre-fetch Dati per Repo

Per ogni repo, il parent pre-fetcha:
```bash
# 1. Manifest principale
gh api /repos/{org}/{repo}/contents/pom.xml --jq '.content' | base64 -d

# 2. File rilevanti (FeignClient, Kafka, config, datasource)
gh api "/repos/{org}/{repo}/git/trees/HEAD?recursive=1" \
  --jq '[.tree[].path | select(test("Client\\.java$|FeignClient|kafka|Kafka|datasource|application\\.yml|application\\.properties|openapi"))] | .[0:20]'

# 3. Contenuto di ogni file rilevante trovato
gh api /repos/{org}/{repo}/contents/{path} --jq '.content' | base64 -d
```

Salva `$OUTPUT_DIR` e tutti i dati pre-fetchati — li passerai inline nei prompt dei subagent.

---

## Pilot Test Procedura

Prima del full run, verifica il pattern con 2 repo (OBBLIGATORIO su sistemi con 5+ repo):

1. Pre-fetcha i dati per i **primi 2 repo** usando i comandi pre-fetch (parent, via Bash)
2. Dispatcha **2 subagent** con i dati gia' inline nel prompt + ISTRUZIONE CRITICA
3. Attendi che completino e verifica:
   ```bash
   ls -la "$OUTPUT_DIR/"             # devono esistere 2 file .yaml
   cat "$OUTPUT_DIR/{repo-1}.yaml"   # YAML valido e leggibile
   ```
4. Se i file esistono e sono leggibili → **procedi al full run**
5. Se i file NON esistono → l'agente non ha usato il Write tool → rivedi istruzioni, STOP e diagnostica

**Non saltare il pilot.** Il costo e' 2 agenti. Il risparmio e' non perdere 42 agenti.

---

## Template Dispatch Subagent

Usa il tool Agent con: `subagent_type: "general-purpose"`, `mode: "bypassPermissions"`, `run_in_background: true`.
Il prompt deve includere il testo della ISTRUZIONE CRITICA con i placeholder risolti.

**FULL RUN SEMPRE** — non chiedere mai all'utente se fare campione o run completa.
Tutti i repo enumerati devono essere processati. Nessuna eccezione.

**Token budget per subagent: 50.000 token** (margine sicuro per file evidenza mirati).
I file di evidenza sono piccoli (pom.xml, application.yml, feign client); 50k e' abbondante
per leggere 5-10 file per repo. Se un singolo file supera il budget → tronca e nota il gap.

**Dispatcha TUTTI i subagent in un singolo blocco parallelo** (1 per repo).

---

## Sezioni Obbligatorie SYSTEM_MAP.md

Struttura del file output → vedi [reference/system-map-template.md](reference/system-map-template.md)

Sezioni obbligatorie:
- Frontmatter YAML (metadata: data, org, pattern, repo count, unverified count)
- Warning anti-hallucination visibile in cima
- C4 System Context (PlantUML)
- C4 Container Diagram con confidence tag su ogni `Rel()`
- Dependency Graph tabellare (From | To | Tipo | Confidence | Fonte)
- Kafka Topic Map
- Database Inventory
- Service Inventory
- **Gap Report** — relazioni non verificate, obbligatorio anche se vuoto
- Evidence Index — path file sorgente per ogni relazione confermata
