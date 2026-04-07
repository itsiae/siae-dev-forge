# Best Practices Alignment — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** Allineare le 30 skill DevForge alle best practice ufficiali Claude Agent Skills
**Architettura:** 3 PR indipendenti — description, progressive disclosure, checklist
**Stack:** Markdown (SKILL.md frontmatter e body)
**SP:** 3 SP-Umano / 1 SP-Augmented
**Design doc:** `docs/plans/2026-03-15-best-practices-alignment-design.md`

---

## PR1: Standardizzare le 30 description

### Task 1: Riscrivere description delle 30 skill [PENDING]

**Formato target per tutte:**
```yaml
description: >
  [Verbo terza persona IT] [cosa fa].
  Trigger: [keyword list].
```

**File coinvolti e nuove description:**

**1. `skills/siae-architecture/SKILL.md`**
```yaml
description: >
  Valuta pattern architetturali, crea diagrammi C4 e guida scelte di design
  (microservizi vs monolite, CQRS, event-driven).
  Trigger: pattern architetturale, C4 model, HLD, bounded context, CQRS,
  microservizi vs monolite, scelta architetturale, resilienza.
```

**2. `skills/siae-automation/SKILL.md`**
```yaml
description: >
  Configura test automation E2E, setup Playwright/Cypress e pipeline CI/CD test.
  Trigger: automatizza test, setup Playwright, setup Cypress, test E2E,
  test di regressione automatici, CI/CD pipeline test, GitHub Actions test,
  /forge-automate.
```

**3. `skills/siae-brainstorming/SKILL.md`**
```yaml
description: >
  Guida il processo di design da idea a design doc approvato, prima di qualsiasi
  implementazione non banale.
  Trigger: feature nuova, design, come procediamo, come progettiamo, quale approccio,
  valutare opzioni, trade-off, prima dell'implementazione, aggiungi feature,
  costruisci, crea componente, nuovo servizio, refactoring architetturale, migrazione.
```

**4. `skills/siae-code-standards/SKILL.md`**
```yaml
description: >
  Applica standard di codifica SIAE multi-stack (Java, TypeScript, Python, HCL).
  Trigger: scrittura codice Java, TypeScript, Python, HCL/Terraform, naming
  conventions, struttura progetto, logging, error handling.
```

**5. `skills/siae-codebase-map/SKILL.md`**
```yaml
description: >
  Mappa la struttura di un codebase e genera CODEBASE_MAP.md per onboarding.
  Trigger: mappa codebase, struttura progetto, CODEBASE_MAP.md, /forge-map,
  analizza architettura repo, onboarding su repo, come e organizzato il codice.
```

**6. `skills/siae-data-engineering/SKILL.md`**
```yaml
description: >
  Guida la costruzione, migrazione e debug di data pipeline ed ETL job su AWS.
  NON per Terraform (usa siae-iac), REST endpoint o frontend.
  Trigger: Glue job, PySpark, ETL, pipeline di ingestion, trasformazione dati,
  Step Functions, data lake, Medallion architecture, bronze-to-silver,
  silver-to-gold, data quality, crawler, batch notturno, Iceberg, CDC,
  delta window, migrare dati da legacy, costruire pipeline, orchestrazione batch,
  implementa Medallion, ingestion file CSV.
```

**7. `skills/siae-debugging/SKILL.md`**
```yaml
description: >
  Esegue root cause investigation prima di proporre qualsiasi fix.
  Trigger: bug, errore, incident, test che fallisce, comportamento inatteso,
  eccezione, stacktrace, crash, errore di compilazione, build failure, 500,
  timeout, NullPointerException, TypeError, non funziona, rotto, fallisce, non va.
```

**8. `skills/siae-documentation/SKILL.md`**
```yaml
description: >
  Genera documentazione tecnica per componenti e API SIAE.
  Trigger: richiesta documentazione, /forge-doc, design review, pre-release.
```

