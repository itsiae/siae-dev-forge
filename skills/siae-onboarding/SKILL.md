---
name: siae-onboarding
description: >
  Use at the start of any SIAE project session to establish project context.
  Trigger: inizio sessione, apertura nuovo progetto, cambio contesto.
user-invocable: false
---

```
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║      ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝      ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝       ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝        ║
║                                                                  ║
║              🔨  DevForge  ·  AI Competence Center               ║
║         "Il codice si forgia. Il developer cresce."              ║
╚══════════════════════════════════════════════════════════════════╝
```

# siae-onboarding

> **Tipo:** Auto | **Fase SDLC:** 1. Init & Setup
>
> Questa skill si attiva automaticamente all'inizio di ogni sessione Claude Code
> su un repository SIAE. Rileva factory, tech stack e regole di progetto, poi
> configura il contesto per tutte le skill successive.

---

## 1. Detection Logic

Esegui i controlli nell'ordine indicato. Il primo match determina lo stack primario.
Un progetto puo' avere piu' stack (es. monorepo con frontend + backend).

### 1.1 Controllo esplicito: `.siae-config.json`

Se presente nella root del progetto, leggi il file e usa i valori dichiarati:

```json
{
  "factory": "digital | core-platforms | data-platform | devops-infra",
  "stack": ["java", "ts-frontend", "ts-backend", "python", "iac"],
  "environments": ["sviluppo", "collaudo", "certificazione", "produzione"],
  "cicd": { "actionsRepo": "itsiae/siae-gh-actions", "actionsVersion": "v2.x" }
}
```

Se il file esiste, **salta la detection automatica** e vai alla sezione 2.

### 1.2 Detection automatica (fallback)

Esegui i probe in ordine. Raccogli TUTTI i match, non fermarti al primo.

| # | File / Pattern | Stack rilevato | Factory probabile |
|---|---------------|----------------|-------------------|
| 1 | `pom.xml` presente | **Java / Spring Boot** | Core Platforms / Digital |
| 2 | `package.json` con dipendenza `vue` | **TS Frontend** (Vue.js 3) | Digital |
| 3 | `package.json` con `express` o `serverless-http` | **TS Backend** (Lambda) | Digital |
| 4 | `requirements.txt` oppure `Makefile` con riferimento a Glue | **Python Data Engineering** | Data Platform |
| 5 | `terragrunt.hcl` oppure file `*.tf` | **IaC** (Terraform + Terragrunt) | DevOps/Infra |
| 6 | `config.yaml` con pattern Terragrunt (`terraform { source = ...}`) | **IaC** | DevOps/Infra |

### 1.3 Probe con tool nativi (permission-free)

Tutti i probe usano Glob, Read e Grep — **nessun Bash richiesto**.
Lancia tutti i probe in parallelo (chiamate multiple in un singolo messaggio).

| # | Probe | Tool |
|---|-------|------|
| 1 | Java / Spring Boot | `Glob("pom.xml")` — se trova risultati → DETECTED: java |
| 2 | TS Frontend (Vue.js) | `Glob("package.json")` + `Read(package.json)` → cerca `"vue"` nelle dipendenze → DETECTED: ts-frontend |
| 3 | TS Backend (Lambda) | `Read(package.json)` → cerca `"express"` o `"serverless-http"` → DETECTED: ts-backend |
| 4 | Python Data Engineering | `Glob("requirements.txt")` + `Grep("pyspark\|awsglue", "requirements.txt")` oppure `Glob("Makefile")` + `Grep("glue", "Makefile")` → DETECTED: python |
| 5 | IaC (Terraform / Terragrunt) | `Glob("terragrunt.hcl")` + `Glob("*.tf")` — se uno dei due trova risultati → DETECTED: iac |
| 6 | IaC via config.yaml | `Glob("config.yaml")` + `Grep("terraform", "config.yaml")` → DETECTED: iac |

