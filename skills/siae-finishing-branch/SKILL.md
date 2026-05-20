---
name: siae-finishing-branch
description: >
  Use when preparing a feature/fix branch for PR. Pre-flight checklist completo
  (test, coverage, CHANGELOG, branch hygiene, blind review gate) prima di
  pushare e aprire la PR. Best after: siae-verification passed.
  Trigger: "pronto per PR", "finisco il branch", "ready to merge", "apro la PR",
  gh pr create, git push + PR, apertura pull request, branch completato,
  implementazione finita, lavoro completato su branch, pre-merge checklist.
validates_via:
  predicate: pre_flight_passed
  evidence_type: log_event
  evidence_check: "DEVFORGE_LOG_FILE contains finishing_branch_verdict event with verdict=PASS for current task_id"
---

# SIAE Finishing Branch — Chiusura Sicura di un Branch

> **Tipo:** Rigid | **Fase SDLC:** 3. Branching (chiusura)

## LA LEGGE DI FERRO

```
NESSUNA PR SENZA VERIFICA COMPLETA DEL BRANCH
```

<EXTREMELY-IMPORTANT>
Aprire una PR e' un atto pubblico che coinvolge i reviewer. Rispetta il loro tempo.
Un branch non verificato e' un'interruzione mascherata da contributo.

Stai per eseguire `git push` + `gh pr create` o suggerire all'utente di aprire una PR?
Hai completato TUTTI gli step di questa skill? (incluso Blind Review Gate)
- NO → NON procedere. Torna allo step mancante.
- SI → Procedi con la pre-flight card 🔴 ALTO.

NON ESISTE una PR "troppo semplice" per questo processo.
</EXTREMELY-IMPORTANT>

---

## Sequenza pre-PR (6 step + 2 gate)

> Per ogni step: dettagli completi, criteri OK, comandi multi-stack, permission-denied
> handling e tabella anti-razionalizzazione → `reference/finishing-branch-checklist.md`.

```
REQUIRED SUB-SKILL: siae-git-env
```

Esegui `siae-git-env` per stabilire `GH_MODE` o `FALLBACK_MODE`. Skip se gia' fatto in sessione.

### Step 0b — Rileva Parent Branch  🟢 SICURO

Il target della PR non e' hardcoded. Va rilevato dinamicamente.

- `release/*` → target `main`
- `feature/*`, `fix/*`, `refactor/*`, `hotfix/*` → calcola merge-base con `origin/release/*` + `origin/sviluppo`
- 0 candidati → chiedi all'utente; 1 candidato → proponi conferma; 2+ → distanza minore vince
- **GUARDRAIL:** se target = `main` e branch corrente non e' `release/*` → 🔴 BLOCCO

Output: `$PARENT_BRANCH` salvato per gli step successivi. Dettagli: `reference/finishing-branch-checklist.md` § Step 0b.

### Step 1 — Verifica Stato del Branch  🟢 SICURO

```bash
git status && git fetch origin
git log origin/$PARENT_BRANCH..HEAD --oneline
git log HEAD..origin/$PARENT_BRANCH --oneline
```

Criteri OK: `git status` clean, conosci i commit avanti/dietro `$PARENT_BRANCH`.
Se `$PARENT_BRANCH` avanzato → `REQUIRED SUB-SKILL: siae-git-workflow` per rebase/merge.

### Step 2 — Verifica Test e Build  🟡 MEDIO

Pre-flight card obbligatoria. Esegui suite completa multi-stack (mvn / yarn / vitest / pytest / terraform).

Criteri OK: 0 failed, 0 skipped non-intentional, coverage non scesa.
Se test rossi → `REQUIRED SUB-SKILL: siae-debugging`. **Mai aprire PR con test rossi.**

Comandi e card → `reference/finishing-branch-checklist.md` § Step 2.

### Step 3 — Revisione Diff  🟢 SICURO

```bash
git diff origin/$PARENT_BRANCH...HEAD
git diff origin/$PARENT_BRANCH...HEAD --name-only
```

