"""Chaos test suite v2 — failure injection sui 40 edge case mappati.

Coverage map (8 CRITICAL + 8 HIGH + 2 LOW = ~18 contract tests):

CRITICAL (design doc v2):
- A1   cache key SHA-based, no TTL
- B1+B7 coverage lines absolute drop penalty
- B3   .devforge-scores.yml config change detected in PR
- D3+D5 S3-authoritative store (NON unit-testabile — Task 16 Terraform)
- E1   budget snapshot immutable post PR_OPEN
- E5   per-dim hard floor separate from overall floor
- F1   hard floor NON-OVERRIDABLE doc grep
- C5   combined lines_drop + pct rise → penalty wins (iter1 fix)

HIGH:
- A2   force-push → sha_exists_in_repo False
- A6   first PR / synthetic baseline → AUTO_APPROVE
- C1   bot PR → is_bot_pr + discipline=100
- C4   empty PR (all dim=100) → AUTO_APPROVE
- D2   no AWS creds → local fallback
- D6   severely_degraded with <2 dims
- E4   weights sum != 1.0 ± 0.01 → ConfigValidationError
- F4   reviewer debounce contract (Step 0.6 reference)

LOW:
- C6   partial score marker (4/5 dim available, not degraded)
- D4   UTC TZ enforcement

Contract-based: asserzioni atomiche, NO snapshot fragile.
"""
from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


# ─── BASELINE STALENESS (A1, A2, A6) ────────────────────────────────


def test_A1_cache_key_sha_no_ttl():
    """A1 CRITICAL: cache key is SHA-based and module has no TTL semantics."""
    from lib.review_evidence.baseline_cache import baseline_key
    import lib.review_evidence.baseline_cache as bc

    key = baseline_key("itsiae/foo", "abcd1234")
    # Filename embeds the immutable SHA, never a timestamp / TTL marker.
    assert key.endswith("abcd1234.json")
    assert key == "itsiae/foo/abcd1234.json"

    src = Path(bc.__file__).read_text()
    # Explicit "no TTL" assertion in the module docstring (contract).
    assert "no TTL" in src or "NO TTL" in src


def test_A2_force_push_detected(tmp_path):
    """A2 HIGH: bogus SHA → sha_exists_in_repo False → recompute trigger."""
    from lib.review_evidence.baseline_cache import sha_exists_in_repo

    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "x@x"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "x"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"], cwd=tmp_path, check=True
    )
    (tmp_path / "f.txt").write_text("x")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True
    )

    # A SHA that cannot possibly be reachable (all zeros) → False.
    assert sha_exists_in_repo(tmp_path, "0" * 40) is False


def test_A6_baseline_synthetic_first_pr():
    """A6 HIGH: first PR (no baseline) + floor pass → AUTO_APPROVE."""
    from lib.review_evidence.config import DevForgeScoresConfig
    from lib.review_evidence.regression import compute_regression_verdict
    from lib.review_evidence.schema import ScoreCard

    cfg = DevForgeScoresConfig()
    current = ScoreCard(
        security=80,
        quality=70,
        coverage=70,
        spec_compliance=80,
        discipline=70,
        overall=75,
        weights_used={},
        missing_components=[],
    )
    rv = compute_regression_verdict(
        current, baseline=None, cfg=cfg, baseline_synthetic=True
    )
    assert rv.decision == "AUTO_APPROVE"
    assert rv.hard_floor_breaches == []


# ─── GAMING (B1+B7, B3, C5) ──────────────────────────────────────────


def test_B1_B7_coverage_lines_drop_penalty():
    """B1+B7 CRITICAL: dev cancella test → lines drop → penalty kicks in."""
    from lib.review_evidence.scoring import CoverageInput, score_coverage

    cov = CoverageInput(
        line_pct=80,
        branch_pct=80,
        current_lines_covered=40,
        baseline_lines_covered=80,
    )
    score = score_coverage(cov, baseline_synthetic=False)
    # lines_drop=40, penalty = min(20, 40*0.5)=20 → 80 - 20 = 60.
    assert score == 60.0


def test_B3_config_change_in_pr_detected(tmp_path):
    """B3 CRITICAL: .devforge-scores.yml modificato in PR → True."""
    from lib.review_evidence.config import detect_config_change_in_pr

    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "x@x"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "x"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"], cwd=tmp_path, check=True
    )
    (tmp_path / ".devforge-scores.yml").write_text(
        "schema_version: 1\nweights:\n  security: 0.30\n"
    )
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True
    )
    (tmp_path / ".devforge-scores.yml").write_text(
        "schema_version: 1\nweights:\n  security: 0.99\n"
    )
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "tamper"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    assert detect_config_change_in_pr(tmp_path, "HEAD~1", "HEAD") is True


