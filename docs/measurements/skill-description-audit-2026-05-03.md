# Skill Description Audit — 2026-05-03 (PR-5)

**Pattern target:** `Use when <trigger>. <terza persona>. Trigger: <lista esaustiva>.`

**Criteria:**
- Inizia con "Use when" (terza persona, pushy)
- Trigger keyword originali preservati al 100% (NO-REGRESSION)
- YAML valido
- Description ≤1024 char

---

## Batch 1 (skill 1-13) — Task 07

### siae-architecture

- Status: REWRITTEN
- Length before: 405 char
- Length after: 447 char
- Pattern compliance: YES (Use when evaluating, choosing, or analyzing architectural patterns ...)
- Trigger keyword count: 16 (C4 model, HLD, bounded context, CQRS, event-driven, microservizi vs monolite, resilienza, accoppiamento, VALUTARE, SCEGLIERE, ANALIZZARE, valutiamo CQRS, microservizi o monolite, crea il C4, definisci i bounded context, HLD per il sistema X)
- Notes: trigger italiani originali preservati verbatim, frame "Use when evaluating/choosing/analyzing" mantiene la semantica del VALUTARE/SCEGLIERE/ANALIZZARE originale

### siae-automation

- Status: REWRITTEN
- Length before: 239 char
- Length after: 325 char
- Pattern compliance: YES (Use when setting up E2E test automation, Playwright/Cypress, or CI/CD test pipelines ...)
- Trigger keyword count: 8 (automatizza test, setup Playwright, setup Cypress, test E2E, test di regressione automatici, CI/CD pipeline test, GitHub Actions test, /forge-automate)
- Notes: trigger originali preservati al 100%

### siae-autoresearch

- Status: REWRITTEN
- Length before: 381 char
- Length after: 470 char
- Pattern compliance: YES (Use when iteratively optimizing an existing DevForge skill ...)
- Trigger keyword count: 10 (ottimizza skill, migliora description, autoresearch, migliora trigger, ottimizza prompt, /forge-autoresearch, analizza performance skill, siae-writing-skills, runner.py, siae-debugging)
- Notes: sezione "NON usare per" preservata (siae-writing-skills, runner.py, siae-debugging boundaries)

### siae-blind-review

- Status: REWRITTEN
- Length before: 262 char
- Length after: 387 char
- Pattern compliance: YES (Use when performing a blind code review ...)
- Trigger keyword count: 8 (blind review, review cieca, audit spec, verifica spec vs codice, review senza diff, /forge-blind-review, REQUIRED SUB-SKILL, siae-finishing-branch)
- Notes: validates_via block preservato intatto, REQUIRED SUB-SKILL marker preservato

### siae-branching-strategy-check

