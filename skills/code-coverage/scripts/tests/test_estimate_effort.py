"""Test Task 10 — forced-choice-coverage-target.

Tre funzioni testate qui:
1. discover_repo_size(manifest_root) → 'small' | 'medium' | 'large'
2. estimate_effort(size_class, target, adjusters) → {p50, p90} minutes
3. CLI estimate_effort.py + sentinel emission

TDD: scritti PRIMA dell'implementazione.
"""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPT_DIR))


def _java_files(repo: Path, count: int = 10, loc_per: int = 100):
    """Crea {count} file Java sotto src/main/java/ con {loc_per} LoC ciascuno."""
    src = repo / "src" / "main" / "java" / "x"
    src.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        body = "\n".join([f"int v{j} = {j};" for j in range(loc_per)])
        (src / f"Cls{i}.java").write_text(f"package x;\nclass Cls{i} {{\n{body}\n}}\n")


# ---------- discover_repo_size ----------

def test_size_small_under_5k_loc(tmp_path):
    from estimate_effort import discover_repo_size
    repo = tmp_path / "repo"
    repo.mkdir()
    _java_files(repo, count=5, loc_per=10)  # ~50 LoC, 5 classes
    assert discover_repo_size(repo) == "small"


def test_size_medium(tmp_path):
    from estimate_effort import discover_repo_size
    repo = tmp_path / "repo"
    repo.mkdir()
    _java_files(repo, count=80, loc_per=200)  # ~16k LoC, 80 classes
    assert discover_repo_size(repo) == "medium"


def test_size_large(tmp_path):
    from estimate_effort import discover_repo_size
    repo = tmp_path / "repo"
    repo.mkdir()
    _java_files(repo, count=400, loc_per=100)  # 40k LoC, 400 classes
    assert discover_repo_size(repo) == "large"


# ---------- estimate_effort ----------

def test_estimate_medium_target_40_baseline():
    from estimate_effort import estimate_effort
    result = estimate_effort("medium", 40)
    assert result["p50"] == 20
    assert result["p90"] == 40


def test_estimate_medium_target_70_baseline():
    from estimate_effort import estimate_effort
    result = estimate_effort("medium", 70)
    assert result["p50"] == 60
    assert result["p90"] == 100


def test_estimate_adjusters_legacy_java():
    """Adjuster: source <10 (legacy) ×1.30."""
    from estimate_effort import estimate_effort
    base = estimate_effort("medium", 40)
    adjusted = estimate_effort("medium", 40, adjusters={"legacy_java": True})
    assert adjusted["p50"] == int(base["p50"] * 1.30)


def test_estimate_composite_pae_deposito_musica():
    """Esempio composito: medium target 70 + legacy + lombok_mismatch + no_assertj."""
    from estimate_effort import estimate_effort
    result = estimate_effort("medium", 70, adjusters={
        "legacy_java": True, "lombok_jdk_mismatch": True, "no_assertj": True,
    })
    # 60 × 1.30 × 1.20 × 1.05 ≈ 98
    assert result["p50"] in range(95, 105)


def test_estimate_unknown_size_default_medium():
    """size_class sconosciuto → fallback medium."""
    from estimate_effort import estimate_effort
    result = estimate_effort("unknown", 40)
    assert "p50" in result and "p90" in result


def test_estimate_invalid_target_below_range_raises():
    """target < 1 → ValueError (new contract: integer in [1, 95])."""
    from estimate_effort import estimate_effort
    try:
        estimate_effort("medium", 0)
        raise AssertionError("expected ValueError for target=0")
    except ValueError:
        pass


def test_estimate_invalid_target_above_range_raises():
    """target > 95 → ValueError (new contract: integer in [1, 95])."""
    from estimate_effort import estimate_effort
    try:
        estimate_effort("medium", 96)
        raise AssertionError("expected ValueError for target=96")
    except ValueError:
        pass


# ---------- validate_target + derive_branch_target (GAP-1) ----------

def test_validate_target_accepts_presets():
    from estimate_effort import validate_target
    assert validate_target(40) == 40
    assert validate_target(70) == 70


def test_validate_target_accepts_custom_in_range():
    """Qualsiasi intero 1..95 e' valido (no whitelist)."""
    from estimate_effort import validate_target
    assert validate_target(1) == 1
    assert validate_target(55) == 55
    assert validate_target(95) == 95


def test_validate_target_rejects_out_of_range():
    from estimate_effort import validate_target
    for bad in (0, -1, 96, 100, 1000):
        try:
            validate_target(bad)
            raise AssertionError(f"expected ValueError for {bad}")
        except ValueError:
            pass


def test_validate_target_rejects_non_integer():
    from estimate_effort import validate_target
    for bad in (40.5, "40", None, [40]):
        try:
            validate_target(bad)
            raise AssertionError(f"expected ValueError for {bad!r}")
        except ValueError:
            pass


def test_derive_branch_target_preset_quick_win():
    from estimate_effort import derive_branch_target
    assert derive_branch_target(40) == 30


def test_derive_branch_target_preset_full_bundle():
    from estimate_effort import derive_branch_target
    assert derive_branch_target(70) == 60


def test_derive_branch_target_custom():
    from estimate_effort import derive_branch_target
    assert derive_branch_target(55) == 45
    assert derive_branch_target(80) == 70


