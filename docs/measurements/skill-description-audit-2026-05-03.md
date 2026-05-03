# Skill Description Audit — 2026-05-03 (PR-5)

**Pattern target:** `Use when <trigger>. <terza persona>. Trigger: <lista esaustiva>.`

**Criteria:**
- Inizia con "Use when" (terza persona, pushy)
- Trigger keyword originali preservati al 100% (NO-REGRESSION)
- YAML valido
- Description ≤1024 char

---

## Batch 1 (skill 1-13) — Task 07

_(da popolare in Task 07: architecture, automation, autoresearch, blind-review,
branching-strategy-check, code-standards, codebase-map, data-engineering,
debugging, dev-analytics, documentation, executing-plans, finishing-branch)_

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
