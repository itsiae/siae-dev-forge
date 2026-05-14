# Task 33 — slash command /forge-release-risk

**Stato:** [DONE]
**SP:** 1 Human / 0.5 Augmented
**Dipendenze:** task-32

## Goal

Creare `commands/forge-release-risk.md` come entry point sottile per la skill.

## File coinvolti

- Create: `commands/forge-release-risk.md`

## Step

### Step 1 — Write slash command

Write `commands/forge-release-risk.md`:
```markdown
---
name: forge-release-risk
description: Pre-deploy risk assessment release branch vs main (18 criteri, score 0-36, decision GO/POSTPONE/NO_GO). Output checklist md versionato + activity event.
allowed-tools: Bash, Read, AskUserQuestion, Write
---

# /forge-release-risk — Release Risk Assessment on-demand

Esegue scorecard 18-criteri pre-deploy per la release branch corrente (o specificata).
Output: file `docs/releases/<date>-<service>-<branch>.md` + scorecard a stdout.

## Cosa fa

1. Detect repo + service via `git rev-parse` + `gh repo view`
2. Select release branch (corrente se `release/**`, altrimenti AskUserQuestion top 5)
3. Generate diff `origin/main...origin/<release>` (file + content)
4. Fill identification (version, Jira tickets, AskUserQuestion per date/owner)
5. **Step 4b — Genesis check**: feature branch mergiate + AskUserQuestion conferma
6. Pre-flight card 🟡 MEDIO → attesa conferma utente
7. Invoke `python -m lib.release_risk assess` (CLI con 18 criteri)
8. Cache check `(branch, diff-hash, baseline-main-sha)` — hit skippa re-run
9. Display scorecard + path output file
10. Emit activity event `release-risk` per forge-adoption

## Quando usarlo

- **Pre-PR self-assessment:** anticipa scorecard prima di `gh pr create` su release branch
- **Re-run dopo fix:** verifica scorecard dopo aver fixato red flag
- **Manual review:** investigation post-incident con scorecard storica
- **Trigger automatico:** hook `pr-release-gate` su `gh pr create --base main` con head `release/**`

## Uso

```bash
# Scorecard interattiva su release branch corrente
/forge-release-risk
```

L'utente viene guidato attraverso 10-step con AskUserQuestion solo per i 4-5 gap reali (release date, owner, user impact >50%, genesis confirmation).

## Output esempio

```
🟡 Release Risk Scorecard — sport-gestione-licenze-service

Release branch: release/2.4.0 → main
Diff hash: abc123def456
Baseline main SHA: 1a2b3c4d

Level: MEDIUM | Score: 7/36 | Decision: GO_WITH_MONITORING

Output: docs/releases/2026-05-14-sport-gestione-licenze-service-release_2.4.0.md
```

## Bypass / override

```bash
# Skip hook automatico pr-release-gate
touch ~/.claude/.devforge-skip-release-risk

# Skip cache (force re-run)
python -m lib.release_risk assess --no-cache ...
```

## Env var rilevanti

Vedi `hooks/ENV_VARS.md` sezione "Release Risk Assessment":
- `DEVFORGE_RELEASE_RISK_DISABLED=1` — kill switch
- `DEVFORGE_RELEASE_RISK_KG_TIMEOUT_SEC` — MCP sport-kg timeout (default 5)
- `DEVFORGE_RELEASE_RISK_SECURITY_CRITICAL_THRESHOLD` — Criterion 17 critical (default 0)
- `DEVFORGE_RELEASE_RISK_SECURITY_HIGH_THRESHOLD` — Criterion 17 high (default 5)

## Differenza vs `/forge-evidence` e `/forge-score`

| Aspetto | `/forge-evidence` (v1) | `/forge-score` (v2) | `/forge-release-risk` |
|---|---|---|---|
| Scope | per-SHA quality signals | per-SHA score 5-dim 0-100 | per-release 18-criteri 0-36 |
| Output | block:bool + reasons | ScoreCard + decision branch | Scorecard MD versionata + PR comment |
| Trigger | Pre-commit hook | On-demand reviewer | PR-open hook release/**→main |

## Design + Plan

- **Design:** `docs/plans/2026-05-14-siae-release-risk-design.md`
- **Plan:** `docs/plans/2026-05-14-siae-release-risk/`
- **Reference checklist:** `skills/siae-release-risk/reference/release-criticality-checklist.md`
- **Reference criteri:** `skills/siae-release-risk/reference/release-risk-criteria.md`
```

### Step 2 — Commit

```bash
git add commands/forge-release-risk.md
git commit -m "feat(release-risk): slash command /forge-release-risk entry point"
```

## Criteri di accettazione

- [ ] Frontmatter con `allowed-tools: Bash, Read, AskUserQuestion, Write`
- [ ] Sezioni standard (Cosa fa, Quando usarlo, Uso, Output, Bypass, Env var, Differenza, Design+Plan)
- [ ] Reference design + plan + skill files
- [ ] Commit eseguito