**Nota:** i probe 2 e 3 condividono `package.json` — una singola `Read` basta per entrambi.

---

## 2. Regole per Stack

Per ogni stack rilevato, applica le regole corrispondenti.
Dettagli completi delle configurazioni factory in `reference/factory-configs.md`.

### 2.1 Java / Spring Boot

| Aspetto | Regola |
|---------|--------|
| **Build tool** | Maven (`mvn`). Parent POM: `it.siae:spring-boot-2-parent-pom` |
| **Framework** | Spring Boot 2.x |
| **Naming** | Package: `it.siae.<progetto>`. Classi: PascalCase. Metodi: camelCase |
| **Test framework** | JUnit 5 + Mockito. Coverage minima: definita nel POM |
| **Librerie standard** | MapStruct (mapping DTO), Lombok (boilerplate), Jackson (JSON) |
| **Deploy target** | OpenShift (Core Platforms) o ECS/Lambda (Digital) |
| **Static analysis** | Qodana con profilo SIAE |

### 2.2 TS Frontend (Vue.js 3)

| Aspetto | Regola |
|---------|--------|
| **Framework** | Vue.js 3 + Composition API (`<script setup>`) |
| **Build tool** | Vite |
| **Naming** | Componenti: PascalCase. Composables: `use<Nome>`. File: kebab-case |
| **Test framework** | Vitest. Copertura minima: **70%** |
| **Integrazioni** | Firebase (auth/hosting), Google Analytics |
| **Stile** | SCSS, design tokens SIAE |
| **Static analysis** | ESLint + Prettier. Qodana |

### 2.3 TS Backend (Lambda)

| Aspetto | Regola |
|---------|--------|
| **Runtime** | Node.js su AWS Lambda via `serverless-http` o API Gateway |
| **Framework** | Express.js |
| **ORM** | Drizzle ORM |
| **Build tool** | esbuild (bundling per Lambda) |
| **Naming** | Handlers: `<risorsa>.handler.ts`. Services: `<risorsa>.service.ts` |
| **Test framework** | Jest. Unit test obbligatori per ogni handler |
| **Deploy target** | AWS Lambda (tag-based deploy) |
| **Static analysis** | ESLint + Prettier. Qodana |

### 2.4 Python Data Engineering

| Aspetto | Regola |
|---------|--------|
| **Framework** | PySpark su AWS Glue |
| **Architettura dati** | Medallion: bronze (raw) -> silver (curated) |
| **Naming** | Moduli: snake_case. Classi: PascalCase. Job: `<dominio>_<azione>` |
| **Test framework** | pytest + pyspark testing utilities |
| **Orchestrazione** | AWS Step Functions |
| **Deploy target** | AWS Glue Jobs |
| **Static analysis** | Qodana, flake8, black |

### 2.5 IaC (Terraform + Terragrunt)

| Aspetto | Regola |
|---------|--------|
| **Tool** | Terraform + Terragrunt |
| **Struttura file** | `_input.tf` (variables), `_local.tf` (locals), `_output.tf` (outputs) |
| **Naming** | Risorse: snake_case. Moduli: kebab-case. Variabili: snake_case |
| **Validazione** | `terraform validate` + `terraform plan` obbligatori prima di apply |
| **Deploy target** | AWS multi-account |
| **Static analysis** | tflint, checkov, Qodana |

---

## 3. Regole Trasversali (tutti gli stack)

### 3.1 CI/CD

- **GitHub Actions**: workflow riutilizzabili da `itsiae/siae-gh-actions` (versione `v2.x`)
- **Deploy**: tag-based. Il push di un tag semantico (`v*.*.*`) triggera il deploy
- **Branch protection**: `main` protetto, PR obbligatoria con almeno 1 review
- **Pipeline tipica**: lint -> test -> build -> Qodana -> deploy (per ambiente)

### 3.2 Ambienti

