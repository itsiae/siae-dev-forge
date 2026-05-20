---
name: forge-execute
description: "Esegue un piano implementativo in una sessione separata, a batch con checkpoint umani"
disable-model-invocation: true
---

Esegui il piano implementativo seguendo la skill `siae-executing-plans`. Argomento opzionale: path al file piano (es. `docs/plans/<topic>/overview.md`). Se non fornito, cerca il piano in `docs/plans/` e chiedi conferma all'utente prima di iniziare. Esegue per batch di 3 task con report e checkpoint umano fra un batch e l'altro. Per ogni task implementativo usa `siae-tdd`. Se il piano non esiste, avvia prima `siae-brainstorming` + `siae-writing-plans`.
