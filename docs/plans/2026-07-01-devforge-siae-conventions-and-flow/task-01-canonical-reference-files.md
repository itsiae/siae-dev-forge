# Task 01 — File canonici SIAE (environments/plan-deploy/multirepo) + guard test

**Cluster:** A contesto (REQ-DF-01, REQ-DF-02, REQ-DF-06)
**Dipendenze:** nessuna (primo task del cluster A; Task 02 e Task 03 dipendono da questo).

## Goal

Creare tre file canonici versionati sotto `skills/using-devforge/reference/` (ambienti/stage,
PLAN e PLAN+DEPLOY, convenzione multi-repo iac/bff/spa) con contenuto verificato dalle fonti
in-repo, e un test di guardia che asserisce esistenza, sezioni attese e assenza di dati personali.

## File coinvolti

- CREA: `skills/using-devforge/reference/siae-environments.md`
- CREA: `skills/using-devforge/reference/siae-plan-deploy.md`
- CREA: `skills/using-devforge/reference/siae-multirepo.md`
- CREA: `tests/test_canonical_reference_files.py`

## Step TDD

### Step 1 — Scrivi il test fallente

Path: `tests/test_canonical_reference_files.py`

```python
"""Guard test per i 3 file canonici SIAE (REQ-DF-01/02/06).

Verifica: esistenza, sezioni `## ` attese, budget byte (<=1800 ciascuno,
allineato a hooks/session-start head -c per file), e anti-leak
(no email personali salvo whitelist git@github.com, no path macchina
/Users/, no IP salvo whitelist proxy corporate 10.255.1.241).

Vedi precedente: docs/plans/2026-06-24-siae-global-rules-injection/task-01.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = REPO_ROOT / "skills" / "using-devforge" / "reference"

EXPECTED_FILES = {
    "siae-environments.md": {
        "## Discrimina il contesto PRIMA di applicare gli ambienti",
        "## Cloud/AWS — ordine ambienti",
        "## SPORT/PAE/POP — ordine ambienti",
        "## Regola anti-confusione",
        "## Se la fonte non è disponibile",
    },
    "siae-plan-deploy.md": {
        "## Disambiguazione obbligatoria (collisione di nomi)",
        "## PLAN — checklist standard",
        "## PLAN+DEPLOY — progressione ambienti",
        "## Deviazioni",
    },
    "siae-multirepo.md": {
        "## Ruoli",
        "## Regola di routing",
        "## Naming (verificato su org `itsiae`, 2026-07-01)",
        "## Cross-cutting",
    },
}

MAX_BYTES = 1800
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
IP_RE = re.compile(r"(?:[0-9]{1,3}\.){3}[0-9]{1,3}")
ALLOWED_IP = "10.255.1.241"


@pytest.mark.parametrize("filename", sorted(EXPECTED_FILES))
def test_canonical_file_exists(filename):
    assert (REFERENCE_DIR / filename).is_file(), f"missing {filename}"


@pytest.mark.parametrize("filename", sorted(EXPECTED_FILES))
def test_canonical_file_has_expected_sections(filename):
    content = (REFERENCE_DIR / filename).read_text(encoding="utf-8")
    headers = {line.strip() for line in content.splitlines() if line.startswith("## ")}
    missing = EXPECTED_FILES[filename] - headers
    assert not missing, f"{filename} missing sections: {missing}"


@pytest.mark.parametrize("filename", sorted(EXPECTED_FILES))
def test_canonical_file_under_byte_budget(filename):
    size = (REFERENCE_DIR / filename).stat().st_size
    assert size <= MAX_BYTES, f"{filename} is {size} bytes, budget is {MAX_BYTES}"


@pytest.mark.parametrize("filename", sorted(EXPECTED_FILES))
def test_canonical_file_no_leaked_email(filename):
    content = (REFERENCE_DIR / filename).read_text(encoding="utf-8")
    emails = [e for e in EMAIL_RE.findall(content) if e != "git@github.com"]
    assert not emails, f"{filename} leaks personal email(s): {emails}"


