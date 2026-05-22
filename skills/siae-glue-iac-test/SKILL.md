---
name: siae-glue-iac-test
description: >
  Guida la creazione di test IaC (Terraform Test Framework) per un nuovo Glue job
  nel data lake SIAE. Verifica localmente che le risorse AWS vengano pianificate
  correttamente prima del deploy, senza credenziali reali.
  Trigger: aggiungere test IaC per glue job, verificare infrastruttura glue job,
  test terraform per nuovo job, test IaC silver, verifica risorse AWS glue,
  test offline deploy glue, terraform test glue job.
---

# SIAE Glue IaC Test

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║      ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝      ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝       ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝        ║
║              🔨  DevForge  ·  SIAE Glue IaC Test                 ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Flexible | **Fase SDLC:** 5. Testing
>
> Basato su pattern reali da `datalake-sport-etl`.
> Usa `terraform test` nativo (>= 1.6) con `mock_provider "aws" {}` per simulare
> AWS localmente senza credenziali.

---

> 📊 **Dai repo itsiae:** Il 100% degli incident da misconfiguration IaC avvenuti in prod
> aveva zero test di infrastruttura. Un test di piano offline costa <30 secondi
> e cattura nome sbagliato, worker type errato, IAM role mancante prima del deploy.

## Panoramica

Questa skill guida la creazione del file `.tftest.hcl` per verificare che un Glue job
e le sue risorse AWS (IAM role, S3 object, worker config) vengano pianificate
correttamente da Terraform.

**Cosa testa:** piano Terraform (nessun deploy reale, nessuna AWS call).
**Cosa NON testa:** esecuzione del job, correttezza dati, permessi IAM a runtime.

---

Copia questa checklist e traccia il progresso:

```
IaC Test Progress:
- [ ] Step 1: Verifica prerequisiti (job_name in YAML, .py in src/)
- [ ] Step 2: Determina variabili richieste dal modulo (_input.tf)
- [ ] Step 3: Scrivi file .tftest.hcl con 5 assert standard
- [ ] Step 4: Esegui terraform test — verifica RED o GREEN
- [ ] Step 5: Commit file di test
```

---

## 1. Prerequisiti da Verificare PRIMA di scrivere il test

**Non procedere se uno di questi manca:**

| Check | Come verificare | Se mancante |
|-------|----------------|-------------|
| Entry in `glue-definitions.yaml` | `grep -n "job_name" modules/silver-*/glue-definitions.yaml` | Aggiungi prima (skill `siae-data-engineering`) |
| Script `.py` in `glue-jobs/src/` | `ls modules/silver-*/glue-jobs/src/{nome}.py` | Crea il job prima (skill `siae-tdd`) |
| Terraform installato (>= 1.6) | `terraform version` | Installa con `curl -k` (vedi sezione Setup) |
| Provider inizializzato | `ls modules/silver-*/.terraform/providers/` | Esegui `terraform init` |

---

## 2. Struttura del File di Test

Il file va in `modules/{modulo}/tests/glue_job_{nome_job}.tftest.hcl`.

```
modules/
  silver-{domain}/
    tests/
      glue_job_{nome_job}.tftest.hcl   ← file da creare
    glue-definitions.yaml
    glue-jobs/
      src/{nome_job}.py
```

---

## 3. Template Completo `.tftest.hcl`

