from unittest.mock import MagicMock
from lib.release_risk.security_state import evaluate_criterion_17


def make_runner(applicable: bool, critical: int = 0, high: int = 0,
                medium: int = 0, low: int = 0, name: str = "FakeRunner"):
    runner = MagicMock()
    runner.is_applicable.return_value = applicable
    runner.__class__.__name__ = name
    type(runner).__name__ = name
    if applicable:
        findings = MagicMock()
        findings.critical = critical
        findings.high = high
        findings.medium = medium
        findings.low = low
        runner.run.return_value = findings
    return runner


def test_no_applicable_runners(tmp_path):
    runner = make_runner(applicable=False)
    r = evaluate_criterion_17(tmp_path, runners_override=[runner])
    assert r.status == "TOOL_UNAVAILABLE"
    assert "No applicable" in r.evidence[0]


def test_runner_returns_none(tmp_path):
    runner = MagicMock()
    runner.is_applicable.return_value = True
    runner.run.return_value = None
    r = evaluate_criterion_17(tmp_path, runners_override=[runner])
    assert r.status == "TOOL_UNAVAILABLE"


def test_no_vulnerabilities_status_no(tmp_path):
    runner = make_runner(applicable=True, critical=0, high=0)
    r = evaluate_criterion_17(tmp_path, runners_override=[runner])
    assert r.status == "NO"
    assert "critical=0" in str(r.evidence)


def test_one_critical_triggers_yes(tmp_path):
    runner = make_runner(applicable=True, critical=1, high=0)
    r = evaluate_criterion_17(tmp_path, runners_override=[runner])
    assert r.status == "YES"
    assert r.weight == 2


def test_high_above_threshold_triggers_yes(tmp_path):
    runner = make_runner(applicable=True, critical=0, high=6)  # > 5
    r = evaluate_criterion_17(tmp_path, runners_override=[runner])
    assert r.status == "YES"


def test_high_at_threshold_does_not_trigger(tmp_path):
    runner = make_runner(applicable=True, critical=0, high=5)  # NOT > 5
    r = evaluate_criterion_17(tmp_path, runners_override=[runner])
    assert r.status == "NO"


def test_aggregates_multiple_runners(tmp_path):
    r1 = make_runner(applicable=True, critical=0, high=3, name="PipAuditRunner")
    r2 = make_runner(applicable=True, critical=0, high=3, name="NpmAuditRunner")
    r = evaluate_criterion_17(tmp_path, runners_override=[r1, r2])
    assert r.status == "YES"  # total high = 6 > 5
    assert "high=6" in str(r.evidence)


def test_env_threshold_override(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_RELEASE_RISK_SECURITY_HIGH_THRESHOLD", "10")
    runner = make_runner(applicable=True, critical=0, high=8)  # > default 5, < env 10
    r = evaluate_criterion_17(tmp_path, runners_override=[runner])
    assert r.status == "NO"


def test_suggested_followup_flag_on_critical(tmp_path):
    runner = make_runner(applicable=True, critical=2)
    r = evaluate_criterion_17(tmp_path, runners_override=[runner])
    assert "suggested_followup_security=True" in str(r.evidence)
