# Task 03 — Repoint onboarding alla fonte canonica ambienti

**Cluster:** A contesto (REQ-DF-01)
**Dipendenze:** Task 01 (crea `skills/using-devforge/reference/siae-environments.md`)

**Goal:** Rimuovere le liste ambienti hardcoded (4-env inline + tag pattern non verificati) da `skills/siae-onboarding/SKILL.md` e `skills/siae-onboarding/reference/factory-configs.md`, sostituendole con un puntatore alla fonte canonica `skills/using-devforge/reference/siae-environments.md`.

## File coinvolti
- MODIFICA: `skills/siae-onboarding/SKILL.md` — blocco `.siae-config.json` (righe 48-55, array `environments` a riga 52) e tabella `### 3.2 Ambienti` (righe 166-174).
- MODIFICA: `skills/siae-onboarding/reference/factory-configs.md` — tabella `### Ambienti OpenShift` (righe 98-105), blocco `### Struttura Repository` (righe 178-198), item 4 in `### Regole CI/CD Comuni` (righe 239-245).
- CREA: `tests/hooks/onboarding-env-repoint.test.sh` (guard test grep-based).

## Step TDD

### Step 1 — Scrivi il test fallente (COMPLETO)
Path: `tests/hooks/onboarding-env-repoint.test.sh`
```bash
#!/usr/bin/env bash
# test: onboarding-env-repoint — asserisce che le liste ambienti hardcoded
# siano state rimosse da siae-onboarding e sostituite da un puntatore
# alla fonte canonica skills/using-devforge/reference/siae-environments.md
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

SKILL_MD="${REPO_ROOT}/skills/siae-onboarding/SKILL.md"
FACTORY_MD="${REPO_ROOT}/skills/siae-onboarding/reference/factory-configs.md"
CANONICAL="skills/using-devforge/reference/siae-environments.md"

PASS=0; FAIL=0
ok(){ if eval "$2"; then echo "  PASS  $1"; PASS=$((PASS+1)); else echo "  FAIL  $1"; FAIL=$((FAIL+1)); fi; }

echo "TEST onboarding-env-repoint"

# T1: i tag pattern sospetti (mai verificati) non devono comparire in SKILL.md
ok "T1: nessun tag pattern v*.*.*-dev.* in SKILL.md" \
  '! grep -qF "v*.*.*-dev.*" "$SKILL_MD"'
ok "T1b: nessun tag pattern v*.*.*-rc.* in SKILL.md" \
  '! grep -qF "v*.*.*-rc.*" "$SKILL_MD"'
ok "T1c: nessun tag pattern v*.*.*-cert.* in SKILL.md" \
  '! grep -qF "v*.*.*-cert.*" "$SKILL_MD"'

# T2: la tabella "### 3.2 Ambienti" con colonna "Tag pattern" non deve piu' esistere
ok "T2: nessuna colonna 'Tag pattern' in SKILL.md" \
  '! grep -qF "Tag pattern" "$SKILL_MD"'

# T3: SKILL.md punta alla fonte canonica
ok "T3: SKILL.md referenzia siae-environments.md" \
  'grep -qF "$CANONICAL" "$SKILL_MD"'

# T4: il blocco .siae-config.json non elenca piu' i 4 ambienti inline
ok "T4: nessun array environments hardcoded in SKILL.md" \
  '! grep -qF "\"sviluppo\", \"collaudo\", \"certificazione\", \"produzione\"" "$SKILL_MD"'

# T5: factory-configs.md non ha piu' i tag pattern sospetti collaudo/cert/prod
ok "T5: nessun tag pattern v*.*.*-rc.* in factory-configs.md" \
  '! grep -qF "v*.*.*-rc.*" "$FACTORY_MD"'
ok "T5b: nessun tag pattern v*.*.*-cert.* in factory-configs.md" \
  '! grep -qF "v*.*.*-cert.*" "$FACTORY_MD"'

# T6: factory-configs.md non elenca piu' i 4 ambienti come "regola comune" hardcoded
ok "T6: nessuna riga '4 ambienti: sviluppo, collaudo' in factory-configs.md" \
  '! grep -qF "4 ambienti**: sviluppo, collaudo, certificazione, produzione" "$FACTORY_MD"'

# T7: factory-configs.md punta alla fonte canonica
ok "T7: factory-configs.md referenzia siae-environments.md" \
  'grep -qF "$CANONICAL" "$FACTORY_MD"'

echo ""; echo "PASS=$PASS FAIL=$FAIL"; [ "$FAIL" -eq 0 ]
```

