# siae-finishing-branch — Scenari specifici

> Reference linked da `../SKILL.md`. Casi non lineari.

## Decisioni Comuni

### Merge Strategy

| Situazione | Strategia consigliata |
|-----------|----------------------|
| Feature con storia significativa da preservare | Merge commit |
| Serie di commit WIP / fix intermedi | Squash merge (default per feature → parent) |
| Branch sincronizzato con parent (pochi commit) | Rebase (history lineare) |

Su SIAE, la strategia default per feature → parent branch e' **squash merge** (cfr. `siae-git-workflow`).

### Quanti reviewer?

Minimo 1 reviewer obbligatorio per PR verso **main** (regola SIAE).
Per PR verso **sviluppo**: review facoltativa per direttiva DevOps SIAE.
Per modifiche ad architettura o moduli condivisi: almeno 2 reviewer (indipendente dal target).

### La PR e' troppo grande?

Una PR > 400 righe di diff e' difficile da revieware correttamente.
Considera di spezzarla in PR piu' piccole con un branch intermedio.

---

## Revert PR già mergiata

Se una PR mergiata ha introdotto regressione in produzione:

1. **Identifica la PR colpevole:** `git log --oneline origin/main` per il commit di squash merge.
2. **Crea un branch di revert:**
   ```bash
   git checkout -b revert/<jira-id>-revert-<feature> origin/main
   git revert -m 1 <squash-commit-sha>
   git push origin HEAD
   ```
3. **Apri PR di revert** verso il branch originale (main o release/*) con titolo `revert: <original-title> [JIRA-ID]`.
4. **Body PR:** spiega il motivo del revert + riferimento alla PR originale + ticket JIRA per il fix futuro.

> ⚠️ Il `-m 1` indica di mantenere la prima parent (mainline). Sbagliarlo rompe la history.

---

## Hotfix urgente

Per hotfix urgenti in produzione, **NON usare questa skill** — usa direttamente `siae-git-workflow` sezione Hotfix.

Caratteristiche dell'hotfix:
- Branch nominato `hotfix/<jira-id>-<descrizione>` da `release/*` o `main`
- Test mirati al fix specifico (non full suite se tempo critico)
- PR con label `hotfix` + reviewer assegnato in tempo reale (Slack/call)
- Merge fast-forward o squash, mai merge commit

---

## Post squash-merge follow-up

Dopo che una PR feature e' stata squashata in `release/*` o `main`, eventuali commit follow-up sul branch originale **non sono cherry-pickabili direttamente** — il commit hash dello squash differisce.

**Pattern corretto per follow-up:**

```bash
# Dal branch nuovo (es. fix/<jira-id>-followup) creato da release/*:
git checkout -b fix/<jira-id>-followup origin/release/<env>

# Porta solo i file modificati nel commit follow-up del branch precedente:
git checkout <vecchio-branch> -- path/to/file1 path/to/file2

# Verifica diff, committa con messaggio convenzionale:
git diff --staged
git commit -m "fix(<scope>): <descrizione> [JIRA-ID]"
git push origin HEAD
```

> Vedi [feedback_post_squash_merge_followup](../../../memory/feedback_post_squash_merge_followup.md) per il pattern completo.

---

## Rebase vs merge contesto branch lungo

Se il branch e' rimasto aperto per >5 giorni e parent e' avanzato significativamente:

| Scenario | Strategia |
|----------|-----------|
| Branch personale, mai condiviso, history pulita desiderata | `git rebase origin/<parent>` |
| Branch condiviso (>1 collaboratore) | `git merge origin/<parent>` (NO rebase, rompe history altrui) |
| Conflitti complessi su file critici | Coordina con team prima del rebase/merge |
| >50 commit di drift dal parent | Considera di chiudere il branch e rifarlo da capo |

**Dopo rebase su branch personale:**
```bash
git push --force-with-lease origin <branch>
```

`--force-with-lease` previene di sovrascrivere lavoro pushato da altri (safer di `--force`).

---

## Branch con più piani associati

Se il branch implementa più di un piano (`docs/plans/<plan-1>.md` + `docs/plans/<plan-2>.md`):

1. Verifica TUTTI i piani con `grep -l "\[PENDING\]\|\[BLOCKED\]" docs/plans/*-plan.md`.
2. Se anche solo uno ha task non-[DONE], applica il Plan Completion Gate (vedi checklist).
3. Considera di aprire PR separate per piani indipendenti — è quasi sempre meglio.