def test_C5_combined_lines_and_pct_signals():
    """C5 CRITICAL (iter1 fix): lines drop + pct rise → penalty wins.

    Scenario hostile: refactor scuro che peggiora qualita' E nasconde test rimossi.
    score_coverage applica penalty su lines absolute drop ANCHE se pct nominale sale.

    Contract:
        - line_pct = 89 (sale rispetto a baseline 80%)
        - current_lines_covered = 40 (scende rispetto a baseline 80)
        - lines_drop = 40, penalty = min(20, 40*0.5) = 20
        - base = min(89, 89) = 89
        - score = max(0, 89 - 20) = 69.0

    Se l'algoritmo guardasse solo line_pct, il punteggio sarebbe 89 (gaming).
    L'asserzione = 69.0 protegge contro questo bypass.
    """
    from lib.review_evidence.scoring import CoverageInput, score_coverage

    cov = CoverageInput(
        line_pct=89.0,
        branch_pct=89.0,
        current_lines_covered=40,
        baseline_lines_covered=80,
    )
    score = score_coverage(cov, baseline_synthetic=False)
    assert score == 69.0, f"C5 fail: expected 69.0, got {score}"


# ─── SPECIAL PR (C1, C4, C6) ─────────────────────────────────────────


def test_C1_bot_pr_skip_discipline():
    """C1 HIGH: dependabot[bot] → is_bot_pr=True, discipline=100."""
    from lib.review_evidence.checks.skill_adoption import detect_skill_adoption
    from lib.review_evidence.scoring import SkillAdoptionInput, score_discipline

    r = detect_skill_adoption(
        repo_root=Path("/tmp"),
        pr_open_time=datetime.now(timezone.utc),
        pr_labels=[],
        pr_user="dependabot[bot]",
    )
    assert r.is_bot_pr is True
    sa = SkillAdoptionInput(
        is_bot_pr=True,
        brainstorming_done=False,
        tdd_cycle_seen=False,
        verification_run=False,
    )
    assert score_discipline(sa) == 100.0


def test_C4_empty_pr_auto_pass():
    """C4 HIGH: PR vuota (solo docs, no regression) → AUTO_APPROVE."""
    from lib.review_evidence.config import DevForgeScoresConfig
    from lib.review_evidence.regression import compute_regression_verdict
    from lib.review_evidence.schema import ScoreCard

    cfg = DevForgeScoresConfig()
    current = ScoreCard(
        security=100,
        quality=100,
        coverage=100,
        spec_compliance=100,
        discipline=100,
        overall=100,
        weights_used={},
        missing_components=[],
    )
    baseline = ScoreCard(
        security=100,
        quality=100,
        coverage=100,
        spec_compliance=100,
        discipline=100,
        overall=100,
        weights_used={},
        missing_components=[],
    )
    rv = compute_regression_verdict(current, baseline, cfg, baseline_synthetic=False)
    assert rv.decision == "AUTO_APPROVE"


def test_C6_partial_score_marker():
    """C6 LOW: multi-stack PR with 1 missing dim → reweighted, not degraded."""
    from lib.review_evidence.scoring import compute_overall

    scores = {
        "security": 80,
        "quality": 70,
        "coverage": None,
        "spec_compliance": 80,
        "discipline": 90,
    }
    weights = {
        "security": 0.30,
        "quality": 0.20,
        "coverage": 0.20,
        "spec_compliance": 0.15,
        "discipline": 0.15,
    }
    overall, degraded = compute_overall(scores, weights)
    assert overall > 0  # reweighted across 4 dims
    assert degraded is False  # ≥2 dim available


# ─── INFRA & CACHE (D2, D4, D6) ──────────────────────────────────────


def test_D2_no_aws_creds_local_fallback(tmp_path, monkeypatch):
    """D2 HIGH: dev senza AWS → fetch_baseline cade su local fallback."""
    from botocore.exceptions import NoCredentialsError

    from lib.review_evidence.baseline_cache import fetch_baseline

    # Redirect local fallback dir into the sandbox so we never touch ~/.claude.
    monkeypatch.setenv("DEVFORGE_BASELINE_LOCAL_DIR", str(tmp_path / "baseline-local"))

    class _FakeS3:
        def get_object(self, **_kw):
            raise NoCredentialsError()

    with patch(
        "lib.review_evidence.baseline_cache.boto3.client", return_value=_FakeS3()
    ):
        result = fetch_baseline("itsiae/foo", "abc")

    # No local file → None (cache miss), but NO exception leaked.
    assert result is None


