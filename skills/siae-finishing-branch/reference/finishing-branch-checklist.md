# siae-finishing-branch — Checklist completa pre-PR

> Reference dettagliato linked da `../SKILL.md`. Use when ready to open PR.

## Pre-flight (obbligatorio)

Aprire una PR e' un atto pubblico che coinvolge i reviewer. Rispetta il loro tempo.
Un branch non verificato e' un'interruzione mascherata da contributo.

NON ESISTE una PR "troppo semplice" per questo processo.
Anche un singolo file modificato merita: test verdi, diff review, commit history pulita.

> 📊 **Dai repo itsiae:** Le PR aperte senza checklist pre-merge hanno 2.8x piu' probabilita' di CHANGES REQUESTED al primo review.
> Fonte: analisi su 816 repository GitHub itsiae (60 Java, 44 HCL, 23 Python, 22 TypeScript).

## Quando si Applica

Usa questa skill quando:
- Hai finito l'implementazione di una feature/fix/refactoring
- Stai per aprire una Pull Request verso il branch parent (rilevato dinamicamente)
- Vuoi verificare la readiness del branch prima di coinvolgere reviewer

**NON usare per:**
- Hotfix urgenti in produzione → usa direttamente `siae-git-workflow` sezione Hotfix
- Merge tra branch protetti (sviluppo → collaudo) → usa `siae-git-workflow` sezione Promozione

---

## 0. Environment Check — GitHub CLI

```
REQUIRED SUB-SKILL: siae-git-env
```

Esegui `siae-git-env` prima di procedere. Il `GH_MODE` determina i comandi usati in Step 5 (apertura PR).
Se gia' eseguita nella sessione, usa il contesto esistente senza ripetere il check.

---

## Step 0b — Rileva Parent Branch

🟢 SICURO

Il target della PR non e' hardcoded. Va rilevato dinamicamente dal branch da cui
e' stato staccato il branch corrente.

**1. Rileva il branch corrente:**

```bash
CURRENT_BRANCH=$(git branch --show-current)
```

**2. Determina il tipo di branch:**

- Se `release/*` → il target e' il default branch (`main`). Salta al risultato.
- Se `feature/*`, `fix/*`, `refactor/*`, `hotfix/*` → procedi con il rilevamento.

**3. Fetch e lista candidati parent:**

```bash
git fetch origin
# Lista branch release/* e sviluppo remoti
git branch -r --list 'origin/release/*'
git branch -r --list 'origin/sviluppo'
```

**4. Calcola il parent piu' probabile:**

| Candidati trovati | Azione |
|-------------------|--------|
| **0 candidati** | Chiedi all'utente: "Non ho trovato branch `release/*` o `sviluppo`. Quale branch e' il target della PR?" |
| **1 candidato** | Proponi con conferma: "Il parent branch rilevato e' `<branch>`. Confermi?" |
| **2+ candidati** | Calcola merge-base per ciascuno (vedi sotto) |

Per 2+ candidati, calcola la distanza di ogni candidato:

```bash
# Per ogni candidato <branch>:
MERGE_BASE=$(git merge-base HEAD origin/<branch>)
DISTANCE=$(git rev-list --count $MERGE_BASE..HEAD)
```

Il candidato con **distanza minore** e' il parent piu' probabile.

- Se il best match e' chiaro (unico minimo, o differenza > 3 commit col secondo):
  → "Il parent branch piu' probabile e' `<branch>` (N commit di distanza). Confermi?"
- Se ambiguo (2+ candidati con distanza simile, differenza ≤ 3 commit):
  → "Ho trovato piu' branch candidati: `<lista con distanze>`. Quale e' il target della PR?"

**5. GUARDRAIL — Protezione default branch:**

Se il target rilevato e' `main` (default branch) e il branch corrente **non** e' `release/*`:

```
🔴 BLOCCO — Solo branch release/* possono aprire PR verso main.
Il branch corrente e' <branch-corrente>.
Scegli un altro target.
```

