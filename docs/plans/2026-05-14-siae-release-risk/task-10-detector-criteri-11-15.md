# Task 10 — detector.py criteri 11-15

**Stato:** [DONE]
**SP:** 1.5 Human / 0.5 Augmented
**Dipendenze:** task-08

## Goal

Estendere `lib/release_risk/detector.py` con criteri 11-15: coverage stub (delega a coverage_src), E2E tests, perf tests, user impact, files count.

## File coinvolti

- Edit: `lib/release_risk/detector.py`

## Step

### Step 1 — Append a detector.py

Aggiungi:
```python
def criterion_11_coverage_stub(coverage_src_fn=None, sha: str = "") -> CriterionResult:
    """+2 se coverage < 70%. Delega a coverage_src_fn (vedi task-14)."""
    if coverage_src_fn is None:
        return CriterionResult(id=11, name="Coverage < 70%", status="REQUIRES_INPUT",
                               weight=2, source="ask:user",
                               notes="coverage_src_fn not provided")
    return coverage_src_fn(sha)


def criterion_12_e2e_tests(ci_config_present: bool, e2e_stage_found: bool) -> CriterionResult:
    """+2 se E2E non eseguiti. CI config + stage detection esterni (delegati a caller)."""
    if not ci_config_present:
        return CriterionResult(id=12, name="E2E tests not run", status="REQUIRES_INPUT",
                               weight=2, source="ask:user", notes="no CI config detected")
    if not e2e_stage_found:
        return CriterionResult(id=12, name="E2E tests not run", status="YES",
                               weight=2, evidence=["no e2e stage in .github/workflows/*.yml"],
                               source="diff:ci")
    return CriterionResult(id=12, name="E2E tests not run", status="NO", weight=2,
                           evidence=["e2e_stage_detected"], source="diff:ci")


def criterion_13_perf_tests(diff_content: str) -> CriterionResult:
    """-1 se perf test eseguiti (mitigazione)."""
    pattern = re.compile(r"jmeter|gatling|locust|k6|performance\.test|load\.test", re.I)
    if pattern.search(diff_content):
        return CriterionResult(id=13, name="Performance tests (mitigation)", status="YES",
                               weight=-1, evidence=["perf_tool_detected"], source="diff:grep")
    return CriterionResult(id=13, name="Performance tests (mitigation)", status="NO",
                           weight=-1, source="diff:grep")


def criterion_14_user_impact(user_impact_ge_50pct: Optional[bool]) -> CriterionResult:
    """+2 se impact > 50% utenti. Inferibile solo da user (caller passa risposta)."""
    if user_impact_ge_50pct is None:
        return CriterionResult(id=14, name="User impact > 50%", status="REQUIRES_INPUT",
                               weight=2, source="ask:user")
    return CriterionResult(id=14, name="User impact > 50%",
                           status="YES" if user_impact_ge_50pct else "NO",
                           weight=2, evidence=[f"user_confirmed={user_impact_ge_50pct}"],
                           source="ask:user")


def criterion_15_files_count(diff_files: list[str]) -> CriterionResult:
    """+1 se modificati > 10 file."""
    count = len(diff_files)
    if count > 10:
        return CriterionResult(id=15, name="Modified > 10 files", status="YES", weight=1,
                               evidence=[f"file_count={count}"], source="diff:count")
    return CriterionResult(id=15, name="Modified > 10 files", status="NO", weight=1,
                           evidence=[f"file_count={count}"], source="diff:count")
```

### Step 2 — Verifica import

Run:
```bash
python3 -c "from lib.release_risk.detector import criterion_11_coverage_stub, criterion_12_e2e_tests, criterion_13_perf_tests, criterion_14_user_impact, criterion_15_files_count; print('OK')"
```

### Step 3 — Commit

```bash
git add lib/release_risk/detector.py
git commit -m "feat(release-risk): detector criteri 11-15 (coverage-stub, E2E, perf, user impact, files)"
```

## Criteri di accettazione

- [ ] 5 funzioni aggiunte
- [ ] Criterion 11 stub delega coverage_src
- [ ] Criterion 13 weight negative mitigation
- [ ] Criterion 14 accetta `None` → REQUIRES_INPUT
- [ ] Commit eseguito
