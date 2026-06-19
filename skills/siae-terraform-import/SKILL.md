---
name: siae-terraform-import
description: >
  Use when an AWS resource already exists in the cloud but Terraform vuole crearla
  da zero (errore ResourceExistsException / EntityAlreadyExists). La skill guida
  l'import nello state Terragrunt di un repo datalake SIAE, gestendo proxy
  Zscaler, render dei _envs templates, override TLS e verifica idempotente.
  Trigger: "terraform import", "ResourceExistsException", "EntityAlreadyExists",
  "importa risorsa esistente", "secret gia creato", "risorsa orfana terraform",
  "adottare risorsa esistente", "siae-terraform-import".
---

# SIAE Terraform Import — DevForge

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗    ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║    ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║    ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝    ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝     ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝      ║
║          🔨 DevForge · SIAE TERRAFORM IMPORT                   ║
║         "Il codice si forgia. Il developer cresce."            ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Rigid | **Fase SDLC:** 4. Deploy / Drift Recovery

---

## LA LEGGE DI FERRO

```
NESSUN IMPORT SENZA PLAN DI VERIFICA. NESSUN APPLY SU IMPORT NON CONFERMATO.
```

Un `terraform import` mal fatto puo' produrre `destroy + recreate` di una risorsa
con dati (es. secret con credenziali, RDS, S3 con oggetti). Sempre `plan` prima,
sempre conferma esplicita dei diff.

---

## Quando si Applica

**Sempre:**

- Errore `ResourceExistsException` / `EntityAlreadyExists` / `AlreadyExistsException`
  da Terraform su una risorsa AWS.
- Risorsa AWS creata da un branch/account/processo esterno che ora vuoi gestire
  in Terraform (es. secret popolato a mano, IAM role pre-esistente).
- Migrazione di ownership tra moduli/repo (data source → resource).
- Drift recovery dopo cancellazione/ricreazione manuale.

**Eccezioni (chiedi prima):**

- Risorse con dati persistenti (RDS, S3 con oggetti, DynamoDB con record):
  conferma con utente che import e' la strada giusta vs delete+recreate.
- Risorse in produzione: serve change request, non improvvisare.
- Drift causato da un altro branch attivo: prima coordina, non fare import unilaterale.

---

## Input Richiesti

| Parametro | Descrizione | Esempio |
|-----------|-------------|---------|
| `repo` | Repo datalake SIAE in cui fare l'import | `datalake-bm-utilizzazioni-ingestion` |
| `live-path` | Sottocartella `live/<module>` con il `terragrunt.hcl` | `live/bronze-bm-utilizzazioni` |
| `env` | Ambiente target | `dev` / `qa` / `prod` |
| `resource-address` | Indirizzo Terraform della risorsa nel modulo | `aws_secretsmanager_secret.rds_credentials` |
| `aws-resource-id` | ID/ARN nativo AWS della risorsa | `arn:aws:secretsmanager:eu-west-1:613577363574:secret:dev-...-pMtou8` |

Se manca anche solo uno, **chiedi all'utente prima di procedere.**

---

## Step 1 — Verifica Prerequisiti

🟢 SICURO

Verifica nell'ordine. Se uno fallisce, ferma e segnala — non improvvisare.

```bash
# 1.1 — terraform e terragrunt installati
which terraform && terraform version | head -1
which terragrunt && terragrunt --version | head -1

# 1.2 — AWS CLI autenticato sull'account corretto
aws sts get-caller-identity --no-verify-ssl 2>/dev/null \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Account: {d[\"Account\"]}')"
```

**Aspettato:** l'`Account` deve corrispondere all'environment scelto. Se errato (es.
serve account dev `613577363574` ma sei su `134565215127`), chiedi all'utente di
switchare profilo SSO prima di procedere. Mai forzare l'import sull'account sbagliato.

```bash
# 1.3 — la risorsa AWS esiste davvero
# Esempio per secretsmanager:
aws secretsmanager describe-secret --secret-id <name> --region <region> --no-verify-ssl
# Esempio per iam role:
aws iam get-role --role-name <name>
# Esempio per s3:
aws s3api head-bucket --bucket <name>
```

Salva l'ARN/ID esatto restituito — sara' l'`aws-resource-id` per l'import.

