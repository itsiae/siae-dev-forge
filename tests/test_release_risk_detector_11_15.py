from lib.release_risk.detector import (
    criterion_11_coverage_stub, criterion_12_e2e_tests, criterion_13_perf_tests,
    criterion_14_user_impact, criterion_15_files_count,
)
from lib.release_risk.schema import CriterionResult


def test_c11_coverage_stub_requires_input_without_fn():
    r = criterion_11_coverage_stub()
    assert r.status == "REQUIRES_INPUT"


def test_c11_coverage_stub_delegates():
    def fake_cov(sha):
        return CriterionResult(id=11, name="Coverage < 70%", status="NO",
                               weight=2, source="evidence:coverage",
                               evidence=["overall_pct=78"])
    r = criterion_11_coverage_stub(coverage_src_fn=fake_cov, sha="abc123")
    assert r.status == "NO"
    assert "overall_pct=78" in r.evidence


def test_c12_e2e_no_ci_config():
    r = criterion_12_e2e_tests(ci_config_present=False, e2e_stage_found=False)
    assert r.status == "REQUIRES_INPUT"


def test_c12_e2e_ci_present_no_stage():
    r = criterion_12_e2e_tests(ci_config_present=True, e2e_stage_found=False)
    assert r.status == "YES"
    assert r.weight == 2


def test_c12_e2e_ci_with_stage():
    r = criterion_12_e2e_tests(ci_config_present=True, e2e_stage_found=True)
    assert r.status == "NO"


def test_c13_perf_jmeter():
    r = criterion_13_perf_tests("Run jmeter -t test.jmx")
    assert r.status == "YES"
    assert r.weight == -1


def test_c13_perf_no():
    r = criterion_13_perf_tests("just code")
    assert r.status == "NO"


def test_c14_user_impact_none():
    r = criterion_14_user_impact(None)
    assert r.status == "REQUIRES_INPUT"


def test_c14_user_impact_true():
    r = criterion_14_user_impact(True)
    assert r.status == "YES"


def test_c14_user_impact_false():
    r = criterion_14_user_impact(False)
    assert r.status == "NO"


def test_c15_files_count_yes():
    r = criterion_15_files_count(["f{}.java".format(i) for i in range(15)])
    assert r.status == "YES"
    assert r.weight == 1


def test_c15_files_count_no():
    r = criterion_15_files_count(["a.java", "b.java"])
    assert r.status == "NO"
