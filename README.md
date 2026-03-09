# siae-devforge

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║      ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝      ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝       ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝        ║
║              🔨 DevForge · AI Competence Center                  ║
║         "Il codice si forgia. Il developer cresce."              ║
╚══════════════════════════════════════════════════════════════════╝
```

**siae-devforge** e' un plugin [Claude Code](https://docs.anthropic.com/en/docs/build-with-claude/claude-code) progettato per lo sviluppo software conforme agli standard SIAE. Copre l'intero ciclo di vita del software (SDLC) con 27 skill, 12 comandi, 3 agent, 3 hook e una test suite, organizzati in una catena a 7 fasi.

> **Versione:** 1.3.0-mvp
> **Autore:** SIAE AI Competence Center
> **Licenza:** Proprietary

---

## Indice

- [Come Funziona](#come-funziona)
- [Installazione](#installazione)
- [La Catena SDLC a 7 Fasi](#la-catena-sdlc-a-7-fasi)
- [Comandi Disponibili](#comandi-disponibili)
- [Skill (26)](#skill-26)
  - [Meta-skill](#meta-skill)
  - [Skill di Processo](#skill-di-processo)
  - [Skill Tech-Specific](#skill-tech-specific)
  - [Skill Cross-cutting e Meta](#skill-cross-cutting-e-meta)
- [Agent (3)](#agent-3)
- [Hook (3)](#hook-3)
- [Design System Visivo](#design-system-visivo)
- [Test Suite](#test-suite)
- [Struttura del Repository](#struttura-del-repository)
- [Stack Supportati](#stack-supportati)
- [Integrazione Atlassian (MCP)](#integrazione-atlassian-mcp)
- [Architettura del Plugin](#architettura-del-plugin)
  - [Token Efficiency](#token-efficiency)
- [Come Contribuire](#come-contribuire)

---

## Come Funziona

siae-devforge e' un **plugin Claude Code** che agisce come "sistema operativo" per lo sviluppo in SIAE. Quando avvii Claude Code con il plugin attivo:

1. **All'avvio** — L'hook `SessionStart` inietta automaticamente la meta-skill `using-devforge`, che insegna a Claude come e quando usare tutte le altre skill
2. **Su ogni task** — Claude controlla se esiste una skill applicabile (con la regola dell'1%: se c'e' anche solo l'1% di possibilita' che una skill sia rilevante, la invoca)
3. **Catena SDLC** — Le skill sono organizzate in 7 fasi ordinate. Claude segue l'ordine corretto: non puo' scrivere codice senza aver fatto brainstorming, non puo' committare senza test
4. **Al commit** — L'hook `PreToolUse` intercetta i comandi `git commit` ed esegue un quality gate a 5 punti (secret scan, naming, test, file size, lint) prima di ogni commit

Il risultato: ogni interazione con Claude Code segue automaticamente gli standard SIAE senza che il developer debba ricordarli.

---

## Installazione

Il plugin e' distribuito tramite un marketplace privato GitHub. Due comandi e sei operativo.

```bash
# 1. Registra il marketplace (una volta sola)
claude plugin marketplace add itsiae/siae-dev-forge

# 2. Installa il plugin
claude plugin install siae-devforge --scope user
```

Riavvia Claude Code per attivare il plugin.

> **Aggiornamento:** per aggiornare il plugin all'ultima versione:
> ```bash
> claude plugin update "siae-devforge@siae-devforge"
> ```

### Requisiti

- [Claude Code](https://docs.anthropic.com/en/docs/build-with-claude/claude-code) installato e configurato
- Accesso in lettura al repository GitHub `itsiae/siae-dev-forge` (chiedi al tuo team lead di aggiungerti al team GitHub `siae-developers`)
- SSH key configurata su GitHub (oppure HTTPS con token)
- (Opzionale) MCP Atlassian configurato per l'integrazione JIRA/Confluence

---

## La Catena SDLC a 7 Fasi

Ogni feature, fix o task attraversa una catena ordinata. Non tutte le fasi sono necessarie per ogni task, ma **l'ordine e' sacro**: non si puo' saltare da fase 2 a fase 5 senza attraversare le intermedie rilevanti.

```
1. Init & Setup          →  2. Req & Design   →  3. Branching
       ↓                           ↓                    ↓
  siae-onboarding             siae-brainstorming    siae-git-workflow
  siae-codebase-map           siae-writing-plans    siae-git-worktrees
  siae-service-logic-map      siae-architecture     siae-finishing-branch
  siae-microservices-map

4. Implementation  →  5. Testing           →  6. QA Gate             →  7. Release
       ↓                     ↓                      ↓                       ↓
  siae-code-standards      siae-tdd             siae-debugging            siae-documentation
  siae-security            siae-qa (Xray TC)    siae-parallel-agents
  siae-iac                 siae-automation
  siae-data-engineering    (Appium/Cypress)
  siae-frontend
  siae-subagent-development
  siae-executing-plans

Cross-cutting (ogni fase): siae-verification | siae-requesting-review | siae-receiving-review