**9. `skills/siae-executing-plans/SKILL.md`**
```yaml
description: >
  Esegue un piano implementativo esistente in una sessione separata da quella
  in cui il piano e' stato scritto.
  Trigger: sessione nuova/separata con piano in docs/plans/, batch execution
  richiesta, piano con REQUIRED SUB-SKILL siae-executing-plans.
```

**10. `skills/siae-finishing-branch/SKILL.md`**
```yaml
description: >
  Chiude un branch in sicurezza prima di aprire qualsiasi PR.
  Trigger: "pronto per PR", "finisco il branch", "ready to merge", "apro la PR",
  gh pr create, git push + PR, apertura pull request, branch completato,
  implementazione finita, lavoro completato su branch, pre-merge checklist.
```

**11. `skills/siae-finops/SKILL.md`**
```yaml
description: >
  Analizza costi AWS, stima impatto PR e identifica risorse idle o sprechi.
  Trigger: review costi AWS, stima impatto PR, ottimizzazione risorse,
  tag compliance, budget analysis, /forge-cost, /forge-finops, Infracost,
  Steampipe, Cloud Custodian, risorse idle, sprechi.
```

**12. `skills/siae-frontend/SKILL.md`**
```yaml
description: >
  Guida la scrittura di componenti Vue.js/Angular/React, test Vitest e deploy
  su S3+CloudFront.
  Trigger: componente Vue.js, Vitest, test frontend, deploy S3 CloudFront,
  Firebase, Pinia, Vue Router, responsive design, drag drop, upload file.
```

**13. `skills/siae-git-env/SKILL.md`**
```yaml
description: >
  Rileva la disponibilita' di GitHub CLI (gh) e stabilisce GH_MODE o FALLBACK_MODE.
  Trigger: REQUIRED SUB-SKILL da siae-git-workflow e siae-finishing-branch.
```

**14. `skills/siae-git-workflow/SKILL.md`**
```yaml
description: >
  Gestisce tutte le operazioni git secondo il branch flow SIAE.
  Trigger: git checkout -b, git commit, git push, git merge, git tag, creazione
  branch, naming branch, conventional commits, pre-flight card, inizio feature,
  preparazione deploy, promozione ambiente, hotfix, rollback, push remoto,
  tag COLLAUDO/CERTIFICAZIONE/PRODUZIONE.
```

**15. `skills/siae-git-worktrees/SKILL.md`**
```yaml
description: >
  Configura workspace isolati con git worktree prima di implementazioni multi-file.
  Trigger: prima di eseguire un piano implementativo, setup workspace isolato,
  implementazione su branch separato, /forge-implement, inizio feature
  multi-commit, isola lavoro, worktree, branch dedicato per implementazione.
```

**16. `skills/siae-iac/SKILL.md`**
```yaml
description: >
  Guida la scrittura e modifica di moduli Terraform, file terragrunt.hcl e
  infrastruttura AWS.
  Trigger: modulo Terraform, terragrunt, file .tf, .hcl, VPC, ECS, Lambda,
  DynamoDB table, S3 bucket, security group, API Gateway, infrastruttura AWS.
```

**17. `skills/siae-microservices-map/SKILL.md`**
```yaml
description: >
  Mappa un sistema a microservizi multi-repository (10+ repo) senza allucinare.
  Trigger: "mappa SPORT", "sistema a microservizi", "dipendenze tra servizi",
  "chi chiama chi", "topologia sistema", /forge-sysmap, onboarding su sistema
  distribuito.
```

**18. `skills/siae-onboarding/SKILL.md`**
```yaml
description: >
  Stabilisce il contesto progetto all'inizio di una sessione SIAE.
  Trigger: inizio sessione, apertura nuovo progetto, cambio contesto.
```

**19. `skills/siae-parallel-agents/SKILL.md`**
```yaml
description: >
  Dispatcha agenti paralleli per debug o task indipendenti simultanei (2+).
  Trigger: failure indipendenti, task paralleli, fix paralleli, investigazione
  multi-dominio, agenti paralleli, bug indipendenti, moduli rotti contemporaneamente.
```

