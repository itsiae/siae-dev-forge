---
name: forge-jasper
description: "Ricostruisci template JRXML da un PDF di riferimento con pixel-match iterativo"
disable-model-invocation: true
---

Invoca la skill siae-devforge:siae-jasper-from-pdf e seguila esattamente come ti viene presentata.

L'utente vuole ricostruire un template JRXML a partire da un PDF di riferimento.
Esegui il workflow completo: analisi PDF reference, generazione JRXML, loop di convergenza pixel-diff, validazione finale.
Se non specificato, cerca un file PDF nella directory corrente o chiedi il percorso.
