# siae-devforge

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗    ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║    ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║    ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝    ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝     ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝      ║
║              🔨 DevForge · AI Competence Center                ║
║         "Il codice si forgia. Il developer cresce."            ║
╚══════════════════════════════════════════════════════════════════╝
```

**siae-devforge** e' un plugin [Claude Code](https://docs.anthropic.com/en/docs/build-with-claude/claude-code) progettato per lo sviluppo software conforme agli standard SIAE. Copre l'intero ciclo di vita del software (SDLC) con 15 skill, 7 comandi, 3 agent e 2 hook, organizzati in una catena a 7 fasi.

> **Versione:** 1.0.0-mvp
> **Autore:** SIAE AI Competence Center
> **Licenza:** Proprietary

---

## Indice

- [Come Funziona](#come-funziona)
- [Installazione](#installazione)
- [La Catena SDLC a 7 Fasi](#la-catena-sdlc-a-7-fasi)
- [Comandi Disponibili](#comandi-disponibili)
- [Skill (15)](#skill-15)
  - [Meta-skill](#meta-skill)
  - [Skill di Processo](#skill-di-processo)
  - [Skill Tech-Specific](#skill-tech-specific)
- [Agent (3)](#agent-3)
- [Hook (2)](#hook-2)
- [Design System Visivo](#design-system-visivo)
- [Struttura del Repository](#struttura-del-repository)
- [Stack Supportati](#stack-supportati)
- [Integrazione Atlassian (MCP)](#integrazione-atlassian-mcp)
- [Architettura del Plugin](#architettura-del-plugin)
- [Come Contribuire](#come-contribuire)

---

## Come Funziona

siae-devforge e' un **plugin Claude Code** che agisce come "sistema operativo" per lo sviluppo in SIAE. Quando avvii Claude Code con il plugin attivo:

1. **All'avvio** — L'hook `SessionStart` inietta automaticamente la meta-skill `using-devforge`, che insegna a Claude come e quando usare tutte le altre skill
2. **Su ogni task** — Claude controlla se esiste una skill applicabile (con la regola dell'1%: se c'e' anche solo l'1% di possibilita' che una skill sia rilevante, la invoca)
3. **Catena SDLC** — Le skill sono organizzate in 7 fasi ordinate. Claude segue l'ordine corretto: non puo' scrivere codice senza aver fatto brainstorming, non puo' committare senza test
4. **Al commit** — L'hook `PreCommit` esegue un quality gate a 5 punti (secret scan, naming, test, file size, lint) prima di ogni commit

Il risultato: ogni interazione con Claude Code segue automaticamente gli standard SIAE senza che il developer debba ricordarli.

---

## Installazione

Il plugin e' privato e non e' disponibile nel marketplace pubblico. L'installazione avviene tramite un marketplace locale.

### Opzione A: Script automatico (raccomandato)

```bash
git clone git@github.com:itsiae/siae-dev-forge.git ~/git/siae-dev-forge
cd ~/git/siae-dev-forge
./install.sh
```

Lo script crea la struttura del marketplace locale, registra il plugin e lo installa in un unico passaggio. E' idempotente: puo' essere rieseguito senza problemi.

### Opzione B: Installazione manuale

**1. Clona il repository**

```bash
git clone git@github.com:itsiae/siae-devforge.git ~/git/siae-dev-forge
```

**2. Crea il marketplace locale**

```bash
mkdir -p ~/.claude/local-plugins/.claude-plugin
mkdir -p ~/.claude/local-plugins/plugins
ln -sf ~/git/siae-dev-forge ~/.claude/local-plugins/plugins/siae-devforge
```

**3. Crea il manifest del marketplace**

Crea il file `~/.claude/local-plugins/.claude-plugin/marketplace.json`:

```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "siae-local",
  "description": "SIAE private plugins marketplace",
  "owner": {
    "name": "SIAE AI Competence Center",
    "email": "ai-cc@siae.it"
  },
  "plugins": [
    {
      "name": "siae-devforge",
      "description": "SIAE Development Forge - AI SDLC Chain per sviluppo software conforme a standard SIAE. 13 skill, 5 comandi, 3 agent, 2 hook.",
      "version": "1.0.0-mvp",
      "author": {
        "name": "SIAE AI Competence Center",
        "email": "ai-cc@siae.it"
      },
      "source": "./plugins/siae-devforge",
      "category": "development",
      "homepage": "https://github.com/itsiae/siae-devforge"
    }
  ]
}
```

**4. Registra il marketplace e installa il plugin**

```bash
claude plugin marketplace add ~/.claude/local-plugins --scope user
claude plugin install siae-devforge@siae-local
```

Dopo l'installazione, il plugin si attiva automaticamente in ogni sessione Claude Code. Riavvia Claude Code per applicare le modifiche.

> **Aggiornamento:** per aggiornare il plugin e' sufficiente fare `git pull` nella cartella clonata. Il symlink garantisce che le modifiche siano immediatamente riflesse senza reinstallare.

### Requisiti

- [Claude Code](https://docs.anthropic.com/en/docs/build-with-claude/claude-code) installato e configurato
- Accesso al repository GitHub `itsiae/siae-devforge`
- (Opzionale) MCP Atlassian configurato per l'integrazione JIRA/Confluence

---

## La Catena SDLC a 7 Fasi

Ogni feature, fix o task attraversa una catena ordinata. Non tutte le fasi sono necessarie per ogni task, ma **l'ordine e' sacro**: non si puo' saltare da fase 2 a fase 5 senza attraversare le intermedie rilevanti.

```
1. Init & Setup    →  2. Req & Design   →  3. Branching
       ↓                     ↓                    ↓
  siae-onboarding     siae-brainstorming    siae-git-workflow
                      siae-architecture

