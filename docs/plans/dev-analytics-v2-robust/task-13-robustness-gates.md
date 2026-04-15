# Task 13 — F6 Robustness Gates (Property-Based + AST Audit + Mutation + Integration)

**Goal:** Quality gates finali. Property-based tests + AST audit logging+errors + mutation testing + integration dual-window end-to-end.
**AC coperti:** AC-MACRO-2, AC-MACRO-3, AC-MACRO-4, AC-MACRO-6, NF18-NF23
**Dipendenze:** Tutti i task precedenti
**Effort:** ~60 min
**Test nuovi:** 54 (10 property + 2 AST + 8 integration dual-window + 34 gap coverage)

## File coinvolti

- `tests/test_property_based.py` — hypothesis tests (10)
- `tests/test_logging_coverage.py` — AST audit (1 test scansiona tutto)
- `tests/test_error_messages.py` — AST audit (1 test scansiona tutto)
- `tests/test_integration_dual_window.py` — 8 test e2e
- `tests/test_gap_coverage.py` — 34 test gap/edge coverage
- `scripts/audit_logging.py` (opzionale helper)

## Step 1 — test_property_based.py

```python
"""Property-based tests via hypothesis (10 test)."""
from __future__ import annotations
from hypothesis import given, strategies as st, settings
import math
import compute_kpis as ck
import compute_ai_impact as ai
import seasonality as s


@given(devs=st.dictionaries(st.text(min_size=1, max_size=30),
                             st.floats(allow_nan=False, allow_infinity=False, min_value=-1e6, max_value=1e6),
                             min_size=3, max_size=100))
@settings(max_examples=100, deadline=5000)
def test_z_score_sum_near_zero(devs):
    """Invariant: sum(z_score) ≈ 0 per population."""
    result = ck.z_score(devs)
    assert abs(sum(result.values())) < 1e-6


@given(devs=st.dictionaries(st.text(min_size=1, max_size=20),
                             st.floats(allow_nan=False, allow_infinity=False, min_value=0, max_value=1e4),
                             min_size=3, max_size=50))
@settings(max_examples=50, deadline=5000)
def test_z_score_finite(devs):
    result = ck.z_score(devs)
    assert all(math.isfinite(v) for v in result.values())


@given(baseline=st.floats(min_value=0.01, max_value=1e6),
       current=st.floats(min_value=0, max_value=1e6))
@settings(max_examples=100)
def test_compute_delta_trend_never_nan(baseline, current):
    from compute_ai_impact import compute_delta
    d = compute_delta(baseline, current)
    assert d.trend in {"IMPROVED", "DEGRADED", "STABLE"}
    assert math.isfinite(d.delta_pct)


@given(year=st.integers(min_value=2020, max_value=2030))
def test_italian_holidays_count_is_12(year):
    assert len(s.italian_holidays(year)) == 12


@given(since=st.dates(min_value=__import__('datetime').date(2020, 1, 1),
                       max_value=__import__('datetime').date(2030, 12, 31)),
       days=st.integers(min_value=1, max_value=365))
def test_working_days_never_exceeds_total(since, days):
    from datetime import timedelta
    until = since + timedelta(days=days)
    wd = s.working_days_in_window(since.isoformat(), until.isoformat())
    assert 0 <= wd <= days + 1


@given(v=st.floats(allow_nan=False, allow_infinity=False, min_value=-10, max_value=10))
def test_z_score_uniform_returns_zero(v):
    """σ=0 → tutti z=0."""
    devs = {"a": v, "b": v, "c": v}
    result = ck.z_score(devs)
    assert all(abs(z) < 1e-9 for z in result.values())


@given(skill_counts=st.dictionaries(st.text(min_size=1), st.integers(min_value=0, max_value=1000), min_size=3, max_size=20),
       roi=st.dictionaries(st.text(min_size=1), st.floats(allow_nan=False, allow_infinity=False, min_value=-5, max_value=5), min_size=3, max_size=20))
def test_correlation_in_range_minus1_to_1(skill_counts, roi):
    corr = ai.skill_usage_correlation(skill_counts, roi)
    if not math.isnan(corr):
        assert -1.001 <= corr <= 1.001


@given(rate=st.floats(min_value=0, max_value=1))
def test_rate_invariant_accepts_valid(rate):
    from validators import assert_rate_in_range
    assert_rate_in_range(rate)  # no raise


@given(bad_rate=st.floats(allow_nan=False, min_value=1.001, max_value=1e6))
def test_rate_invariant_rejects_invalid(bad_rate):
    from validators import assert_rate_in_range
    import pytest as pt
    with pt.raises(ValueError):
        assert_rate_in_range(bad_rate)


@given(items=st.lists(st.floats(allow_nan=False, min_value=0, max_value=1e4), min_size=0, max_size=50))
def test_median_robust_to_any_input_size(items):
    """Median non crasha su qualsiasi input list."""
    import statistics
    if items:
        m = statistics.median(items)
        assert math.isfinite(m)
```

## Step 2 — test_logging_coverage.py (AST audit)

