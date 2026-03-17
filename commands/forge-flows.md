---
name: forge-flows
description: "Analisi flussi frontend: rileva framework, mappa sezioni navigazionali, genera test list per sezione pronta per Xray (CSV o MCP)"
disable-model-invocation: true
---

Invoca la skill siae-devforge:siae-nr-test-flows e seguila esattamente come ti viene presentata.
Esegui il workflow completo a 6 step: framework detection, flow map YAML, prioritizzazione,
generazione test list per sezione (happy path + edge + negativi + profilazione),
presentazione con hard gate approvazione utente, export in Xray o CSV.