Meta: siae-writing-skills
```

### Esempio: nuova feature end-to-end

1. **Init** — `siae-onboarding` rileva che sei su un repo Java/Spring Boot
2. **Design** — `/forge-plan` avvia il brainstorming socratico, produce un design doc con stima SP
3. **Branching** — `siae-git-workflow` crea `feature/JIRA-123-nuova-feature` da sviluppo
4. **Implementation** — `siae-code-standards` applica naming Java, `siae-security` verifica IAM
5. **Testing** — `siae-tdd` forza il ciclo RED → GREEN → REFACTOR prima del codice
6. **QA Gate** — `siae-debugging` interviene se i test falliscono, genera RCA se serve
7. **Release** — `siae-documentation` genera HLD/LLD, pubblica su Confluence via MCP
   + `siae-requesting-review` guida la PR description e l'assegnazione del reviewer

---

## Comandi Disponibili

I comandi sono scorciatoie per invocare le funzionalita' piu' comuni del plugin. Si usano nella chat di Claude Code.

| Comando | Descrizione | Skill/Agent invocato |
|---------|-------------|---------------------|
| `/forge-map` | Mappa e documenta il codebase con subagent Sonnet in parallelo. Genera `docs/CODEBASE_MAP.md` | `siae-codebase-map` |
| `/forge-sysmap` | Mappa un sistema a microservizi multi-repo senza allucinare. Enumera repo con pattern, subagent paralleli, genera `docs/SYSTEM_MAP.md` con C4 diagrams, dependency graph, Kafka map, Gap Report | `siae-microservices-map` |
| `/forge-plan` | Brainstorming socratico + piano implementativo con stima SP e task JIRA | `siae-brainstorming` |
| `/forge-test` | Genera suite test TDD seguendo RED-GREEN-REFACTOR | `siae-tdd` |
| `/forge-qa` | Export QA Xray: legge AC da Jira, genera Test Plan e Test Case step-based (Xray API o CSV) | `siae-qa` |
| `/forge-automate` | Automation QA: matcha TC Xray, esegue test con appium-mcp (mobile) o Cypress (web), sincronizza risultati | `siae-automation` |
| `/forge-review` | Code review contro standard SIAE (Qodana, security, naming, architettura) | `code-reviewer` + `spec-reviewer` |
| `/forge-implement` | Implementa piano con subagent freschi e review a 2 stadi (spec + quality) | `siae-subagent-development` |
| `/forge-doc` | Genera documentazione tecnica (HLD, LLD, API doc) con template e Mermaid | `siae-documentation` |
| `/forge-rca` | Root Cause Analysis per incident e bug, genera report RCA | `siae-debugging` |
| `/forge-logic-build` | Costruisce catalogo L1+L2+L3 (domain profile + workflow map + business rules) per tutti i microservizi | `siae-service-logic-map` |
| `/forge-logic-search` | Cerca concetto o workflow nel catalogo logic (es. "preventivo", "rinnovo") | `siae-service-logic-map` |

### Uso

```
> /forge-map
# Claude scansiona il codebase con tiktoken, raggruppa i file per modulo/layer,
# dispatcha subagent Sonnet in parallelo, sintetizza in docs/CODEBASE_MAP.md

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

## Mappa del Sistema — Come Collaborano le Skill di Discovery

Per sistemi a microservizi come SPORT (~42 repo), siae-devforge fornisce due skill complementari
che insieme danno una comprensione completa del sistema:

| Skill | Comando | Risponde a | Output |
|---|---|---|---|
| `siae-service-logic-map` | `/forge-logic-build` | "Cosa fa ogni cluster?" | `docs/logic-catalog/cluster-*.md` — domain profile L1+L2+L3 per cluster |
| `siae-microservices-map` | `/forge-sysmap` | "Chi chiama chi?" | `docs/SYSTEM_MAP.md` — grafo dipendenze con edge CONFIRMED/INFERRED |

**Workflow tipico (comando singolo):**

```
/forge-logic-build sport-fdc-*
   → Step 0: cerca SYSTEM_MAP.md — se non esiste, esegue /forge-sysmap automaticamente
   → Step 3: cluster detection dal grafo (evidenza-based, conferma utente)
   → Step 4: pre-fetch dati L1+L2+L3 per cluster + dispatch agenti paralleli
   → Step 5: siae-documentation eseguito automaticamente sui cluster-*.md
   → Output: docs/logic-catalog/cluster-{nome}.md  (1 per cluster, sezioni L1+L2+L3)
             docs/logic-catalog/clusters.yaml       (indice)
             docs/logic-catalog/system-overview.md  (visione d'insieme)

/forge-logic-search "diffida"
   → Cerca nel catalogo: quali cluster/servizi implementano un concetto
   → Incrocia con SYSTEM_MAP per le dipendenze
```

**Esempio reale — Sport FDC (Filiera del Credito, 3 repo):**

```
Cluster rilevati da SYSTEM_MAP.md:
  fdc-core (2 servizi): fascicolo ↔ evidenza (dipendenza bidirezionale CONFIRMED)
  fdc-documento (1 servizio): standalone

Output:
  docs/systems/sport-fdc/logic-catalog/cluster-fdc-core.md
  docs/systems/sport-fdc/logic-catalog/cluster-fdc-documento.md
  docs/systems/sport-fdc/logic-catalog/clusters.yaml
```

**Domande che ogni skill risponde:**

| Domanda | Skill |
|---|---|
| "Da cosa dipende sport-gestione-abbonamento?" | siae-microservices-map |
| "Chi pubblica sul topic `abbonamento.creato`?" | siae-microservices-map |
| "Cosa fa sport-contabilita?" | siae-service-logic-map |
| "Quali servizi gestiscono il workflow di rinnovo?" | siae-service-logic-map |
| "Se modifico la logica di calcolo, chi ne risente?" | entrambe — `/forge-logic-search` + `SYSTEM_MAP.md` |