**Risultato:** il parent branch rilevato e confermato viene salvato come `$PARENT_BRANCH`
e usato in tutti gli step successivi.

---

## Step 1 — Verifica Stato del Branch

🟢 SICURO

```bash
# Stato corrente
git status

# Confronto con $PARENT_BRANCH (quanti commit avanti/dietro?)
git log origin/$PARENT_BRANCH..HEAD --oneline

# Controlla se $PARENT_BRANCH e' avanzato
git fetch origin
git log HEAD..origin/$PARENT_BRANCH --oneline
```

**Criteri di OK:**
- [ ] Nessun file non committato (`git status` clean)
- [ ] Tutti i commit sono nel branch (nessun lavoro perso)
- [ ] Conosco quanti commit apporto a `$PARENT_BRANCH`

**Se `$PARENT_BRANCH` e' avanzato rispetto al tuo branch:**

```
REQUIRED SUB-SKILL: siae-git-workflow
```

Esegui un rebase o merge da `$PARENT_BRANCH` prima di procedere.

---

## Step 2 — Verifica Test e Build

🟡 MEDIO — Mostra pre-flight card prima di eseguire la suite

| 🟡 MEDIO (reversibile) — 🔨 DevForge · siae-finishing-branch |
|:---|
| 🌿 Branch: `<branch-name>` |
| **▼ Azione** |
| 1. 🧪 Azione: Esecuzione suite di test completa → `<directory test>` |
| 💡 Perche': Verifica che il branch non abbia regressions prima di aprire la PR |
| 🚫 Se NO: La suite non viene eseguita — rischio di aprire PR con test rossi |

Esegui la suite di test completa — non solo i test che hai modificato.

```bash
# Java
mvn test

# TypeScript backend
yarn test

# TypeScript frontend
npx vitest run

# Python
pytest

# IaC
terraform validate && terraform plan -detailed-exitcode
```

**Criteri di OK:**
- [ ] Tutti i test passano (0 failed, 0 skipped non-intentional)
- [ ] Nessuna regressione introdotta
- [ ] Coverage non e' scesa sotto la soglia del progetto

**Se i test falliscono:**

```
REQUIRED SUB-SKILL: siae-debugging
```

Non aprire la PR con test rossi. MAI.

---

## Step 3 — Revisione Diff

🟢 SICURO

Leggi il diff completo come se fossi il reviewer.

```bash
# Diff rispetto a $PARENT_BRANCH
git diff origin/$PARENT_BRANCH...HEAD

# Lista file modificati
git diff origin/$PARENT_BRANCH...HEAD --name-only

# Statistiche
git diff origin/$PARENT_BRANCH...HEAD --stat
```

**Cerca e rimuovi:**
- [ ] `console.log`, `print()`, `logger.debug` temporanei
- [ ] `TODO` / `FIXME` che non vuoi portare in PR (crea ticket JIRA separato)
- [ ] Credenziali, API key, valori hardcoded
- [ ] File di configurazione locale (`.env`, `application-local.properties`)
- [ ] Codice commentato senza motivazione
- [ ] Import non usati

**Se trovi problemi:**

```bash
git add <file>
git commit -m "chore: clean up before PR"
```

---

## Step 4 — Verifica Commit History

🟢 SICURO

```bash
git log origin/$PARENT_BRANCH..HEAD --oneline
```

**Criteri di OK:**
- [ ] Tutti i commit seguono conventional commits (`feat:`, `fix:`, `test:`, `refactor:`, `chore:`)
- [ ] Ogni commit e' atomico (un singolo cambiamento logico)
- [ ] Nessun commit di "fix typo" che potrebbe essere squashato
- [ ] Il JIRA ID e' presente nei commit rilevanti

**Se la history e' caotica (troppi WIP commit):**

Considera di squashare localmente prima della PR:
```bash
# Squash degli ultimi N commit in uno solo
git rebase -i origin/$PARENT_BRANCH
# Nel editor: lascia "pick" solo sul primo, cambia gli altri in "squash"
```