**20. `skills/siae-qa/SKILL.md`**
```yaml
description: >
  Genera documentazione test formale per Xray a completamento implementazione.
  Trigger: completamento brainstorming (Fase 2), completamento ciclo TDD (Fase 5),
  /forge-qa.
```

**21. `skills/siae-receiving-review/SKILL.md`**
```yaml
description: >
  Gestisce la ricezione di feedback di code review. Ogni commento richiede
  reazione esplicita.
  Trigger: ho ricevuto feedback su una PR, il reviewer ha lasciato commenti,
  CHANGES REQUESTED, commenti su PR, review ricevuta, fix richiesti dal reviewer,
  rispondi ai commenti, il reviewer ha chiesto modifiche.
```

**22. `skills/siae-requesting-review/SKILL.md`**
```yaml
description: >
  Completa la PR con description e reviewer assegnato dopo l'apertura.
  Trigger: "pronto per review", "ho aperto la PR", "chiedo il review", PR aperta
  senza reviewer assegnato, assegna reviewer, richiedi review, PR creata, post-PR,
  reviewer mancante.
```

**23. `skills/siae-security/SKILL.md`**
```yaml
description: >
  Applica policy di sicurezza SIAE (OWASP Top 10, AWS security, PII copyright).
  Trigger: codice security-sensitive, gestione credenziali, IAM policy, encryption,
  dati personali autori/artisti, codici ISWC/ISRC.
```

**24. `skills/siae-service-logic-map/SKILL.md`**
```yaml
description: >
  Profila microservizi: dominio, entita', workflow, regole business, cluster.
  Trigger: "cosa fa {servizio}", "lanciamo su {pattern}", "analizziamo {sistema}",
  "mappa la logica", "build catalogo L1/L2/L3", "regole business di", "Drools in",
  "quali servizi gestiscono X", impact analysis, /forge-logic-build,
  /forge-logic-search.
```

**25. `skills/siae-subagent-development/SKILL.md`**
```yaml
description: >
  Dispatcha task implementativi a subagent paralleli da un piano validato nella
  sessione corrente.
  Trigger: /forge-implement, implementa il piano, dispatcha task, lancia implementer,
  subagent, controller-subagent, orchestrazione implementazione.
```

**26. `skills/siae-tdd/SKILL.md`**
```yaml
description: >
  Guida il ciclo TDD per qualsiasi scrittura di codice di produzione. Test PRIMA
  del codice, sempre.
  Trigger: implementazione feature, bug fix, refactoring, qualsiasi scrittura di
  codice, aggiungi metodo, crea classe, modifica logica, nuovo endpoint, scrivi
  funzione, implementa, codifica, sviluppa.
```

**27. `skills/siae-verification/SKILL.md`**
```yaml
description: >
  Verifica con evidenza prima di qualsiasi dichiarazione di completamento.
  Nessun "fatto" senza prova.
  Trigger: prima di commit, PR, task complete, dichiarazioni di successo, "fatto",
  "fixato", "funziona", "completato", "pronto", "implementato", "risolto",
  "test passano", "build verde", "tutto ok", "finito".
```

**28. `skills/siae-writing-plans/SKILL.md`**
```yaml
description: >
  Trasforma un design approvato in un piano implementativo step-by-step concreto
  e bite-sized.
  Trigger: scrivi piano implementativo, trasforma design in task, decomposizione
  step, piano bite-sized, aggiorna piano, task implementativi, docs/plans/.
```

**29. `skills/siae-writing-skills/SKILL.md`**
```yaml
description: >
  Guida la creazione e il miglioramento di skill DevForge.
  Trigger: nuova skill DevForge, migliora skill, scrivi skill, behaviour change,
  template skill, progetta skill.
```

**30. `skills/using-devforge/SKILL.md`**
```yaml
description: >
  Stabilisce il framework di discovery e invocazione skill DevForge all'inizio
  di ogni conversazione.
  Trigger: inizio sessione, apertura nuovo progetto, prima interazione.
```

**Step per ognuna delle 30 skill:**
1. Apri `skills/<name>/SKILL.md`
2. Sostituisci il blocco `description: >` nel frontmatter con la nuova versione
3. Non toccare nulla al di fuori del frontmatter

