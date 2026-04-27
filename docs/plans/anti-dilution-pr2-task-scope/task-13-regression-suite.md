---
task: 13
title: Regression suite PR #2
size: L
depends: [01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12]
---

# Task 13 — regression suite `tests/pr2-task-scope/`

Suite completa per i cambiamenti PR #2. Target: ≥40 test PASS, zero
regression sui 51 test PR #1 + 161 baseline.

## Layout

```
tests/pr2-task-scope/
├── run-all.sh
├── lib/
│   ├── test_task_id.sh              # 10 casi (task 2)
│   └── test_file_taxonomy.sh        # 25 casi (task 3)
├── scripts/
│   └── test_generate_prereq_map.sh  # 5 casi (task 4)
├── hooks/
│   ├── test_tdd_gate_task_scope.sh          # task 5
│   ├── test_brainstorming_gate_task_scope.sh # task 6
│   ├── test_evidence_stop_gate.sh            # task 7
│   ├── test_pre_commit_parser.sh             # task 8
│   ├── test_coverage_force_run.sh            # task 8
│   ├── test_sub_skill_gate_generated.sh      # task 9
│   ├── test_pr_blind_review_gate.sh          # task 10
│   └── test_plan_gate_write.sh               # task 11
├── integration/
│   ├── test_dual_write_divergence.sh         # shadow-check
│   ├── test_rollback_use_session_scope.sh    # rollback end-to-end
│   ├── test_evidence_copy_forward.sh         # task 2 + gate integration
│   └── test_abuse_tracking.sh                # tutti i bypass env var
└── fixtures/
    ├── itsiae-repo/                          # mock git repo scope:itsiae
    └── other-repo/                           # mock git repo out-of-scope
```

## Driver `run-all.sh`

Segue pattern `tests/compression-regression/run-all.sh`:
- Counter PASS / FAIL / SKIP
- Summary line finale
- Exit code = FAIL count

## Test di integrazione critici

### test_dual_write_divergence.sh

Scenario: invoca 20 operazioni tipiche (Edit/Write/git commit/gh pr create)
con e senza `DEVFORGE_USE_SESSION_SCOPE=1`. Calcola divergenza (n_block_task
vs n_block_session). Assert <10%.

### test_rollback_use_session_scope.sh

Scenario end-to-end:
1. Setup task: branch + design doc
2. Invoca siae-brainstorming → scrive entrambi
3. Set `DEVFORGE_USE_SESSION_SCOPE=1`
4. Cambia branch (task_id cambia)
5. Edit file prod → deve essere **allowed** (session-scope ha skill, task-scope non avrebbe)
6. Unset env → Edit file prod → deve essere **blocked** (task-scope non ha)

### test_evidence_copy_forward.sh

Scenario:
1. Setup task A: branch=foo, design doc mtime=T1 → TASK_A
2. Invoca siae-brainstorming → task_skills_validated += siae-brainstorming (TASK_A)
3. Modifica design doc (mtime=T2) → TASK_B
4. Edit prod code
5. Assert: task_skills_validated (TASK_B) contiene siae-brainstorming (copy-forward)

### test_abuse_tracking.sh

Tutti i bypass (SKIP_BRAINSTORMING, SKIP_GIT_GATE, FORCE_STOP,
SKIP_BLIND_REVIEW) chiamati ≥5 volte stesso giorno → verifica log
`bypass_abuse_suspected` emesso.

## Acceptance

- [ ] ≥40 test nuovi PASS
- [ ] 51/51 test PR #1 continuano a PASS (no regression compression)
- [ ] 161 test baseline continuano a PASS (stesso set pre/post PR #1)
- [ ] Shadow-check divergenza <10% misurata e loggata
- [ ] `tests/pr2-task-scope/run-all.sh` exit 0
- [ ] CI (se presente) green

## Out of scope

- Test E2E con Claude Code runtime → smoke test manuale post-merge
- Load test: performance dei gate → PR #3 observability (dashboard)