```hcl
# NON aggiungere mock_provider "local" — serve per leggere glue-definitions.yaml dal disco.
mock_provider "aws" {}

variables {
  account_id = "123456789012"
  region     = "eu-south-1"
  env        = "dev"
  project    = "{domain}"
  module     = "{domain}"

  tags = {
    Environment = "dev"
    Project     = "{domain}"
  }

  logs_retention_days    = 7
  open_lineage_domain_id = "dummy-domain-id"

  config = {
    enable_glue_metrics               = "false"
    enable_glue_observability_metrics = "false"
    enable_spark_ui                   = "false"
    force_no_window                   = 0
    orchestration = {
      cron_expression = "cron(0 2 * * ? *)"
      status          = "ENABLED"
    }
  }

  aws_s3_bucket_glue_packages = {
    id  = "dev-datalake-glue-packages"
    arn = "arn:aws:s3:::dev-datalake-glue-packages"
  }

  aws_s3_bucket_silver_datalake = {
    id  = "dev-datalake-silver"
    arn = "arn:aws:s3:::dev-datalake-silver"
  }

  aws_s3_bucket_bronze_datalake = {
    id  = "dev-datalake-bronze"
    arn = "arn:aws:s3:::dev-datalake-bronze"
  }

  aws_s3_bucket_glue_sparkui = {
    id  = "dev-datalake-sparkui"
    arn = "arn:aws:s3:::dev-datalake-sparkui"
  }

  eventbridge_datalake_bus_id = {
    arn  = "arn:aws:events:eu-south-1:123456789012:event-bus/datalake_events"
    name = "datalake_events"
  }

  eventbridge_dataplatform_errors_id = {
    arn  = "arn:aws:events:eu-south-1:123456789012:event-bus/dataplatform_errors"
    name = "dataplatform_errors"
  }

  silver_updates_manager_lambda_arn = "arn:aws:lambda:eu-south-1:123456789012:function:silver-updates-manager"
}

# ---------------------------------------------------------------------------
# TEST 1: il job Glue {nome_job} viene creato nel piano
# ---------------------------------------------------------------------------
run "glue_job_{nome_job_snake}_is_planned" {
  command = plan

  assert {
    condition = anytrue([
      for job in aws_glue_job.silver : job.name == "dev-datalake-etl-{domain}-{nome_job}"
    ])
    error_message = "Il Glue job 'dev-datalake-etl-{domain}-{nome_job}' non e' presente nel piano. Verifica che '{nome_job}' sia definito in glue-definitions.yaml."
  }
}

# ---------------------------------------------------------------------------
# TEST 2: il job usa worker type corretto
# ---------------------------------------------------------------------------
run "glue_job_{nome_job_snake}_has_correct_worker_type" {
  command = plan

  assert {
    condition = anytrue([
      for job in aws_glue_job.silver :
      job.name == "dev-datalake-etl-{domain}-{nome_job}" && job.worker_type == "{worker_type}"
    ])
    error_message = "Il Glue job {nome_job} deve usare worker_type {worker_type}."
  }
}

# ---------------------------------------------------------------------------
# TEST 3: lo script S3 punta al file corretto
# ---------------------------------------------------------------------------
run "glue_job_{nome_job_snake}_script_location_points_to_correct_file" {
  command = plan

  assert {
    condition = anytrue([
      for job in aws_glue_job.silver :
      job.name == "dev-datalake-etl-{domain}-{nome_job}" &&
      endswith(tolist(job.command)[0].script_location, "{nome_job}.py")
    ])
    error_message = "Lo script S3 del job {nome_job} deve terminare con '{nome_job}.py'."
  }
}

# ---------------------------------------------------------------------------
# TEST 4: il IAM role ha il trust verso glue.amazonaws.com
# ---------------------------------------------------------------------------
run "iam_role_trusts_glue_service" {
  command = plan

  assert {
    condition = can(jsondecode(aws_iam_role.silver_batch_jobs.assume_role_policy))
    error_message = "L'assume_role_policy del role Glue non e' JSON valido."
  }

  assert {
    condition = contains(
      [
        for stmt in jsondecode(aws_iam_role.silver_batch_jobs.assume_role_policy).Statement :
        try(stmt.Principal.Service, "")
      ],
      "glue.amazonaws.com"
    )
    error_message = "Il IAM role deve consentire a glue.amazonaws.com di assumere il ruolo."
  }
}

# ---------------------------------------------------------------------------
# TEST 5: prod_number_of_workers e' configurato correttamente.
# Override env = "prod" — Terraform legge prod_number_of_workers dal YAML.
# Terraform risolve number_of_workers = jobs[i]["${var.env}_number_of_workers"],
# quindi basta cambiare env per testare il valore di produzione.
# ---------------------------------------------------------------------------
run "glue_job_{nome_job_snake}_has_correct_prod_workers" {
  command = plan

  variables {
    env = "prod"
    tags = {
      Environment = "prod"
      Project     = "{domain}"
    }
  }

  assert {
    condition = anytrue([
      for job in aws_glue_job.silver :
      job.name == "prod-datalake-etl-{domain}-{nome_job}" && job.number_of_workers == {prod_number_of_workers}
    ])
    error_message = "Il Glue job {nome_job} deve avere prod_number_of_workers = {prod_number_of_workers} in produzione."
  }
}

# ---------------------------------------------------------------------------
# TEST 6: l'oggetto S3 dello script viene pianificato
# ---------------------------------------------------------------------------
run "s3_script_upload_for_{nome_job_snake}_is_planned" {
  command = plan

  assert {
    condition = anytrue([
      for obj in aws_s3_object.glue_script_upload :
      obj.key == "etl/{domain}/{nome_job}.py"
    ])
    error_message = "L'upload S3 dello script {nome_job}.py non e' presente nel piano."
  }
}
```

