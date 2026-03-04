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

Aprire una PR è un atto pubblico che coinvolge i reviewer. Rispetta il loro tempo.
Un branch non verificato è un'interruzione mascherata da contributo.

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

## Processo in 5 Step

### Step 1 — Verifica Stato del Branch

🟢 SICURO

```bash
# Stato corrente
git status

# Confronto con sviluppo (quanti commit avanti/dietro?)
git log origin/sviluppo..HEAD --oneline

# Controlla se sviluppo è avanzato
git fetch origin
git log HEAD..origin/sviluppo --oneline
```

**Criteri di OK:**
- [ ] Nessun file non committato (`git status` clean)
- [ ] Tutti i commit sono nel branch (nessun lavoro perso)
- [ ] Conosco quanti commit apporto a sviluppo

**Se sviluppo è avanzato rispetto al tuo branch:**

```
REQUIRED SUB-SKILL: siae-git-workflow
```

Esegui un rebase o merge da sviluppo prima di procedere.

---

### Step 2 — Verifica Test e Build

🟡 MEDIO

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
- [ ] Coverage non è scesa sotto la soglia del progetto

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
- [ ] Ogni commit è atomico (un singolo cambiamento logico)
- [ ] Nessun commit di "fix typo" che potrebbe essere squashato
- [ ] Il JIRA ID è presente nei commit rilevanti

**Se la history è caotica (troppi WIP commit):**

Considera di squashare localmente prima della PR:
```bash
# Squash degli ultimi N commit in uno solo
git rebase -i origin/sviluppo
# Nel editor: lascia "pick" solo sul primo, cambia gli altri in "squash"
```

> ⚠️ Il rebase modifica la history. Farlo SOLO se il branch NON è ancora stato pushato,
> o se è un branch personale non condiviso.

---

### Step 5 — Apri la Pull Request

🔴 ALTO — Pre-flight card obbligatoria

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  PRE-FLIGHT CARD — Apertura PR           ┃
┃  Rischio: 🔴 ALTO                         ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃  Branch:   feature/{JIRA-ID}-...         ┃
┃  Target:   sviluppo                      ┃
┃  Commit:   N commit                      ┃
┃                                          ┃
┃  Checklist:                              ┃
┃  [ ] git status clean                   ┃
┃  [ ] Test suite: tutti verdi             ┃
┃  [ ] Diff revisionato (no debug code)    ┃
┃  [ ] Commit history ordinata             ┃
┃                                          ┃
┃  Confermi apertura PR? [s/N]             ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

**Dopo la conferma:**

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

---

## Decisioni Comuni

### Merge Strategy

| Situazione | Strategia consigliata |
|-----------|----------------------|
| Feature con storia significativa da preservare | Merge commit |
| Serie di commit WIP / fix intermedi | Squash merge (default su sviluppo) |
| Branch sincronizzato con sviluppo (pochi commit) | Rebase (history lineare) |

Su SIAE, la strategia default per feature → sviluppo è **squash merge** (cfr. `siae-git-workflow`).

### Quanti reviewer?

Minimo 1 reviewer obbligatorio per merge su sviluppo (regola SIAE).
Per modifiche ad architettura o moduli condivisi: almeno 2.

### La PR è troppo grande?

Una PR > 400 righe di diff è difficile da revieware correttamente.
Considera di spezzarla in PR più piccole con un branch intermedio.

---

## Anti-Rationalization Table

| Pensiero | Realta' |
|----------|---------|
| "Apro la PR e poi fixo i test rossi" | I reviewer vedono i test rossi. Non aprire PR broken. |
| "E' una modifica piccola, non serve review" | 1 review obbligatoria. Sempre. |
| "Ho testato manualmente, basta" | I test manuali non prevengono regressioni future. |
| "I console.log li tolgo dopo il merge" | Dopo il merge non li togli. Fallo ora. |
| "La history caotica va bene, lo squasha GitHub" | Squash in PR perde contesto. Fallo tu con intenzione. |
| "Il JIRA ID non serve nel commit" | Tracciabilita' obbligatoria. Sempre. |

---

## Classificazione Rischio

| Operazione | Livello | Note |
|-----------|---------|------|
| `git diff`, `git log`, `git status` | 🟢 Sicuro | Solo lettura |
| Esecuzione test suite | 🟡 Medio | Pre-flight consigliata |
| `git push` | 🔴 Alto | Pre-flight obbligatoria |
| Apertura PR | 🔴 Alto | Pre-flight obbligatoria |
| `git rebase -i` | 🔴 Alto | Solo su branch non condivisi |
