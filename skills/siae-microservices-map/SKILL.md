---
name: siae-microservices-map
description: >
  Use when mapping a multi-repository microservices system (10+ repos). Trigger:
  "mappa SPORT", "sistema a microservizi", "dipendenze tra servizi", "chi chiama chi",
  "topologia sistema", /forge-sysmap, onboarding su sistema distribuito.
---

# SIAE Microservices Map — Mappa Sistemi Distribuiti Senza Allucinare

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗    ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║    ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║    ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝    ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝     ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝      ║
║              🗺️ DevForge · MICROSERVICES MAP                  ║
║         "Il codice si forgia. Il developer cresce."            ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Flexible | **Fase SDLC:** 1. Init & Setup

---

## ANTI-HALLUCINATION PROTOCOL — NON NEGOZIABILE

```
MAI SCRIVERE UNA RELAZIONE TRA SERVIZI SENZA CITARE IL FILE SORGENTE CHE LA PROVA.
SE NON HAI LETTO IL FILE, LA RELAZIONE NON ESISTE.
```

### Gerarchia Fonti (invariabile)

```
TIER 1 — Codice sorgente    feign client, RestTemplate, WebClient, HTTP calls
TIER 2 — Config runtime     application.yml, .env, docker-compose
TIER 3 — Infrastruttura     k8s manifests, terraform, service mesh config
TIER 4 — Contratti API      openapi.yaml, swagger.json
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VIETATO                     README, documentazione testuale, naming repo, memoria umana
```

### Confidence Tag Obbligatori

```
[CONFIRMED]      evidenza Tier 1 letta direttamente
[INFERRED]       evidenza Tier 2-4 — DEVI citare file:riga
[UNVERIFIED]     nessuna evidenza — visibile nel Gap Report, MAI rimosso
[FILE_NOT_FOUND] file non accessibile — blocca analisi quel repo
```

---

## GUARDRAIL ANTI-LAZY — VERIFICA FORMALE OBBLIGATORIA

<EXTREMELY-IMPORTANT>
Saltare uno step o dichiarare un risultato senza evidenza eseguita e' disonesta', non efficienza.
</EXTREMELY-IMPORTANT>

### Checklist di Completamento Step (obbligatoria)

Prima di passare da uno step al successivo, devi dichiarare esplicitamente:

```
STEP {N} COMPLETATO
Evidenza: {cosa hai eseguito / fetchato / letto}
Output prodotto: {cosa e' stato generato}
Repo processati: {N}/{totale}
Passaggio al Step {N+1}: SI
```

Se non puoi compilare questo blocco con dati reali → lo step NON e' completato.

### Tabella Anti-Lazy

| Pensiero | Realta' | Blocco |
|----------|---------|--------|
| "Ho capito il pattern, salto gli altri repo" | Ogni repo puo' avere un'eccezione. Il pattern non e' evidenza | Processa tutti i repo nel pattern |
| "I repo con nome simile fanno probabilmente la stessa cosa" | Il naming non e' architettura | Analizza ogni repo individualmente |
| "Posso inferire le relazioni dal contesto gia' raccolto" | L'inferenza e' allucinazione — ogni edge deve avere fonte propria | Fetch del file specifico per ogni edge |
| "Ho abbastanza dati per scrivere la mappa" | Abbastanza != completo. Cosa manca? Documenta i gap | Compila il Gap Report prima di scrivere la mappa |
| "Il subagent ha gia' coperto questo" | Hai letto l'output del subagent? Hai verificato che abbia processato TUTTI i file? | Leggi ogni scheda evidenza prima di aggregare |
| "Questo step e' troppo lento, lo semplifico" | La lentezza e' il costo dell'accuratezza. Non negoziabile | Esegui lo step completo o comunica il blocco all'utente |
| "Ho gia' fatto cose simili, so come va a finire" | Questa istanza puo' differire. Zero assunzioni da esperienze passate | Esegui ogni step su questo sistema specifico |