4. Implementation  →  5. Testing           →  6. QA Gate        →  7. Release
       ↓                     ↓                      ↓                    ↓
  siae-code-standards   siae-tdd             siae-debugging       siae-documentation
  siae-security         siae-qa (Xray TC)
  siae-iac              siae-automation
  siae-data-engineering (Appium/Cypress)
  siae-frontend
```

### Esempio: nuova feature end-to-end

1. **Init** — `siae-onboarding` rileva che sei su un repo Java/Spring Boot
2. **Design** — `/forge-plan` avvia il brainstorming socratico, produce un design doc con stima SP
3. **Branching** — `siae-git-workflow` crea `feature/JIRA-123-nuova-feature` da sviluppo
4. **Implementation** — `siae-code-standards` applica naming Java, `siae-security` verifica IAM
5. **Testing** — `siae-tdd` forza il ciclo RED → GREEN → REFACTOR prima del codice
6. **QA Gate** — `siae-debugging` interviene se i test falliscono, genera RCA se serve
7. **Release** — `siae-documentation` genera HLD/LLD, pubblica su Confluence via MCP

---

## Comandi Disponibili

I comandi sono scorciatoie per invocare le funzionalita' piu' comuni del plugin. Si usano nella chat di Claude Code.

| Comando | Descrizione | Skill/Agent invocato |
|---------|-------------|---------------------|
| `/forge-plan` | Brainstorming socratico + piano implementativo con stima SP e task JIRA | `siae-brainstorming` |
| `/forge-test` | Genera suite test TDD seguendo RED-GREEN-REFACTOR | `siae-tdd` |
| `/forge-qa` | Export QA Xray: legge AC da Jira, genera Test Plan e Test Case step-based (Xray API o CSV) | `siae-qa` |
| `/forge-automate` | Automation QA: matcha TC Xray, esegue test con appium-mcp (mobile) o Cypress (web), sincronizza risultati | `siae-automation` |
| `/forge-review` | Code review contro standard SIAE (Qodana, security, naming, architettura) | `code-reviewer` + `spec-reviewer` |
| `/forge-doc` | Genera documentazione tecnica (HLD, LLD, API doc) con template e Mermaid | `siae-documentation` |
| `/forge-rca` | Root Cause Analysis per incident e bug, genera report RCA | `siae-debugging` |

### Uso

```
> /forge-plan
# Claude avvia il brainstorming socratico: esplora contesto, fa domande,
# propone 2-3 approcci con trade-off, produce design doc e piano implementativo

> /forge-test
# Claude analizza il codice e genera test TDD per ogni file modificato

> /forge-qa
# Claude legge gli AC da Jira (o li chiede al developer), legge la Test Strategy
# da Confluence, genera Test Plan e Test Case step-based, esporta in Xray o CSV

> /forge-automate
# Claude rileva il canale (mobile/web), matcha i TC Xray con Automazione=Y,
# genera i test (appium-mcp per mobile su BrowserStack, Cypress per web),
# esegue i test e sincronizza i risultati nella Test Execution Xray