### Task 2: Aggiornare Dynamic Skill Catalog in using-devforge [PENDING]

**File coinvolti:**
- Modifica: `skills/using-devforge/SKILL.md` — tabella "Dynamic Skill Catalog"

La tabella in fondo a `using-devforge/SKILL.md` contiene la colonna
"INVOCA SE l'utente menziona" che riflette le description. Va aggiornata
per essere coerente con le nuove description.

**Step 1:** Leggi la tabella attuale nel file
**Step 2:** Per ogni riga, aggiorna la colonna "INVOCA SE" con i trigger
dalla nuova description corrispondente
**Step 3:** Verifica che tutte le 30 righe siano presenti e coerenti

### Task 3: Esegui test strutturali [PENDING]

**Step 1: Esegui test**
```bash
cd siae-dev-forge && bash tests/run-all.sh
```
Output atteso: tutti i test passano (0 failures)

**Step 2: Se falliscono, correggi e riesegui**

### Task 4: Commit PR1 [PENDING]

```bash
git add skills/*/SKILL.md
git commit -m "docs(skills): standardize all 30 descriptions to uniform IT format with explicit trigger

Align with official Claude Agent Skills best practices: third person,
verb-led descriptions, explicit trigger keywords."
```

---

## PR2: Progressive Disclosure per 3 skill > 470 righe

### Task 5: Estrai template da siae-service-logic-map [PENDING]

**File coinvolti:**
- Modifica: `skills/siae-service-logic-map/SKILL.md` (488 righe → target < 350)
- Crea: `skills/siae-service-logic-map/TEMPLATES.md`

**Step 1:** Leggi `skills/siae-service-logic-map/SKILL.md` per intero
**Step 2:** Identifica sezioni template e output di esempio (L1/L2/L3)
**Step 3:** Crea `TEMPLATES.md` con le sezioni estratte, incluso TOC se > 100 righe
**Step 4:** In SKILL.md, sostituisci le sezioni estratte con:
```markdown
## Template e Esempi Output
Vedi [TEMPLATES.md](TEMPLATES.md) per template completi L1/L2/L3 e esempi output.
```
**Step 5:** Verifica che SKILL.md sia < 350 righe

### Task 6: Estrai template da siae-qa [PENDING]

**File coinvolti:**
- Modifica: `skills/siae-qa/SKILL.md` (485 righe → target < 350)
- Crea: `skills/siae-qa/XRAY-TEMPLATES.md`

**Step 1:** Leggi `skills/siae-qa/SKILL.md` per intero
**Step 2:** Identifica sezioni template Xray e esempi test case
**Step 3:** Crea `XRAY-TEMPLATES.md` con le sezioni estratte, incluso TOC se > 100 righe
**Step 4:** In SKILL.md, sostituisci le sezioni estratte con:
```markdown
## Template Xray e Esempi
Vedi [XRAY-TEMPLATES.md](XRAY-TEMPLATES.md) per template Xray completi e esempi test case.
```
**Step 5:** Verifica che SKILL.md sia < 350 righe

### Task 7: Estrai template da siae-microservices-map [PENDING]

**File coinvolti:**
- Modifica: `skills/siae-microservices-map/SKILL.md` (472 righe → target < 350)
- Crea: `skills/siae-microservices-map/TEMPLATES.md`

**Step 1:** Leggi `skills/siae-microservices-map/SKILL.md` per intero
**Step 2:** Identifica sezioni template SYSTEM_MAP e esempi output
**Step 3:** Crea `TEMPLATES.md` con le sezioni estratte, incluso TOC se > 100 righe
**Step 4:** In SKILL.md, sostituisci le sezioni estratte con:
```markdown
## Template e Esempi Output
Vedi [TEMPLATES.md](TEMPLATES.md) per template SYSTEM_MAP completi e esempi output.
```
**Step 5:** Verifica che SKILL.md sia < 350 righe

### Task 8: Test + Commit PR2 [PENDING]