**Roadmap:** `/forge-impact <concetto>` unifichera' i due cataloghi per rispondere
all'ultima domanda in un unico comando.

---

## Skill (27)

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
  - `package.json` → TypeScript (controlla Vue.js/Angular/React per frontend, Express per backend Lambda)
  - `requirements.txt` / Glue → Python/Data Engineering (PySpark, Medallion)
  - `*.tf` / `terragrunt.hcl` → IaC/Terraform (Terragrunt multi-module)
- **Output:** Messaggio di benvenuto con stack rilevato e skill disponibili
- **Reference file:** `skills/siae-onboarding/reference/factory-configs.md` — configurazioni per factory

#### `siae-codebase-map` — Mappa architetturale del codebase (Fase 1: Init)

- **Trigger:** `/forge-map`, onboarding su progetto sconosciuto, codebase > 50 file senza `docs/CODEBASE_MAP.md`
- **Principio:** Claude Opus orchestra, Sonnet legge. Nessun file del codebase viene letto da Opus direttamente
- **Processo a 7 step:**
  1. Verifica se `docs/CODEBASE_MAP.md` esiste e se ci sono modifiche da `last_mapped`
  2. Scansione con `scripts/scan-codebase.py` (tiktoken) — albero file con conteggio token
  3. Pianifica i subagent raggruppando per modulo/layer (budget: 150k token ciascuno)
  4. Dispatcha TUTTI i subagent Sonnet in parallelo (singolo messaggio con chiamate Task)
  5. Sintetizza i report: merge, deduplicazione, cross-cutting concerns, diagramma Mermaid
  6. Scrive `docs/CODEBASE_MAP.md` con frontmatter `last_mapped`, `total_files`, `total_tokens`
  7. Aggiorna `CLAUDE.md` con sezione architettura
- **Strategia per stack SIAE:** Java per modulo Maven, TS per layer (handlers/services/repositories), Python/Glue per job, IaC per ambiente, Vue per feature/dominio
- **Update mode:** se mappa esiste, dispatcha subagent solo per moduli modificati da git
- **Integrazione `siae-onboarding`:** suggerisce `/forge-map` se repo > 50 file senza mappa
- **Script:** `skills/siae-codebase-map/scripts/scan-codebase.py` — scanner Python con tiktoken, ignora `.gitignore`
- **Tipo:** Flexible

#### `siae-service-logic-map` — Domain Profile e Workflow Map L1+L2+L3 (Fase 1: Init)

- **Trigger:** "cosa fa `{servizio}`", `/forge-logic-build`, "mappa la logica", "regole business di", "build catalogo", "quali servizi gestiscono X", impact analysis
- **Anti-hallucination protocol:** ogni workflow citato DEVE avere un file sorgente. Tag obbligatori: `[CONFIRMED]` / `[INFERRED]` / `[UNVERIFIED]` / `[FILE_NOT_FOUND]`
- **3 livelli di analisi:**
  - **L1 Domain Profile:** dominio, entità principali, API esposte (da OpenAPI), dipendenze dichiarate
  - **L2 Workflow Map:** metodi `public` con `@Transactional`, `@Scheduled`, `@KafkaListener` — flusso operazioni chiave
  - **L3 Business Rules:** regole Drools (`KieSession`, `fireAllRules`), query JPA con business logic, condizioni di dominio significative
- **Processo:** SYSTEM_MAP.md discovery (auto-genera con `siae-microservices-map` se assente) → cluster detection → pre-fetch parallelo → dispatch agenti (1 per cluster) → POST-BUILD con `siae-documentation`
- **Output:** `docs/logic-catalog/cluster-{nome}.md` (L1+L2+L3), `clusters.yaml`, `system-overview.md`
- **Comandi:** `/forge-logic-build` (costruisce), `/forge-logic-search` (cerca concetto nel catalogo)
- **Tipo:** Flexible

#### `siae-microservices-map` — Mappa sistemi distribuiti multi-repo senza allucinare (Fase 1: Init)

- **Trigger:** "mappa SPORT", "sistema a microservizi", "dipendenze tra servizi", "chi chiama chi", `/forge-sysmap`, onboarding su sistema distribuito con 2+ repository
- **Principio:** Anti-Hallucination Protocol — ogni relazione nella mappa deve essere supportata da un'evidenza citata (file + path sorgente). Se l'evidenza non esiste → `[UNVERIFIED]`. Mai inferire relazioni dal nome del servizio, da README o da pattern di sistemi simili
- **Approccio:** Hybrid — GitHub API per inventario repo, file-fetching mirato per evidenze, subagent paralleli 1 per repo
- **Gerarchia fonti:** Tier 1 (codice sorgente) > Tier 2 (config runtime) > Tier 3 (infrastruttura) > Tier 4 (contratti API). README e documentazione testuale sono fonti vietate
- **Confidence tagging:** `[CONFIRMED]` (Tier 1 letto) / `[INFERRED]` (Tier 2-4, con file:riga citato) / `[UNVERIFIED]` (nessuna evidenza) / `[FILE_NOT_FOUND]` (file non accessibile)
- **5 fasi:** PRE-FLIGHT (exit se GitHub non disponibile) → ENUMERATE (lista repo con pattern) → PROFILE+EXTRACT (subagent paralleli, schede evidenza YAML) → CROSS-REF (grafo dipendenze + Kafka map) → OUTPUT (`docs/SYSTEM_MAP.md` con C4 diagrams, dependency graph, Gap Report, Evidence Index)
- **Guardrail anti-lazy:** checklist completamento step, verifica formale pre-Gap Report, `REQUIRED SUB-SKILL: siae-verification` prima di dichiarare completa la mappa
- **Reference:** `reference/system-map-template.md` — template SYSTEM_MAP.md; `reference/evidence-patterns.md` — pattern per stack Java/Node/Python
- **Tipo:** Flexible