def test_derive_branch_target_floor_at_one():
    """target_line <= 10 deve produrre target_branch >= 1 (floor a 1)."""
    from estimate_effort import derive_branch_target
    assert derive_branch_target(1) == 1
    assert derive_branch_target(5) == 1
    assert derive_branch_target(10) == 1


def test_estimate_custom_target_no_longer_raises():
    """target=55 (custom) deve essere accettato e produrre stime."""
    from estimate_effort import estimate_effort
    result = estimate_effort("medium", 55)
    assert "p50" in result and "p90" in result
    assert result["p50"] > 0 and result["p90"] > 0


# ---------- CLI sentinel emission ----------

def test_cli_emits_sentinel_pending_choice(tmp_path):
    """python3 estimate_effort.py <repo> emette pending-user-choice.json."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _java_files(repo, count=10, loc_per=50)
    cov = repo / ".code-coverage"
    cov.mkdir()
    # Simulate env.json minimal
    (cov / "env.json").write_text(json.dumps({
        "required_framework": "junit5",
        "compat_profile": "legacy-java",
        "is_spring_boot": True,
        "assertion_lib": "junit5_vanilla",
    }))
    (cov / "stack.json").write_text(json.dumps({"manifest_root": "."}))

    result = subprocess.run(
        ["python3", str(SCRIPT_DIR / "estimate_effort.py"), str(repo)],
        capture_output=True, text=True, check=True,
    )
    sentinel_path = cov / "pending-user-choice.json"
    assert sentinel_path.is_file(), "sentinel pending-user-choice.json not emitted"
    sentinel = json.loads(sentinel_path.read_text())
    assert sentinel["type"] == "forced_choice_coverage_target"
    assert "A" in sentinel["options"]
    assert "B" in sentinel["options"]
    assert sentinel["options"]["A"]["target_line"] == 40
    assert sentinel["options"]["B"]["target_line"] == 70


def test_cli_target_flag_bypasses_sentinel(tmp_path):
    """--target=40 CLI bypass: NO sentinel, scrive user-choice.json direttamente."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _java_files(repo, count=5, loc_per=10)
    cov = repo / ".code-coverage"
    cov.mkdir()
    (cov / "env.json").write_text(json.dumps({"required_framework": "junit5"}))
    (cov / "stack.json").write_text(json.dumps({"manifest_root": "."}))

    result = subprocess.run(
        ["python3", str(SCRIPT_DIR / "estimate_effort.py"), str(repo), "--target=40"],
        capture_output=True, text=True, check=True,
    )
    sentinel_path = cov / "pending-user-choice.json"
    choice_path = cov / "user-choice.json"
    assert not sentinel_path.is_file(), "sentinel should NOT exist when --target passed"
    assert choice_path.is_file(), "user-choice.json should be written by --target"
    choice = json.loads(choice_path.read_text())
    assert choice["target_line"] == 40


# ---------- _interp_baseline extrapolation (MAJOR fix from code review) ----------

def test_interp_baseline_midpoint_between_presets():
    """target=55 = midpoint tra 40 (p50=20) e 70 (p50=60) per medium → p50=40."""
    from estimate_effort import _interp_baseline
    base = _interp_baseline("medium", 55)
    assert base["p50"] == 40.0, f"expected 40.0, got {base['p50']}"
    assert base["p90"] == 70.0, f"expected 70.0, got {base['p90']}"


def test_interp_baseline_extrapolates_below_40_no_clamp():
    """target=10 deve produrre stima INFERIORE a target=40 (non clampata)."""
    from estimate_effort import _interp_baseline
    base_10 = _interp_baseline("medium", 10)
    base_40 = _interp_baseline("medium", 40)
    assert base_10["p50"] < base_40["p50"], \
        f"target=10 ({base_10['p50']}) deve essere < target=40 ({base_40['p50']})"
    assert base_10["p50"] >= 1.0, "floor minimo p50 >= 1.0"


def test_interp_baseline_extrapolates_above_70_no_clamp():
    """target=90 deve produrre stima SUPERIORE a target=70 (non clampata)."""
    from estimate_effort import _interp_baseline
    base_70 = _interp_baseline("medium", 70)
    base_90 = _interp_baseline("medium", 90)
    assert base_90["p50"] > base_70["p50"], \
        f"target=90 ({base_90['p50']}) deve essere > target=70 ({base_70['p50']})"


def test_estimate_effort_emits_warn_for_extrapolation(capsys):
    """estimate_effort con target fuori [40,70] deve emettere WARN su stderr."""
    from estimate_effort import estimate_effort
    estimate_effort("medium", 20)
    captured = capsys.readouterr()
    assert "WARN" in captured.err or "warn" in captured.err.lower(), \
        f"expected WARN on stderr for extrapolated target, got: {captured.err!r}"


def test_estimate_effort_no_warn_for_presets(capsys):
    """target=40 o 70 non deve emettere WARN."""
    from estimate_effort import estimate_effort
    estimate_effort("medium", 40)
    estimate_effort("medium", 70)
    captured = capsys.readouterr()
    assert "WARN" not in captured.err, \
        f"unexpected WARN on stderr for preset: {captured.err!r}"


def test_validate_target_rejects_bool():
    """bool e' subclass di int in Python — deve essere esplicitamente respinto."""
    from estimate_effort import validate_target
    for bad in (True, False):
        try:
            validate_target(bad)
            raise AssertionError(f"expected ValueError for {bad!r}")
        except ValueError:
            pass