> ⚠️ Il rebase modifica la history. Farlo SOLO se il branch NON e' ancora stato pushato,
> o se e' un branch personale non condiviso.

---

## Step 4b — Plan Completion Gate (pre-PR)

Prima di aprire la PR, verifica se esiste un piano associato al lavoro corrente:

```bash
grep -l "\[PENDING\]\|\[BLOCKED\]" docs/plans/*-plan.md 2>/dev/null
```

**Se esiste un piano con task non-[DONE]:**

```
🔴 BLOCCO — Piano incompleto associato a questo branch.

Piano: docs/plans/<file>.md
Stato: X [DONE] / Y [PENDING] / Z [BLOCKED]

Non puoi aprire la PR finche' il piano non e' completato al 100%.

Opzioni:
1. Completa i task [PENDING]
2. Rimuovi i task [BLOCKED] dal piano (con conferma utente)
3. L'utente autorizza esplicitamente la PR parziale
```

**L'opzione 3 richiede che l'utente scriva esplicitamente:**
`"procedi con PR parziale — motivo: ..."`

Senza questa autorizzazione esplicita, NON procedere con Step 5.

**Se non ci sono piani o tutti i task sono [DONE]:** procedi con Step 5.

---

## Step 4c — Blind Review Gate (pre-PR)

🟡 MEDIO

```
REQUIRED SUB-SKILL: siae-blind-review
```

Esegui una blind review prima di aprire la PR. Il reviewer parte SOLO dal design doc
e trova il codice autonomamente.

**Se il design doc esiste in `docs/plans/`:**
Invoca `siae-blind-review`. Attendi il verdetto.

- **Verdetto PASS:** procedi con Step 5
- **Verdetto FAIL:** riporta i finding. NON aprire la PR finche' non sono risolti
  o l'utente autorizza esplicitamente: `"procedi senza blind review — motivo: ..."`

**Se non esiste un design doc:**
La blind review non puo' procedere. Segnala e procedi con Step 5.
Questo e' un gap nel processo — il lavoro e' stato fatto senza spec scritta.

---

## Step 5 — Apri la Pull Request

🔴 ALTO — Pre-flight card obbligatoria

| 🔴 ALTO (difficile da annullare) — 🔨 DevForge · siae-finishing-branch |
|:---|
| **⚠️ OPERAZIONE DIFFICILE DA ANNULLARE** |
| 🌿 Branch: `<branch-corrente>` · 🎯 Target: `$PARENT_BRANCH` · 📝 Commit: `N commit` |
| **▼ Azione** |
| 1. 🚀 Azione: Push branch + apertura PR → `origin/<branch-corrente>` verso `$PARENT_BRANCH` |
| 💡 Perche': Branch pronto, test verdi, diff revisionato |
| 🚫 Se NO: Il branch resta locale, nessuna PR aperta |

⏸️ **ATTENDI CONFERMA ESPLICITA** — mostra la card e NON eseguire finché l'utente
risponde esplicitamente ("sì, procedi" / "no, annulla"). Silenzio ≠ consenso.

**Dopo la conferma:**

**Se GH_MODE:**

```bash
# Push del branch
git push origin <branch-corrente>

# Apri PR via GitHub CLI
gh pr create \
  --base $PARENT_BRANCH \
  --title "feat({scope}): descrizione [JIRA-ID]" \
  --body "$(cat <<'EOF'
## Cosa fa questa PR

[Descrizione della modifica]

## Come testare

1. ...
2. ...

## JIRA

[JIRA-ID](https://jira.siae.it/browse/JIRA-ID)

## Checklist

- [ ] Test passano
- [ ] Self-review completata
- [ ] Documentazione aggiornata (se necessario)
EOF
)"
```

**Se FALLBACK_MODE:**

```bash
# Push del branch
git push origin <branch-corrente>
```

