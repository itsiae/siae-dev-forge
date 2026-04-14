---
name: using-devforge
description: >
  Stabilisce il backbone core di discovery e invocazione skill DevForge
  all'inizio di ogni conversazione.
  Trigger: inizio sessione, apertura nuovo progetto, prima interazione.
---

## SUBAGENT-STOP — Gate Check

<SUBAGENT-STOP>
Sei un subagent con un task specifico assegnato dal tuo orchestratore?

SE SI: fermati qui. Non applicare la regola dell'1%. Segui solo il prompt del
tuo orchestratore e la tua allowlist.

SE NO: procedi normalmente. Questa skill definisce il backbone operativo della
sessione.
</SUBAGENT-STOP>

## Come Accedere Alle Skill

In Claude Code usa lo `Skill` tool. Quando una skill si applica, invocala
prima di rispondere o agire.

Non usare il Read tool sui file delle skill.

## La Regola

Se pensi che ci sia anche l'1% di probabilita' che una skill si applichi,
DEVI invocarla.

Se una skill si applica al task, non hai scelta: la usi.

Questo non e' negoziabile. Non e' opzionale. Non puoi razionalizzare per
evitarlo.

**OBBLIGO CATALOGO:** il Dynamic Skill Catalog viene iniettato nella sessione.
Per ogni messaggio utente devi scansionarlo e confrontare la colonna
**INVOCA SE l'utente menziona** con la richiesta corrente. Se trovi un match
anche parziale, invoca la skill prima di rispondere.

Le domande sono task. Il controllo delle skill viene prima anche delle domande
di chiarimento.

## DevForge Backbone Core

- Le skill di processo vengono prima: `siae-brainstorming`,
  `siae-debugging`, `siae-git-workflow`.
- Le skill specialistiche si agganciano al flusso core, non lo sostituiscono.
- Qualsiasi task implementativo: feature, bug fix, refactoring, config,
  ottimizzazione -> `siae-brainstorming` prima di tutto.
- Dopo brainstorming approvato -> `siae-writing-plans`.
- Bug, errore, crash, stacktrace, test che fallisce -> `siae-debugging`
  prima del fix.
- Scrittura di codice di produzione -> `siae-tdd`.
- Task security-sensitive -> `siae-security` insieme alla skill di dominio.
- Operazioni git -> `siae-git-workflow`.
- Branch pronto per PR / apertura PR -> `siae-finishing-branch`.
- Review del codice / audit -> `siae-blind-review`.
- Richiesta review su PR -> `siae-requesting-review`.
- Feedback review ricevuto -> `siae-receiving-review`.
- Prima di dichiarare "fatto", "fixato", "completato", "pronto" ->
  `siae-verification`.

## Always-On Companion Skills

Le skill specifiche di dominio non partono mai da sole. Si agganciano sempre a
companion skills del backbone:

- Qualsiasi implementazione o modifica di codice/config/IaC/data/frontend ->
  skill di dominio + `siae-security` + `siae-tdd`.
- Qualsiasi task che puo' finire in PR, audit o code review ->
  skill di dominio + workflow review (`siae-blind-review`,
  `siae-requesting-review`, `siae-receiving-review`) + `siae-verification`.
- `siae-security` non e' solo per task "esplicitamente security": e' companion
  di default per codice, config, IAM, dati, API, frontend, Terraform e review.
- Il workflow review non e' opzionale: se stai cambiando qualcosa che andra' in
  branch/PR, il backbone deve preparare o eseguire la review.

## Skill Priority

Quando piu' skill potrebbero applicarsi, usa questo ordine:

1. `siae-verification`
2. `siae-tdd`
3. `siae-git-workflow`
4. `siae-security`
5. `siae-debugging`
6. `siae-brainstorming`
7. Tutte le altre skill

Le skill di dominio vengono dopo le skill di processo. In pratica:

- "Costruiamo X" -> brainstorming prima, poi skill specialistiche.
- "Fix questo bug" -> debugging prima, poi skill specialistiche, poi TDD.
- "Devo fare git commit / push / PR" -> git-workflow prima.
- "Questo tocca credenziali, IAM, encryption o PII" -> security sempre.
- "Penso di aver finito" -> verification prima di dirlo.

## Gate Operativi

### Git Operations Intercept

Prima di `git checkout -b`, `git commit`, `git push`, `git merge`, `git tag`,
`gh pr create` verifica di avere gia' invocato `siae-git-workflow`.

Prima di aprire una PR o dichiarare un branch "pronto", verifica di avere gia'
invocato `siae-finishing-branch`.

### EnterPlanMode Intercept

Prima di EnterPlanMode verifica che il brainstorming sia gia' stato fatto.
Se non e' stato fatto, invoca prima `siae-brainstorming`.

### Review Intercept

Se stai facendo audit o code review, attiva il workflow review corretto:
`siae-blind-review`, `siae-requesting-review`, `siae-receiving-review`.

### Verification Intercept

Nessuna dichiarazione di completamento senza evidenza. Prima di dire che un
task e' completato, fixato o pronto, invoca `siae-verification`.

## Regole Operative Brevi

- Se una skill specialistica matcha, agganciala al backbone core corretto.
- Se servono piu' di 3 skill per un singolo messaggio, chiedi di decomporre.
- I diagrammi utente devono essere PlantUML, non Mermaid.
- Non fare "prima una cosa veloce". Il check skill viene sempre prima.

## Istruzioni Utente

Le istruzioni dell'utente dicono COSA fare. Le skill dicono COME farlo in modo
disciplinato.

Se l'utente chiede un risultato, non saltare il workflow: attiva le skill
rilevanti e poi esegui il task.
