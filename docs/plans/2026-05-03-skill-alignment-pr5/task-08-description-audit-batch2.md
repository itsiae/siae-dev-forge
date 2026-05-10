# Task 08 — Description Audit Batch 2 (skill 14-26)

**Goal:** Audit + rewrite description batch 2 (domain skills middle).

**Skill coperte (batch 2)**:
14. siae-finops
15. siae-flutter
16. siae-frontend
17. siae-git-env
18. siae-git-workflow
19. siae-git-worktrees
20. siae-iac
21. siae-jasper-from-pdf
22. siae-microservices-map
23. siae-nr-test-flows
24. siae-onboarding
25. siae-parallel-agents
26. siae-qa

## Step 1 — Stesso processo Task 07

Per ogni skill applica:
1. Leggi description
2. Verifica pattern "Use when X"
3. Rewrite se non conforme (preservando trigger keyword esistenti)
4. Edit tool con old/new exact
5. Verifica YAML
6. Aggiorna audit log
7. Smoke test attivazione

## Esempi prima/dopo

### siae-iac

**Dopo** (esempio):
```yaml
description: >
  Use when writing or modifying Terraform modules, terragrunt.hcl files, or AWS
  infrastructure. Covers VPC, ECS, Lambda, DynamoDB, S3, security groups, API
  Gateway, IaC patterns. Examples: "modulo Terraform per nuovo servizio",
  "terragrunt.hcl per VPC", "Lambda function infrastructure".
```

### siae-frontend

**Dopo**:
```yaml
description: >
  Use when writing Vue.js / Angular / React components, Vitest tests, S3+CloudFront
  deploys, or frontend integrations (Pinia, Vue Router, Firebase). Examples:
  "componente Vue per drag-drop", "deploy frontend S3", "test Vitest".
```

## Step 2 — Note specifiche batch 2

- **siae-git-workflow**: già toccata in PR-4 task 04 per leakage. In questo batch verifica solo description pattern compliance, NON ri-toccare il body.
- **siae-microservices-map**: già toccata in PR-4 task 03. Verify only.
- **siae-parallel-agents**: skill specializzata, mantieni focus stretto su "task indipendenti paralleli".

## Step 3 — Smoke test prompt

| Skill | Smoke prompt |
|---|---|
| siae-frontend | "creo componente Vue.js drag-drop" |
| siae-iac | "modulo Terraform VPC" |
| siae-jasper-from-pdf | "ricostruisci jrxml da pdf" |
| siae-flutter | "app Flutter con Riverpod" |
| siae-microservices-map | "mappa sistema microservizi" (verify post-PR-4) |
| siae-git-workflow | "git checkout -b nuovo branch" (verify post-PR-4) |
| ... | ... |

## Step 4 — Commit

```bash
git add skills/siae-{finops,flutter,frontend,git-env,git-workflow,git-worktrees,iac,jasper-from-pdf,microservices-map,nr-test-flows,onboarding,parallel-agents,qa}/SKILL.md docs/measurements/skill-description-audit-2026-05-03.md
git commit -m "refactor(skills): description audit batch 2 (13 skill, 'Use when X' pattern)

Domain skill batch (finops, flutter, frontend, iac, jasper, ...). Skill già
toccate in PR-4 (git-workflow, microservices-map) verify only.
NO-REGRESSION: 13/13 smoke test OK."
```

## Criteri accettazione

- 13/13 description "Use when X"
- YAML valido
- audit log aggiornato
- smoke test 13/13 PASS

## NO-REGRESSION

Verifica esplicita per skill toccate in PR-4: `git-workflow`, `microservices-map`. Description rewrite NON deve invalidare il leakage strip.