Cerca e rimuovi: `console.log`/`print()`/`logger.debug` temporanei, TODO da PR separare,
credenziali/API key, `.env`/`application-local.properties`, codice commentato, import non usati.

### Step 4 — Verifica Commit History  🟢 SICURO

`git log origin/$PARENT_BRANCH..HEAD --oneline`

Criteri OK: conventional commits (`feat:`/`fix:`/`test:`/`refactor:`/`chore:`), atomicità,
JIRA ID nei commit rilevanti, no WIP commits residui.

Squash con `git rebase -i origin/$PARENT_BRANCH` solo se branch NON pushato/condiviso.

### Step 4b — Plan Completion Gate (pre-PR)

```bash
grep -l "\[PENDING\]\|\[BLOCKED\]" docs/plans/*-plan.md 2>/dev/null
```

Se piano con task non-[DONE] → 🔴 BLOCCO. Eccezione esplicita richiede:
`"procedi con PR parziale — motivo: ..."` scritto dall'utente.

### Step 4c — Blind Review Gate (pre-PR)  🟡 MEDIO

```
REQUIRED SUB-SKILL: siae-blind-review
```

- Design doc esiste in `docs/plans/` → invoca, attendi verdetto
- PASS → Step 5; FAIL → riporta finding, NON aprire PR senza fix o autorizzazione esplicita
- No design doc → segnala gap, procedi con Step 5

### Step 5 — Apri la Pull Request  🔴 ALTO

Pre-flight card obbligatoria. ⏸️ **ATTENDI CONFERMA ESPLICITA** ("sì, procedi" / "no, annulla"). Silenzio ≠ consenso.

Dopo conferma:

**GH_MODE:**
```bash
git push origin <branch-corrente>
gh pr create --base $PARENT_BRANCH --title "feat({scope}): descrizione [JIRA-ID]" --body "$(cat <<'EOF'
## Cosa fa questa PR
[Descrizione]
## Come testare
1. ...
## JIRA
[JIRA-ID](https://jira.siae.it/browse/JIRA-ID)
## Checklist
- [ ] Test passano
- [ ] Self-review completata
- [ ] Documentazione aggiornata (se necessario)
EOF
)"
```

**FALLBACK_MODE:** `git push` + apertura manuale via `https://github.com/<owner>/<repo>/compare/$PARENT_BRANCH...<branch>`. Template completo in checklist reference.

Post-PR:
```
REQUIRED SUB-SKILL: siae-requesting-review
```

---

## Scenari specifici

Casi non lineari → `reference/finishing-branch-scenarios.md`:
- Revert PR già mergiata (`git revert -m 1 <sha>`)
- Hotfix urgente (usa `siae-git-workflow` direttamente)
- Post squash-merge follow-up (`git checkout <branch> -- files`, mai cherry-pick)
- Rebase vs merge su branch lunghi
- Branch con più piani associati

---

## Sub-skill richieste (riepilogo)

| Trigger | Sub-skill |
|---------|-----------|
| Pre-flight env | `siae-git-env` |
| `$PARENT_BRANCH` avanzato | `siae-git-workflow` |
| Test falliti | `siae-debugging` |
| Pre-PR design check | `siae-blind-review` |
| Post-PR review request | `siae-requesting-review` |
| Post-merge feedback | `siae-receiving-review` |

---

## Limiti Operativi

| Vincolo | Limite | Se superato |
|---------|--------|-------------|
| Tentativi max per step | 2 | Fermati. Chiedi all'utente. |
| Step totali chiusura | 6 + 2 gate | Se servono di piu', branch ha problemi strutturali |
| Output max analisi | 300 righe | Sintetizza |

---

## Permission Denied — riassunto

Bash negato in Step 1/2/4/5: presenta i comandi, chiedi output all'utente, analizza testo.
Step 3 partial: Read/Grep permission-free per file modificati. NON entrare in retry loop.
Dettagli completi → `reference/finishing-branch-checklist.md` § Permission Denied Handling.