@pytest.mark.parametrize("filename", sorted(EXPECTED_FILES))
def test_canonical_file_no_leaked_machine_path(filename):
    content = (REFERENCE_DIR / filename).read_text(encoding="utf-8")
    assert "/Users/" not in content, f"{filename} leaks a machine-local path"
    assert "OneDrive" not in content, f"{filename} leaks a machine-local path"


@pytest.mark.parametrize("filename", sorted(EXPECTED_FILES))
def test_canonical_file_only_whitelisted_ip(filename):
    content = (REFERENCE_DIR / filename).read_text(encoding="utf-8")
    ips = sorted(set(IP_RE.findall(content)))
    disallowed = [ip for ip in ips if ip != ALLOWED_IP]
    assert not disallowed, f"{filename} contains non-whitelisted IP(s): {disallowed}"
```

### Step 2 — Esegui il test e osserva il fallimento atteso

Comando:

```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge" && python3 -m pytest tests/test_canonical_reference_files.py -v
```

Output atteso (i 3 file non esistono ancora — fallimento su `test_canonical_file_exists`):

```
FAILED tests/test_canonical_reference_files.py::test_canonical_file_exists[siae-environments.md] - AssertionError: missing siae-environments.md
FAILED tests/test_canonical_reference_files.py::test_canonical_file_exists[siae-multirepo.md] - AssertionError: missing siae-multirepo.md
FAILED tests/test_canonical_reference_files.py::test_canonical_file_exists[siae-plan-deploy.md] - AssertionError: missing siae-plan-deploy.md
```

(Le altre parametrizzazioni falliscono a cascata con `FileNotFoundError` — atteso, sono skippabili
mentalmente: il segnale che conta è `test_canonical_file_exists` rosso su tutti e 3.)

### Step 3 — Implementa il contenuto minimo (crea i 3 file canonici)

Path: `skills/using-devforge/reference/siae-environments.md`

```markdown
# SIAE Environments

> Fonte canonica versionata (REQ-DF-01). Iniettata da `hooks/session-start`.
> Se questo file manca, DICHIARA l'assenza — non inventare gli stage.

## Discrimina il contesto PRIMA di applicare gli ambienti
- **Cloud/AWS** (datalake/IaC): marker `*.tf`, `terragrunt.hcl`, repo `datalake-*`/`*-iac`.
- **SPORT/PAE/POP** (microservizi OpenShift): marker `pom.xml`+`mvnw`, `Dockerfile`, `chart/`.
- Nel dubbio: ispeziona `.github/workflows/` (terragrunt → cloud; MVN_CD → microservizio).

## Cloud/AWS — ordine ambienti
`dev` → `qa` → `prod` (valore tecnico `AWS_ENV`).
GitHub Environment corrispondenti: `collaudo` / `certificazione` / `produzione`.
Deploy via reusable workflow `terragrunt-plan.yaml` / `cd-terragrunt-plan-deploy.yaml`.

## SPORT/PAE/POP — ordine ambienti
`sviluppo` → `collaudo` → `certificazione` → `produzione`.
Deploy via **git tag** (`git tag sviluppo|collaudo` + push) → build → OpenShift.
Ambienti = namespace OpenShift (repo Variables `OPENSHIFT_NAMESPACE_DEV/_COLL/_CERT/_PROD`).

## Regola anti-confusione
- **collaudo** = stage di TEST (non pre-produzione).
- **certificazione** = stage di PRE-PRODUZIONE (viene dopo collaudo, prima di produzione).
- Non sono sinonimi e non sono intercambiabili.

## Se la fonte non è disponibile
Dichiara esplicitamente "fonte ambienti/stage non disponibile" — non ipotizzare l'elenco.
```

Path: `skills/using-devforge/reference/siae-plan-deploy.md`

```markdown
# SIAE PLAN e PLAN+DEPLOY

> Fonte canonica versionata (REQ-DF-02). Iniettata da `hooks/session-start`.
> Se questo file manca, DICHIARA l'assenza — non inventare la checklist.

## Disambiguazione obbligatoria (collisione di nomi)
Qui "PLAN" = **pipeline infrastrutturale SIAE** (reusable workflow
`terragrunt-plan.yaml`; PLAN+DEPLOY = `cd-terragrunt-plan-deploy.yaml`).
NON è il "PLAN" interno DevForge (EnterPlanMode / `siae-writing-plans`).
Se il task riguarda un design/piano DevForge, questo file non si applica.