> /forge-review
# Il code-reviewer esegue una review a 6 punti sui file modificati

> /forge-doc HLD
# Claude genera un High Level Design doc con diagrammi C4 in Mermaid

> /forge-rca
# Claude avvia un'investigazione sistematica del bug con template RCA
```

---

## Skill (15)

### Meta-skill

#### `using-devforge` — Il Sistema Operativo del Plugin

Caricata automaticamente all'avvio di ogni sessione. Insegna a Claude:

- **La regola dell'1%**: se una skill potrebbe applicarsi, DEVE essere invocata
- **Tabella Red Flags**: 12 razionalizzazioni comuni che Claude riconosce e blocca ("E' solo una domanda semplice", "Posso farlo velocemente")
- **Mappa skill**: quale skill usare per ogni tipo di task, con priorita' (processo prima, implementazione dopo)
- **Catena SDLC**: l'ordine delle 7 fasi con vincoli di sequenza
- **Classificazione skill**: Rigid (segui esattamente) vs Flexible (adatta al contesto)
- **Verifica prima del completamento**: 5 passi obbligatori (IDENTIFICA → ESEGUI → LEGGI → VERIFICA → AFFERMA) prima di dichiarare "fatto"

### Skill di Processo

#### `siae-onboarding` — Auto-detect progetto (Fase 1: Init)

- **Trigger:** Inizio sessione, apertura nuovo progetto
- **Funzione:** Rileva automaticamente factory, tech stack e regole di progetto analizzando i file nella root:
  - `pom.xml` → Java/Spring Boot (parent POM `it.siae:spring-boot-2-parent-pom`, JUnit5, MapStruct, Lombok)
  - `package.json` → TypeScript (controlla Vue.js per frontend, Express per backend Lambda)
  - `requirements.txt` / Glue → Python/Data Engineering (PySpark, Medallion)
  - `*.tf` / `terragrunt.hcl` → IaC/Terraform (Terragrunt multi-module)
- **Output:** Messaggio di benvenuto con stack rilevato e skill disponibili
- **Reference file:** `skills/siae-onboarding/reference/factory-configs.md` — configurazioni per factory

#### `siae-brainstorming` — Design validato prima del codice (Fase 2: Design)

- **Trigger:** Feature nuova, design, componente, modifica comportamentale
- **HARD-GATE:** Nessuna implementazione prima del design approvato
- **Processo a 6 punti:**
  1. Esplora contesto progetto (file, commit, JIRA se disponibile)
  2. Domande chiarificatrici una alla volta (preferenza: scelta multipla)
  3. Proponi 2-3 approcci con trade-off e stima Story Points (scala Fibonacci 1-13)
  4. Presenta design per sezioni con approvazione incrementale
  5. Scrivi design doc in `docs/plans/YYYY-MM-DD-<topic>-design.md`
  6. Transizione a `siae-git-workflow` per creare il feature branch
- **Integrazione JIRA:** Cerca ticket correlati, produce output strutturato per creazione ticket
- **Tipo:** Rigid (segui esattamente)

#### `siae-architecture` — Pattern architetturali SIAE (Fase 2: Design)

- **Trigger:** Design sistema, pattern C4, decisioni AWS
- **Contenuto:**
  - Modello C4 (Context → Container → Component → Code)
  - Pattern osservati nei repo SIAE: microservizi Java/OpenShift, serverless TS/Lambda, data pipeline Medallion, IaC Terragrunt, frontend SPA Vue.js
  - Mappa servizi AWS usati: Lambda, Glue, S3, DynamoDB, RDS, SNS, SQS, Cognito, KMS, CloudFront, EventBridge
  - Template HLD con sezioni predefinite
- **Reference files:** `reference/aws-patterns.md`, `reference/c4-template.md`
- **Tipo:** Flexible

#### `siae-git-workflow` — Branch strategy e deployment (Fase 3: Branching)

- **Trigger:** Branch, merge, release, tag, deploy
- **Branch strategy:** `feature/` → `sviluppo` → `collaudo` → `certificazione` → `produzione`
- **Naming:** `feature/{JIRA-ID}-descrizione`, `fix/{JIRA-ID}-descrizione`, `hotfix/{JIRA-ID}-descrizione`
- **Merge:** Squash merge su sviluppo, merge commit su collaudo/certificazione
- **Deploy:** Tag-based (`COLLAUDO`, `CERTIFICAZIONE`, `PRODUZIONE`) triggera CD via GitHub Actions
- **HARD-GATE:** Mai push diretto su collaudo/certificazione/produzione
- **Reusable Actions:** Riferimento a `itsiae/siae-gh-actions` (v2.x)
- **Tipo:** Rigid

#### `siae-tdd` — Test-Driven Development obbligatorio (Fase 5: Testing)

- **Trigger:** Implementazione feature, bug fix
- **The Iron Law:** NESSUN CODICE DI PRODUZIONE SENZA TEST FALLENTE PRIMA
- **Workflow:** RED → GREEN → REFACTOR → COMMIT (un commit per ciclo)
- **Framework per stack:**
  - Java: JUnit 5 + Mockito + AssertJ (`should_{behavior}_when_{condition}()`)
  - TypeScript backend: Jest + ts-jest (`{filename}.spec.ts`)
  - TypeScript frontend: vitest + @testing-library/vue (`{Component}.spec.ts`)
  - Python: pytest + pytest-mock (`test_{module}.py`)
- **Coverage target:** >= 70% linee
- **Tabella anti-rationalization:** 12+ scuse riconosciute e bloccate
- **Reference file:** `reference/framework-configs.md` — configurazione CI per test
- **Tipo:** Rigid

#### `siae-qa` — Orchestrazione QA Xray (Fase 5: Testing / QA)

- **Trigger:** Fine brainstorming (AC pronti), fine ciclo TDD (test automatizzati scritti), `/forge-qa`
- **HARD-GATE:** Gli AC devono essere disponibili prima di generare qualsiasi Test Case
- **Graceful degradation a 3 tier:**
  - **Tier 1 — MCP Atlassian:** legge AC da Jira, legge Test Strategy da Confluence, crea oggetti Xray via MCP
  - **Tier 2 — REST API Xray:** usa le env vars `XRAY_CLIENT_ID` + `XRAY_CLIENT_SECRET` per importare via API
  - **Tier 3 — CSV export:** genera CSV semicolon-separated in formato Xray-importabile (importabile manualmente in 30 secondi)
- **Workflow a 5 fasi:**
  1. Lettura AC da Jira (con fallback: description → commenti → Confluence → domande al developer)
  2. Lettura Test Strategy da Confluence (WARNING se non trovata, mai blocco)
  3. Generazione Test Plan (struttura con versione, sprint, link Story, scope)
  4. Generazione Test Case step-based (Action + Expected Result per step, Automazione/NRT verificati col developer)
  5. Export/Sincronizzazione (MCP / API / CSV)
- **Reference file:** `skills/siae-qa/reference/xray-csv-template.md` — formato CSV con colonne, regole e esempio completo
- **Tipo:** Rigid

#### `siae-automation` — Automation QA Xray (Fase 5: Testing / Automation)

- **Trigger:** Dopo siae-qa quando almeno un TC ha `Automazione = Y`, `/forge-automate`
- **Rilevamento canale automatico:** analizza i file del progetto per determinare mobile (iOS/Android) o web (Cypress)
- **Workflow a 5 fasi:**
  1. Ricerca TL esistente in Xray (non assume che non esista — cerca sempre prima)
  2. Analisi ROI su tutti i TC della TL: punteggio su NRT, categoria, step count → fasce 🟢 ALTO / 🟡 MEDIO / 🔴 BASSO
  3. Proposta lista automation al developer con ragionamento; il developer conferma, aggiunge o rimuove TC
  4. Generazione test E2E per i soli TC confermati:
     - **Mobile**: upload APK/IPA su BrowserStack, mapping step → appium-mcp tool calls, esecuzione su device reali
     - **Web**: spec `cypress/e2e/{story-id}/TC-{N}-{slug}.cy.ts` con titolo `it('TC-N: scenario')`, esecuzione `npx cypress run`
  5. Caricamento su Xray (crea/aggiorna Test Execution) o produzione CSV per import manuale
- **Sync risultati:** PASS/FAIL/SKIP per TC, screenshot allegati ai fallimenti, nessuna TE duplicata
- **Reference files:** `reference/appium-browserstack-config.md`, `reference/cypress-xray-config.md`
- **Tipo:** Rigid

#### `siae-debugging` — Investigazione sistematica (Fase 6: QA Gate)

- **Trigger:** Debug issue, errore, incident, test fallito
- **4 fasi obbligatorie:**
  1. Root Cause Investigation (traccia dal sintomo, log CloudWatch)
  2. Pattern Analysis (bug isolato o sistemico?)
  3. Hypothesis Testing (una ipotesi alla volta, documenta risultati)
  4. Implementation (fix minimale + test di regressione)
- **HARD-GATE:** Fase 1 DEVE completarsi prima di qualsiasi fix
- **Safety net:** Se 3+ fix falliscono → STOP, metti in discussione l'architettura
- **Template RCA:** `template/rca-template.md` per incident report strutturato
- **Tipo:** Rigid

#### `siae-documentation` — Documentazione tecnica (Fase 7: Release)

- **Trigger:** Richiesta doc HLD, LLD, API doc
- **3 tipi di documentazione:**
  1. **HLD (High Level Design):** Visione sistema, C4 livello 1-2, decisioni architetturali, NFR
  2. **LLD (Low Level Design):** Dettaglio componenti, sequence diagram, data model, API contract
  3. **API Documentation:** OpenAPI/Swagger spec, endpoint reference, auth, error codes
- **Output:** Markdown con diagrammi Mermaid, pubblicabile su Confluence via MCP
- **Template files:** `template/hld-template.md`, `template/lld-template.md`, `template/api-doc-template.md`
- **Tipo:** Flexible

### Skill Tech-Specific

#### `siae-code-standards` — Naming e convenzioni multi-stack (Fase 4)

- **Trigger:** Scrittura codice Java, TypeScript, Python, HCL
- **Convenzioni trasversali:** camelCase (variabili), PascalCase (classi), kebab-case (file), UPPER_SNAKE_CASE (costanti)
- **Java:** Package `it.siae.{dominio}.{modulo}`, Spring profiles `application-{ambiente}.yml`, parent POM, SLF4J logging
- **TypeScript:** DAO/Service suffix PascalCase, ESLint + Prettier, esbuild per Lambda, Vite per frontend
- **Python:** Module snake_case, Glue job naming `{domain}_{operation}.py`, pytest standard
- **HCL:** Meta files con `_prefix` (`_input.tf`, `_local.tf`, `_output.tf`), Terragrunt live/modules mirror
- **Tipo:** Flexible

#### `siae-security` — Sicurezza AWS e dominio copyright (Fase 4)

- **Trigger:** Codice security-sensitive, IAM, gestione PII
- **OWASP Top 10** adattato ad AWS
- **AWS Security SIAE:** IAM least privilege, OIDC per GitHub Actions, Cognito JWT, KMS encryption at rest, Secrets Manager, VPC per Lambda
- **Dominio copyright:** Trattamento PII autori/artisti conforme GDPR, validazione ISWC/ISRC, encryption dati finanziari ripartizione
- **Secret scanning:** Pre-flight card CRITICO per qualsiasi pattern di secret nel codice
- **Vincoli:** Nessun secret in git, nessun IAM `*` policy, nessun S3 bucket pubblico
- **Tipo:** Flexible

#### `siae-iac` — Infrastructure as Code (Fase 4)

- **Trigger:** Terraform, Terragrunt, infrastruttura
- **Pattern:** Terragrunt `live/` + `modules/` mirror, `config.yaml` injection
- **Convenzioni TF:** `_input.tf`, `_local.tf`, `_output.tf` (underscore prefix), `{servizio}-{risorsa}.tf`
- **Remote state:** S3 + DynamoDB lock, key = `{env}-{repo-name}-terraform-state`
- **CI/CD:** Makefile tag-based deploy, GH Actions reusable workflows
- **Vincoli:** No inline policy, no hardcoded AMI/region, `for_each` invece di `count`
- **Tipo:** Flexible

#### `siae-data-engineering` — Data Pipeline (Fase 4)

- **Trigger:** Glue, PySpark, Medallion, ETL, Step Functions
- **Medallion Architecture:** Bronze (raw ingestion) → Silver (cleansed/enriched)
- **AWS Glue:** PySpark job structure, Glue catalog, job definitions YAML
- **Orchestrazione:** Step Functions state machine, EventBridge trigger
- **Naming:** `bronze-{domain}`, `silver-{domain}`
- **Vincoli:** No pandas in Glue (usa PySpark), partition key obbligatoria, idempotenza
- **Tipo:** Flexible

#### `siae-frontend` — Frontend SPA (Fase 4)

- **Trigger:** Vue.js, vitest, Firebase, Google Analytics
- **Stack:** Vue.js 3 + TypeScript + Pinia + PrimeVue
- **Deploy:** S3 bucket + CloudFront distribution
- **Test:** vitest + @testing-library/vue, coverage >= 70%
- **Config esterne:** Firebase Remote Config + log
- **Error tracking:** Google Analytics con differenziazione errori server/client/network
- **Brand SIAE:** `#000000`, `#2F3546`, `#00B4F9`, `#F6F6F6`, font Roboto
- **Vincoli:** No CSS inline, CSS variables, responsive mobile-first
- **Tipo:** Flexible