### Verifica Formale Prima del Gap Report

Prima di scrivere il Gap Report (Step 4), rispondi obbligatoriamente a queste domande:

```
VERIFICA PRE-GAP-REPORT
1. Quanti repo erano nel pattern? ___
2. Quanti repo hanno prodotto una scheda evidenza? ___
3. Quanti repo hanno FILE_NOT_FOUND su tutti i file? ___
4. Quanti edge sono stati marcati UNVERIFIED? ___
5. Ci sono topic Kafka senza publisher o consumer verificato? ___
6. Ci sono URL in chiamate REST non risolti a un repo noto? ___
```

Se la risposta a 1 != risposta a (2+3) → ci sono repo non processati. Torna allo Step 3.

```
REQUIRED SUB-SKILL: siae-verification
```

Prima di dichiarare la mappa "completa" o "pronta", invoca `siae-verification`.

---

## Quando si Applica

**Sempre:**
- Mapping di un sistema a microservizi con 2+ repository
- Onboarding su sistema distribuito sconosciuto
- Necessita' di capire chi chiama chi, quali eventi circolano, quali DB esistono
- Richiesta `/forge-sysmap`

**Eccezioni (chiedi esplicitamente):**
- Un solo repo → usa `siae-codebase-map`
- Accesso GitHub non disponibile → STOP al Pre-flight (Step 1)

---

## Istruzioni

### Step 1 — PRE-FLIGHT: Verifica Accesso GitHub

🟢 SICURO

Prima di qualsiasi analisi, verifica che l'accesso sia disponibile.
**Se anche uno solo di questi check fallisce: STOP. Comunica il blocco all'utente con istruzioni recovery. NON procedere con dati parziali.**

```bash
# Check 1: GitHub token disponibile
gh auth status

# Check 2: Organizzazione raggiungibile (1 sola chiamata test)
gh api /orgs/{org}/repos?per_page=1

# Check 3: Chiedi all'utente se non fornito
# - Nome organizzazione GitHub (es. "itsiae")
# - Pattern repo (es. "sport-*")
```

Output atteso: conferma accesso + organizzazione + pattern prima di procedere.

---

### Step 2 — ENUMERATE: Inventario Completo

🟢 SICURO

```bash
# Lista tutti i repo dell'organizzazione con pattern
gh api /orgs/{org}/repos?per_page=100&type=all --paginate \
  | jq '[.[] | select(.name | startswith("{pattern}")) | {name, language, topics: .topics, archived, default_branch}]'
```

- **Escludi** repo `archived: true` → notifica all'utente con lista
- **Escludi** fork → notifica all'utente con lista
- **Output:** `inventory.json` con lista `{name, language, topics, archived, default_branch}`

---

### Step 3 — PROFILE + EXTRACT: Analisi Evidenze per Repo

🟡 MEDIO — Mostra pre-flight card prima di eseguire

```bash
echo '{
  "level": "MEDIO",
  "skill": "siae-microservices-map",
  "context": [
    {"emoji": "📦", "label": "Repo da analizzare", "value": "{N repo}"},
    {"emoji": "🏢", "label": "Organizzazione", "value": "{org}"},
    {"emoji": "🔍", "label": "Pattern", "value": "{pattern}"}
  ],
  "actions": [
    {"emoji": "🌐", "label": "Fetch file evidenza per ogni repo", "path": "GitHub API"},
    {"emoji": "🤖", "label": "Dispatch subagent paralleli", "path": "1 subagent per repo"}
  ],
  "reason": "Lettura file da N repository remoti",
  "ifno": "Analisi non eseguita, mappa non generata"
}' | python3 design-system/generate-card.py
```

#### 3a — PROFILE: Verifica Esistenza File Evidenza

Per ogni repo, controlla quali file evidenza esistono **prima di fetcharli**:

