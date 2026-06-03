---
name: siae-release-pr-to-main
description: >
  Use when promoting a release branch to main by opening a PR `release/{area}_DL_{increment}` → `main`,
  optionally mergiando prima la feature branch corrente (o una passata in input) dentro la release.
  Trigger: "pr verso main", "promuovi release", "release to main", "apri PR main", "merge feature in release e PR",
  "promozione main", "siae-release-pr-to-main", "pr release main".
---

# SIAE Release PR to Main — DevForge

> **Tipo:** Rigid | **Fase SDLC:** 6. Promozione → main

---

## LEGGE DI FERRO

```
LA RELEASE SI PROMUOVE A main SOLO VIA PR. IL MERGE FEATURE→RELEASE È OPT-IN.
```

Niente push diretto su `main`. Niente merge automatico della feature dentro la release senza conferma esplicita dell'utente.

---

## Input Richiesti

| Parametro     | Descrizione                              | Esempio          | Obbligatorio |
|---------------|------------------------------------------|------------------|--------------|
| `area`        | Area / dominio funzionale                | `EDW`            | Sì           |
| `increment`   | Increment / sprint id                    | `01_28`          | Sì           |
| `feature`     | Branch feature da mergiare nella release | `EDW-1566`       | No           |
| `do_merge`    | Eseguire merge feature→release           | `true` / `false` | No (default `false`) |

Naming derivato (convenzione SIAE):
- **Release branch:** `release/{area}_DL_{increment}` → es. `release/EDW_DL_01_28`
- **Feature branch:** `feature/{area}_DL_{increment}/{feature}` → es. `feature/EDW_DL_01_28/EDW-1566`

Se `area` o `increment` mancano, **fermati e chiedili**. Non inventarli mai.

---

## Pre-flight Card (ALTO)

Prima di qualsiasi azione mostra all'utente:

```
┌─ SIAE Release PR to Main ──────────────────────────────────┐
│ Repo:        <repo>                                        │
│ Area:        <area>                                        │
│ Increment:   <increment>                                   │
│ Release:     release/<area>_DL_<increment>                 │
│ Feature:     <feature or "—">                              │
│ Merge plan:  <do_merge ? "feature → release" : "skip">     │
│ PR target:   release/<area>_DL_<increment> → main          │
└────────────────────────────────────────────────────────────┘
```

Se `do_merge` non è stato fornito esplicitamente dall'utente, **chiedilo** con AskUserQuestion:
- "Fare merge di `feature/...` dentro `release/...` prima di aprire la PR?" → opzioni: `No, salta merge (Recommended)` / `Sì, esegui merge`.

Default = **No merge**.

---

## Procedura

### 0. Validazione

1. Verifica che la working directory sia un repo git: `git rev-parse --is-inside-work-tree`.
2. Verifica che il remote `origin` punti a un repo GitHub `itsiae/*` (branching strategy SIAE).
3. `git fetch origin`.
4. Verifica esistenza di:
   - `origin/release/{area}_DL_{increment}`
   - `origin/main`
   - `origin/feature/{area}_DL_{increment}/{feature}` **solo se** `feature` è fornito.

Se uno dei branch non esiste → STOP, segnala all'utente.

### 1. Working tree dirty?

`git status --porcelain`. Se ci sono modifiche non committate:
- Se il diff è dominato da line-ending (insertions == deletions su molti file), è quasi certamente un artefatto WSL CRLF/LF. Stasha con:
  ```
  git stash push -u -m "auto-stash-before-release-pr"
  ```
  e avvisa l'utente che lo stash è recuperabile.
- Altrimenti → STOP, chiedi all'utente cosa fare (commit / stash / abort).

### 2. Checkout release e aggiornamento

```
git checkout release/{area}_DL_{increment}
git pull --ff-only origin release/{area}_DL_{increment}
```

### 3. Merge feature → release (SOLO se `do_merge=true`)

```
git merge --no-ff feature/{area}_DL_{increment}/{feature} \
  -m "merge(release): {feature} into release/{area}_DL_{increment}"
```

In caso di conflitti → STOP, **non risolvere automaticamente**. Segnala i file in conflitto e chiedi all'utente.

Push del merge commit:
```
git push origin release/{area}_DL_{increment}
```

> Nota: il push di un merge commit su un branch condiviso può richiedere conferma esplicita dell'utente (auto-mode classifier). Se viene negato, fermati e chiedi autorizzazione.

### 4. Verifica esistenza PR

```
gh pr list --base main --head release/{area}_DL_{increment} --state open --json number,url
```

Se esiste già una PR aperta → restituisci l'URL, **non aprirne una nuova**.

### 5. Apertura PR verso main

```
gh pr create \
  --base main \
  --head release/{area}_DL_{increment} \
  --title "release({area}_DL_{increment}): promote to main" \
  --body "$(cat <<'EOF'
## Summary
- Promozione release `release/{area}_DL_{increment}` verso `main`
- <descrivere brevemente cosa contiene la release: feature mergeate, fix, moduli toccati>

## Test plan
- [ ] Pipeline plan_dev verde
- [ ] Pipeline plan_qa verde
- [ ] Review IaC e moduli toccati
- [ ] Validazione logica Glue / Step Functions (se applicabile)

Co-Authored-By: SIAE DevForge
EOF
)"
```

Se è stato fatto merge della feature in step 3, includere nel summary anche la feature mergiata.

### 6. Output finale

Mostra all'utente:
- URL della PR creata (o esistente).
- Se è stato fatto stash in step 1, ricordare il nome dello stash.
- Branch corrente alla fine (resta su `release/...` se l'utente non ha chiesto altro).

---

## Modalità di invocazione

```
/siae-release-pr-to-main area=EDW increment=01_28
/siae-release-pr-to-main area=EDW increment=01_28 feature=EDW-1566 do_merge=true
/siae-release-pr-to-main area=EDW increment=01_28 feature=EDW-1566   # chiederà se mergiare
```

Se l'utente fornisce input in linguaggio naturale ("apri PR per EDW increment 01_28") → mappa ai parametri ed esegui la pre-flight card prima di procedere.

---

## Cosa NON fare

- ❌ Non pushare mai su `main` direttamente.
- ❌ Non fare merge della feature nella release senza conferma esplicita (default = no).
- ❌ Non risolvere conflitti di merge automaticamente.
- ❌ Non inventare `area` o `increment` se non forniti.
- ❌ Non usare `--no-verify`, `--force`, `reset --hard` su branch condivisi.
- ❌ Non eseguire `git config` per cambiare identità o remote.

---

## Checklist finale

- [ ] Pre-flight card mostrata
- [ ] `do_merge` confermato (o default `false` applicato)
- [ ] Release branch aggiornato da origin
- [ ] (Opt) Merge feature→release effettuato senza conflitti e pushato
- [ ] PR verso main creata (o riutilizzata se già esistente)
- [ ] URL PR restituito all'utente
