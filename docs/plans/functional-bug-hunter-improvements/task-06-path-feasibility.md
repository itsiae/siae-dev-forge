# Task 06 — Implement scripts/path_feasibility.py + smoke test

**Stato**: [PENDING] · **Effort**: 3h · **File toccati**: 3 (script + 2 test fixture)

## Goal

Codificare in script eseguibile la "Phase 6 — Path feasibility filter"
dichiarata nello SKILL.md. Oggi è solo prosa; chiude il gap A1 #2
dell'audit ("capability dichiarata ma non codificata").

## Acceptance

- File `skills/siae-functional-bug-hunter/scripts/path_feasibility.py`
  esiste, eseguibile (`chmod +x`), shebang `#!/usr/bin/env python3`.
- Stdlib only (Python 3.9+).
- CLI:
  `path_feasibility.py --hypotheses <path> --roots <root1> [<root2>...] [--out <path>] [--skip-dirs ...]`
- Output: scrive verdict (`feasible` / `infeasible` + `verdict_reason`
  + `matched_files`) inline su ogni hypothesis nel file di output.
- Verdetti basati su 3 condizioni:
  1. `actor_primitive[s]` presente (altrimenti infeasible
     `no_actor_primitive`)
  2. `evidence_path` matched almeno un file in scope (altrimenti
     infeasible `evidence_path_not_in_scope`)
  3. Almeno 1 `path_predicate` (case-insensitive substring) presente nei
     file matched (altrimenti infeasible `no_predicate_matched`; se
     zero predicates dichiarati → feasible `no_predicates_declared`)
- Exit codes: 0 ok, 1 no input / malformed JSON / zero hypotheses,
  2 IO error scrittura.
- Smoke test fixture (≥1 positive + ≥1 negative) in
  `tests/path_feasibility/`.

## Implementation

1. **Test first (TDD)**: scrivere
   `tests/path_feasibility/test_path_feasibility.py` con almeno 4 test:
   - `test_feasible_with_predicate_match` — actor + evidence_path in scope
     + predicate matched
   - `test_infeasible_no_actor` — no actor_primitive
   - `test_infeasible_evidence_path_not_in_scope` — path non esiste
   - `test_infeasible_no_predicate_matched` — predicates declared but none
     found
2. Tests devono fallire (file `path_feasibility.py` ancora assente o
   stub).
3. Implementare `scripts/path_feasibility.py` finché tutti i test
   passano (Green).
4. Refactor se necessario (Refactor phase).

## Why glob+keyword e non AST

Decisione Round 2 consenso: AST richiederebbe tree-sitter setup +
gestione per-stack (Java, TS, Python). La forma minimale glob+keyword
chiude il claim della SKILL.md ("filters by path feasibility") con
deterministica baseline. Upgrade ad AST è scope v1.3.0.