#### `siae-brainstorming` — Design validato prima del codice (Fase 2: Design)

- **Trigger:** Feature nuova, design, componente, modifica comportamentale
- **HARD-GATE:** Nessuna implementazione prima del design approvato
- **Processo a 6 punti:**
  1. Esplora contesto progetto (file, commit, JIRA se disponibile)
  2. Domande chiarificatrici una alla volta (preferenza: scelta multipla)
  3. Proponi 2-3 approcci con trade-off e stima Story Points (scala Fibonacci 1-13)
  4. Presenta design per sezioni con approvazione incrementale
  5. Scrivi design doc in `docs/plans/YYYY-MM-DD-<topic>-design.md`
  6. `REQUIRED SUB-SKILL: siae-writing-plans` — produce il piano implementativo bite-sized
- **Integrazione JIRA:** Cerca ticket correlati, produce output strutturato per creazione ticket
- **Tipo:** Rigid (segui esattamente)

#### `siae-writing-plans` — Piano implementativo bite-sized (Fase 2: Design)

- **Trigger:** Design approvato da `siae-brainstorming`, spec/requisiti esistenti, piano da aggiornare
- **HARD-GATE:** Richiede design approvato. Senza design, torna a `siae-brainstorming`
- **Produce:**
  - Decomposizione in task indipendenti con dipendenze esplicite
  - Ogni step = 1 azione (2-5 min): path esatti, codice completo, comando + output atteso
  - Header obbligatorio con `REQUIRED SUB-SKILL: siae-subagent-development` embedded
  - Execution handoff: subagent (questa sessione) → `siae-subagent-development`, o sessione separata → `siae-executing-plans`
- **Output:** `docs/plans/YYYY-MM-DD-<topic>-plan.md`
- **Tipo:** Rigid (segui esattamente)

#### `siae-architecture` — Pattern architetturali SIAE (Fase 2: Design)

- **Trigger:** Design sistema, pattern C4, decisioni AWS
- **Contenuto:**
  - Modello C4 (Context → Container → Component → Code)
  - Pattern osservati nei repo SIAE: microservizi Java/OpenShift, serverless TS/Lambda, data pipeline Medallion, IaC Terragrunt, frontend SPA Vue.js (standard) / Angular / React
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

#### `siae-finishing-branch` — Chiusura sicura di un branch (Fase 3: Branching)

- **Trigger:** "pronto per PR", "finisco il branch", "ready to merge", "apro la PR"
- **Processo a 5 step:** Verifica stato → Test e build → Revisione diff → Commit history → Apri PR
- **Controlli automatici:** `git status` clean, test verdi, rimozione debug code, commit history ordinata
- **Pre-flight card** obbligatoria prima di `git push` e apertura PR
- **Decide merge strategy:** squash (default feature → sviluppo), merge commit, rebase
- **Template PR:** titolo, body strutturato, checklist per reviewer
- **Integrazione:** se test falliscono → `REQUIRED SUB-SKILL: siae-debugging`. Se sviluppo è avanzato → `REQUIRED SUB-SKILL: siae-git-workflow`
- **Tipo:** Rigid

#### `siae-git-worktrees` — Workspace isolato prima dell'implementazione (Fase 3: Branching)