Poi apri la PR manualmente:
1. Vai su: `https://github.com/<owner>/<repo>/compare/$PARENT_BRANCH...<branch-corrente>`
2. Clicca "Create pull request"
3. Usa il template seguente per il body:

```
## Cosa fa questa PR

[Descrizione della modifica]

## Come testare

1. ...
2. ...

## JIRA

[JIRA-ID](https://jira.siae.it/browse/JIRA-ID)

## Checklist

- [ ] Test passano
- [ ] Self-review completata
- [ ] Documentazione aggiornata (se necessario)
```

---

## Permission Denied Handling

**Step 1 (Stato branch) — Bash negato:**
- `git status`, `git log`, `git fetch`: fornisci i comandi esatti e chiedi all'utente di eseguirli e incollare l'output
- L'analisi dello stato procede normalmente sull'output fornito

**Step 2 (Test e Build) — Bash negato:**
- Presenta il comando test corretto per lo stack rilevato
- Chiedi all'utente di eseguirlo e riportare l'output
- Analizza l'output per determinare se procedere

**Step 3 (Revisione diff) — parzialmente permission-free:**
- `Read` dei file modificati — permission-free (ma richiede la lista dei file)
- `git diff`: se Bash negato, chiedi all'utente di eseguire e incollare
- Grep per `console.log`, `TODO`, credenziali: `Grep(pattern, path)` — permission-free

**Step 4 (Commit history) — Bash negato:**
- Fornisci il comando `git log` e chiedi l'output

**Step 5 (Apri PR) — Bash negato:**
- Presenta il template PR completo come output testuale
- Fornisci i comandi `git push` e `gh pr create` pronti per copia-incolla
- L'utente esegue manualmente

**Fasi completabili senza permessi:** analisi diff parziale (Read/Grep), template PR
**Fasi che richiedono permessi:** Step 1-2, 4-5 (Bash per git e test)

Se i permessi sono negati:
1. Completa le verifiche possibili con Read/Grep
2. Presenta tutti i comandi da eseguire manualmente
3. Fornisci il template PR completo pronto per copia
4. NON entrare in loop di retry su tool negato
5. NON dichiarare completamento per fasi non eseguite

---

## Limiti Operativi

| Vincolo | Limite | Se superato |
|---------|--------|-------------|
| Tentativi max per step | 2 | Fermati. Chiedi all'utente prima di riprovare. |
| Step totali della chiusura branch | 6 | Se ne servono di piu', il branch ha problemi strutturali. |
| Output max per analisi | 300 righe | Sintetizza. L'utente non legge wall-of-text. |

---

## Tabella Anti-Razionalizzazione

| Pensiero | Realta' |
|----------|---------|
| "Apro la PR e poi fixo i test rossi" | I reviewer vedono i test rossi. Non aprire PR broken. |
| "E' una modifica piccola, non serve review" | 1 review obbligatoria. Sempre. |
| "Ho testato manualmente, basta" | I test manuali non prevengono regressioni future. |
| "I console.log li tolgo dopo il merge" | Dopo il merge non li togli. Fallo ora. |
| "La history caotica va bene, lo squasha GitHub" | Squash in PR perde contesto. Fallo tu con intenzione. |
| "Il JIRA ID non serve nel commit" | Tracciabilita' obbligatoria. Sempre. |
| "Il piano e' quasi completo, apro la PR lo stesso" | Quasi completo = incompleto. Finisci i task o chiedi eccezione esplicita. |

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Note |
|-----------|---------|------|
| `git diff`, `git log`, `git status` | 🟢 Sicuro | Solo lettura |
| Esecuzione test suite | 🟡 Medio | Pre-flight obbligatoria |
| `git push` | 🔴 Alto | Pre-flight obbligatoria |
| Apertura PR | 🔴 Alto | Pre-flight obbligatoria |
| Apertura PR con piano incompleto | 🚨 Critico | Hard block (richiede eccezione esplicita) |
| `git rebase -i` | 🔴 Alto | Solo su branch non condivisi |