---

## Agent (3)

Gli agent sono processi autonomi che eseguono task complessi. Vengono lanciati dai comandi o dalle skill.

### `code-reviewer` — Review a 6 Punti

Esegue una code review strutturata contro gli standard SIAE:

1. **Conformita' standard** — Naming, struttura, logging (→ `siae-code-standards`)
2. **Sicurezza** — OWASP, secret, IAM (→ `siae-security`)
3. **Test coverage** — >= 70%, pattern TDD (→ `siae-tdd`)
4. **Architettura** — Pattern C4, servizi AWS (→ `siae-architecture`)
5. **Code quality** — Complessita', duplicazione, dead code (regole Qodana)
6. **Documentazione** — Commenti dove necessario, changelog

**Output:** Report strutturato per severity (Critical / Major / Minor / Info), con `file:line`, descrizione, suggerimento fix.

**Distrust pattern:** "L'implementer ha finito sospettosamente in fretta. Verifica tutto indipendentemente."

### `spec-reviewer` — Conformita' alla Specifica

Verifica che l'implementazione corrisponda al design doc:

- Tutti i requisiti del design sono implementati?
- Nessuna feature non richiesta aggiunta (YAGNI)?
- I test coprono tutti i requisiti?
- I file modificati sono quelli previsti dal piano?