## PLAN — checklist standard
1. `terragrunt plan` sull'ambiente target.
2. Review del plan output (risorse create/modificate/distrutte).
3. Nessun `apply` senza un plan verde e revisionato.

## PLAN+DEPLOY — progressione ambienti
- Cloud: `dev` → `qa` → `prod`, **senza salti**.
- Microservizi: `sviluppo` → `collaudo` → `certificazione` → `produzione`, **senza salti**.
- Nessun deploy verso `certificazione`/`produzione` senza il gate previsto:
  produzione = merge su `main`, e solo branch `release/**` può aprire PR verso
  `main` (branching strategy SIAE).

## Deviazioni
Qualsiasi deviazione dalla progressione o dal gate va **segnalata esplicitamente
all'utente**, mai applicata in silenzio.
```

Path: `skills/using-devforge/reference/siae-multirepo.md`

```markdown
# SIAE Multi-repo (iac/bff/spa)

> Fonte canonica versionata (REQ-DF-06). Iniettata da `hooks/session-start`.
> Se questo file manca, DICHIARA l'assenza — non indovinare il repo da toccare.

## Ruoli
- **iac** — Infrastructure as Code: modifiche infra (Terraform/terragrunt).
- **bff** — Backend for Frontend: API/backend.
- **spa** — Single Page Application: frontend.

## Regola di routing
- Modifica infra → repo `*-iac`.
- Modifica API/backend → repo `*-bff`.
- Modifica frontend → repo `*-spa`.
- **Mai** applicare modifiche nel repo sbagliato: se il task è cross-cutting,
  ripartire le modifiche coerentemente sui repo giusti (vedi Cross-cutting).

## Naming (verificato su org `itsiae`, 2026-07-01)
Convenzione a suffisso: `*-iac` (50+ repo), `*-bff` (13 repo), `*-spa` (9 repo).
Triple complete di esempio: `jarvis-{iac,bff,spa}`, `rete-eventi-{core-iac,bff,spa}`,
`routing-algorithm-{core-iac,bff,spa}`, `dataplatform-datacatalog-{iac,bff,spa}`.
Segnale secondario (se il nome non basta): iac = `*.tf`/`terragrunt.hcl`;
bff = servizio backend/API; spa = frontend `package.json`+router/build.
Nota: SIAE usa anche i suffissi `-be`/`-fe`/`-service` per i microservizi
SPORT/PAE — non sostituiscono `iac`/`bff`/`spa`, sono una convenzione diversa.

## Cross-cutting
Un cambiamento che tocca infra + backend + frontend (es. nuovo endpoint con
consumo frontend) va ripartito coerentemente sui tre repo, non concentrato in uno solo.
```

### Step 4 — Esegui il test e osserva il successo

Comando:

```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge" && python3 -m pytest tests/test_canonical_reference_files.py -v
```

Output atteso:

```
tests/test_canonical_reference_files.py::test_canonical_file_exists[siae-environments.md] PASSED
tests/test_canonical_reference_files.py::test_canonical_file_exists[siae-multirepo.md] PASSED
tests/test_canonical_reference_files.py::test_canonical_file_exists[siae-plan-deploy.md] PASSED
tests/test_canonical_reference_files.py::test_canonical_file_has_expected_sections[siae-environments.md] PASSED
tests/test_canonical_reference_files.py::test_canonical_file_has_expected_sections[siae-multirepo.md] PASSED
tests/test_canonical_reference_files.py::test_canonical_file_has_expected_sections[siae-plan-deploy.md] PASSED
tests/test_canonical_reference_files.py::test_canonical_file_under_byte_budget[siae-environments.md] PASSED
tests/test_canonical_reference_files.py::test_canonical_file_under_byte_budget[siae-multirepo.md] PASSED
tests/test_canonical_reference_files.py::test_canonical_file_under_byte_budget[siae-plan-deploy.md] PASSED
tests/test_canonical_reference_files.py::test_canonical_file_no_leaked_email[siae-environments.md] PASSED
tests/test_canonical_reference_files.py::test_canonical_file_no_leaked_email[siae-multirepo.md] PASSED
tests/test_canonical_reference_files.py::test_canonical_file_no_leaked_email[siae-plan-deploy.md] PASSED
tests/test_canonical_reference_files.py::test_canonical_file_no_leaked_machine_path[siae-environments.md] PASSED
tests/test_canonical_reference_files.py::test_canonical_file_no_leaked_machine_path[siae-multirepo.md] PASSED
tests/test_canonical_reference_files.py::test_canonical_file_no_leaked_machine_path[siae-plan-deploy.md] PASSED
tests/test_canonical_reference_files.py::test_canonical_file_only_whitelisted_ip[siae-environments.md] PASSED
tests/test_canonical_reference_files.py::test_canonical_file_only_whitelisted_ip[siae-multirepo.md] PASSED
tests/test_canonical_reference_files.py::test_canonical_file_only_whitelisted_ip[siae-plan-deploy.md] PASSED

