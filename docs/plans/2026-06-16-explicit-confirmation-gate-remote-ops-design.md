# Design: Explicit Confirmation Gate for Remote Write/Update/Delete Operations

**Data:** 2026-06-16
**Branch:** feat/explicit-confirmation-gate-remote-ops
**PR:** #337
**Scope:** 10 skill DevForge

---

## Contesto

Le skill DevForge guidano un agente AI nell'esecuzione di operazioni su sistemi remoti
(AWS, GitHub, Firebase, DMS). Senza un gate esplicito, l'agente può eseguire operazioni
distruttive o irreversibili in risposta a istruzioni ambigue o silenzio dell'utente.

Il gate di conferma esplicita introduce un punto di pausa obbligatorio prima di qualsiasi
operazione write/update/delete su sistemi remoti, richiedendo una risposta esplicita
"sì, procedi" / "no, annulla" prima di procedere.

---

## Schema Canonico — Gate CRITICO (9 elementi obbligatori)

Ogni gate deve contenere, nell'ordine:

```markdown
🔴 CRITICO — Mostra pre-flight card prima di eseguire

| 🔴 CRITICO ({descrizione operazione}) — 🔨 DevForge · {nome-skill} |
|:---|
| **⚠️ OPERAZIONE REMOTA — {TIPO}: WRITE/UPDATE/DELETE SU {sistema}** |
| 📋 Risorsa: `{risorsa}` · 🌍 Ambiente: `{ambiente}` |
| **▼ Azioni** |
| 1. {azione concreta con comando} |
| 2. {effetto downstream se rilevante} |
| 💡 Perché: {motivazione tecnica concreta — cosa si rompe se sbagliato} |
| 🚫 Se NO: {conseguenza concreta del rifiuto — operazione non eseguita} |

⏸️ **ATTENDI CONFERMA ESPLICITA** — mostra la card e NON eseguire finché l'utente
risponde esplicitamente ("sì, procedi" / "no, annulla"). Silenzio ≠ consenso.

**Solo dopo "sì, procedi"**, esegui:

{comando/azione eseguibile}
```

**Nota severity icon:** Usare `🚨 CRITICO` per operazioni irreversibili (push tag, terraform apply, delete permanente); `🔴 CRITICO` per operazioni critiche con recovery difficile ma possibile.

---

## Operazioni in Scope

Qualsiasi operazione che:
1. Scrive, aggiorna o elimina dati su un sistema remoto (AWS, GitHub, Firebase, DMS)
2. Triggera effetti downstream immediati (pipeline CI/CD, job batch, replication)
3. È difficilmente reversibile senza un'azione separata

### Tabella operazioni in scope per sistema

| Sistema | Operazioni in scope | Skill |
|---|---|---|
| AWS S3 | sync (sovrascrittura assets), delete bucket/prefix | siae-frontend, siae-data-engineering |
| AWS Glue Catalog | schema update, job start | siae-data-engineering |
| AWS EventBridge | enable/disable/modifica schedule | siae-data-engineering |
| AWS IAM | creazione/modifica policy, aggiunta ARN | siae-datalake-iac-setup, siae-dwh-etl-edw-add-submodule |
| AWS CloudFront | invalidazione cache | siae-frontend |
| Terraform state (S3 remote) | import, state rm | siae-terraform-import |
| Pipeline CI/CD (GitHub Actions via tag) | push tag rc-* | siae-iac, siae-datalake-deploy |
| GitHub Environments | write/overwrite variabili AWS CI/CD | siae-datalake-etl-setup, siae-datalake-ingestion-setup |
| Firebase Remote Config | write/update/delete parametri | siae-frontend |
| AWS DMS mapping (effetto differito) | modifica regole JSON (applicate al prossimo riavvio task) | siae-dms-rename-column |
| File system locale (irreversibile) | rm -rf directory scaffolding | siae-datalake-etl-setup, siae-datalake-ingestion-setup |
| GitHub Actions workflow CI/CD | sed -i versione siae-gh-actions | siae-datalake-iac-setup |

---

## Operazioni Escluse

| Sistema | Motivazione esclusione |
|---|---|
| Operazioni git (push branch, tag, merge) | Gestite dalla skill `siae-git-workflow` con proprio schema di gate |
| `siae-finops` | Escluso esplicitamente per scelta di design |
| Lettura/analisi file locali | Non producono effetti remoti |
| `terraform plan` | Read-only, nessun effetto sullo state |

---

## Criteri per future skill

Una skill che introduce operazioni in scope DEVE:

1. Aggiungere il gate con schema canonico a 9 elementi PRIMA del comando eseguibile
2. Classificare l'operazione nella tabella di classificazione rischio con livello CRITICO e `Card: Sì`
3. Aggiornare la sezione Vincoli con "GATE CRITICO OBBLIGATORIO / silenzio ≠ consenso"
4. Verificare che il gate sia posizionato PRIMA del comando, non dopo

---

## Skill Modificate (questa PR)

| Skill | Path | Gate aggiunti/aggiornati |
|---|---|---|
| `siae-datalake-deploy` | `skills/siae-datalake-deploy/SKILL.md` | `make {ambiente}` (SICURO → CRITICO) |
| `siae-frontend` | `skills/siae-frontend/SKILL.md` | Deploy S3+CloudFront; Firebase Remote Config |
| `siae-iac` | `skills/siae-iac/SKILL.md` | Tag deploy `rc-*` |
| `siae-terraform-import` | `skills/siae-terraform-import/SKILL.md` | `terragrunt import`; `terragrunt state rm` |
| `siae-data-engineering` | `skills/siae-data-engineering/SKILL.md` | Schema Glue Catalog; `force_no_window=1`; `aws glue start-job-run`; EventBridge |
| `siae-datalake-iac-setup` | `skills/siae-datalake-iac-setup/SKILL.md` | Modifica policy IAM; `sed -i` versione CI/CD workflow |
| `siae-datalake-etl-setup` | `skills/siae-datalake-etl-setup/SKILL.md` | `rm -rf` scaffolding; GitHub Env Sync |
| `siae-datalake-ingestion-setup` | `skills/siae-datalake-ingestion-setup/SKILL.md` | `rm -rf` scaffolding; GitHub Env Sync |
| `siae-dwh-etl-edw-add-submodule` | `skills/siae-dwh-etl-edw-add-submodule/SKILL.md` | Aggiunta ARN IAM a policy condivisa |
| `siae-dms-rename-column` | `skills/siae-dms-rename-column/SKILL.md` | Inserimento regole DMS mapping |