### Step 2 — Esegui e osserva il FAIL
Comando:
```bash
bash "tests/hooks/onboarding-env-repoint.test.sh"
```
Output atteso (FAIL, i file non sono ancora stati modificati):
```
TEST onboarding-env-repoint
  FAIL  T1: nessun tag pattern v*.*.*-dev.* in SKILL.md
  FAIL  T1b: nessun tag pattern v*.*.*-rc.* in SKILL.md
  FAIL  T1c: nessun tag pattern v*.*.*-cert.* in SKILL.md
  FAIL  T2: nessuna colonna 'Tag pattern' in SKILL.md
  FAIL  T3: SKILL.md referenzia siae-environments.md
  FAIL  T4: nessun array environments hardcoded in SKILL.md
  FAIL  T5: nessun tag pattern v*.*.*-rc.* in factory-configs.md
  FAIL  T5b: nessun tag pattern v*.*.*-cert.* in factory-configs.md
  FAIL  T6: nessuna riga '4 ambienti: sviluppo, collaudo' in factory-configs.md
  FAIL  T7: factory-configs.md referenzia siae-environments.md

PASS=0 FAIL=10
```
Exit code: `1`.

### Step 3 — Implementa il minimo necessario

**3a. `skills/siae-onboarding/SKILL.md` righe 48-55** (blocco `.siae-config.json`), sostituire:
```
```json
{
  "factory": "digital | core-platforms | data-platform | devops-infra",
  "stack": ["java", "ts-frontend", "ts-backend", "python", "iac"],
  "environments": ["sviluppo", "collaudo", "certificazione", "produzione"],
  "cicd": { "actionsRepo": "itsiae/siae-gh-actions", "actionsVersion": "v2.x" }
}
```
```
con:
```
```json
{
  "factory": "digital | core-platforms | data-platform | devops-infra",
  "stack": ["java", "ts-frontend", "ts-backend", "python", "iac"],
  "environments": ["<vedi fonte canonica ambienti>"],
  "cicd": { "actionsRepo": "itsiae/siae-gh-actions", "actionsVersion": "v2.x" }
}
```

> **Ambienti:** l'elenco ordinato e i due modelli (Cloud/AWS vs SPORT/PAE/OpenShift) sono
> nella fonte canonica `skills/using-devforge/reference/siae-environments.md` (iniettata
> a session-start). Non hardcodare qui i valori: consultala per popolare `environments`.
```

**3b. `skills/siae-onboarding/SKILL.md` righe 166-174** (tabella `### 3.2 Ambienti`), sostituire:
```
### 3.2 Ambienti

| Ambiente | Scopo | Tag pattern |
|----------|-------|-------------|
| **sviluppo** | Sviluppo e test interni | `v*.*.*-dev.*` |
| **collaudo** | Test di integrazione | `v*.*.*-rc.*` |
| **certificazione** | UAT e validazione | `v*.*.*-cert.*` |
| **produzione** | Ambiente live | `v*.*.*` |
```
con:
```
### 3.2 Ambienti

> **Fonte canonica:** l'elenco ordinato di ambienti/stage e le regole di deploy
> (Cloud/AWS: `dev`→`qa`→`prod`; SPORT/PAE/OpenShift: `sviluppo`→`collaudo`→`certificazione`→`produzione`
> via git tag) sono in `skills/using-devforge/reference/siae-environments.md`, iniettato a
> session-start. Consultala prima di assumere nomi o pattern di tag: non sono documentati
> qui per evitare drift tra due copie della stessa informazione.
```

**3c. `skills/siae-onboarding/reference/factory-configs.md` righe 98-105** (tabella `### Ambienti OpenShift`), sostituire:
```
### Ambienti OpenShift

| Ambiente | Namespace pattern | Note |
|----------|-------------------|------|
| sviluppo | `<app>-dev` | Deploy automatico su push in `develop` |
| collaudo | `<app>-coll` | Deploy su tag `v*.*.*-rc.*` |
| certificazione | `<app>-cert` | Deploy su tag `v*.*.*-cert.*` |
| produzione | `<app>-prod` | Deploy su tag `v*.*.*` con approvazione |
```
con:
```
### Ambienti OpenShift

> **Fonte canonica:** l'ordine ambienti (`sviluppo`→`collaudo`→`certificazione`→`produzione`)
> e il meccanismo di deploy via git tag sono in
> `skills/using-devforge/reference/siae-environments.md`. Il namespace pattern (`<app>-dev`,
> `<app>-coll`, `<app>-cert`, `<app>-prod`) resta specifico di questa factory (Core Platforms/OpenShift).
```

**3d. `skills/siae-onboarding/reference/factory-configs.md` righe 178-198** (blocco `### Struttura Repository`), sostituire il code block con i sotto-percorsi `sviluppo/`, `collaudo/`, `certificazione/`, `produzione/`:
```
### Struttura Repository

```
infrastructure/
  _envcommon/           # Moduli Terragrunt condivisi tra ambienti
  sviluppo/
    account.hcl
    <regione>/
      <servizio>/
        terragrunt.hcl
  collaudo/
    account.hcl
    <regione>/
      <servizio>/
        terragrunt.hcl
  certificazione/
    ...
  produzione/
    ...
  terragrunt.hcl        # Root config