```bash
# 1.4 — il modulo Terraform dichiara la risorsa
cd <repo>
grep -rn "<resource-address-tail>" modules/<module>/*.tf
```

La risorsa Terraform deve esistere come `resource ...` nel modulo. Se nel codice
e' ancora un `data ...`, vai allo Step 2bis (conversione data → resource) prima.

---

## Step 2 — Rendering del file _envs/{env}.yaml

🟢 SICURO

Il file `live/_envs/{env}.tmpl` contiene variabili `$VAR` che la pipeline CI/CD
rende a runtime usando le GitHub Actions environment variables. Localmente devi
fare lo stesso con `envsubst`.

```bash
cd <repo>

# 2.1 — Carica tutte le variabili da GH env
for v in $(grep -oE '\$[A-Z_]+' live/_envs/{env}.tmpl | sort -u | tr -d '$'); do
  val=$(gh api "repos/itsiae/<repo>/environments/<env-name>/variables/$v" --jq .value 2>/dev/null)
  echo "$v=${val}"
  export "$v=$val"
done

# 2.2 — Rendering
envsubst < live/_envs/{env}.tmpl > live/_envs/{env}.yaml

# 2.3 — Verifica nessuna variabile rimasta non sostituita
grep -E '\$[A-Z_]+' live/_envs/{env}.yaml && echo "ERRORE: variabili non risolte" || echo "OK"
```

Naming nota: il GitHub environment name **non sempre coincide** con `env`. Mapping
SIAE standard:
- `env=dev` → `environment=collaudo`
- `env=qa`  → `environment=certificazione`
- `env=prod` → `environment=produzione`

⚠️ Il file `live/_envs/{env}.yaml` e' **gitignorato** — non committarlo mai.

---

## Step 2bis — Conversione data → resource (se necessario)

🟡 MEDIO

Se la risorsa nel codice e' ancora un `data` source, vai prima fatto questo passaggio:

1. Sposta la dichiarazione da `data "aws_..."` a `resource "aws_..."` nel modulo
   (esempio: file `secrets-manager.tf` per i secret, pattern allineato a
   `datalake-bm-estero-ingestion`).
2. Aggiorna ogni riferimento da `data.aws_xxx.yyy.<attr>` a `aws_xxx.yyy.<attr>`.
3. Commit + push.

A questo punto, **se non importi prima**, il prossimo `plan` tentera' di **creare**
una risorsa che esiste gia' in AWS → `ResourceExistsException` al `apply`. Devi
SEMPRE fare l'import prima del primo apply post-conversione.

---

## Step 3 — Workaround TLS proxy Zscaler (se applicabile)

🟡 MEDIO

Se sei su WSL/laptop aziendale SIAE, Zscaler intercetta TLS e i provider Terraform
falliscono con `tls: failed to verify certificate: x509: certificate signed by
unknown authority`.

Soluzione: genera un CA bundle combinato (sistema + Zscaler chain) e passalo via env.

```bash
# 3.1 — Estrai la chain Zscaler dall'endpoint AWS
echo | openssl s_client -showcerts -connect releases.hashicorp.com:443 2>/dev/null \
  | sed -ne '/-BEGIN CERTIFICATE-/,/-END CERTIFICATE-/p' > /tmp/zscaler_chain.pem

# 3.2 — Verifica che la chain contenga 2-3 certificati Zscaler
grep -c "BEGIN CERTIFICATE" /tmp/zscaler_chain.pem

# 3.3 — Crea bundle combinato (sistema CA + Zscaler)
cat /etc/ssl/certs/ca-certificates.crt /tmp/zscaler_chain.pem > /tmp/combined_ca.pem

# 3.4 — Test con curl
SSL_CERT_FILE=/tmp/combined_ca.pem curl -sI https://releases.hashicorp.com/ | head -3
```

Da qui in poi, per ogni comando `terragrunt`/`terraform` esporta:

```bash
export SSL_CERT_FILE=/tmp/combined_ca.pem
export AWS_CA_BUNDLE=/tmp/combined_ca.pem
```

Se NON sei dietro Zscaler (CI runner, VM cloud), salta questo step.

---

## Step 4 — Pre-flight Card

🔴 CRITICO — Mostra pre-flight card prima di eseguire