- **Trigger:** Prima di eseguire un piano implementativo, inizio feature, setup workspace isolato
- **La regola:** Non iniziare mai l'implementazione nel branch corrente — crea sempre un worktree isolato
- **Selezione directory (ordine di priorita'):** `.worktrees/` > `worktrees/` > `CLAUDE.md` > chiedi all'utente
- **Safety gate:** `git check-ignore` prima di creare directory locali. Se non ignorata → aggiunge a `.gitignore` + commit automatico
- **Branch base SIAE:** sempre `sviluppo` (mai `main`/`master`)
- **Auto-detect setup:** `mvn dependency:resolve` / `npm install` / `pip install` / `poetry install` per stack rilevato
- **Baseline test:** esegue test suite dopo creazione — se falliscono, riporta e chiede consenso prima di procedere
- **Tipo:** Rigid

#### `siae-parallel-agents` — Dispatch parallelo per task/failure indipendenti (Fase 4 / 6)

- **Trigger:** 2+ failure indipendenti, 2+ task senza dipendenze, debugging multi-dominio
- **Principio:** Investigare o implementare problemi indipendenti in sequenza e' spreco — dispatch un agente per dominio
- **Il pattern a 4 step:** Identifica domini indipendenti → Crea task (scope/goal/vincoli/output) → Dispatch in parallelo → Review, verifica conflitti, esegui suite completa
- **Quando NON usare:** failure correlati, stato condiviso tra agenti, fase esplorativa (non sai ancora cosa e' rotto)
- **Integrazione:** si combina con `siae-subagent-development` per implementazioni parallele con review a 2 stadi
- **Tipo:** Flexible

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
- **Tecniche di supporto:**
  - `testing-anti-patterns.md` — 5 anti-pattern comuni nei test (mock sbagliati, metodi test-only nel codice di produzione, mock incompleti). Da leggere quando aggiungi mock o utility di test
  - `condition-based-waiting.md` — pattern `waitFor()` per eliminare test flaky da `setTimeout` fissi (TypeScript, Python, Java/Awaitility)
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
- **Tecniche di supporto:**
  - `defense-in-depth.md` — Pattern a 4 layer per validare il fix (Entry Point, Business Logic, Environment Guards, Debug Instrumentation)
  - `find-polluter.sh` — Script per test bisection: `./find-polluter.sh '<pattern>' '<glob>'` identifica quale test causa pollution
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

- **Trigger:** Vue.js / Angular / React, vitest, Firebase, Google Analytics
- **Stack standard SIAE:** Vue.js 3 + TypeScript + Pinia + PrimeVue. Angular e React supportati dove già adottati.
- **Deploy:** S3 bucket + CloudFront distribution (tutti i framework)
- **Test:** vitest + @testing-library/{vue|angular|react}, coverage >= 70%
- **Config esterne:** Firebase Remote Config + log
- **Error tracking:** Google Analytics con differenziazione errori server/client/network
- **Brand SIAE:** `#000000`, `#2F3546`, `#00B4F9`, `#F6F6F6`, font Roboto
- **Vincoli:** No CSS inline, CSS variables, responsive mobile-first
- **Tipo:** Flexible

### Skill Cross-cutting e Meta

#### `siae-verification` — Protocollo di Verifica Pre-Completamento (Cross-cutting)

- **Trigger:** Prima di qualsiasi claim di completamento: commit, PR, task complete, "fatto", "fixato"
- **Protocollo a 5 step:** IDENTIFICA → ESEGUI → LEGGI → VERIFICA → AFFERMA
- **Iron Law:** NESSUN CLAIM DI COMPLETAMENTO SENZA EVIDENZA FRESCA
- **Tabella anti-razionalizzazione:** 12 pensieri di bypass riconosciuti e bloccati
- **Reference file:** `reference/common-failures.md` — claim comuni per stack con comandi e errori tipici
- **Tipo:** Rigid

#### `siae-subagent-development` — Orchestratore Implementazione con Subagent (Fase 4)

- **Trigger:** Piano implementativo presente con task indipendenti, `/forge-implement`
- **Processo:** Per ogni task del piano → implementer subagent → spec-reviewer → code-quality-reviewer
- **Distrust pattern:** reviewer indipendenti con "L'implementer ha finito sospettosamente in fretta"
- **Self-review checklist a 4 aree:** completezza, qualità, disciplina (YAGNI), testing — obbligatoria prima del report
- **Max 2 iterazioni** fix-review per stadio, poi escalation all'utente
- **Integration:** `REQUIRED SUB-SKILL: siae-tdd` per implementer, `REQUIRED SUB-SKILL: siae-verification` per tutti
- **Tipo:** Rigid

#### `siae-executing-plans` — Esecuzione piano in sessione separata (Fase 4)

- **Trigger:** Sessione separata aperta con piano in `docs/plans/`, batch execution con checkpoint umani
- **Differenza da `siae-subagent-development`:** Claude esegue direttamente (non dispatcha subagent); checkpoint = l'utente decide se continuare; adatto per iterazione lenta e controllata
- **Processo:** carica piano → revisione critica → batch 3 task → report + attesa feedback → batch successivo → `siae-verification` + `siae-finishing-branch`
- **Stop immediato** in caso di blocco — non indovinare, non deviare dal piano
- **Integration:** `REQUIRED SUB-SKILL: siae-tdd` per ogni task, `REQUIRED SUB-SKILL: siae-verification` a fine piano
- **Tipo:** Rigid

#### `siae-requesting-review` — Richiedere una Code Review Efficace (Cross-cutting)

- **Trigger:** "pronto per review", "ho aperto la PR", "chiedo il review", PR aperta senza reviewer assegnato
- **La Legge di Ferro:** NESSUNA PR SENZA DESCRIPTION COMPLETA E REVIEWER ASSEGNATO
- **Processo a 4 step:**
  1. Scrivi PR description completa (cosa / perché / come verificare) con template obbligatorio
  2. Assegna reviewer: scegli con criterio (dominio, disponibilità, ownership), 1-2 reviewer max
  3. Self-review obbligatoria: leggi il tuo diff come se fossi il reviewer, rimuovi debug code, verifica test
  4. Notifica il reviewer con contesto (link PR + deadline + note specifiche se serve)
- **Categoria PR:** feature / fix / refactor / chore — influenza il tipo di descrizione
- **Integrazione:** se i test sono rossi → `REQUIRED SUB-SKILL: siae-finishing-branch` prima di aprire la PR
- **Tipo:** Rigid

#### `siae-receiving-review` — Elaborazione feedback code review ricevuto (Cross-cutting)

- **Trigger:** Ho ricevuto feedback su una PR, il reviewer ha lasciato commenti, CHANGES REQUESTED
- **Processo a 4 step:** Leggi tutto prima di agire → Categorizza → Pianifica e implementa → Rispondi a ogni commento
- **Categorie feedback:** REQUIRED (blocca merge), SUGGESTION, QUESTION, NITPICK, DISCUSSION
- **Mindset:** il feedback è un regalo; ogni commento richiede risposta esplicita, mai silenzio
- **Fix con TDD:** per ogni REQUIRED non banale → `REQUIRED SUB-SKILL: siae-tdd`
- **Gestione disaccordo:** risposta con evidenza tecnica, escalate al team lead se irrisolto
- **Tipo:** Rigid

#### `siae-writing-skills` — Guida per Creare Skill DevForge (Meta)

- **Trigger:** Creazione nuove skill, miglioramento skill esistenti
- **CSO (Claude Search Optimization):** come scrivere description efficaci
- **Principi di persuasione:** 7 principi Cialdini adattati a DevForge (compliance 33% → 72%)
- **TDD per documentazione:** RED-GREEN-REFACTOR applicato a skill
- **Reference files:**
  - `reference/persuasion-principles.md` — 7 principi con esempi
  - `reference/testing-skills.md` — metodologia TDD per skill
  - `reference/skill-template.md` — template SKILL.md pronto all'uso
- **Tipo:** Flexible

---

## Test Suite

Il plugin include una test suite per validare la struttura e il funzionamento delle skill.

```bash
# Esegui tutti i test
cd siae-dev-forge && bash tests/run-all.sh
```

### Suite disponibili

| Suite | Cosa testa | Comando |
|-------|-----------|---------|
| **Structure Validation** | SKILL.md presente con frontmatter valido per ogni skill | Automatico |
| **Dynamic Catalog** | `lib/skills-core.js` rileva tutte le skill | Automatico |
| **Commands Validation** | Ogni comando ha frontmatter valido | Automatico |
| **Skill Triggering** | Prompt naturali attivano le skill corrette (richiede Claude CLI) | `tests/skill-triggering/run-all.sh` |
| **Token Usage Analysis** | Analisi costi per agente/subagent da file sessione .jsonl | `python3 tests/analyze-token-usage.py <session.jsonl>` |

### Aggiungere un prompt di test

1. Crea un file `.txt` in `tests/skill-triggering/prompts/`
2. Scrivi un prompt realistico in italiano che dovrebbe attivare una skill specifica
3. Aggiungi il mapping in `tests/skill-triggering/run-all.sh` nella funzione `get_expected_skill`

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

## Hook (3)

Gli hook si attivano automaticamente in risposta a eventi di Claude Code.

### `SessionStart` — Bootstrap del Plugin

- **Evento:** Apertura sessione (startup, resume, clear, compact)
- **Funzione:** Legge `skills/using-devforge/SKILL.md` e lo inietta come contesto addizionale
- **Effetto:** Claude "impara" il sistema di skill al boot, senza che l'utente debba fare nulla
- **Pattern:** Lazy loading — solo la meta-skill viene caricata. Le skill specifiche vengono invocate on-demand

### `PreToolUse` (Bash) — Quality Gate

- **Evento:** Prima di ogni `git commit` (intercettato via PreToolUse sul tool Bash)
- **5 verifiche:**

| # | Check | Livello | Blocca? |
|---|-------|---------|---------|
| 1 | **Secret Scan** — Pattern regex per AWS keys, password, token, private key, connection string | CRITICO | Si (non negoziabile) |
| 2 | **Naming Convention** — File kebab-case, classi PascalCase, costanti UPPER_SNAKE | MEDIO | No (warning) |
| 3 | **Test Check** — File test corrispondente per ogni file sorgente modificato | MEDIO | No (warning) |
| 4 | **File Size** — Nessun file > 1 MB | ALTO | Si (richiede conferma) |
| 5 | **Lint Check** — ESLint/Checkstyle/Flake8/tflint se configurato | MEDIO | No (warning) |

- **Output:** Pre-flight card con riepilogo PASS/FAIL per ogni check

### `PostToolUse` (Skill) — Activity Logging

- **Evento:** Dopo ogni invocazione del tool Skill
- **Funzione:** Logga l'evento `skill_invoked` nel file di activity log `~/.claude/devforge-activity.jsonl`
- **Dati registrati:** Timestamp, session ID, nome della skill invocata, fase SDLC
- **Pattern:** Append-only JSONL — ogni riga e' un evento JSON auto-contenuto

### Activity Log

Tutti e 3 gli hook scrivono eventi strutturati in `~/.claude/devforge-activity.jsonl` tramite il logger centralizzato `lib/logger.sh`. Il file e' in formato JSONL (una riga JSON per evento) e traccia:

| Evento | Sorgente | Dati |
|--------|----------|------|
| `session_start` | SessionStart hook | Directory progetto, versione plugin, durata boot |
| `quality_gate` | PreToolUse hook | Comando git intercettato |
| `skill_invoked` | PostToolUse hook | Nome della skill invocata, fase SDLC |

#### Schema JSONL

Ogni riga del log contiene i campi seguenti:

```json
{
  "ts": "2026-03-04T10:30:00.000Z",
  "sid": "a1b2c3d4",
  "branch": "feature/SDLC-142-add-login",
  "jira_id": "SDLC-142",
  "project": "diritti-gestione-service",
  "event": "skill_invoked",
  "status": "success",
  "duration_ms": 1234,
  "meta": {"skill_name": "siae-tdd", "sdlc_phase": "5. Testing"}
}
```

| Campo | Descrizione |
|-------|-------------|
| `ts` | Timestamp UTC ISO 8601 |
| `sid` | Session ID (8 char hash, rinnovato ad ogni SessionStart) |
| `branch` | Branch git corrente (o `no-branch` fuori da un repo) |
| `jira_id` | JIRA ID estratto automaticamente dal nome del branch (o `null`) |
| `project` | Nome della directory root del progetto git |
| `event` | Tipo evento: `session_start`, `quality_gate`, `skill_invoked` |
| `status` | `success` o `error` |
| `duration_ms` | Durata in millisecondi (solo per eventi timed) |
| `meta` | Oggetto JSON con dati specifici dell'evento |

#### Correlazione Cross-Session

I campi `branch`, `jira_id` e `project` permettono di tracciare il flusso SDLC **attraverso sessioni diverse**. Questo e' fondamentale per:

- **Drift detection:** Identificare sessioni che fanno Implementation senza un Design precedente
- **Multi-repo tracking:** Seguire un ticket JIRA (es. `SPORT-456`) attraverso microservizi diversi
- **Analisi cicli iterativi:** Rilevare fix non risolutive che iterano sullo stesso branch

#### Query di Esempio

```bash
# Ultimi 10 eventi
tail -10 ~/.claude/devforge-activity.jsonl

# Skill piu' invocate
jq -r 'select(.event=="skill_invoked") | .meta.skill_name' ~/.claude/devforge-activity.jsonl | sort | uniq -c | sort -rn

# Sessioni di oggi
jq -r 'select(.event=="session_start")' ~/.claude/devforge-activity.jsonl | grep "$(date +%Y-%m-%d)"

# Fasi SDLC per un ticket JIRA specifico (cross-session)
jq -r 'select(.jira_id=="SDLC-142" and .event=="skill_invoked") | "\(.ts) \(.sid) \(.meta.sdlc_phase) \(.meta.skill_name)"' ~/.claude/devforge-activity.jsonl

# Drift detection: sessioni con Implementation ma senza Design
jq -sr '
  group_by(.sid)[] |
  {sid: .[0].sid, phases: [.[] | select(.event=="skill_invoked") | .meta.sdlc_phase] | unique} |
  select((.phases | any(startswith("4."))) and (.phases | any(startswith("2.")) | not))
' ~/.claude/devforge-activity.jsonl

# Storia di un branch attraverso sessioni diverse
jq -r 'select(.branch=="feature/SPORT-456-fix-sync") | "\(.ts) [\(.sid)] \(.event) \(.meta)"' ~/.claude/devforge-activity.jsonl
```

---

## Design System Visivo

Tutte le skill seguono il **DevForge Visual Design System** definito in `design-system/devforge-visual.md`:

- **Banner ASCII** di apertura con nome skill e fase SDLC
- **Legge di Ferro** — principio non negoziabile in maiuscolo (skill Rigid)
- **Pre-flight cards** generate dinamicamente via `design-system/generate-card.py` con bordi ASCII e livelli di rischio codificati a colori:
  - `MEDIO` (giallo, bordo `╔╗`) — Richiede attenzione, reversibile
  - `ALTO` (rosso, bordo `┏┓`) — Difficile da annullare, richiede conferma
  - `CRITICO` (rosso intenso) — Blocca l'operazione
- **Classificazione Rischio Operazioni** — tabella con colonna Card (Si/No) per ogni step
- **Tabella Anti-Razionalizzazione** — blocca le scorciatoie cognitive tipiche del dominio

> Copertura completa su tutte le 26 skill: ogni skill Rigid ha Legge di Ferro + Anti-Razi,
> ogni skill ha Risk Table e pre-flight cards per le operazioni con rischio >= MEDIO.

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
│   ├── hooks.json               # Registro hook (SessionStart, PreToolUse, PostToolUse)
│   ├── run-hook.cmd             # Script dispatcher cross-platform (polyglot bash/cmd)
│   ├── session-start            # Hook bootstrap: inietta using-devforge al boot
│   ├── pre-commit               # Hook quality gate: 5 check prima di ogni commit
│   └── post-skill               # Hook activity log: traccia skill invocate
│
├── lib/
│   ├── skills-core.js           # Discovery dinamica skill e catalogo auto-generato
│   └── logger.sh                # Activity logger centralizzato (JSONL append)
│
├── skills/
│   ├── using-devforge/          # Meta-skill: sistema operativo del plugin
│   │   └── SKILL.md
│   ├── siae-onboarding/         # Auto-detect progetto e stack
│   │   ├── SKILL.md
│   │   └── reference/
│   │       └── factory-configs.md
│   ├── siae-codebase-map/       # Mappa architetturale con subagent Sonnet
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       └── scan-codebase.py # Scanner tiktoken (basato su Cartographer MIT)
│   ├── siae-service-logic-map/  # Domain profile L1+L2+L3 per microservizi
│   │   ├── SKILL.md
│   │   └── reference/
│   ├── siae-microservices-map/  # Mappa sistemi distribuiti multi-repo senza allucinare
│   │   ├── SKILL.md
│   │   └── reference/
│   │       ├── system-map-template.md  # Template SYSTEM_MAP.md con C4 + Gap Report
│   │       └── evidence-patterns.md   # Pattern evidenza per Java/Node/Python
│   ├── siae-brainstorming/      # Brainstorming socratico
│   │   └── SKILL.md
│   ├── siae-writing-plans/      # Piano implementativo bite-sized
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
│   ├── siae-frontend/           # Vue.js 3 (standard), Angular, React, vitest, Firebase
│   │   └── SKILL.md
│   ├── siae-tdd/                # TDD obbligatorio
│   │   ├── SKILL.md
│   │   ├── testing-anti-patterns.md  # 5 anti-pattern comuni nei test
│   │   ├── condition-based-waiting.md # Pattern waitFor() per test flaky
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
│   ├── siae-documentation/      # HLD, LLD, API doc
│   │   ├── SKILL.md
│   │   └── template/
│   │       ├── hld-template.md
│   │       ├── lld-template.md
│   │       └── api-doc-template.md
│   ├── siae-verification/       # Protocollo verifica pre-completamento
│   │   ├── SKILL.md
│   │   └── reference/
│   │       └── common-failures.md
│   ├── siae-subagent-development/ # Orchestratore implementazione con subagent
│   │   ├── SKILL.md
│   │   ├── implementer-prompt.md
│   │   ├── spec-reviewer-prompt.md
│   │   └── code-quality-reviewer-prompt.md
│   ├── siae-executing-plans/    # Esecuzione piano in sessione separata
│   │   └── SKILL.md
│   ├── siae-requesting-review/  # PR description efficace e assegnazione reviewer
│   │   ├── SKILL.md
│   │   └── reference/
│   ├── siae-receiving-review/   # Elaborazione feedback code review ricevuto
│   │   └── SKILL.md
│   └── siae-writing-skills/     # Guida per creare nuove skill
│       ├── SKILL.md
│       └── reference/
│           ├── persuasion-principles.md
│           ├── testing-skills.md
│           └── skill-template.md
│
├── commands/
│   ├── forge-map.md             # /forge-map → siae-codebase-map
│   ├── forge-sysmap.md         # /forge-sysmap → siae-microservices-map
│   ├── forge-plan.md            # /forge-plan → siae-brainstorming
│   ├── forge-test.md            # /forge-test → siae-tdd
│   ├── forge-qa.md              # /forge-qa → siae-qa
│   ├── forge-automate.md        # /forge-automate → siae-automation
│   ├── forge-review.md          # /forge-review → code-reviewer + spec-reviewer
│   ├── forge-implement.md       # /forge-implement → siae-subagent-development
│   ├── forge-doc.md             # /forge-doc → siae-documentation
│   ├── forge-rca.md             # /forge-rca → siae-debugging
│   ├── forge-logic-build.md     # /forge-logic-build → siae-service-logic-map
│   └── forge-logic-search.md    # /forge-logic-search → siae-service-logic-map
│
├── agents/
│   ├── code-reviewer.md         # Review a 6 punti con distrust pattern
│   ├── spec-reviewer.md         # Verifica conformita' specifica
│   └── doc-generator.md         # Generazione HLD/LLD/API doc
│
├── design-system/
│   └── devforge-visual.md       # Banner, pre-flight cards, codifica rischio
│
├── tests/
│   ├── run-all.sh               # Runner principale per tutti i test
│   └── skill-triggering/
│       ├── run-all.sh           # Esegue tutti i prompt di test
│       ├── run-test.sh          # Test singolo: prompt → skill invocata
│       └── prompts/             # Prompt di test in italiano (scenari SIAE)
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

### Token Efficiency

Il plugin e' progettato per minimizzare il consumo di token per sessione senza rinunciare alla copertura comportamentale.

Ogni parola nel context window **costa token ad ogni singolo messaggio** della sessione — non una volta sola, ma ogni volta che Claude ragiona. Su una sessione di 30 messaggi, 1000 parole extra equivalgono a ~40.000 token sprecati.

**Le 3 ottimizzazioni implementate:**

| Tecnica | Implementazione | Impatto |
|---------|----------------|---------|
| **Lazy Loading** | `SessionStart` inietta solo `using-devforge`. Le 20 skill operative sono caricate on-demand via Skill tool, solo quando servono | Le skill non usate non pesano nulla in sessione |
| **Sub-skill Extraction** | `siae-verification` e' una skill separata, caricata solo su commit/PR/claim di completamento — non sempre in context | Meno token in boot, caricata solo quando serve |
| **Description Trap Fix** | Le description YAML devono essere trigger-only: Claude carica il corpo completo solo quando serve, non segue la description come sostituto | Compliance: Claude legge sempre il corpo della skill |

### Principi di Design

1. **Lazy Loading + Dynamic Discovery** — Solo la meta-skill `using-devforge` viene caricata al boot, con un catalogo skill generato dinamicamente da `lib/skills-core.js`. Tutte le skill vengono invocate on-demand via Skill tool, minimizzando il consumo di contesto. Nuove skill aggiunte nella directory `skills/` appaiono automaticamente al prossimo boot
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
  SessionStart Hook → Inietta using-devforge + log session_start
        │
        ▼
  Messaggio utente → using-devforge controlla skill applicabili
        │
        ▼
  Skill invocata → PostToolUse Hook → log skill_invoked
        │
        ▼
  Esecuzione con HARD-GATE e pre-flight cards
        │
        ▼
  Commit → PreToolUse Hook (Bash) → Quality Gate 5 punti + log quality_gate
        │
        ▼
  Output: codice conforme, testato, documentato, sicuro
        │
        ▼
  Activity log: ~/.claude/devforge-activity.jsonl (JSONL append-only)
```

---

## Come Contribuire

### Aggiungere una Nuova Skill

1. Crea la directory `skills/<nome-skill>/`
2. Crea `SKILL.md` seguendo il template in `design-system/devforge-visual.md`
3. Frontmatter YAML obbligatorio: `name`, `description`
4. Includi il banner ASCII DevForge
5. Per skill Rigid: aggiungi LA LEGGE DI FERRO, Tabella Anti-Razionalizzazione e HARD-GATE
5b. Per tutte le skill: aggiungi Classificazione Rischio Operazioni con colonna Card (Si/No)
5c. Per operazioni con Card=Si: aggiungi blocco `generate-card.py` nello step corrispondente
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