```
```
con:
```
### Struttura Repository

> **Nota ambienti:** questa factory (DevOps/Infra) usa il modello Cloud/AWS documentato in
> `skills/using-devforge/reference/siae-environments.md` (valore tecnico `dev`→`qa`→`prod`).
> Le directory sotto `infrastructure/` seguono comunque il naming GitHub Environment
> (`sviluppo`/`collaudo`/`certificazione`/`produzione`) per storico repo — verifica la
> fonte canonica prima di assumere quale nome si applica al contesto tecnico vs GitHub Environment.

```
infrastructure/
  _envcommon/           # Moduli Terragrunt condivisi tra ambienti
  <ambiente-1>/
    account.hcl
    <regione>/
      <servizio>/
        terragrunt.hcl
  <ambiente-2>/
    ...
  <ambiente-N>/
    ...
  terragrunt.hcl        # Root config
```
```

**3e. `skills/siae-onboarding/reference/factory-configs.md` righe 239-245** (`### Regole CI/CD Comuni`), sostituire:
```
## Regole CI/CD Comuni

Tutte le factory condividono:

1. **GitHub Actions** riutilizzabili dal repository `itsiae/siae-gh-actions` (versione `v2.x`)
2. **Deploy tag-based**: il push di un tag semantico triggera il deploy sull'ambiente corrispondente
3. **Qodana** come quality gate obbligatorio su ogni PR
4. **4 ambienti**: sviluppo, collaudo, certificazione, produzione
5. **Branch protection** su `main`: PR obbligatoria con almeno 1 review approvata
```
con:
```
## Regole CI/CD Comuni

Tutte le factory condividono:

1. **GitHub Actions** riutilizzabili dal repository `itsiae/siae-gh-actions` (versione `v2.x`)
2. **Deploy tag-based**: il push di un tag semantico triggera il deploy sull'ambiente corrispondente
3. **Qodana** come quality gate obbligatorio su ogni PR
4. **Ambienti**: vedi fonte canonica `skills/using-devforge/reference/siae-environments.md` (l'elenco e l'ordine variano per Cloud/AWS vs SPORT/PAE/OpenShift, non c'e' un unico "4 ambienti" valido ovunque)
5. **Branch protection** su `main`: PR obbligatoria con almeno 1 review approvata
```

Applica le 5 edit sopra con lo strumento di editing file (sostituzione esatta del blocco citato, char-for-char sui delimitatori indicati).

### Step 4 — Esegui e osserva il PASS
Comando:
```bash
bash "tests/hooks/onboarding-env-repoint.test.sh"
```
Output atteso:
```
TEST onboarding-env-repoint
  PASS  T1: nessun tag pattern v*.*.*-dev.* in SKILL.md
  PASS  T1b: nessun tag pattern v*.*.*-rc.* in SKILL.md
  PASS  T1c: nessun tag pattern v*.*.*-cert.* in SKILL.md
  PASS  T2: nessuna colonna 'Tag pattern' in SKILL.md
  PASS  T3: SKILL.md referenzia siae-environments.md
  PASS  T4: nessun array environments hardcoded in SKILL.md
  PASS  T5: nessun tag pattern v*.*.*-rc.* in factory-configs.md
  PASS  T5b: nessun tag pattern v*.*.*-cert.* in factory-configs.md
  PASS  T6: nessuna riga '4 ambienti: sviluppo, collaudo' in factory-configs.md
  PASS  T7: factory-configs.md referenzia siae-environments.md

PASS=10 FAIL=0
```
Exit code: `0`.

### Step 5 — Commit
```bash
git add skills/siae-onboarding/SKILL.md skills/siae-onboarding/reference/factory-configs.md tests/hooks/onboarding-env-repoint.test.sh
git commit -m "fix(onboarding): repoint liste ambienti hardcoded alla fonte canonica siae-environments.md"
```

## Criteri di accettazione
- [ ] `skills/siae-onboarding/SKILL.md` non contiene piu' i tag pattern `v*.*.*-dev.*`/`-rc.*`/`-cert.*` ne' la tabella `Tag pattern` in "3.2 Ambienti" (AC3 — non hardcodare fonte non versionata/non verificata).
- [ ] `skills/siae-onboarding/SKILL.md` (blocco `.siae-config.json` e sezione "3.2 Ambienti") rimanda esplicitamente a `skills/using-devforge/reference/siae-environments.md` (AC3).
- [ ] `skills/siae-onboarding/reference/factory-configs.md` non contiene piu' i tag pattern `v*.*.*-rc.*`/`-cert.*` in "Ambienti OpenShift", ne' la riga "4 ambienti: sviluppo, collaudo, certificazione, produzione" in "Regole CI/CD Comuni" (AC3).
- [ ] `skills/siae-onboarding/reference/factory-configs.md` rimanda a `skills/using-devforge/reference/siae-environments.md` in almeno 2 punti (Ambienti OpenShift + Regole CI/CD Comuni) (AC3).
- [ ] Il namespace pattern OpenShift (`<app>-dev`, `<app>-coll`, `<app>-cert`, `<app>-prod`) resta documentato in factory-configs.md — non e' un tag pattern e non fa parte dell'invenzione da rimuovere (nessuna perdita di informazione legittima, solo rimozione dei tag semver non verificati).
- [ ] `bash tests/hooks/onboarding-env-repoint.test.sh` → `PASS=10 FAIL=0`, exit code 0.
- [ ] Nessuna regressione: le sezioni non toccate di `SKILL.md` e `factory-configs.md` restano invariate.