| Ambiente | Scopo | Tag pattern |
|----------|-------|-------------|
| **sviluppo** | Sviluppo e test interni | `v*.*.*-dev.*` |
| **collaudo** | Test di integrazione | `v*.*.*-rc.*` |
| **certificazione** | UAT e validazione | `v*.*.*-cert.*` |
| **produzione** | Ambiente live | `v*.*.*` |

### 3.3 Static Analysis

- **Qodana**: obbligatorio su tutti i repository SIAE
- Profilo configurato nel file `.qodana.yaml` alla root del progetto
- I risultati Qodana bloccano la PR se il quality gate non e' superato

---

## 4. Welcome Message

Dopo la detection, mostra il seguente messaggio di benvenuto:

```
╔══════════════════════════════════════════════════════════════════╗
║  🔨 DevForge · Onboarding completato                             ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  📂 Progetto:     <nome directory>                               ║
║  🏭 Factory:      <factory rilevata>                             ║
║  🛠️  Stack:        <stack rilevato/i>                            ║
║  🌍 Ambienti:     sviluppo · collaudo · certificazione · prod    ║
║  🔄 CI/CD:        GitHub Actions (itsiae/siae-gh-actions v2.x)   ║
║  📊 Quality:      Qodana                                         ║
║                                                                  ║
╠══════════════════════════════════════════════════════════════════╣
║  Skill disponibili per questo stack:                             ║
║                                                                  ║
║  • siae-code-standards   Convenzioni codice per <stack>          ║
║  • siae-tdd              Test-driven development                 ║
║  • siae-git-workflow      Branch, merge, release                 ║
║  • siae-security          Security review                        ║
║  • <skill specifiche per stack rilevato>                         ║
║                                                                  ║
║  Digita /help per la lista completa dei comandi DevForge.        ║
╚══════════════════════════════════════════════════════════════════╝
```

**Dopo il welcome message**, controlla se la mappa architetturale esiste (permission-free):

1. `Glob("docs/CODEBASE_MAP.md")` — se trova risultati → mappa esiste, carica il sommario con `Read`
2. Se non esiste → conta i file sorgente in parallelo:
   - `Glob("**/*.java")`, `Glob("**/*.ts")`, `Glob("**/*.py")`, `Glob("**/*.tf")`
   - Somma i risultati per ottenere il conteggio totale

- Se `docs/CODEBASE_MAP.md` esiste → carica il sommario e mostralo nel welcome
- Se non esiste **e** il repo ha > 50 file sorgente → aggiungi al welcome:
  ```
  💡 Questo progetto non ha una mappa architetturale.
     Esegui /forge-map per generarla (subagent Sonnet, ~5 min).
  ```
- Se non esiste e il repo è piccolo (≤ 50 file) → nessun suggerimento

### 4.1 Incomplete Plan Detection

Dopo il welcome message, verifica se ci sono piani incompleti:

```bash
grep -l "\[PENDING\]\|\[BLOCKED\]" docs/plans/*-plan.md 2>/dev/null
```

**Se trovati**, per ogni piano incompleto conta gli stati:

```bash
grep -c "\[DONE\]" docs/plans/<file>.md
grep -c "\[PENDING\]" docs/plans/<file>.md
grep -c "\[BLOCKED\]" docs/plans/<file>.md
```

Mostra il seguente avviso:

```
⚠️  PIANI INCOMPLETI RILEVATI:
─────────────────────────────
📋 docs/plans/<filename>.md
   X [DONE] / Y [PENDING] / Z [BLOCKED]

Vuoi riprendere l'esecuzione (→ siae-executing-plans) o procedere con altro?
```

L'utente decide:
- **Riprendere** → invoca `siae-executing-plans` con il piano incompleto
- **Procedere con altro** → l'utente fornisce il motivo, si prosegue normalmente

Nessun blocco forzato — il reminder è **sempre** visibile ma non impedisce il lavoro.

