---
name: siae-finops
description: >
  Review costi AWS, stima impatto PR, ottimizzazione risorse,
  tag compliance, budget analysis, /forge-cost, /forge-finops,
  Infracost, Steampipe, Cloud Custodian, risorse idle, sprechi.
---

# SIAE FinOps — Cost Visibility & Governance

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗    ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║    ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║    ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝    ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝     ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝      ║
║              🔨 DevForge · SIAE FINOPS                          ║
║         "Il codice si forgia. Il developer cresce."             ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Flexible | **Fase SDLC:** 4. Implementation

---

## Quando si Applica

**Sempre:**
- Revisione costi AWS (risorse idle, sprechi, ottimizzazione)
- Stima impatto economico di modifiche Terraform/Terragrunt nelle PR
- Audit tag compliance (risorse senza tag obbligatori)
- Query interattive sui costi da Claude Code
- Setup o configurazione Infracost, Steampipe MCP, Cloud Custodian

**Eccezioni:**
- Per tagging standard e convenzioni .tf/.hcl usa `siae-iac`
- Per security review (IAM, encryption) usa `siae-security`

---

## Prerequisiti

| Tool | Scopo | Installazione | Verifica |
|------|-------|---------------|----------|
| Infracost CLI | Stima costi pre-deploy | `brew install infracost` | `infracost --version` |
| INFRACOST_API_KEY | Autenticazione API pricing | `infracost auth login` (gratuito) | `infracost configure get api_key` |
| Steampipe | Query SQL su risorse AWS | `brew install steampipe` | `steampipe --version` |
| Steampipe AWS plugin | Accesso dati AWS | `steampipe plugin install aws` | `steampipe plugin list` |
| Steampipe MCP server | Integrazione Claude Code | Config in `mcp_servers` | Verifica tool `steampipe_query` disponibile |
| Cloud Custodian | Governance automatizzata | `pip install c7n c7n-org` | `custodian version` |

**Se un prerequisito manca:** guida l'utente al setup con i comandi sopra. Non procedere senza verifica.

---

## 1. Shift-Left — Stima Costi Pre-Deploy (Infracost)

### Quando usare

Prima di ogni PR che modifica file `.tf` o `terragrunt.hcl`. Stima l'impatto economico della modifica.

### Flusso manuale (Claude Code)

```
REQUIRED SUB-SKILL: siae-iac
```

**Step 1:** Detecta file Terragrunt/Terraform nella directory corrente

```bash
# Verifica presenza IaC
ls -la *.tf terragrunt.hcl 2>/dev/null || echo "Nessun file IaC trovato"
```

**Step 2:** Esegui stima costi

🟡 MEDIO — Mostra pre-flight card prima di eseguire

| 🟡 MEDIO (reversibile) — 🔨 DevForge · siae-finops |
|:---|
| Azione: Stima costi Infracost |
| Path: `<directory IaC>` |
| Perche': Calcola impatto economico delle modifiche Terraform |
| Se NO: Nessuna chiamata API esterna |

```bash
infracost diff --path=. --format=json --out-file=/tmp/infracost.json
infracost output --path=/tmp/infracost.json --format=table
```

**Step 3:** Analizza e presenta risultati

Presenta tabella riassuntiva:

| Risorsa | Costo Attuale | Costo Nuovo | Delta |
|---------|---------------|-------------|-------|
| `<risorsa>` | $X/mese | $Y/mese | +$Z/mese |

Se delta > $50/mese, mostra warning con suggerimenti da [infracost-patterns.md](reference/infracost-patterns.md).

### Flusso automatico (GitHub Actions)

Vedi sezione 4 per il reusable workflow. Ogni PR su repo HCL riceve automaticamente un commento con la stima costi.

### Usage File per Servizi SIAE

Per servizi usage-based (Lambda, DynamoDB, Glue) Infracost non puo' stimare senza un usage file. Vedi [infracost-patterns.md](reference/infracost-patterns.md) per template.

---

## 2. Query Interattive — Steampipe MCP

### Setup MCP Server

Aggiungere in configurazione Claude Code MCP servers:

```json
{
  "steampipe": {
    "command": "npx",
    "args": ["-y", "@turbot/steampipe-mcp"],
    "env": {
      "STEAMPIPE_INSTALL_DIR": "~/.steampipe"
    }
  }
}
```

### Query Catalog

Usa il tool `steampipe_query` per eseguire SQL sulle risorse AWS. Catalogo completo in [steampipe-queries.md](reference/steampipe-queries.md).

**Query principali:**

| Obiettivo | Uso |
|-----------|-----|
| Top spender del mese | Identifica servizi piu' costosi |
| Risorse idle | Lambda >90gg, DynamoDB <10 RCU, EBS detached |
| Tag audit | Risorse senza tag obbligatori (6 tag SIAE) |
| Cost trend | Confronto mese-su-mese per anomalie |
| Query libera | L'utente chiede, tu traduci in SQL |

### AWS Thrifty Benchmark

Per check sistematico, esegui AWS Thrifty (55 benchmark):

```bash
powerpipe benchmark run aws_thrifty.benchmark.aws_thrifty --output=brief
```

---

## 3. Governance Automatizzata — Cloud Custodian

```
REQUIRED SUB-SKILL: siae-verification
```

### Policy Library SIAE

8 policy iniziali documentate in [custodian-policies.md](reference/custodian-policies.md).