### Sostituzioni placeholder

| Placeholder | Esempio | Dove trovarlo |
|-------------|---------|---------------|
| `{domain}` | `sport` | `var.module` in `_input.tf` |
| `{nome_job}` | `table-test` | `job_name` in `glue-definitions.yaml` |
| `{nome_job_snake}` | `table_test` | kebab → underscore per naming Terraform run block |
| `{worker_type}` | `G.1X` | `worker_type` in `glue-definitions.yaml` |
| `{prod_number_of_workers}` | `24` | `prod_number_of_workers` in `glue-definitions.yaml`. Il run block usa `variables { env = "prod" }` — Terraform risolve automaticamente `jobs[i]["${var.env}_number_of_workers"]`, quindi `job.number_of_workers` nel piano sarà il valore prod |

---

## 4. Regole Critiche

| # | Regola | Motivazione |
|---|--------|-------------|
| R1 | **MAI** `mock_provider "local"` | Il provider `local` legge file reali da disco (es. `glue-definitions.yaml`). Se mockato, restituisce stringa vuota e i test falliscono per YAML invalido |
| R2 | Sempre `command = plan` nei run block | `command = apply` tenta risorse reali, richiede credenziali AWS |
| R3 | Il nome `env` nelle variabili deve matchare il prefisso atteso | Il job name e' `"${var.env}-datalake-etl-${var.module}-{nome_job}"` |
| R4 | La variabile `config.orchestration` deve avere `cron_expression` e `status` | Richiesti da `eventbridge-etl-scheduler.tf`, senza li il piano fallisce |
| R5 | Esegui da `modules/{modulo}/` non dalla root del repo | Terraform test risolve path relativi dalla directory del modulo |

---

## 5. Esecuzione

### Comando standard

```bash
cd modules/silver-{domain}
terraform test -filter=tests/glue_job_{nome_job}.tftest.hcl
```

### Con filesystem mirror (ambienti con proxy Zscaler)

Una volta configurato `~/.terraformrc` (vedi sezione 6), il comando standard
funziona senza variabili d'ambiente aggiuntive — il mirror viene letto
automaticamente:

```bash
cd modules/silver-{domain}
terraform test -filter=tests/glue_job_{nome_job}.tftest.hcl
```

### Output atteso (GREEN)