```
manifest:   pom.xml | build.gradle | package.json | requirements.txt | pyproject.toml
config:     src/main/resources/application.yml | application.properties | application-*.yml
infra:      docker-compose.yml | k8s/*.yaml | terraform/*.tf | .env.example
api:        openapi.yaml | swagger.yaml | api-docs.json | src/main/resources/static/openapi*
```

Usa GitHub API per HEAD check (non scaricare il file se non esiste):
```bash
gh api /repos/{org}/{repo}/contents/{path} --jq '.name' 2>/dev/null
```

Output: per ogni repo → lista file da fetchare (solo esistenti).

#### 3b — EXTRACT: Setup Output Directory e Pre-fetch Dati

**ANTI-CONTEXT-OVERFLOW — OBBLIGATORIO.**
Il **parent** pre-fetcha TUTTI i dati via Bash. I subagent ricevono i dati inline nel prompt
e usano SOLO il Write tool. I subagent NON usano Bash. NON chiamano `gh api`.

```bash
# Crea la directory di raccolta evidenze PRIMA di qualsiasi fetch
OUTPUT_DIR="/tmp/siae-sysmap-$(date +%Y%m%d%H%M%S)"
mkdir -p "$OUTPUT_DIR"
echo "Evidence dir: $OUTPUT_DIR"
```

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

#### 3c — EXTRACT: Pilot Test (OBBLIGATORIO su sistemi con 5+ repo)

Prima del full run, verifica il pattern con 2 repo:

1. Pre-fetcha i dati per i **primi 2 repo** usando i comandi in 3b (parent, via Bash)
2. Dispatcha **2 subagent** con i dati già inline nel prompt + istruzione ISTRUZIONE CRITICA
3. Attendi che completino e verifica:
   ```bash
   ls -la "$OUTPUT_DIR/"             # devono esistere 2 file .yaml
   cat "$OUTPUT_DIR/{repo-1}.yaml"   # YAML valido e leggibile
   ```
4. Se i file esistono e sono leggibili → **procedi al full run (Step 3d)**
5. Se i file NON esistono → l'agente non ha usato il Write tool → rivedi istruzioni, STOP e diagnostica

**Non saltare il pilot.** Il costo è 2 agenti. Il risparmio è non perdere 42 agenti.

#### 3d — EXTRACT: Dispatch Subagent Paralleli (Full Run)

**FULL RUN SEMPRE** — non chiedere mai all'utente se fare campione o run completa.
Tutti i repo enumerati devono essere processati. Nessuna eccezione.

**Token budget per subagent: 50.000 token** (margine sicuro per file evidenza mirati).
I file di evidenza sono piccoli (pom.xml, application.yml, feign client); 50k è abbondante
per leggere 5-10 file per repo. Se un singolo file supera il budget → tronca e nota il gap.

**Dispatcha TUTTI i subagent in un singolo blocco parallelo** (1 per repo).

Ogni subagent riceve i file pre-fetchati del suo repo inline nel prompt e produce una **scheda evidenza strutturata**.

**⚠️ ISTRUZIONE CRITICA DA INCLUDERE IN OGNI SUBAGENT (copia verbatim):**

```
Hai già tutti i dati necessari nel prompt. NON usare Bash. NON usare gh api. Usa SOLO il Write tool.

  1. Analizza i dati forniti e compila la scheda evidenza YAML (formato sotto).
  2. Applica il protocollo bias da conferma per ogni edge: quale file? quale riga?
     Se non puoi rispondere → confidence: INFERRED o UNVERIFIED.
  3. Scrivi la scheda in: {OUTPUT_DIR}/{repo-name}.yaml  (usa il Write tool)
  4. Rispondi con UNA SOLA RIGA: "✅ {repo-name} salvato in {OUTPUT_DIR}/{repo-name}.yaml"
  5. NON includere il contenuto YAML nel tuo output testuale.
     Il YAML va SOLO nel file — mai nel corpo della risposta.
```