**Output:** PASS/FAIL con lista discrepanze.

### `doc-generator` — Generazione Documentazione

Analizza il codice sorgente e genera documentazione:

- HLD da template (diagrammi C4 in Mermaid)
- LLD da template (sequence diagram, data model)
- API doc OpenAPI/Swagger

Se MCP Atlassian e' disponibile, pubblica direttamente su Confluence.

---

## Hook (2)

Gli hook si attivano automaticamente in risposta a eventi di Claude Code.

### `SessionStart` — Bootstrap del Plugin

- **Evento:** Apertura sessione (startup, resume, clear, compact)
- **Funzione:** Legge `skills/using-devforge/SKILL.md` e lo inietta come contesto addizionale
- **Effetto:** Claude "impara" il sistema di skill al boot, senza che l'utente debba fare nulla
- **Pattern:** Lazy loading — solo la meta-skill viene caricata. Le skill specifiche vengono invocate on-demand

### `PreCommit` — Quality Gate

- **Evento:** Prima di ogni commit
- **5 verifiche:**

| # | Check | Livello | Blocca? |
|---|-------|---------|---------|
| 1 | **Secret Scan** — Pattern regex per AWS keys, password, token, private key, connection string | CRITICO | Si (non negoziabile) |
| 2 | **Naming Convention** — File kebab-case, classi PascalCase, costanti UPPER_SNAKE | MEDIO | No (warning) |
| 3 | **Test Check** — File test corrispondente per ogni file sorgente modificato | MEDIO | No (warning) |
| 4 | **File Size** — Nessun file > 1 MB | ALTO | Si (richiede conferma) |
| 5 | **Lint Check** — ESLint/Checkstyle/Flake8/tflint se configurato | MEDIO | No (warning) |