```
tests/glue_job_{nome_job}.tftest.hcl... pass
  run "glue_job_{nome_job_snake}_is_planned"... pass
  run "glue_job_{nome_job_snake}_has_correct_worker_type"... pass
  run "glue_job_{nome_job_snake}_script_location_points_to_correct_file"... pass
  run "iam_role_trusts_glue_service"... pass
  run "glue_job_{nome_job_snake}_has_correct_prod_workers"... pass
  run "s3_script_upload_for_{nome_job_snake}_is_planned"... pass

Success! 6 passed, 0 failed.
```

### Interpretare un fallimento

| Errore | Causa | Fix |
|--------|-------|-----|
| `assert condition evaluated to false` | Il job non e' in `glue-definitions.yaml` | Aggiungi l'entry YAML |
| `Error: Invalid reference` / `aws_glue_job.silver is tuple` | Sintassi iterazione errata | Usa `for job in aws_glue_job.silver` (count → lista) |
| `Error: Invalid YAML` | `mock_provider "local"` attivo | Rimuovilo |
| `Error: Missing required argument "cron_expression"` | `config.orchestration` incompleto | Aggiungi `cron_expression` e `status` |
| `Error: .terraform not found` | Provider non inizializzato | Esegui `terraform init` |

---

## 6. Setup Ambiente (prima volta)

> **Ambiente richiesto: WSL (Linux).** I comandi sotto presuppongono shell
> bash su WSL/Linux. Da PowerShell/cmd su Windows path e binari ELF non
> funzionano.

### 6.0 Pre-check — NON ri-scaricare quello che hai gia'

Prima di lanciare qualunque `curl`, verifica cosa e' gia' installato. Lo zip
del provider AWS pesa ~190 MB e Terraform ~70 MB: salta lo step se l'output
del check e' positivo.

```bash
uname -a                                          # deve contenere "Linux"
command -v terraform && terraform version          # >= 1.6.0 → salta 6.1
ls ~/terraform-mirror/registry.terraform.io/hashicorp/aws/*/linux_amd64/terraform-provider-aws_v*_x5 2>/dev/null   # presente → salta 6.2 step 1-2
cat ~/.terraformrc 2>/dev/null                     # contiene filesystem_mirror → salta 6.2 step 3
```

### 6.1 Terraform in WSL / Linux (se non gia' installato)

Il trust store di sistema contiene gia' il root CA Zscaler, quindi `--cacert`
e' sufficiente — non usare `-k` (skip TLS), che maschera errori reali.

```bash
curl -fL --cacert /etc/ssl/certs/ca-certificates.crt \
  -o /tmp/terraform.zip \
  https://releases.hashicorp.com/terraform/1.12.0/terraform_1.12.0_linux_amd64.zip
unzip /tmp/terraform.zip -d /tmp/terraform-bin
sudo mv /tmp/terraform-bin/terraform /usr/local/bin/terraform
terraform version
```

### 6.2 Filesystem mirror per provider AWS (proxy Zscaler)

Setup persistente — eseguito una volta sola, riutilizzato da tutti i repo.
La versione `6.44.0` qui e' un esempio; usa quella richiesta dal repo (vedi
`.terraform.lock.hcl`). **Esegui solo gli step che il pre-check 6.0 segnala
come mancanti.**

```bash
# 1. Scarica il provider con cert Zscaler dal trust store (skip se gia' presente in ~/terraform-mirror)
mkdir -p ~/terraform-providers && cd ~/terraform-providers
curl -fL --cacert /etc/ssl/certs/ca-certificates.crt \
  -o terraform-provider-aws_6.44.0_linux_amd64.zip \
  https://releases.hashicorp.com/terraform-provider-aws/6.44.0/terraform-provider-aws_6.44.0_linux_amd64.zip
unzip -o terraform-provider-aws_6.44.0_linux_amd64.zip -d ./extracted/

# 2. Layout filesystem mirror (struttura registry.terraform.io/<owner>/<name>/<version>/<os_arch>)
MIRROR=~/terraform-mirror/registry.terraform.io/hashicorp/aws/6.44.0/linux_amd64
mkdir -p "$MIRROR"
cp ~/terraform-providers/extracted/terraform-provider-aws_v6.44.0_x5 "$MIRROR/"
chmod +x "$MIRROR/terraform-provider-aws_v6.44.0_x5"

# 3. Configura ~/.terraformrc (sostituisci <USER> con `echo $USER`)
cat > ~/.terraformrc <<EOF
provider_installation {
  filesystem_mirror {
    path    = "$HOME/terraform-mirror"
    include = ["registry.terraform.io/hashicorp/aws"]
  }
  direct {
    exclude = ["registry.terraform.io/hashicorp/aws"]
  }
}
EOF

# 4. Verifica
cd modules/silver-{domain}
terraform init -backend=false
terraform test
```

