---
name: forge-finops
description: "Analisi completa costi cloud: detecta AWS/Azure, identifica account, analizza sprechi e ottimizzazioni"
disable-model-invocation: true
---

Invoca la skill siae-devforge:siae-finops. Questo comando esegue un'analisi OPERATIVA completa.

## Flusso Automatico

### Step 1 — Cloud Detection

Detecta quale cloud e' configurato e quale account/subscription e' attivo:

```bash
# AWS
aws sts get-caller-identity 2>/dev/null

# Azure
az account show 2>/dev/null
```

Se entrambi falliscono → guida setup credenziali.
Se entrambi presenti → chiedi quale analizzare.
Mostra all'utente: account ID, alias/nome, region/location, identita' corrente.

### Step 2 — Analisi Completa Automatica

Esegui TUTTE queste analisi in sequenza. Non chiedere, fai.

**A) Cost Overview:**
- Top 10 servizi piu' costosi (mese corrente)
- Confronto mese-su-mese (trend)
- Costo per ambiente (tag Environment)

**B) Risorse Idle / Sprechi:**
- Lambda non invocate >90 giorni
- DynamoDB sotto-utilizzate
- EBS volumes non attached
- Snapshot vecchi >180 giorni
- RDS con CPU <10%
- Glue job con capacity eccessiva

**C) Tag Compliance:**
- Risorse senza tag obbligatori SIAE (Environment, Project, ManagedBy, Team, CostCenter, Repository)
- Percentuale compliance per tag

**D) Ottimizzazioni:**
- Ambienti dev/collaudo attivi off-hours (candidati a scheduling)
- Risorse over-provisioned (rightsizing)
- Storage senza lifecycle policy

### Step 3 — Report

Presenta i risultati come report strutturato:

```
FINOPS ANALYSIS REPORT
══════════════════════
Cloud:        AWS / Azure
Account:      <account-id> (<alias>)
Region:       <region>
Data:         <data analisi>

1. COST OVERVIEW
   Top spender: ...
   Trend: ...

2. SPRECHI IDENTIFICATI
   [tabella con risorsa, tipo spreco, costo stimato, azione suggerita]

3. TAG COMPLIANCE
   [percentuale per tag, risorse non conformi]

4. OTTIMIZZAZIONI RACCOMANDATE
   [lista prioritizzata per risparmio stimato]

RISPARMIO STIMATO TOTALE: $X/mese
```

### Strumenti Disponibili

Usa qualsiasi strumento disponibile nell'ordine di preferenza:
1. **Steampipe MCP** (se configurato) → query SQL dirette
2. **AWS CLI / Azure CLI** → comandi nativi
3. **Infracost** (se presente) → per stime costi IaC
4. **Console URLs** → se CLI non disponibile, fornisci link diretti alla console

Se nessun tool e' disponibile, guida il setup partendo dal piu' rapido (CLI nativo).