- **Output:** Pre-flight card con riepilogo PASS/FAIL per ogni check

---

## Design System Visivo

Tutte le skill seguono il **DevForge Visual Design System** definito in `design-system/devforge-visual.md`:

- **Banner ASCII** di apertura con nome skill
- **Pre-flight cards** con bordi ASCII e livelli di rischio codificati a colori:
  - `LOW` (verde) — Informativo
  - `MEDIO` (giallo) — Richiede attenzione
  - `ALTO` (rosso) — Richiede conferma esplicita
  - `CRITICO` (rosso lampeggiante) — Blocca l'operazione
- **Codifica rischio** per classificare ogni operazione

---

## Struttura del Repository

```
siae-devforge/
├── .claude-plugin/
│   └── plugin.json              # Manifest del plugin (nome, versione, autore)
├── .mcp.json                    # Configurazione MCP server (Atlassian)
├── .gitignore
│
├── hooks/
│   ├── hooks.json               # Registro hook (SessionStart, PreCommit)
│   ├── run-hook.cmd             # Script dispatcher cross-platform (polyglot bash/cmd)
│   ├── session-start            # Hook bootstrap: inietta using-devforge al boot
│   └── pre-commit               # Hook quality gate: 5 check prima di ogni commit
│
├── skills/
│   ├── using-devforge/          # Meta-skill: sistema operativo del plugin
│   │   └── SKILL.md
│   ├── siae-onboarding/         # Auto-detect progetto e stack
│   │   ├── SKILL.md
│   │   └── reference/
│   │       └── factory-configs.md
│   ├── siae-brainstorming/      # Brainstorming socratico
│   │   └── SKILL.md
│   ├── siae-architecture/       # Pattern C4, AWS, HLD
│   │   ├── SKILL.md
│   │   └── reference/
│   │       ├── aws-patterns.md
│   │       └── c4-template.md
│   ├── siae-git-workflow/       # Branch strategy, tag deploy
│   │   └── SKILL.md
│   ├── siae-code-standards/     # Naming multi-stack
│   │   └── SKILL.md
│   ├── siae-security/           # OWASP, AWS security, PII
│   │   └── SKILL.md
│   ├── siae-iac/                # Terragrunt, Terraform
│   │   └── SKILL.md
│   ├── siae-data-engineering/   # Glue, PySpark, Medallion
│   │   └── SKILL.md
│   ├── siae-frontend/           # Vue.js 3, vitest, Firebase
│   │   └── SKILL.md
│   ├── siae-tdd/                # TDD obbligatorio
│   │   ├── SKILL.md
│   │   └── reference/
│   │       └── framework-configs.md
│   ├── siae-qa/                 # Orchestrazione QA Xray (AC, Test Plan, Test Case)
│   │   ├── SKILL.md
│   │   └── reference/
│   │       └── xray-csv-template.md
│   ├── siae-automation/         # Automation QA (appium-mcp/BrowserStack, Cypress/Xray)
│   │   ├── SKILL.md
│   │   └── reference/
│   │       ├── appium-browserstack-config.md
│   │       └── cypress-xray-config.md
│   ├── siae-debugging/          # Debug sistematico, RCA
│   │   ├── SKILL.md
│   │   └── template/
│   │       └── rca-template.md
│   └── siae-documentation/      # HLD, LLD, API doc
│       ├── SKILL.md
│       └── template/
│           ├── hld-template.md
│           ├── lld-template.md
│           └── api-doc-template.md
│
├── commands/
│   ├── forge-plan.md            # /forge-plan → siae-brainstorming
│   ├── forge-test.md            # /forge-test → siae-tdd
│   ├── forge-qa.md              # /forge-qa → siae-qa
│   ├── forge-automate.md        # /forge-automate → siae-automation
│   ├── forge-review.md          # /forge-review → code-reviewer + spec-reviewer
│   ├── forge-doc.md             # /forge-doc → siae-documentation
│   └── forge-rca.md             # /forge-rca → siae-debugging
│
├── agents/
│   ├── code-reviewer.md         # Review a 6 punti con distrust pattern
│   ├── spec-reviewer.md         # Verifica conformita' specifica
│   └── doc-generator.md         # Generazione HLD/LLD/API doc
│
├── design-system/
│   └── devforge-visual.md       # Banner, pre-flight cards, codifica rischio
│
└── docs/
    └── plans/                   # Design doc generati dal brainstorming
```

