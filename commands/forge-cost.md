---
name: forge-cost
description: "Stima costi della PR corrente via Infracost su Terragrunt/Terraform"
disable-model-invocation: true
---

Invoca la skill siae-devforge:siae-finops e segui la sezione "1. Shift-Left — Stima Costi Pre-Deploy (Infracost)". Esegui il flusso manuale:

1. Detecta file Terragrunt/Terraform nella directory corrente
2. Verifica `infracost` CLI installato (se assente, guida setup)
3. Esegui `infracost diff --path=. --format=json`
4. Presenta tabella con delta costi per risorsa
5. Se delta > $50/mese, mostra warning con suggerimenti ottimizzazione