def test_D4_utc_only_no_local_tz():
    """D4 LOW: timestamp UTC sempre, no local TZ leak."""
    now = datetime.now(timezone.utc)
    assert now.tzinfo == timezone.utc
    # UTC offset must be zero — guards against accidental aware-but-local TZ.
    assert now.utcoffset().total_seconds() == 0


def test_D6_severely_degraded_one_dim():
    """D6 HIGH: only 1 dim available → severely_degraded=True."""
    from lib.review_evidence.scoring import compute_overall

    scores = {
        "security": 80,
        "quality": None,
        "coverage": None,
        "spec_compliance": None,
        "discipline": None,
    }
    weights = {
        "security": 0.30,
        "quality": 0.20,
        "coverage": 0.20,
        "spec_compliance": 0.15,
        "discipline": 0.15,
    }
    overall, degraded = compute_overall(scores, weights)
    assert degraded is True
    assert overall == 80.0  # falls back to the single available dim


# ─── MATH & THRESHOLD (E1, E4, E5) ───────────────────────────────────


def test_E1_budget_snapshot_immutable():
    """E1 CRITICAL: admin change post-PR_OPEN non bleed nello snapshot."""
    from lib.review_evidence.config import DevForgeScoresConfig
    from lib.review_evidence.regression import snapshot_budget_at_pr_open

    cfg = DevForgeScoresConfig()
    snap = snapshot_budget_at_pr_open(cfg, pr_open_iso="2026-05-13T10:00:00Z")

    # Tamper live config post-snapshot.
    cfg.hard_block_budget["security"] = -100
    cfg.hard_floors["security"] = 999
    cfg.weights["security"] = 0.99

    # Snapshot must be untouched (deepcopy contract).
    assert snap["hard_block_budget"]["security"] == -2
    assert snap["hard_floors"]["security"] == 60
    assert snap["weights"]["security"] == 0.30
    assert snap["pr_open_iso"] == "2026-05-13T10:00:00Z"


def test_E4_weights_sum_validation_fails(tmp_path):
    """E4 HIGH: sum(weights) ≠ 1.0 ± 0.01 → ConfigValidationError."""
    from lib.review_evidence.config import ConfigValidationError, load_scores_config

    (tmp_path / ".devforge-scores.yml").write_text(
        "schema_version: 1\n"
        "weights:\n"
        "  security: 0.10\n"
        "  quality: 0.10\n"
        "  coverage: 0.10\n"
        "  spec_compliance: 0.10\n"
        "  discipline: 0.10\n"
    )
    with pytest.raises(ConfigValidationError):
        load_scores_config(tmp_path)


def test_E5_min_dim_hard_floor_separate():
    """E5 CRITICAL: any dim < min_dim (40) = block, even if overall passes."""
    from lib.review_evidence.config import DevForgeScoresConfig
    from lib.review_evidence.regression import (
        compute_regression_verdict,
        is_hard_floor_breached,
    )
    from lib.review_evidence.schema import ScoreCard

    cfg = DevForgeScoresConfig()
    sc = ScoreCard(
        security=80,
        quality=35,  # < min_dim=40 → trigger
        coverage=70,
        spec_compliance=80,
        discipline=80,
        overall=70,  # >> overall floor 55 — but per-dim floor still bites.
        weights_used={},
        missing_components=[],
    )
    assert is_hard_floor_breached(sc, cfg) is True

    # Compute path emits BLOCK_HARD_FLOOR (non-overridable).
    rv = compute_regression_verdict(sc, baseline=None, cfg=cfg, baseline_synthetic=True)
    assert rv.decision == "BLOCK_HARD_FLOOR"
    assert any("quality" in b for b in rv.hard_floor_breaches)


# ─── REVIEWER (F1, F4) ───────────────────────────────────────────────


def test_F1_hard_floor_non_overridable_doc():
    """F1 CRITICAL: agents/code-reviewer.md documenta hard floor non-overridable."""
    content = (REPO_ROOT / "agents" / "code-reviewer.md").read_text()
    upper = content.upper()
    assert "NON-OVERRIDABLE" in upper, "Reviewer agent must state NON-OVERRIDABLE"
    assert "BREAK-GLASS" in upper, "Reviewer agent must document the BREAK-GLASS path"


def test_F4_reviewer_debounce_contract():
    """F4 HIGH: reviewer agent referenzia Step 0.6 (entry-point debounce)."""
    content = (REPO_ROOT / "agents" / "code-reviewer.md").read_text()
    # Contract-level: the reviewer prompt anchors a Step 0.6 section that
    # owns the gatekeeper logic + debounce semantics.
    assert "Step 0.6" in content
