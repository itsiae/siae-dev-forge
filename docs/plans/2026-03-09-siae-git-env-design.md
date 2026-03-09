# Design: siae-git-env — GitHub CLI Detection Utility Skill

**Data:** 2026-03-09
**Autore:** DevForge AI
**Stato:** Approvato

---

## Contesto

Le skill git di DevForge (`siae-git-workflow`, `siae-finishing-branch`) contengono
operazioni GitHub-native (apertura PR, merge, status review) che usano `gh` CLI.

**Problema attuale:**
- Nessuna delle skill verifica se `gh` è installato prima di usarlo
- `siae-finishing-branch` usa `gh pr create` senza fallback
- Se `gh` non è disponibile, i comandi falliscono senza alternativa chiara
- Logica di detection assente o duplicata tra skill

**Soluzione:** una micro-skill di utility `siae-git-env` invocata come sub-skill
all'inizio di ogni skill git che ha operazioni GitHub-native nel flusso.

---

## Decisioni Architetturali

### Pattern scelto: Approccio 3 — Skill di utility condivisa

Motivazione: centralizza la detection in un unico punto, estendibile in futuro,
evita duplicazione tra le skill che cresceranno nel catalogo.

**Alternativa scartata:** detection inline in ogni skill → duplicazione e inconsistenza.
**Alternativa scartata:** detection solo in `siae-git-workflow` → non copre invocazioni
dirette di `siae-finishing-branch`.

### Scope v1 (YAGNI)

Controlla solo:
- `gh` installato (`gh --version`)
- `gh` autenticato (`gh auth status`)

Non controlla (fuori scope v1): `git lfs`, `git-crypt`, versione git minima.

---

## Design

### Struttura file

```
skills/
  siae-git-env/
    SKILL.md
```

### Output della skill

La skill produce un blocco di contesto ambiente che Claude porta nella sessione:

```
GIT_ENV CONTEXT
───────────────
gh CLI:    ✅ disponibile (v2.x.x)   |  ❌ non disponibile
GH_MODE:   NATIVE                    |  FALLBACK
```

### GH_MODE vs FALLBACK_MODE

| Operazione | GH_MODE | FALLBACK_MODE |
|---|---|---|
| Apri PR | `gh pr create ...` | Template markdown completo in chat + URL browser |
| Vedi PR | `gh pr list` / `gh pr view` | `git log --oneline` + link GitHub nel browser |
| Merge PR | `gh pr merge` | Istruzioni UI GitHub (URL specifico) |
| Stato review | `gh pr status` | Istruzioni UI GitHub |

**Principio:** in FALLBACK_MODE nessuna operazione viene omessa. Ogni operazione
GitHub-native ha un'alternativa completa (template, URL, istruzioni step-by-step).

### Skill che invocano siae-git-env

| Skill | Invoca siae-git-env | Motivazione |
|---|---|---|
| `siae-git-workflow` | ✅ Step 0 | Flusso merge/promozione usa GitHub |
| `siae-finishing-branch` | ✅ Step 0 | `gh pr create` in Step 5 |
| `siae-git-worktrees` | ❌ non necessario | Nessuna operazione GitHub-native |

### Integrazione nelle skill esistenti

Ogni skill interessata aggiunge all'inizio:

```markdown
## 0. Environment Check

REQUIRED SUB-SKILL: siae-git-env

Esegui siae-git-env prima di qualsiasi operazione git.
Il GH_MODE determinato qui vale per tutta la sessione.
```

Nelle sezioni che usano `gh`, la skill specifica esplicitamente:

```markdown
**Se GH_MODE:**   `gh pr create ...`
**Se FALLBACK:**  [template PR completo + URL apertura manuale]
```

---

## Criteri di Accettazione

- [ ] `siae-git-env/SKILL.md` creata con check `gh --version` e `gh auth status`
- [ ] Output GIT_ENV CONTEXT mostrato all'utente in modo leggibile
- [ ] `siae-git-workflow` aggiornata con Step 0 che invoca `siae-git-env`
- [ ] `siae-finishing-branch` aggiornata con Step 0 + comportamento condizionale in Step 5
- [ ] In FALLBACK_MODE ogni operazione GitHub-native ha alternativa completa
- [ ] `plugin.json` aggiornato con nuova skill nel catalogo

---

## Stima Story Points

**SP: 3** — Moderato. Nuova skill da creare + aggiornamento 2 skill esistenti.
Nessuna incognita tecnica, ma richiede attenzione ai fallback per ogni operazione.

---

## JIRA TICKET OUTPUT

```
Tipo:        Task
Sommario:    Add siae-git-env utility skill for GitHub CLI detection
Descrizione: Creare micro-skill siae-git-env che verifica la presenza e
             autenticazione di gh CLI, e aggiornare siae-git-workflow e
             siae-finishing-branch per usarla come sub-skill Step 0.
Story Points: 3
Labels:      devforge, skills, git
Acceptance Criteria:
  - [ ] siae-git-env/SKILL.md creata con detection gh + auth
  - [ ] GIT_ENV CONTEXT mostrato in modo leggibile
  - [ ] siae-git-workflow aggiornata con Step 0
  - [ ] siae-finishing-branch aggiornata con Step 0 + fallback condizionale
  - [ ] FALLBACK_MODE copre tutte le operazioni GitHub-native
  - [ ] plugin.json aggiornato
```