| # | Policy | Risorsa | Azione | Trigger |
|---|--------|---------|--------|---------|
| 1 | tag-enforcement | Tutte | notify + auto-tag | Tag obbligatorio mancante |
| 2 | unused-lambda | Lambda | notify | Non invocata >90 giorni |
| 3 | idle-dynamodb | DynamoDB | notify | <10 RCU/giorno per 14gg |
| 4 | detached-ebs | EBS | notify + schedule delete | Non attached |
| 5 | old-snapshots | Snapshot | notify | >180 giorni |
| 6 | off-hours-dev | ECS, RDS | stop | Sviluppo fuori orario (20:00-08:00) |
| 7 | oversized-rds | RDS | rightsizing notify | CPU media <10% per 14gg |
| 8 | glue-runaway | Glue | notify | Job running >4 ore |

### Pattern Enforcement

```
dry-run → notify → tag → stop/delete
```

**MAI** eseguire policy con azioni distruttive senza:

| 🔴 ALTO (difficile da annullare) — 🔨 DevForge · siae-finops |
|:---|
| OPERAZIONE DIFFICILE DA ANNULLARE |
| Policy: `<nome policy>` |
| Account: `<account AWS>` |
| 1. Azione: Esecuzione policy Cloud Custodian con remediation |
| Perche': `<motivazione>` |
| Se NO: Policy non eseguita, risorse invariate |

### Setup Multi-Account (c7n-org)

```bash
# Dry-run su tutti gli account
custodian run -s /tmp/c7n-output --dry-run policies/cost/*.yml

# Esecuzione reale (dopo approvazione)
c7n-org run -c accounts.yml -s /tmp/c7n-output -u policies/cost/*.yml
```

---

## 4. Tagging Strategy Evoluta

```
REQUIRED SUB-SKILL: siae-iac
```

### 6 Tag Obbligatori SIAE

| Tag | Scopo | Valori | Enforcement |
|-----|-------|--------|-------------|
| `Environment` | Segregazione ambienti | sviluppo, collaudo, certificazione, produzione | Terragrunt |
| `Project` | Raggruppamento progetto | diritti, catalogo, sport, ... | Terragrunt |
| `ManagedBy` | Drift detection | Terraform | Terragrunt |
| `Team` | Chargeback tra factory | digital-factory, core-platforms, data-platform, devops | Terragrunt + Custodian |
| `CostCenter` | Allocazione finanziaria | CC-XXXX | Terragrunt + Custodian |
| `Repository` | Link al repo GitHub | itsiae/repo-name | Terragrunt + Custodian |

Dettagli implementativi in [tagging-strategy.md](reference/tagging-strategy.md).

### Enforcement Chain

```
Terragrunt config.yaml → definisce Team + CostCenter
  → Terraform _local.tf → applica su ogni risorsa
    → Infracost PR → segnala risorse senza tag
      → Cloud Custodian → tag-or-notify post-deploy
        → CUR 2.0 → groupBy tag per dashboard
```

---

## Tabella Anti-Razionalizzazione

| Pensiero | Realta' |
|----------|---------|
| "AWS costa poco, non serve ottimizzare" | 816 repo x 4 ambienti x risorse idle = sprechi invisibili che sommano |
| "I costi li vedo dalla console" | La console non e' proattiva. Infracost + Steampipe portano i costi dove lavori |
| "Il tagging lo faccio dopo" | Senza tag, i costi sono un blob unico. Impossibile attribuire responsabilita' |
| "Cloud Custodian e' overkill" | 8 policy base coprono l'80% degli sprechi. Non e' overkill, e' igiene |
| "Dev e collaudo costano poco" | Dev/collaudo attivi 24/7 = 128 ore/settimana pagate per 40 ore usate |
| "L'Infracost comment nelle PR e' rumore" | Un developer informato e' un developer responsabile. Il costo non e' rumore |
| "Lo faccio a mano una volta al mese" | Il controllo manuale dura 1 mese. Le policy automatiche durano per sempre |
| "La stima Infracost non e' precisa" | Una stima imprecisa e' infinitamente meglio di zero visibilita' |

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|-----------|---------|------|
| Query Steampipe (read-only) | 🟢 Sicuro | No |
| Infracost breakdown/diff | 🟡 Medio | Si (API call esterna) |
| Cloud Custodian dry-run | 🟡 Medio | No |
| Cloud Custodian notify | 🟡 Medio | Si |
| Cloud Custodian enforce (stop/delete) | 🔴 Alto | Si |
| Modifica tag su risorse produzione | 🔴 Alto | Si |

---

## Vincoli

1. **NON** eseguire policy Custodian con azioni distruttive senza pre-flight card 🔴
2. **NON** chiamare Infracost API senza informare l'utente (chiama API pricing esterne)
3. **SEMPRE** verificare prerequisiti tool prima di usarli (fallback con istruzioni setup)
4. **SEMPRE** presentare risultati in tabella markdown leggibile
5. **PRE-FLIGHT OBBLIGATORIA** per operazioni con rischio >= 🟡 — costruisci come markdown table inline

---

## Risorse Aggiuntive

- [reference/infracost-patterns.md](reference/infracost-patterns.md) — Setup Terragrunt, usage file templates
- [reference/steampipe-queries.md](reference/steampipe-queries.md) — Catalogo query SQL per servizio AWS
- [reference/custodian-policies.md](reference/custodian-policies.md) — Policy YAML library SIAE
- [reference/tagging-strategy.md](reference/tagging-strategy.md) — Evoluzione tag 3→6 + enforcement chain
