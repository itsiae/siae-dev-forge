---
title: FSM Backbone — Considered and Deferred
date: 2026-04-25
status: deferred
author: lodetomasi
related: 2026-04-25-anti-dilution-enforcement-design.md
---

# FSM Backbone — Considered and Deferred

## Question

Utente 2026-04-25: "vedi se ha senso fare una backbone di ai-sdlc più
deterministica". Dovremmo introdurre una Finite State Machine esplicita
(IDLE → INTAKE → BRAINSTORM → PLAN_APPROVED → IMPLEMENT → TDD_RED →
TDD_GREEN → REVIEW → VERIFIED) come livello sopra le skill DevForge?

## Context

Il backbone attuale (post PR #1-3) è rule-based + evidence-based:
- Regola 1% (markdown nel prompt)
- `validates_via` predicates in frontmatter SKILL.md (PR #1)
- Task-scoped state (PR #2)
- Observability loop (PR #3)

Una FSM esplicita aggiungerebbe:
- Stato SDLC corrente in `~/.claude/.devforge-fsm-state`
- Transizioni valide codificate come adjacency list
- Gate diventano check su transizione legale
- Evidence diventa pre-condition della transizione

## Decision

**Deferred fino a post-measurement PR #2.**

## Rationale

### Perché "no" adesso

1. **Premature abstraction**. PR #1-3 già implementano le primitive (evidence
   contract + task-scope + prereq map). La FSM emerge come VIEW su questi dati,
   non come NUOVO layer.

2. **Measure first**. Il problema misurato è adoption ceremoniale (invocazione
   senza evidence). L'evidence contract da solo risolve il 60% della
   diluizione. Prima di aggiungere complessità, misuriamo il lift reale.

3. **Flessibilità perduta**. Workflow reali hanno cicli legittimi (review →
   fix → re-test). Una FSM rigida disegnata a priori li spezza. Una FSM
   data-driven (imparata da telemetry) li accomoda.

4. **YAGNI esplicito**. 11 ADR nel design PR #1-3 sono già ai limiti di
   scope. Aggiungere "FSM layer" espande il progetto senza evidenza che
   serva.

### Perché "forse dopo"

Se post-PR-2 (2 settimane di telemetry) misuriamo:
- adoption per-task < 70% su 2+ skill core → l'evidence contract non basta,
  serve forcing-function sul flusso
- pattern di "skip" ripetitivo (es. utenti saltano sempre verification dopo
  commit) → la FSM discovered da telemetry rivelerebbe dove gli umani
  divergono dal backbone, con dati

Allora vale la pena progettare PR #4 "FSM emergente":

```bash
python3 lib/fsm-learner.py \
    --events docs/measurements/post-pr2-2weeks/ \
    --out docs/plans/fsm-discovered.dot
```

Confronto con FSM teorica → gap = transizioni da proteggere con gate FSM hard.

**Questo approach data-driven è più solido** perché:
- Parte da dati reali, non da modello mentale
- 1 script Python (2 SP), non redesign
- Restituisce lista ordinata di "next bottleneck" misurato

## Gate di riconsiderazione

Riconsidera questa decisione SE:

1. 14 giorni post-merge PR #2, adoption per-task < 70% su 2+ skill core
2. Telemetria mostra skip pattern ricorrenti su transizione specifica
   (es. "dopo commit, skip verification in X% delle sessioni")
3. Utenti segnalano confusione su "quale skill ora" (= backbone testuale
   insufficiente → FSM visibile aiuterebbe)

In assenza di questi segnali, la FSM resta deferred.

## Alternatives considered

- **FSM designed from scratch (redesign completo)**: rifiutato per #1-#4
  sopra. Perdita del lavoro PR #1 già fatto + rischio over-engineering.
- **FSM parziale solo su TDD cycle (RED-GREEN-REFACTOR)**: già presente
  nel codice (`capture-test-result` hook). Estendere allo SDLC completo
  = FSM emergente PR #4 post-misurazione.
- **FSM come documentazione senza enforcement**: basso ROI. Il grafo
  Graphviz nel design doc esiste già — non aggiunge determinismo.

## Consequences

- PR #1-3 procedono come pianificato
- Post-merge PR #2, si aggiunge task di measurement: "run fsm-learner
  2 settimane dopo il merge, confronta con backbone teorica"
- Se threshold di riconsiderazione scatta → PR #4 FSM emergente
- Se non scatta → backbone resta rule+evidence based (più semplice da
  mantenere)

## References

- Design madre: `docs/plans/2026-04-25-anti-dilution-enforcement-design.md`
- Baseline: `docs/measurements/baseline-2026-04-25/`
- A/B test: `docs/measurements/ab-test-2026-04-25.md`