```python
"""AST audit: ogni branch condizionale ha log.* call."""
import ast
from pathlib import Path


SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
MODULES_TO_AUDIT = [
    "autodetect_sources", "collect_github", "collect_s3_telemetry",
    "collect_anthropic_api", "compute_kpis", "compute_ai_impact",
    "compute_branches", "compute_reviews", "run_analytics",
]


def _has_log_call(node: ast.AST) -> bool:
    """Check if subtree contains a log.* call."""
    for n in ast.walk(node):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            if isinstance(n.func.value, ast.Name) and n.func.value.id in ("log", "logger", "logging"):
                return True
    return False


def test_exception_handlers_have_logging():
    """Ogni except body contiene almeno 1 log.* call."""
    issues = []
    for mod_name in MODULES_TO_AUDIT:
        path = SCRIPTS_DIR / f"{mod_name}.py"
        if not path.exists():
            continue
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if not _has_log_call(node):
                    # Skip if body is just 'pass' or 'raise'
                    is_bare_raise = any(isinstance(s, ast.Raise) for s in node.body)
                    if not is_bare_raise:
                        issues.append(f"{mod_name}:{node.lineno} except senza log")
    assert not issues, f"Logging gaps: {issues}"
```

## Step 3 — test_error_messages.py (AST audit)

```python
"""AST audit: RuntimeError messages actionable."""
import ast
from pathlib import Path


VERBS = {"run", "verifica", "configura", "controllare", "install", "esegui", "rimuovi", "usa", "apri"}
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"


def _extract_raise_msg(node: ast.Raise) -> str | None:
    if not node.exc or not isinstance(node.exc, ast.Call):
        return None
    if not node.exc.args:
        return None
    arg = node.exc.args[0]
    if isinstance(arg, ast.Constant):
        return arg.value if isinstance(arg.value, str) else None
    if isinstance(arg, ast.JoinedStr):
        # f-string: check static parts for verbs
        parts = [v.value for v in arg.values if isinstance(v, ast.Constant) and isinstance(v.value, str)]
        return " ".join(parts)
    return None


def test_runtime_errors_actionable():
    """Ogni RuntimeError raise ha messaggio ≥20 char + verbo azione."""
    issues = []
    for py in SCRIPTS_DIR.glob("*.py"):
        tree = ast.parse(py.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Raise) and node.exc and isinstance(node.exc, ast.Call):
                func = node.exc.func
                if isinstance(func, ast.Name) and func.id == "RuntimeError":
                    msg = _extract_raise_msg(node) or ""
                    if len(msg) < 20:
                        issues.append(f"{py.name}:{node.lineno} msg too short: {msg[:30]!r}")
                    if not any(v in msg.lower() for v in VERBS):
                        issues.append(f"{py.name}:{node.lineno} no verb: {msg[:50]!r}")
    assert not issues, f"Non-actionable errors: {issues}"
```

## Step 4 — test_integration_dual_window.py (8 test)

End-to-end con fixture dual-window:
```python
def test_dual_window_e2e_produces_excel_with_ai_impact_sheet(): ...
def test_dual_window_overlap_raises_actionable(): ...
def test_dual_window_baseline_empty_no_crash_warning(): ...
def test_dual_window_current_empty_no_crash_warning(): ...
def test_dual_window_ai_impact_computes_deltas(): ...
def test_dual_window_seasonality_adjustment_applied(): ...
def test_dual_window_cost_fallback_to_anthropic_api_when_s3_off(): ...
def test_dual_window_cost_override_cli_wins_over_api(): ...
```

## Step 5 — test_gap_coverage.py (34 test di coverage gap)

Analizza pytest --cov output → aggiungi test per linee non coperte. Esempi:
- Cache atomic write race
- Unicode nel glossary yaml
- Disk full su save
- Excel file locked retry
- Encoding errors su commit messages
- Timezone DST boundary
- Empty list edge su ogni KPI
- Single dev / single commit edge

## Step 6 — Mutation testing

```bash
cd skills/siae-dev-analytics
pip install mutmut
mutmut run --paths-to-mutate scripts/compute_kpis.py
mutmut run --paths-to-mutate scripts/compute_ai_impact.py
mutmut run --paths-to-mutate scripts/autodetect_sources.py
mutmut results
# Verifica mutation score >= 85% su ciascuno
```

Se score < 85%: analizza survivors, aggiungi test targeted.

## Step 7 — Smoke test finale

```bash
cat > /tmp/sport-licenze-dual.yml <<EOF
version: 2
scope: {repos: [itsiae/sport-gestione-licenze-service]}
time_window:
  baseline: {from: "2026-01-01", to: "2026-02-14"}
  current:  {from: "2026-02-15", to: "today"}
developers:
  exclude: []
options:
  enable_ai_impact: true
  min_commits_threshold: 1
  anthropic_org_id: null
output:
  format: xlsx
  path: /tmp/sport-licenze-analytics-v2.xlsx
EOF

cd skills/siae-dev-analytics
PYTHONPATH=scripts python3 scripts/run_analytics.py run --config /tmp/sport-licenze-dual.yml
```

Output atteso: `Report saved to: /tmp/sport-licenze-analytics-v2.xlsx`, 8 sheet, AI Impact Detail con before/after valori.

## Verify completa

```bash
cd skills/siae-dev-analytics
PYTHONPATH=scripts python3 -m pytest tests/ -v --cov=scripts --cov-report=term
# Atteso: 272 passed, coverage >= 85%
```

## Criteri accettazione

- [ ] 10 property-based tests pass (hypothesis max_examples=50-100)
- [ ] AST audit logging: 0 except body senza log.* (eccetto bare raise)
- [ ] AST audit errors: 0 RuntimeError con msg <20 char o senza verbo
- [ ] 8 integration test dual-window pass
- [ ] 34 gap coverage test pass
- [ ] Mutation score ≥85% su compute_kpis, compute_ai_impact, autodetect_sources
- [ ] Coverage line ≥85% overall
- [ ] Smoke test produce xlsx 8-sheet valido su sport-gestione-licenze-service
- [ ] Suite totale: 272 test passed, 0 skip, 0 fail