| 🔴 CRITICO (import state remoto) — 🔨 DevForge · siae-terraform-import |
|:---|
| **⚠️ OPERAZIONE REMOTA — WRITE/UPDATE/DELETE SU TERRAFORM STATE** |
| 📋 Risorsa: `<resource-address>` · 🌍 Ambiente: `<env>` |
| 🆔 Repo: `<repo>` · AWS ID: `<aws-resource-id>` |
| **▼ Azioni** |
| 1. `terragrunt import <resource-address> <aws-resource-id>` — scrive la risorsa nello state remoto S3 |
| 2. `terragrunt plan` — verifica che il plan mostri 0 destroy (lettura, non scrive) |
| 💡 Perche': la risorsa esiste in AWS ma non e' nello state — import evita ResourceExistsException al prossimo apply; se l'ID e' sbagliato, lo state punta a risorsa errata → drift permanente irreversibile senza rollback manuale |
| 🚫 Se NO: la risorsa resta orfana, il prossimo apply fallira' con ResourceExistsException |

⏸️ **ATTENDI CONFERMA ESPLICITA** — mostra la card e NON eseguire finche' l'utente
risponde esplicitamente ("sì, procedi" / "no, annulla"). Silenzio ≠ consenso.

**Solo dopo "sì, procedi"**, esegui:

---

## Step 5 — Esegui l'Import

🔴 CRITICO — esegui solo dopo conferma esplicita dello Step 4

**Solo dopo "sì, procedi"**, esegui dal cwd `live/<module-path>`:

```bash
cd <repo>/<live-path>

SSL_CERT_FILE=/tmp/combined_ca.pem \
AWS_CA_BUNDLE=/tmp/combined_ca.pem \
ENV=<env> terragrunt import \
  --terragrunt-non-interactive \
  '<resource-address>' \
  '<aws-resource-id>' 2>&1 | tail -30
```

Aspettato:

```
... Importing from ID "<aws-resource-id>"...
Prepared <aws-resource-type> for import
... Refreshing state... [id=<aws-resource-id>]
Import successful!
```

Se vedi `Import successful!` → procedi allo Step 6.

Se vedi errori (TLS, credenziali, resource not found, address mismatch), **non
forzare**. Diagnostica:
- `Address <resource> does not exist` → typo nell'address, verifica con `grep`
- `cannot import non-existent remote object` → l'ID AWS e' sbagliato
- `tls: failed to verify certificate` → torna allo Step 3
- `NoCredentialProviders` → SSO scaduto, ri-loggi e riprova
- `ResourceNotFoundException` → l'aws-resource-id punta a un account diverso

---

## Step 6 — Verifica Plan Post-Import

🟢 SICURO — questo step e' OBBLIGATORIO

```bash
SSL_CERT_FILE=/tmp/combined_ca.pem \
AWS_CA_BUNDLE=/tmp/combined_ca.pem \
ENV=<env> terragrunt plan \
  --terragrunt-non-interactive 2>&1 | grep -E "Plan:|will be|<resource-tail>" | tail -20
```

**Verdetto:**

| Plan output | Significato | Azione |
|-------------|-------------|--------|
| `Plan: 0 to add, 0 to change, 0 to destroy` | Import perfetto, state allineato | ✅ Done |
| `Plan: 0 to add, 1 to change, 0 to destroy` con solo `tags`/`description` | Cosmetico, nessun replace | ✅ Done — il prossimo apply fara' update in-place |
| `Plan: 0 to add, N to change, 0 to destroy` | Drift su attributi — verifica | 🟡 Mostra diff all'utente, conferma se ok |
| `Plan: 1 to add, 0 to destroy` sulla risorsa importata | Address sbagliato, doppione | 🔴 STOP: `terragrunt state rm` dell'import errato |
| `Plan: 1 to destroy, 1 to add` (replace) | Risorsa verra' DISTRUTTA e RICREATA | 🚨 STOP: investiga `# forces replacement`, valuta se modificare il codice |

**Se vedi `destroy` o `replace` sulla risorsa appena importata**, NON applicare.
Probabili cause:
- Naming/tag che non si possono cambiare in-place → modifica codice per matchare
- Attributi `lifecycle` mancanti → aggiungi `prevent_destroy = true` in codice prima
- Risorsa importata in modulo sbagliato → import era nel posto sbagliato