**Aggiornamento versione:** quando un repo bumpa il provider AWS, ripeti
solo gli step 1-2 con la nuova versione. Il mirror puo' contenere piu'
versioni in parallelo, nessuna modifica a `~/.terraformrc`.

> **Nota:** Il mirror e' richiesto solo in ambienti con proxy Zscaler che intercetta TLS.
> In ambienti con accesso diretto a Internet, `terraform init` funziona senza configurazione aggiuntiva.

---

## 7. Aggiungere un Test per un Nuovo Glue Job — Checklist

```
- [ ] 1. Verifica entry in glue-definitions.yaml: grep job_name="{nome_job}"
- [ ] 2. Verifica script: ls glue-jobs/src/{nome_job}.py
- [ ] 3. Crea tests/glue_job_{nome_job_snake}.tftest.hcl dal template (sezione 3)
- [ ] 4. Sostituisci tutti i placeholder ({domain}, {nome_job}, {worker_type})
- [ ] 5. terraform test -filter=tests/glue_job_{nome_job_snake}.tftest.hcl
- [ ] 6. Output: Success! 5 passed, 0 failed
- [ ] 7. Commit: feat({domain}): add IaC test for {nome_job} glue job
```

---

## 8. Pattern Assert Addizionali

Da aggiungere se il job ha requisiti specifici:

**Numero workers per ambiente:**
```hcl
assert {
  condition = anytrue([
    for job in aws_glue_job.silver :
    job.name == "dev-datalake-etl-{domain}-{nome_job}" && job.number_of_workers == {N}
  ])
  error_message = "Il job {nome_job} deve avere {N} workers in dev."
}
```

**Timeout specifico:**
```hcl
assert {
  condition = anytrue([
    for job in aws_glue_job.silver :
    job.name == "dev-datalake-etl-{domain}-{nome_job}" && job.timeout == {minuti}
  ])
  error_message = "Il job {nome_job} deve avere timeout di {minuti} minuti."
}
```

**Glue version:**
```hcl
assert {
  condition = anytrue([
    for job in aws_glue_job.silver :
    job.name == "dev-datalake-etl-{domain}-{nome_job}" && job.glue_version == "5.0"
  ])
  error_message = "Il job {nome_job} deve usare Glue 5.0."
}
```

---

## Limiti Operativi

| Vincolo | Limite | Se superato |
|---------|--------|-------------|
| Tentativi per errore di configurazione | 2 | Diagnosi diversa. Leggi output completo `terraform test -verbose` |
| File modificati per step | 2 | Solo `.tftest.hcl` + eventuale `glue-definitions.yaml` |
| Assert per run block | Max 3 | Separa in run block distinti se servono piu' verifiche |

---

REQUIRED SUB-SKILL: siae-verification

Invoca `siae-verification` prima di dichiarare il test IaC completato.

---

## Classificazione Rischio Operazioni

| Operazione | Rischio | Card |
|------------|---------|------|
| Scrittura file `.tftest.hcl` | 🟢 Sicuro | No |
| `terraform test` (plan only) | 🟢 Sicuro | No |
| `terraform init` con mirror | 🟡 Medio | No |
| `terraform apply` | 🚨 Critico | Si (vedi `siae-iac`) |