---

## Stack Supportati

siae-devforge supporta i 4 stack tecnologici principali presenti nei repository SIAE:

| Stack | Linguaggio | Framework/Tool | Repo tipici |
|-------|-----------|----------------|-------------|
| **Java Backend** | Java 11+ | Spring Boot 2, Maven, JUnit5, MapStruct, Lombok | ~60 repo |
| **TypeScript Backend** | TypeScript | Express.js, Lambda, Drizzle ORM, Jest, esbuild | ~22 repo |
| **TypeScript Frontend** | TypeScript | Vue.js 3, Pinia, PrimeVue, vitest, Firebase | ~15 repo |
| **Python Data** | Python 3 | AWS Glue, PySpark, Medallion architecture | ~23 repo |
| **Infrastructure** | HCL | Terraform, Terragrunt, multi-module | ~44 repo |

Il rilevamento e' automatico all'apertura di un progetto (skill `siae-onboarding`).

---

## Integrazione Atlassian (MCP)

Il plugin include una configurazione MCP per Atlassian (`.mcp.json`). Quando configurata:

- **JIRA:** Ricerca ticket correlati durante il brainstorming, creazione ticket con stima SP, transizione stato
- **Confluence:** Pubblicazione documentazione HLD/LLD/API direttamente dallo skill di documentazione

