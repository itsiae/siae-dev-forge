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

Invoca le skill via `Skill` tool. Non leggere i file skill con Read.

## La Regola

Se pensi che ci sia anche l'1% di probabilita' che una skill si applichi,
DEVI invocarla.

Se una skill si applica al task, non hai scelta: la usi. Questo non e'
negoziabile. Non e' opzionale. Non puoi razionalizzare per evitarlo.

**OBBLIGO CATALOGO:** il Dynamic Skill Catalog viene iniettato nella sessione.
Per ogni messaggio utente scansiona la colonna **INVOCA SE l'utente menziona**
e, se trovi un match anche parziale, invoca la skill prima di rispondere.
Le domande sono task: il controllo skill viene prima anche delle domande di
chiarimento.

## DevForge Backbone Core

- Le skill di processo vengono prima: `siae-brainstorming`, `siae-debugging`, `siae-git-workflow`.
- Le skill specialistiche si agganciano al flusso core, non lo sostituiscono.
- Qualsiasi task implementativo (feature, bug fix, refactoring, config, ottimizzazione) -> `siae-brainstorming` prima di tutto.
- Dopo brainstorming approvato -> `siae-writing-plans`.
- Bug, errore, crash, stacktrace, test che fallisce -> `siae-debugging` prima del fix.
- Scrittura di codice di produzione -> `siae-tdd`.
- Task security-sensitive -> `siae-security` insieme alla skill di dominio.
- Operazioni git -> `siae-git-workflow`.
- Branch pronto per PR / apertura PR -> `siae-finishing-branch`.
- Review del codice / audit -> `siae-blind-review`.
- Richiesta review su PR -> `siae-requesting-review`.
- Feedback review ricevuto -> `siae-receiving-review`.
- Prima di dichiarare "fatto", "fixato", "completato", "pronto" -> `siae-verification`.

## Always-On Companion Skills

Le skill di dominio non partono mai da sole: si agganciano sempre a companion del backbone.

- Qualsiasi implementazione o modifica di codice/config/IaC/data/frontend ->
  skill di dominio + `siae-security` + `siae-tdd`.
- Qualsiasi task che puo' finire in PR, audit o code review -> skill di dominio + workflow review (`siae-blind-review`, `siae-requesting-review`, `siae-receiving-review`) + `siae-verification`.
- `siae-security` non e' solo per task "esplicitamente security": e' companion di default per codice, config, IAM, dati, API, frontend, Terraform e review.
- Il workflow review non e' opzionale: se stai cambiando qualcosa che andra' in branch/PR, il backbone deve preparare o eseguire la review.

## Priority & Rules

Ordine quando piu' skill matchano: 1) `siae-verification` 2) `siae-tdd`
3) `siae-git-workflow` 4) `siae-security` 5) `siae-debugging`
6) `siae-brainstorming` 7) altre skill (dominio dopo processo).

- "Costruiamo X" -> brainstorming prima, poi specialistiche.
- "Fix questo bug" -> debugging prima, poi specialistiche, poi TDD.
- "git commit/push/PR" -> git-workflow prima.
- "Credenziali/IAM/encryption/PII" -> security sempre.
- "Penso di aver finito" -> verification prima di dirlo.
- Se una skill specialistica matcha, agganciala al backbone core corretto.
- Se servono piu' di 3 skill per un singolo messaggio, chiedi di decomporre.
- I diagrammi utente devono essere PlantUML, non Mermaid.
- Non fare "prima una cosa veloce". Il check skill viene sempre prima.

## Gate Operativi

- **Git Intercept**: prima di `git checkout -b`, `git commit`, `git push`,
  `git merge`, `git tag`, `gh pr create` -> `siae-git-workflow` gia' invocato.
  Prima di aprire una PR o dichiarare un branch "pronto" ->
  `siae-finishing-branch` gia' invocato.
- **EnterPlanMode Intercept**: prima di EnterPlanMode verifica brainstorming
  gia' fatto; se no, invoca prima `siae-brainstorming`.
- **Review Intercept**: audit o code review -> attiva workflow review
  (`siae-blind-review`, `siae-requesting-review`, `siae-receiving-review`).
- **Verification Intercept**: nessuna dichiarazione di completamento senza
  evidenza; prima di dire task completato/fixato/pronto -> `siae-verification`.