Adatta le righe `Skill disponibili` in base allo stack rilevato:
- Java -> aggiungi `siae-architecture`
- TS Frontend -> aggiungi `siae-frontend`
- TS Backend -> aggiungi `siae-architecture`
- Python -> aggiungi `siae-data-engineering`
- IaC -> aggiungi `siae-iac`

Se lo stack non e' stato rilevato, mostra un avviso:

```
⚠️  Stack non rilevato automaticamente.
    Crea un file .siae-config.json nella root del progetto
    oppure indica manualmente il tipo di progetto.
```

---

## 5. Vincoli

1. **Non modificare mai file del progetto** durante l'onboarding. Questa skill e' di sola lettura.
2. **Non creare `.siae-config.json`** automaticamente — suggeriscilo se mancante, ma lascia la scelta all'utente.
3. **Non assumere lo stack** se nessun probe ha match. Chiedi conferma esplicita.
4. **Rispetta l'ordine dei probe**: il primo match in 1.2 determina la factory primaria, ma raccogli tutti i match per progetti multi-stack.
5. **Esegui l'onboarding una sola volta** per sessione, a meno che l'utente non cambi contesto esplicitamente.
6. **Rischio**: tutte le operazioni di questa skill sono 🟢 SICURO (sola lettura). Questa skill usa esclusivamente Glob, Read e Grep. Non richiede approvazione utente per nessuna operazione.
7. **Riferimento factory**: per le configurazioni dettagliate delle factory, consulta `reference/factory-configs.md`.

---

## Tabella Anti-Razionalizzazione

| Pensiero | Realta' |
|----------|---------|
| "Conosco gia' questo progetto, posso iniziare direttamente." | La codebase cambia tra una sessione e l'altra. Commit, PR, refactoring e nuove feature sono accaduti mentre non eri connesso. Saltare l'onboarding significa lavorare su un modello mentale obsoleto. |
| "CODEBASE_MAP.md e' documentazione, non e' critica per iniziare." | CODEBASE_MAP.md e' la fonte di verita' sull'architettura attuale. Senza leggerla, rischi di duplicare moduli esistenti, ignorare dependency critiche o violare pattern stabiliti dal team. |
| "Ho letto il codice una volta, ricordo la struttura." | La memoria della sessione precedente non e' affidabile per decisioni architetturali. Il progetto evolve. Leggere CODEBASE_MAP.md richiede 2 minuti. Correggere un'assunzione errata richiede ore. |
| "I design doc sono teorici, guardo direttamente il codice." | I design doc recenti (es. `docs/plans/`) contengono decisioni prese dopo l'ultimo deploy: ADR, vincoli tecnici, workaround noti. Il codice mostra il 'come', i design doc spiegano il 'perche''. |
| "L'onboarding rallenta il lavoro vero." | L'onboarding di questa skill e' sola lettura e richiede meno di 5 minuti. Iniziare senza contesto produce errori che impiegano ore a debuggare, PR rifiutate per violazioni di standard ignoti, e regressioni evitabili. |
| "Se c'e' un problema lo vedro' durante il test." | Alcuni errori contestuali (factory sbagliata, stack assumptions errate, ambiente target non identificato) non emergono nei test unitari. Emergono in produzione o nella PR review, quando il costo del fix e' massimo. |
| "La detection automatica e' opzionale se so gia' il progetto." | La detection popola il contesto per TUTTE le skill successive della sessione. Senza di essa, skill come siae-tdd, siae-security e siae-architecture operano senza sapere framework, test runner e standard di copertura applicabili a questo stack specifico. |

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|------------|---------|------|
| Lettura file di progetto (pom.xml, package.json, ...) | 🟢 Sicuro | No |
| Lettura `.siae-config.json` | 🟢 Sicuro | No |
| Mostra welcome message | 🟢 Sicuro | No |
| Suggerimento creazione `.siae-config.json` | 🟢 Sicuro | No |