======================== 18 passed in 0.XXs ========================
```

### Step 5 — Commit

```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge" && git add skills/using-devforge/reference/siae-environments.md skills/using-devforge/reference/siae-plan-deploy.md skills/using-devforge/reference/siae-multirepo.md tests/test_canonical_reference_files.py && git commit -m "feat(context): file canonici SIAE environments/plan-deploy/multirepo + guard test"
```

## Criteri di accettazione

- [ ] `skills/using-devforge/reference/siae-environments.md` esiste, contiene le 5 sezioni `## ` attese, ordine ambienti Cloud/AWS (`dev→qa→prod`) e SPORT/PAE/POP (`sviluppo→collaudo→certificazione→produzione`) verificati contro `skills/using-devforge/reference/siae-global-rules.md:8-48` (AC1, AC3 di REQ-DF-01).
- [ ] Il file distingue esplicitamente collaudo (test) da certificazione (pre-produzione) in una sezione dedicata (AC2 di REQ-DF-01).
- [ ] Il file include la frase di fallback "dichiara l'assenza" per il caso fonte non disponibile (AC4 di REQ-DF-01 — nota: il fallback *runtime* nel hook è Task 02, qui si documenta solo l'istruzione).
- [ ] `skills/using-devforge/reference/siae-plan-deploy.md` esiste, contiene le 4 sezioni `## ` attese, apre disambiguando esplicitamente PLAN/PLAN+DEPLOY SIAE (terragrunt) da PLAN DevForge interno (AC di REQ-DF-02 "output PLAN segue checklist standard").
- [ ] La sezione PLAN+DEPLOY documenta progressione ambienti senza salti e gate release/**→main (fonte: `skills/siae-branching-strategy-check/reference/branching-strategy.md:19-22`) per entrambi i sistemi (AC2 di REQ-DF-02).
- [ ] La sezione Deviazioni istruisce a segnalarle esplicitamente, mai applicarle in silenzio (AC4 di REQ-DF-02).
- [ ] `skills/using-devforge/reference/siae-multirepo.md` esiste, contiene le 4 sezioni `## ` attese, definisce i ruoli iac/bff/spa da `requirements-devforge.md:19-21` e la regola di routing (AC1/AC2 di REQ-DF-06).
- [ ] La sezione Naming cita la convenzione a suffisso verificata sull'org `itsiae` (`*-iac` 50+, `*-bff` 13, `*-spa` 9) con le 4 triple di esempio e il segnale secondario via marker di stack (AC3 di REQ-DF-06).
- [ ] La sezione Cross-cutting copre il caso di modifica multi-repo coerente (AC4 di REQ-DF-06).
- [ ] Tutti e 3 i file sono ≤ 1800 byte (`wc -c`), coerente col budget dichiarato in `hooks/session-start:296` (`GLOBAL_MEMORY_MAX_BYTES=2000`).
- [ ] `tests/test_canonical_reference_files.py` esiste e i 18 test (`pytest -v`) passano.
- [ ] Anti-leak: nessuna email personale (whitelist `git@github.com`), nessun path `/Users/`/`OneDrive`, nessun IP non whitelisted (`10.255.1.241`) nei 3 file nuovi.
