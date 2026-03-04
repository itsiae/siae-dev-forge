---
name: forge-implement
description: "Implementa un piano con subagent freschi e review a 2 stadi (spec + quality)"
disable-model-invocation: true
---

Implementa il piano implementativo corrente usando la skill `siae-subagent-development`. Per ogni task del piano, lancia un subagent implementer fresco, poi verifica con spec-reviewer e code-quality-reviewer. Se non esiste un piano in `docs/plans/`, avvia prima il brainstorming con `siae-brainstorming`.