L'integrazione e' **opzionale**: tutte le skill funzionano anche senza MCP Atlassian configurato. Le funzionalita' JIRA/Confluence vengono semplicemente saltate se non disponibili.

Per configurare MCP Atlassian, segui la [documentazione ufficiale](https://developer.atlassian.com/cloud/mcp/).

---

## Architettura del Plugin

### Principi di Design

1. **Lazy Loading** — Solo la meta-skill `using-devforge` viene caricata al boot. Tutte le altre skill vengono invocate on-demand via Skill tool, minimizzando il consumo di contesto
2. **Catena Ordinata** — Le skill rispettano l'ordine SDLC. Le skill di processo (fasi 1-3, 5-6) precedono sempre quelle di implementazione (fase 4)
3. **Rigid vs Flexible** — Le skill di processo (TDD, debugging, brainstorming, git-workflow) sono rigide (segui esattamente). Le skill di dominio (architecture, code-standards, security, iac, data-engineering, frontend, documentation) sono flessibili (adatta al contesto)
4. **Anti-Rationalization** — Ogni skill rigida include una tabella di scuse comuni che Claude riconosce e blocca, prevenendo scorciatoie
5. **Distrust Pattern** — Gli agent di review (code-reviewer, spec-reviewer) trattano l'output dell'implementer con sospetto costruttivo: verificano tutto indipendentemente
6. **HARD-GATE** — Punti di blocco non negoziabili: nessun codice senza design approvato, nessun fix senza root cause, nessun commit con secret
7. **Verification Before Completion** — 5 passi obbligatori prima di dichiarare qualsiasi task completo

### Flusso Dati

```
Claude Code Session
        │
        ▼
  SessionStart Hook → Inietta using-devforge
        │
        ▼
  Messaggio utente → using-devforge controlla skill applicabili
        │
        ▼
  Skill invocata → Esecuzione con HARD-GATE e pre-flight cards
        │
        ▼
  Commit → PreCommit Hook → Quality Gate 5 punti
        │
        ▼
  Output: codice conforme, testato, documentato, sicuro
```

---

## Come Contribuire

### Aggiungere una Nuova Skill

1. Crea la directory `skills/<nome-skill>/`
2. Crea `SKILL.md` seguendo il template in `design-system/devforge-visual.md`
3. Frontmatter YAML obbligatorio: `name`, `description`
4. Includi il banner ASCII DevForge
5. Per skill rigide: aggiungi tabella anti-rationalization e HARD-GATE
6. Aggiungi la skill alla tabella in `skills/using-devforge/SKILL.md`
7. Se serve un comando: crea il thin wrapper in `commands/`

### Aggiungere un Nuovo Agent

1. Crea il file `agents/<nome-agent>.md`
2. Frontmatter: `name`, `description`, `model: inherit`
3. Definisci il framework di analisi e l'output atteso
4. Aggiungi il distrust pattern se l'agent verifica lavoro altrui

### Convenzioni Commit

Il plugin segue le convenzioni SIAE per i commit:

- `feat:` — Nuova skill, comando, agent o hook
- `fix:` — Correzione bug in skill/hook esistente
- `refactor:` — Ristrutturazione senza cambio di comportamento
- `docs:` — Aggiornamento documentazione o template
- `chore:` — Manutenzione, aggiornamento dipendenze

---

*Fatto per SIAE da SIAE AI Competence Center.*