**Step 1: Esegui test**
```bash
cd siae-dev-forge && bash tests/run-all.sh
```

**Step 2: Commit**
```bash
git add skills/siae-service-logic-map/ skills/siae-qa/ skills/siae-microservices-map/
git commit -m "refactor(skills): extract templates to auxiliary files for progressive disclosure

Move verbose template/example sections from 3 skills (service-logic-map,
qa, microservices-map) into dedicated files to stay under 500-line limit."
```

---

## PR3: Checklist per debugging, data-engineering, iac

### Task 9: Aggiungi checklist a siae-debugging [PENDING]

**File coinvolti:**
- Modifica: `skills/siae-debugging/SKILL.md`

**Step 1:** Leggi `skills/siae-debugging/SKILL.md` per intero
**Step 2:** Identifica la sezione workflow principale
**Step 3:** Inserisci all'inizio della sezione workflow:

````markdown
Copia questa checklist e traccia il progresso:

```
Debug Progress:
- [ ] Step 1: Reproduci il problema (evidenza del fallimento)
- [ ] Step 2: Raccogli contesto (log, stacktrace, git blame)
- [ ] Step 3: Formula ipotesi di root cause
- [ ] Step 4: Verifica ipotesi (test mirato)
- [ ] Step 5: Applica fix + regression test
```
````

### Task 10: Aggiungi checklist a siae-data-engineering [PENDING]

**File coinvolti:**
- Modifica: `skills/siae-data-engineering/SKILL.md`

**Step 1:** Leggi `skills/siae-data-engineering/SKILL.md` per intero
**Step 2:** Identifica la sezione workflow principale
**Step 3:** Inserisci all'inizio della sezione workflow:

````markdown
Copia questa checklist e traccia il progresso:

```
Pipeline Progress:
- [ ] Step 1: Identifica sorgente e schema input
- [ ] Step 2: Definisci trasformazione (mapping campi)
- [ ] Step 3: Implementa Glue job con test locale
- [ ] Step 4: Valida output (data quality checks)
- [ ] Step 5: Configura orchestrazione (Step Functions/EventBridge)
```
````

**Step 4 (bonus):** Riga 263 — sostituisci `year=2026/month=03/day=12` con `year=YYYY/month=MM/day=DD`

### Task 11: Aggiungi checklist a siae-iac [PENDING]

**File coinvolti:**
- Modifica: `skills/siae-iac/SKILL.md`

**Step 1:** Leggi `skills/siae-iac/SKILL.md` per intero
**Step 2:** Identifica la sezione workflow principale
**Step 3:** Inserisci all'inizio della sezione workflow:

````markdown
Copia questa checklist e traccia il progresso:

```
IaC Progress:
- [ ] Step 1: Definisci risorse in _input.tf / _local.tf
- [ ] Step 2: Implementa modulo (.tf)
- [ ] Step 3: Configura live/ (terragrunt.hcl)
- [ ] Step 4: terraform plan — verifica diff
- [ ] Step 5: Security review (IAM least privilege, encryption)
```
````

### Task 12: Test + Commit PR3 [PENDING]

**Step 1: Esegui test**
```bash
cd siae-dev-forge && bash tests/run-all.sh
```

**Step 2: Commit**
```bash
git add skills/siae-debugging/SKILL.md skills/siae-data-engineering/SKILL.md skills/siae-iac/SKILL.md
git commit -m "feat(skills): add structured checklists to debugging, data-engineering, iac

Align with official Claude Agent Skills best practices: copyable checklists
for multi-step workflows improve agent compliance and progress tracking."
```

---

## Riepilogo

| PR | Task | File modificati | Rischio |
|----|------|----------------|---------|
| PR1 | 1-4 | 30 SKILL.md (frontmatter) | BASSO |
| PR2 | 5-8 | 3 SKILL.md + 3 nuovi file | BASSO |
| PR3 | 9-12 | 3 SKILL.md (body) | BASSO |

**Ordine consigliato:** PR1 → PR2 → PR3 (merge sequenziale, PR indipendenti)
