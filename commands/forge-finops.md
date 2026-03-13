---
name: forge-finops
description: "Dashboard interattiva costi AWS via Steampipe MCP + AWS Thrifty benchmark"
disable-model-invocation: true
---

Invoca la skill siae-devforge:siae-finops e segui la sezione "2. Query Interattive — Steampipe MCP". Presenta il menu interattivo:

a) Top 10 servizi piu' costosi (mese corrente)
b) Risorse idle/sotto-utilizzate (AWS Thrifty)
c) Tag compliance audit (risorse senza tag obbligatori)
d) Cost trend (mese-su-mese)
e) Query libera (linguaggio naturale → SQL)

Verifica che il Steampipe MCP server sia attivo. Se non disponibile, guida il setup.
Usa il catalogo query in reference/steampipe-queries.md.