Il parent non ingestisce l'analisi: riceve solo la riga di conferma (~50 token).
Con 42 agenti: 42 × 50 token = 2.1k token nel parent (invece di ~210k → context overflow).

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

**Protocollo bias da conferma** — ogni subagent DEVE rispondere prima di scrivere un edge:
1. Quale file contiene questa evidenza?
2. Ho letto quel file, o sto assumendo che esista?
3. L'evidenza e' diretta (codice) o indiretta (config → URL)?

Se non si risponde alla domanda 1 con un path preciso → `[UNVERIFIED]`.

---

### Step 3e — COLLECT: Raccogli Evidence Files

🟢 SICURO

Dopo che **tutti** i subagent hanno completato:

```bash
# Conta i file salvati — deve corrispondere al numero di repo
ls "$OUTPUT_DIR"/*.yaml | wc -l

# Lista file per verifica rapida
ls -la "$OUTPUT_DIR"/*.yaml
```

**Se il conteggio non corrisponde:**
- Identifica quali repo mancano (confronta lista repo con file in OUTPUT_DIR)
- Re-dispatcha SOLO i repo mancanti (singolo agente per ognuno)
- NON rieseguire repo già presenti

Procedi a Step 4 leggendo i file YAML uno per uno con il Read tool.

---

### Step 4 — CROSS-REF: Costruzione Grafo

🟢 SICURO

Aggrega tutte le schede evidenza:

1. **Risoluzione URL → repo**: mappa `http://sport-anagrafe` → `itsiae/sport-anagrafe`
   - Cerca corrispondenze esatte nel nome repo
   - Cerca in config centrali (es. API Gateway, Consul, Eureka)
   - Se non risolto → edge marcato `[UNVERIFIED]` con URL originale

2. **Costruzione grafo**: ogni edge = `(source_repo, target_repo, tipo, confidence, source_file:riga)`

3. **Kafka topology**: aggrega `publishes` e `consumes` per topic
   - Un topic senza consumer noto → `[UNVERIFIED consumer]`
   - Un topic senza publisher noto → `[UNVERIFIED publisher]`

4. **Gap report**: tutti gli `[UNVERIFIED]` e `[FILE_NOT_FOUND]` — **MAI rimossi o nascosti**

---

### Step 5 — OUTPUT: Scrivi `docs/SYSTEM_MAP.md`

🟡 MEDIO — Mostra pre-flight card prima di scrivere

```bash
echo '{
  "level": "MEDIO",
  "skill": "siae-microservices-map",
  "context": [
    {"emoji": "📊", "label": "Repo mappati", "value": "{N}/{total}"},
    {"emoji": "🔗", "label": "Edge confermati", "value": "{N}"},
    {"emoji": "⚠️", "label": "Edge UNVERIFIED", "value": "{N}"}
  ],
  "actions": [
    {"emoji": "📝", "label": "Scrittura SYSTEM_MAP.md", "path": "docs/SYSTEM_MAP.md"}
  ],
  "reason": "Creazione file documentazione architettura sistema",
  "ifno": "Mappa presentata solo in chat — copiare manualmente"
}' | python3 design-system/generate-card.py
```

Struttura del file output → vedi [reference/system-map-template.md](reference/system-map-template.md)

Sezioni obbligatorie:
- Frontmatter YAML (metadata: data, org, pattern, repo count, unverified count)
- Warning anti-hallucination visibile in cima
- C4 System Context (Mermaid)
- C4 Container Diagram con confidence tag su ogni `Rel()`
- Dependency Graph tabellare (From | To | Tipo | Confidence | Fonte)
- Kafka Topic Map
- Database Inventory
- Service Inventory
- **Gap Report** — relazioni non verificate, obbligatorio anche se vuoto
- Evidence Index — path file sorgente per ogni relazione confermata

---

## Tabella Anti-Razionalizzazione

