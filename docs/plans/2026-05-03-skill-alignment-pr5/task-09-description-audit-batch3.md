# Task 09 — Description Audit Batch 3 (skill 27-37)

**Goal:** Audit + rewrite description batch 3 (tooling + meta skills).

**Skill coperte (batch 3)**:
27. siae-brainstorming (verify post-PR-4)
28. siae-receiving-review
29. siae-requesting-review
30. siae-retrospective
31. siae-robot-framework
32. siae-security
33. siae-service-logic-map
34. siae-subagent-development
35. siae-tdd (verify post-PR-4)
36. siae-verification (verify post-PR-4)
37. siae-writing-plans (verify post-PR-4)
38. siae-writing-skills
39. using-devforge (verify post-PR-4)

NB: 13 skill nel batch (totale 13+13+13=39, copertura completa del directory `skills/`). Verificato con `ls skills/ | wc -l = 39`.

## Step 1 — Stesso processo Task 07/08

Per ogni skill:
1. Read description
2. Pattern check "Use when X"
3. Rewrite se necessario
4. Edit tool
5. YAML check
6. Audit log
7. Smoke test

## Esempi prima/dopo

### siae-receiving-review

```yaml
description: >
  Use when receiving code review feedback on a PR (CHANGES REQUESTED, comments,
  fix requested by reviewer). Forces explicit reaction to every comment.
  Examples: "feedback PR ricevuto", "rispondi a commenti review",
  "CHANGES REQUESTED su PR".
```

### siae-security

```yaml
description: >
  Use when handling security-sensitive code: credentials, IAM policy, encryption,
  PII (autori/artisti), copyright codes (ISWC/ISRC). Applies OWASP Top 10 + AWS
  security policy. Examples: "codice security-sensitive", "IAM policy nuovo
  Lambda", "encryption at rest", "PII autori".
```

### siae-subagent-development

```yaml
description: >
  Use when dispatching parallel implementer subagents from a validated plan in
  the current session (vs siae-executing-plans for separate session). Examples:
  "dispatcha task implementer", "controller-subagent orchestration",
  "/forge-implement".
```

### siae-writing-skills

```yaml
description: >
  Use when creating or improving DevForge skills (SKILL.md, behaviour change,
  template skill). Examples: "nuova skill DevForge", "migliora description
  skill", "scrivi skill".
```

## Step 2 — Verify-only per backbone già fatte in PR-4

- siae-tdd, siae-verification, siae-writing-plans, using-devforge: solo verify che pattern "Use when X" sia presente. Se sì, log "OK_AS_IS" nell'audit. Se no (regressione PR-4), riallinea.

## Step 3 — Smoke test prompt

| Skill | Smoke prompt |
|---|---|
| siae-receiving-review | "ho ricevuto feedback su PR #X" |
| siae-requesting-review | "ho aperto la PR, chiedo review" |
| siae-retrospective | "fine sessione, salva lezioni" |
| siae-security | "review IAM policy" |
| siae-service-logic-map | "impact di modifica DTO" |
| siae-subagent-development | "dispatcha task implementer" |
| siae-tdd | "implementa la funzione X" (verify) |
| ... | ... |

## Step 4 — Commit

```bash
git add skills/{siae-receiving-review,siae-requesting-review,siae-retrospective,siae-robot-framework,siae-security,siae-service-logic-map,siae-subagent-development,siae-tdd,siae-verification,siae-writing-plans,siae-writing-skills,using-devforge}/SKILL.md docs/measurements/skill-description-audit-2026-05-03.md
git commit -m "refactor(skills): description audit batch 3 (13 skill, completing 39/39)

Batch finale: review skills, security, service-logic-map, subagent-development,
writing-skills + verify-only per backbone già fatte in PR-4.
NO-REGRESSION: 12/12 smoke test OK. 39/39 skill totali in pattern 'Use when X'."
```

## Criteri accettazione

- 13/13 description "Use when X" (verify per backbone)
- 39/39 totali compliant (verifica grep finale)
- audit log completo
- smoke test 12/12 PASS

## Verifica finale 39/39

```bash
COUNT_TOTAL=$(ls skills/ | wc -l | tr -d ' ')
COUNT_COMPLIANT=$(for f in skills/*/SKILL.md; do grep -l 'Use when' "$f"; done | wc -l | tr -d ' ')
echo "Total: $COUNT_TOTAL, Compliant: $COUNT_COMPLIANT"
```

Output atteso: `Total: 39, Compliant: 39`.

## NO-REGRESSION

Verifica che `siae-tdd` mantenga ancora i 20+ trigger keyword (riduzione in PR-6). Se PR-4 ha già normalizzato la description di tdd, qui è verify-only.