- Status: REWRITTEN
- Length before: 364 char
- Length after: 422 char
- Pattern compliance: YES (Use when checking SIAE branching strategy compliance ...)
- Trigger keyword count: 9 (branching check, /branching-strategy-check, PR verso main, verifica branching strategy, violazioni branching, default branch errato, release branch, itsiae, release/**)
- Notes: scope itsiae org / current repo / topic-selected repos esplicito; default branch + release/** policy preservati

### siae-code-standards

- Status: REWRITTEN
- Length before: 210 char
- Length after: 285 char
- Pattern compliance: YES (Use when writing or reviewing code that must follow SIAE multi-stack ...)
- Trigger keyword count: 9 (Java, TypeScript, Python, HCL, HCL/Terraform, naming conventions, struttura progetto, logging, error handling)
- Notes: tutti gli stack tags (Java/TypeScript/Python/HCL) preservati

### siae-codebase-map

- Status: REWRITTEN
- Length before: 226 char
- Length after: 283 char
- Pattern compliance: YES (Use when mapping a single-repo codebase structure ...)
- Trigger keyword count: 7 (mappa codebase, struttura progetto, CODEBASE_MAP.md, /forge-map, analizza architettura repo, onboarding su repo, come e organizzato il codice)
- Notes: aggiunto qualificatore "single-repo" per disambiguare da siae-microservices-map (multi-repo)

### siae-data-engineering

- Status: REWRITTEN
- Length before: 473 char
- Length after: 549 char
- Pattern compliance: YES (Use when building, migrating, or debugging AWS data pipelines and ETL jobs ...)
- Trigger keyword count: 22 (Glue job, PySpark, ETL, pipeline di ingestion, trasformazione dati, Step Functions, data lake, Medallion architecture, bronze-to-silver, silver-to-gold, data quality, crawler, batch notturno, Iceberg, CDC, delta window, migrare dati da legacy, costruire pipeline, orchestrazione batch, implementa Medallion, ingestion file CSV, siae-iac)
- Notes: boundary "NON per Terraform (usa siae-iac), REST endpoint o frontend" preservato come anti-misroute

### siae-debugging

- Status: OK_AS_IS (verify post-PR-4)
- Length before: 365 char
- Length after: 365 char
- Pattern compliance: YES (Use when investigating a bug, errore, incident ...)
- Trigger keyword count: già OK post-PR-4 (refactor 612f4c9 - progressive disclosure)
- Notes: nessuna modifica necessaria, description già conformante "Use when X" pattern dopo PR-4

### siae-dev-analytics

- Status: REWRITTEN
- Length before: 435 char
- Length after: 557 char
- Pattern compliance: YES (Use when measuring velocity and quality of SIAE developers using Claude Code + DevForge ...)
- Trigger keyword count: 16 ("misura produttività dev", "ROI Claude Code", "KPI sviluppatori", "analytics dev", "report performance team", "/forge-analytics", "dev metrics", "velocity quality report", "dashboard produttività", "cosa fanno gli sviluppatori", "benchmark dev", "ROI AI coding", 11 KPI, DORA, DX AI Measurement, ROI Index)
- Notes: convertito da inline single-line a folded `>` per leggibilità; tutti i 16 trigger preservati verbatim

### siae-documentation

- Status: REWRITTEN
- Length before: 131 char
- Length after: 205 char
- Pattern compliance: YES (Use when generating technical documentation for SIAE components and APIs ...)
- Trigger keyword count: 4 (richiesta documentazione, /forge-doc, design review, pre-release)
- Notes: description originale molto sintetica, aggiunto frame "Use when generating ..." preservando i 4 trigger

### siae-executing-plans

- Status: OK_AS_IS (verify post-PR-4)
- Length before: 363 char
- Length after: 363 char
- Pattern compliance: YES (Use when executing an approved implementation plan in a separate session ...)
- Trigger keyword count: già OK post-PR-4 (refactor 829f98a - progressive disclosure)
- Notes: nessuna modifica necessaria, description già conformante post-PR-4

### siae-finishing-branch

- Status: OK_AS_IS (verify post-PR-4)
- Length before: 435 char
- Length after: 435 char
- Pattern compliance: YES (Use when preparing a feature/fix branch for PR ...)
- Trigger keyword count: già OK post-PR-4 (refactor 870bcab - progressive disclosure)
- Notes: nessuna modifica necessaria, description già conformante post-PR-4

---

## Batch 1 — Summary

- **Skill rewritten:** 10/13
- **Skill verify-only OK_AS_IS:** 3/13 (debugging, executing-plans, finishing-branch — già conformanti post-PR-4)
- **YAML valid:** 13/13
- **Pattern "Use when X" compliance:** 13/13
- **Trigger keyword preservation (NO-REGRESSION):** 100% (109/109 trigger originali preservati nelle 10 skill rewritten)
- **Description length max:** 557 char (siae-dev-analytics) — well under 1024 limit

---

## Batch 2 (skill 14-26) — Task 08

### siae-finops

- Status: REWRITTEN
- Length before: 248 char
- Length after: 400 char
- Pattern compliance: YES (Use when reviewing AWS costs, ...)
- Trigger keyword count: 13 (review costi AWS, stima impatto PR, ottimizzazione risorse, tag compliance, budget analysis, /forge-cost, /forge-finops, Infracost, Steampipe, Cloud Custodian, risorse idle, sprechi, +AWS)
- Notes: trigger originali preservati verbatim, aggiunto frame "Use when" + bilingue

### siae-flutter

- Status: REWRITTEN
- Length before: 245 char
- Length after: 339 char
- Pattern compliance: YES (Use when developing Flutter mobile apps ...)
- Trigger keyword count: 14 (Flutter, Dart, Riverpod, ObjectBox, Get_it, Amplify, Cognito, app mobile, widget, build_runner, Dio, Crashlytics, deep link, geolocation)
- Notes: trigger originali preservati

### siae-frontend

- Status: REWRITTEN
- Length before: 234 char
- Length after: 346 char
- Pattern compliance: YES (Use when writing Vue.js/Angular/React components ...)
- Trigger keyword count: 10 (componente Vue.js, Vitest, test frontend, deploy S3 CloudFront, Firebase, Pinia, Vue Router, responsive design, drag drop, upload file)
- Notes: trigger originali preservati

### siae-git-env

- Status: REWRITTEN
- Length before: 165 char
- Length after: 276 char
- Pattern compliance: YES (Use when a parent skill needs to detect GitHub CLI ...)
- Trigger keyword count: 1 (REQUIRED SUB-SKILL da siae-git-workflow e siae-finishing-branch)
- Notes: skill internal sub-skill, trigger by-parent preservato

### siae-git-workflow

- Status: REWRITTEN (verify post-PR-4 task 04 OK — leakage strip non invalidato)
- Length before: 360 char
- Length after: 508 char
- Pattern compliance: YES (Use when running any git operation ...)
- Trigger keyword count: 17 (git checkout -b, git commit, git push, git merge, git tag, creazione branch, naming branch, conventional commits, pre-flight card, inizio feature, preparazione deploy, promozione ambiente, hotfix, rollback, push remoto, tag deploy ambiente, +operazione git)
- Notes: trigger PR-4 leakage strip preservato (tag deploy ambiente generico, NO COLLAUDO/CERTIFICAZIONE/PRODUZIONE in description)

### siae-git-worktrees

- Status: REWRITTEN
- Length before: 290 char
- Length after: 413 char
- Pattern compliance: YES (Use when setting up an isolated workspace ...)
- Trigger keyword count: 9 (prima di eseguire un piano implementativo, setup workspace isolato, implementazione su branch separato, /forge-implement, inizio feature multi-commit, isola lavoro, worktree, branch dedicato per implementazione)
- Notes: trigger originali preservati

### siae-iac

- Status: REWRITTEN
- Length before: 255 char
- Length after: 344 char
- Pattern compliance: YES (Use when writing or modifying Terraform modules ...)
- Trigger keyword count: 12 (modulo Terraform, terragrunt, file .tf, .hcl, VPC, ECS, Lambda, DynamoDB table, S3 bucket, security group, API Gateway, infrastruttura AWS)
- Notes: trigger originali preservati

### siae-jasper-from-pdf

- Status: REWRITTEN
- Length before: 446 char
- Length after: 461 char
- Pattern compliance: YES (Use when reverse-engineering a PDF ...)
- Trigger keyword count: 10 ("jrxml da pdf", "ricostruisci jasper", "pdf to jrxml", "genera template jasper", "replica pdf in jasper", "/forge-jasper", "jasper from pdf", "crea jrxml dal pdf", "reverse engineering pdf jasper", "JasperReports da pdf")
- Notes: trigger originali preservati al 100%

### siae-microservices-map

- Status: REWRITTEN (verify post-PR-4 task 03 OK — strip 'SPORT' non invalidato)
- Length before: 285 char
- Length after: 369 char
- Pattern compliance: YES (Use when mapping a multi-repository microservices system ...)
- Trigger keyword count: 7 ("mappa sistema", "sistema a microservizi", "topologia distribuita", "dipendenze tra servizi", "chi chiama chi", "topologia sistema", /forge-sysmap, onboarding su sistema distribuito)
- Notes: trigger PR-4-strip preservati (no SPORT, generico)

### siae-nr-test-flows

- Status: REWRITTEN
- Length before: 270 char
- Length after: 384 char
- Pattern compliance: YES (Use when QA needs to analyze a frontend/mobile repo ...)
- Trigger keyword count: 5 (no-regression test flows, NRT suite, /forge-flows, repo Vue/React/Angular/Ionic/Flutter, team QA deve mappare flussi per regressione)
- Notes: trigger originali preservati

### siae-onboarding

- Status: REWRITTEN
- Length before: 130 char
- Length after: 259 char
- Pattern compliance: YES (Use when starting a new SIAE session ...)
- Trigger keyword count: 3 (inizio sessione, apertura nuovo progetto, cambio contesto)
- Notes: trigger originali preservati, user-invocable:false mantenuto

### siae-parallel-agents

- Status: REWRITTEN
- Length before: 244 char
- Length after: 350 char
- Pattern compliance: YES (Use when dispatching 2+ independent parallel agents ...)
- Trigger keyword count: 7 (failure indipendenti, task paralleli, fix paralleli, investigazione multi-dominio, agenti paralleli, bug indipendenti, moduli rotti contemporaneamente)
- Notes: trigger originali preservati, focus stretto su task indipendenti paralleli

### siae-qa

- Status: REWRITTEN
- Length before: 178 char
- Length after: 261 char
- Pattern compliance: YES (Use when generating formal Xray test documentation ...)
- Trigger keyword count: 3 (completamento brainstorming (Fase 2), completamento ciclo TDD (Fase 5), /forge-qa)
- Notes: trigger originali preservati

---

## Batch 2 — Summary

- **Skill rewritten:** 13/13
- **YAML valid:** 13/13
- **Pattern "Use when X" compliance:** 13/13
- **Trigger keyword preservation:** 13/13 (NO-REGRESSION)
- **Description length max:** 508 char (siae-git-workflow) — well under 1024 limit
- **Verify post-PR-4 OK:** siae-git-workflow (leakage strip preservato), siae-microservices-map (SPORT strip preservato)

---

## Batch 3 (skill 27-39) — Task 09

### siae-brainstorming

- Status: OK_AS_IS (verify post-PR-4)
- Pattern compliance: YES (Use when designing any implementation task before writing code ...)
- Notes: backbone PR-4, gia' in pattern target

### siae-receiving-review

- Status: REWRITTEN
- Pattern compliance: YES (Use when receiving code review feedback on a PR ...)
- Trigger keyword count: 8 (ho ricevuto feedback su una PR, il reviewer ha lasciato commenti, CHANGES REQUESTED, commenti su PR, review ricevuta, fix richiesti dal reviewer, rispondi ai commenti, il reviewer ha chiesto modifiche)
- Notes: trigger originali preservati al 100%

### siae-requesting-review

- Status: REWRITTEN
- Pattern compliance: YES (Use when a PR has been opened and you need to complete it with description and assigned reviewer ...)
- Trigger keyword count: 9 ("pronto per review", "ho aperto la PR", "chiedo il review", PR aperta senza reviewer assegnato, assegna reviewer, richiedi review, PR creata, post-PR, reviewer mancante)
- Notes: trigger originali preservati al 100%

### siae-retrospective

- Status: REWRITTEN
- Pattern compliance: YES (Use when closing a session, opening a PR, or extracting lessons learned ...)
- Trigger keyword count: 8 (fine sessione, lezioni apprese, cosa ho imparato, retrospettiva, salva per la prossima volta, /forge-retro, apertura PR, REQUIRED da post-commit-review hook su gh pr create)
- Notes: trigger originali preservati al 100%, hook chain (post-commit-review) preservato

### siae-robot-framework

- Status: OK_AS_IS (gia' in pattern target da scrittura originale)
- Pattern compliance: YES (Use when: file .robot/.resource aperti/creati/modificati ...)
- Notes: gia' compliant pre-PR-5, no rewrite needed

### siae-security

- Status: REWRITTEN
- Pattern compliance: YES (Use when handling security-sensitive code: credentials, IAM policy, encryption, PII ...)
- Trigger keyword count: 6 (codice security-sensitive, gestione credenziali, IAM policy, encryption, dati personali autori/artisti, codici ISWC/ISRC)
- Notes: trigger originali preservati al 100%, riferimenti OWASP/AWS/PII espliciti nella prima frase

### siae-service-logic-map

- Status: REWRITTEN (verify post-PR-4 task 02 — pattern non era ancora "Use when", ora allineato)
- Pattern compliance: YES (Use when profiling microservizi or running a single-task impact analysis pre-flight ...)
- Trigger keyword count: 14 ("cosa fa {servizio}", "lanciamo su {pattern}", "analizziamo {sistema}", "mappa la logica", "build catalogo L1/L2/L3", "regole business di", "Drools in", "quali servizi gestiscono X", impact analysis, pre-flight MCP, demand impact, blast radius, "modifica su servizio business-critical o microservizio", /forge-logic-build, /forge-logic-search, /forge-mcp-preflight)
- Notes: trigger originali preservati al 100%, modalita' A/B preservate, slash commands preservati

### siae-subagent-development

- Status: REWRITTEN
- Pattern compliance: YES (Use when dispatching parallel implementer subagents from a validated plan ...)
- Trigger keyword count: 7 (/forge-implement, implementa il piano, dispatcha task, lancia implementer, subagent, controller-subagent, orchestrazione implementazione)
- Notes: trigger originali preservati al 100%, disambiguazione vs siae-executing-plans aggiunta nella prima frase

### siae-tdd

- Status: OK_AS_IS (verify post-PR-4)
- Pattern compliance: YES (Use when implementing production code (feature, bug fix, refactor) ...)
- Notes: backbone PR-4 task 06, validates_via preservato

### siae-verification

- Status: OK_AS_IS (verify post-PR-4)
- Pattern compliance: YES (Use when verifying that a fix or change is complete BEFORE declaring it done ...)
- Notes: backbone PR-4, validates_via preservato

### siae-writing-plans

- Status: OK_AS_IS (verify post-PR-4)
- Pattern compliance: YES (Use when transforming an approved design doc into a step-by-step implementation plan ...)
- Notes: backbone PR-4

### siae-writing-skills

- Status: REWRITTEN
- Pattern compliance: YES (Use when creating or improving DevForge skills ...)
- Trigger keyword count: 6 (nuova skill DevForge, migliora skill, scrivi skill, behaviour change, template skill, progetta skill)
- Notes: trigger originali preservati al 100%

### using-devforge

- Status: OK_AS_IS (verify post-PR-4 — pattern "Use at session start" semanticamente equivalente, accettato in PR-4 validation report sezione "Description pattern compliance")
- Pattern compliance: YES (Use at session start or new project context to establish the DevForge backbone ...)
- Notes: pattern "Use at" deliberato per session-start hook trigger

---

## Batch 3 — Summary

- **Skill rewritten:** 7/13
- **Skill OK_AS_IS (verify-only):** 6/13 (siae-brainstorming, siae-robot-framework, siae-tdd, siae-verification, siae-writing-plans, using-devforge)
- **YAML valid:** 7/7 rewritten
- **Pattern "Use when" compliance:** 13/13 (incluso "Use at" semanticamente equivalente per using-devforge)
- **Trigger keyword preservation:** 7/7 rewritten (NO-REGRESSION, 58/58 trigger preservati totali)

---

## Verifica finale 39/39

```
$ COUNT=$(for f in skills/*/SKILL.md; do grep -A 30 '^description:' "$f" | head -30 | grep -q 'Use when\|Use at' && echo OK; done | wc -l)
$ TOTAL=$(ls -d skills/*/ | wc -l)
Total skills: 39, Compliant: 39
```

**Result: 39/39 PASS** — PR-5 description audit completato (PR-4 backbone 8 + Task 07 batch 1 + Task 08 batch 2 + Task 09 batch 3 = 39).

## Smoke test (deferred a post-merge blind-review)

I smoke test attivazione skill richiedono session restart (skill registry e' snapshot-ata al boot della sessione Claude Code). Vedi PR-4 validation report per la stessa motivazione tecnica. Eseguire in sessione fresca dopo merge PR-5 con i prompt elencati nei task 07/08/09 spec.