| Pensiero | Realta' |
|----------|---------|
| "Dal nome del servizio si capisce che chiama X" | Il nome non e' evidenza. Servizi rinominati, naming storico, omonimie. Cerca il Feign client. Se non c'e' → `[UNVERIFIED]` |
| "Probabilmente usa Kafka perche' e' un sistema eventi" | "Probabilmente" e' un'allucinazione pianificata. Cerca `@KafkaListener`. Se non c'e' → `[UNVERIFIED]` |
| "Il README dice che si integra con Y" | I README sono documentazione aspirazionale, non contratti. Solo codice e config sono fonti valide |
| "Mi sembra che questo servizio sia il gateway" | "Mi sembra" e' bias di conferma. Verifica `spring.cloud.gateway.*` o `@EnableZuulProxy`. Evidenza o niente |
| "Ho gia' visto sistemi simili, di solito hanno..." | Pattern di altri sistemi != evidenza di questo sistema. Analizza questo repo, non i tuoi ricordi |
| "Non trovo il file, ma quasi certamente esiste" | Non trovare = non esiste o non accessibile. Marca esplicitamente: `[FILE_NOT_FOUND]` |
| "Aggregando piu' repo posso inferire la topologia" | L'inferenza aggregata amplifica gli errori. Ogni edge del grafo deve avere una fonte atomica |
| "Sono sicuro che questi due servizi comunicano" | La certezza non e' evidenza. Quale file, quale riga? Se non puoi rispondere → `[UNVERIFIED]` |
| "E' ovvio che il servizio X gestisce Y dal contesto del dominio" | Il contesto di dominio non e' codice. Zero assunzioni da semantica del nome |
| "Mettere [UNVERIFIED] fa sembrare la mappa incompleta" | La mappa e' piu' utile con i gap espliciti che con le relazioni inventate. I gap sono informazione |
| "Faccio un campione per velocizzare" | FULL RUN sempre. Il campione crea false certezze su un sistema parziale |

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|-----------|---------|------|
| Verifica accesso GitHub (auth status) | 🟢 Sicuro | No |
| Enumerazione repo (API read-only) | 🟢 Sicuro | No |
| Profile check esistenza file (HEAD) | 🟢 Sicuro | No |
| Fetch file evidenza + dispatch subagent | 🟡 Medio | Si |
| Scrittura docs/SYSTEM_MAP.md | 🟡 Medio | Si |

---

## Vincoli

1. **NON** scrivere relazioni senza citare file sorgente + riga
2. **NON** usare README, documentazione testuale o naming del repo come fonte
3. **NON** rimuovere o nascondere gap e relazioni `[UNVERIFIED]` dall'output
4. **NON** procedere se il Pre-flight GitHub fallisce — comunicare il blocco e fermarsi
5. **SEMPRE** includere il Gap Report nel file output, anche se vuoto
6. **SEMPRE** applicare confidence tag a ogni edge nel grafo
7. **SEMPRE** dispatching subagent in parallelo (un blocco unico) — mai sequenziale
8. **PRE-FLIGHT OBBLIGATORIA** per operazioni con rischio >= 🟡 — genera con `design-system/generate-card.py`

---

## Step Successivo — Profilazione Logica (opzionale)

Dopo aver generato `SYSTEM_MAP.md`, puoi approfondire cosa fa ogni servizio:

```
REQUIRED SUB-SKILL: siae-service-logic-map
```

`siae-service-logic-map` profila domain, entity, workflow e business rule per ogni servizio
mappato, costruendo il catalogo L1+L2+L3 a partire dal `SYSTEM_MAP.md` prodotto da questa skill.

---

## Risorse Aggiuntive

- [reference/system-map-template.md](reference/system-map-template.md) — Template completo SYSTEM_MAP.md
- [reference/evidence-patterns.md](reference/evidence-patterns.md) — Pattern per stack Java/Spring Boot, Node.js, Python
- Design doc: `docs/plans/2026-03-07-microservices-map-design.md`