---

## Step 7 — Cleanup e Documentazione

🟢 SICURO

```bash
# 7.1 — Cancella file render locale (gia gitignored, ma good hygiene)
rm -f live/_envs/<env>.yaml

# 7.2 — Verifica state remoto contiene la nuova risorsa
SSL_CERT_FILE=/tmp/combined_ca.pem AWS_CA_BUNDLE=/tmp/combined_ca.pem \
  ENV=<env> terragrunt state list \
  --terragrunt-non-interactive 2>&1 | grep <resource-tail>
```

Documenta nel commit/PR:
- Quale risorsa importata e da dove proveniva (es. "creato da branch X")
- ARN/ID importato
- Per quali altri ambienti l'import va ripetuto

**Per qa/prod**: NON automatizzare l'import dentro il workflow CI senza approvazione
esplicita — un import errato in prod e' molto piu' difficile da riparare. Lascia
che venga fatto manualmente dal team responsabile.

---

## Comando Riassunto — Cheatsheet

```bash
# 0. Prerequisiti
which terraform terragrunt && aws sts get-caller-identity --no-verify-ssl

# 1. Render env
cd <repo>
for v in AWS_ENV LOGS_RETENTION_DAYS BRONZE_DATALAKE_BUCKET_ID GLUE_PACKAGES_BUCKET_ID \
         VPC_STAGE SG_DEFAULT JDBC_CONNECTION_URL CRON_SCHED CRON_STATUS; do
  export "$v=$(gh api repos/itsiae/<repo>/environments/<gh-env>/variables/$v --jq .value 2>/dev/null)"
done
envsubst < live/_envs/<env>.tmpl > live/_envs/<env>.yaml

# 2. CA bundle Zscaler
echo | openssl s_client -showcerts -connect releases.hashicorp.com:443 2>/dev/null \
  | sed -ne '/-BEGIN/,/-END/p' > /tmp/zscaler_chain.pem
cat /etc/ssl/certs/ca-certificates.crt /tmp/zscaler_chain.pem > /tmp/combined_ca.pem

# 3. Import
cd live/<module>
SSL_CERT_FILE=/tmp/combined_ca.pem AWS_CA_BUNDLE=/tmp/combined_ca.pem \
  ENV=<env> terragrunt import --terragrunt-non-interactive \
  '<resource.name>' '<aws-id-arn>'

# 4. Plan verify
SSL_CERT_FILE=/tmp/combined_ca.pem AWS_CA_BUNDLE=/tmp/combined_ca.pem \
  ENV=<env> terragrunt plan --terragrunt-non-interactive 2>&1 \
  | grep -E "Plan:|will be"
```

---

## Fallback Obbligatori

### Risposta ambigua alla card

Se l'utente non risponde con "sì, procedi" o "no, annulla": NON eseguire.
Chiedere: *"Confermo l'import? Rispondi 'sì, procedi' oppure 'no, annulla'."*

### Plan post-import mostra `destroy` o `replace`

NON applicare. Mostra il diff completo all'utente con la sezione `# forces
replacement` e chiedi come procedere:
1. Aggiusta codice Terraform per evitare il replace
2. Aggiungi `lifecycle { prevent_destroy = true }` se applicabile
3. Annulla l'import con `terragrunt state rm` — vedi gate CRITICO obbligatorio qui sotto

### Rollback import errato — `terragrunt state rm`

Se l'import ha associato l'address sbagliato o l'ID AWS e' errato, il rollback richiede
la rimozione dallo state remoto. Questa operazione e' **irreversibile** (lo state viene
modificato immediatamente sul backend S3 remoto) — richiede gate esplicito.

🔴 CRITICO — Mostra pre-flight card prima di eseguire

| 🔴 CRITICO (state rm — rollback import) — 🔨 DevForge · siae-terraform-import |
|:---|
| **⚠️ OPERAZIONE REMOTA — DELETE SU TERRAFORM STATE** |
| 📋 Risorsa: `<resource-address>` · 🌍 Ambiente: `<env>` |
| 🆔 Repo: `<repo>` |
| **▼ Azioni** |
| 1. `terragrunt state rm <resource-address>` — rimuove la risorsa dallo state remoto S3 |
| 💡 Perche': l'import precedente ha associato address o ID errato; `state rm` ripristina lo state prima dell'import permettendo di ritentare con i dati corretti |
| 🚫 Se NO: lo state rimane con la associazione errata, i prossimi plan/apply useranno l'ID sbagliato generando drift permanente |

⏸️ **ATTENDI CONFERMA ESPLICITA** — mostra la card e NON eseguire finche' l'utente
risponde esplicitamente ("sì, procedi" / "no, annulla"). Silenzio ≠ consenso.

**Solo dopo "sì, procedi"**, esegui:

```bash
cd <repo>/<live-path>
SSL_CERT_FILE=/tmp/combined_ca.pem \
AWS_CA_BUNDLE=/tmp/combined_ca.pem \
ENV=<env> terragrunt state rm \
  --terragrunt-non-interactive \
  '<resource-address>'
