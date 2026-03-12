---
name: siae-finishing-branch
description: >
  Chiusura sicura di un branch di sviluppo.
  Trigger: "pronto per PR", "finisco il branch", "ready to merge", "apro la PR".
---

# SIAE Finishing Branch — Chiusura Sicura di un Branch

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║      ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝      ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝       ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝        ║
║              🔨 DevForge · FINISHING BRANCH                      ║
║         "Il codice si forgia. Il developer cresce."              ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Rigid | **Fase SDLC:** 3. Branching (chiusura)

---

## LA LEGGE DI FERRO

```
NESSUNA PR SENZA VERIFICA COMPLETA DEL BRANCH
```

Aprire una PR e' un atto pubblico che coinvolge i reviewer. Rispetta il loro tempo.
Un branch non verificato e' un'interruzione mascherata da contributo.

---

## Quando si Applica

Usa questa skill quando:
- Hai finito l'implementazione di una feature/fix/refactoring
- Stai per aprire una Pull Request verso `sviluppo`
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

## Processo in 5 Step

### Step 1 — Verifica Stato del Branch

🟢 SICURO

```bash
# Stato corrente
git status

# Confronto con sviluppo (quanti commit avanti/dietro?)
git log origin/sviluppo..HEAD --oneline

# Controlla se sviluppo e' avanzato
git fetch origin
git log HEAD..origin/sviluppo --oneline
```

**Criteri di OK:**
- [ ] Nessun file non committato (`git status` clean)
- [ ] Tutti i commit sono nel branch (nessun lavoro perso)
- [ ] Conosco quanti commit apporto a sviluppo

**Se sviluppo e' avanzato rispetto al tuo branch:**

```
REQUIRED SUB-SKILL: siae-git-workflow
```

Esegui un rebase o merge da sviluppo prima di procedere.

---

### Step 2 — Verifica Test e Build

🟡 MEDIO — Mostra pre-flight card prima di eseguire la suite

| 🟡 MEDIO (reversibile) — 🔨 DevForge · siae-finishing-branch |
|:---|
| 🌿 Branch: `<branch-name>` |
| 1. 🧪 Azione: Esecuzione suite di test completa |
| 📂 `<directory test>` |
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

### Step 3 — Revisione Diff

🟢 SICURO

Leggi il diff completo come se fossi il reviewer.

```bash
# Diff rispetto a sviluppo
git diff origin/sviluppo...HEAD

# Lista file modificati
git diff origin/sviluppo...HEAD --name-only

# Statistiche
git diff origin/sviluppo...HEAD --stat
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

### Step 4 — Verifica Commit History

🟢 SICURO

```bash
git log origin/sviluppo..HEAD --oneline
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
git rebase -i origin/sviluppo
# Nel editor: lascia "pick" solo sul primo, cambia gli altri in "squash"
```

> ⚠️ Il rebase modifica la history. Farlo SOLO se il branch NON e' ancora stato pushato,
> o se e' un branch personale non condiviso.

---

### Step 4b — Plan Completion Gate (pre-PR)

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

### Step 5 — Apri la Pull Request

🔴 ALTO — Pre-flight card obbligatoria

| 🔴 ALTO (difficile da annullare) — 🔨 DevForge · siae-finishing-branch |
|:---|
| ⚠️ OPERAZIONE DIFFICILE DA ANNULLARE |
| 🌿 Branch: `feature/{JIRA-ID}-descrizione` |
| 🎯 Target: `sviluppo` |
| 📝 Commit: `N commit` |
| 1. 🚀 Azione: Push branch + apertura PR |
| 📂 `origin/feature/{JIRA-ID}-descrizione` |
| 💡 Perche': Branch pronto, test verdi, diff revisionato |
| 🚫 Se NO: Il branch resta locale, nessuna PR aperta |

**Dopo la conferma:**

**Se GH_MODE:**

```bash
# Push del branch
git push origin feature/{JIRA-ID}-descrizione

# Apri PR via GitHub CLI
gh pr create \
  --base sviluppo \
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
git push origin feature/{JIRA-ID}-descrizione
```

Poi apri la PR manualmente:
1. Vai su: `https://github.com/<owner>/<repo>/compare/sviluppo...feature/{JIRA-ID}-descrizione`
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

## Decisioni Comuni

### Merge Strategy

| Situazione | Strategia consigliata |
|-----------|----------------------|
| Feature con storia significativa da preservare | Merge commit |
| Serie di commit WIP / fix intermedi | Squash merge (default su sviluppo) |
| Branch sincronizzato con sviluppo (pochi commit) | Rebase (history lineare) |

Su SIAE, la strategia default per feature → sviluppo e' **squash merge** (cfr. `siae-git-workflow`).

### Quanti reviewer?

Minimo 1 reviewer obbligatorio per merge su sviluppo (regola SIAE).
Per modifiche ad architettura o moduli condivisi: almeno 2.

### La PR e' troppo grande?

Una PR > 400 righe di diff e' difficile da revieware correttamente.
Considera di spezzarla in PR piu' piccole con un branch intermedio.

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
