---
status: approved
date: 2026-06-26
topic: prereq-map forward-handoff inversion + tdd-gate durable ledger fallback
---

# Design — Fix inversione forward-handoff nel generatore prereq-map + tdd-gate ledger durevole

## Contesto

Segnalazione utente: "il bug degli hook ritardato". Il TDD Gate bloccava in loop
l'edit di codice di produzione anche dopo aver completato il ciclo TDD, e per
debuggare un bug serviva la catena impossibile `brainstorm → tdd → debug`. Root
cause analysis (siae-debugging, 4 fasi) ha isolato due difetti distinti.

## Problema

### RC-A — Inversione semantica nel generatore della mappa prerequisiti

`lib/generate-prereq-map.sh` interpretava `REQUIRED SUB-SKILL: X` nel corpo di una
skill (handoff **forward**: "invoca X durante/dopo questa skill") come prerequisito
**a monte**. Produceva edge invertiti `siae-debugging=siae-tdd` e
`siae-receiving-review=siae-tdd`, forzando una catena semanticamente impossibile
(non puoi scrivere un test fallente prima di aver diagnosticato il bug). Gli autori
avevano già il meccanismo `CROSS_CUTTING` (per verification/retrospective) ma
avevano dimenticato siae-tdd e gli altri forward-handoff.

### RC-B — tdd-gate fidato solo del session file effimero

`hooks/tdd-gate` decideva allow/block con un puro `grep -qF siae-tdd` su
`.devforge-session-skills`, azzerato a cold-start e mai scritto quando il
sub-skill-gate rifiuta l'invocazione Skill in PreToolUse. Il ledger task-scoped
durevole veniva calcolato ma usato solo per logging.

## Decisione

- **RC-A**: marcare le 6 skill forward-handoff come entry-point (`NONE` in
  `_curated_prereqs`), stesso pattern già usato per siae-brainstorming/siae-onboarding.
  Rigenerare la mappa.
- **RC-B**: fallback del gate sul ledger per-task durevole
  (`.devforge-task-skills/<task_id>/skills_invoked`), coerente con il modello
  task-scoped (ADR-001). Rollback `DEVFORGE_USE_SESSION_SCOPE=1` preservato.

## Criteri di accettazione

- La mappa rigenerata non contiene edge forward (`siae-debugging`, `siae-receiving-review`,
  `siae-codebase-map`, le 3 datalake-setup non sono più chiavi).
- Gli edge legittimi a monte restano intatti (`siae-tdd=siae-brainstorming`, ecc.).
- Il gate consente l'edit quando il ledger task ha siae-tdd anche con session file vuoto;
  blocca quando non c'è evidenza in nessuna delle due fonti.
- Nessuna regressione sulle suite esistenti.

## File modificati

- `hooks/tdd-gate` — fallback RC-B sul ledger task durevole
- `lib/generate-prereq-map.sh` — 6 entry `NONE` per le skill forward-handoff (RC-A)
- `lib/prereq-map.generated` — rigenerata, rimosse le 2 inversioni
- `tests/hooks/test_tdd_gate_task_ledger.sh` — nuovo test RC-B (3 casi)
- `tests/lib/test_generate_prereq_map.sh` — sezione no-forward-edges (RC-A)
- `tests/tdd-gate-external.test.sh` — HOME ermetico per isolare il ledger dalla sessione live

## Follow-up (fuori scope)

- `hooks/session-start` azzera `.devforge-tdd-state` incondizionatamente (fail-open).
- Bootstrap paradox: effetto sugli altri seat solo dopo rilascio/update del plugin.