```

Dopo il `state rm`, torna allo Step 4 per ritentare l'import con i dati corretti.

### Backend S3 inaccessibile

Se l'init terragrunt fallisce con "S3 bucket does not exist", controlla:
- Il bucket esista davvero (`aws s3 ls` con `--no-verify-ssl`)
- Le credenziali AWS abbiano permessi sul bucket
- Il nome bucket in `live/terragrunt.hcl` sia corretto (usa `${local.config.repository_name}`)

### TLS Zscaler persistente

Se nemmeno il CA combinato risolve: cambia approccio. Esegui l'import via
GitHub Actions runner (no Zscaler) con un workflow ad-hoc `workflow_dispatch`.

---

## Tabella Anti-Razionalizzazione

| Pensiero | Realta' |
|----------|---------|
| "Faccio import senza plan, e' veloce" | Senza plan rischi destroy invisibili. Sempre verifica. |
| "L'ARN sara' giusto, non lo verifico" | Un solo carattere sbagliato in ARN e importi risorsa errata → drift permanente |
| "Skippo --terragrunt-non-interactive, rispondo a mano" | Terragrunt puo' prompt-are anche durante import — meglio non-interactive |
| "La risorsa esiste, ma non la importo, faccio destroy+recreate" | Per secret/RDS perdi dati. Import e' quasi sempre la strada giusta |
| "Faccio import direttamente in prod" | Mai senza change request e backup state. Test in dev/qa prima. |
| "Lo state lo committo per sicurezza" | MAI committare `terraform.tfstate` o `.terragrunt-cache/`. Sono nel `.gitignore` |
| "L'errore TLS lo ignoro con --insecure" | `insecure = true` nel provider funziona ma e' workaround. Meglio CA bundle pulito. |
| "Modifico provider.tf nel cache, tanto e' temporaneo" | Il cache viene rigenerato → modifiche perse. Usa override file (`*_override.tf`) o env vars |

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|------------|---------|------|
| Verifica risorsa AWS esiste | 🟢 Sicuro | No |
| Render env templates | 🟢 Sicuro | No |
| Generazione CA bundle Zscaler | 🟢 Sicuro | No |
| Lettura state remoto (`state list`) | 🟢 Sicuro | No |
| `terragrunt plan` (read-only) | 🟢 Sicuro | No |
| **`terragrunt import` (modifica state)** | 🔴 CRITICO | Sì |
| **`terragrunt state rm` (rollback import)** | 🔴 CRITICO | Sì |
| `terragrunt apply` post-import | 🔴 CRITICO | Sì (skill separata, non in scope qui) |

---

## Vincoli

1. **MAI** import senza prima aver verificato che la risorsa AWS esiste davvero
2. **MAI** import senza plan di verifica subito dopo
3. **MAI** committare `terraform.tfstate`, `terraform.tfstate.backup`, `.terragrunt-cache/`
4. **MAI** import in prod senza change request approvata
5. **SEMPRE** mostrare la pre-flight card prima dell'import
6. **SEMPRE** verificare l'account AWS attivo prima di lanciare `terragrunt import`
7. **SEMPRE** documentare nel commit/PR cosa e' stato importato e perche'
8. **PRE-FLIGHT OBBLIGATORIA** per import (rischio 🔴) e per `state rm` di rollback
9. **MAI** usare `--no-verify-ssl` o `insecure = true` come workaround permanente —
   solo per debug, mai committare nel codice
