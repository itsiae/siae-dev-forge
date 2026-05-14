# Task 37 — eval disambiguation set

**Stato:** [DONE]
**SP:** 1 Human / 0.5 Augmented
**Dipendenze:** task-32

## Goal

Creare `evals/release-risk/disambiguation.yaml` con 10 prompt per validare trigger corretto della skill vs altre skill DevForge (siae-finishing-branch, siae-branching-strategy-check, forge-evidence/forge-score).

## File coinvolti

- Create: `evals/release-risk/disambiguation.yaml`

## Step

### Step 1 — Write eval set

Write `evals/release-risk/disambiguation.yaml`:
```yaml
# Eval set per disambiguation siae-release-risk vs altre skill
# Trigger expected: ["siae-release-risk"] o ["other"] esplicito

skill: siae-release-risk
version: "1.0"

cases:
  - id: 1
    prompt: "Voglio fare lo scorecard di rischio della release prima del deploy"
    expected_skill: siae-release-risk
    rationale: "Trigger esplicito 'scorecard' + 'release' + 'deploy'"

  - id: 2
    prompt: "Devo aprire la PR per il feature branch fix/auth-bug"
    expected_skill: siae-finishing-branch
    rationale: "Non release branch, è feature → siae-finishing-branch"

  - id: 3
    prompt: "Quali sono i rischi di rilasciare questa release in produzione?"
    expected_skill: siae-release-risk
    rationale: "Trigger 'rischi' + 'release' + 'produzione'"

  - id: 4
    prompt: "Verifica la branching strategy del repo itsiae"
    expected_skill: siae-branching-strategy-check
    rationale: "Trigger 'branching strategy' specifico"

  - id: 5
    prompt: "Calcola la score card review-evidence del SHA corrente"
    expected_skill: forge-score
    rationale: "Trigger 'score card' + 'review-evidence' per /forge-score v2"

  - id: 6
    prompt: "Devo fare CAB approval prima del deploy della release/2.4.0"
    expected_skill: siae-release-risk
    rationale: "Trigger 'CAB approval' + 'deploy release'"

  - id: 7
    prompt: "Quali feature branch sono state mergiate nella release/3.0.0?"
    expected_skill: siae-release-risk
    rationale: "Trigger 'feature branch mergiate' + 'release' → genesis check Step 4b"

  - id: 8
    prompt: "Sto per fare gh pr create --base main da release/2.4.0"
    expected_skill: siae-release-risk
    rationale: "Trigger automatico hook pr-release-gate (anche manualmente)"

  - id: 9
    prompt: "Pronto per la PR?"
    expected_skill: siae-finishing-branch
    rationale: "Trigger 'pronto per PR' classico finishing-branch (non release-specific)"

  - id: 10
    prompt: "Voglio valutare il delivery risk della release/4.0 prima di tag"
    expected_skill: siae-release-risk
    rationale: "Trigger 'delivery risk' + 'release' + pre-tag"

acceptance:
  required_pass: 10
  allow_partial: false  # tutti devono PASSARE per merge
```

### Step 2 — Commit

```bash
git add evals/release-risk/disambiguation.yaml
git commit -m "test(release-risk): eval disambiguation set 10 prompt vs altre skill"
```

## Criteri di accettazione

- [ ] 10 prompt con expected_skill esplicito
- [ ] 3+ casi vs siae-finishing-branch (più simile)
- [ ] 2+ casi vs siae-branching-strategy-check
- [ ] 1+ caso vs forge-score
- [ ] 4+ casi positivi siae-release-risk
- [ ] acceptance required_pass: 10
- [ ] Commit eseguito
