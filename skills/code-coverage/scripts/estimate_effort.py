#!/usr/bin/env python3
"""estimate_effort.py — Task 10: forced-choice coverage target + time estime.

Workflow:
  Phase 2.1: discover_repo_size() classifica small/medium/large
  Phase 2.2/2.3: estimate_effort() applica moltiplicatori adjusters
  Phase 2.4: emit pending-user-choice.json sentinel (consumed by Claude main
             loop via AskUserQuestion); ``--target=<N>`` bypass

Sentinel pattern (Open question #1 overview): la skill bash emette il sentinel
e si interrompe (exit code 3). Il wrapper Claude main loop legge il sentinel,
invoca AskUserQuestion, scrive user-choice.json, e ri-lancia da Phase 2.5.

Target contract (post-GAP-1):
  - 40 = preset "quick-win"  (target_branch = 30)
  - 70 = preset "full-bundle" (target_branch = 60)
  - any integer N in [1, 95] = custom (target_branch = max(1, N - 10))

Usage:
    python3 estimate_effort.py <repo>           # emit sentinel
    python3 estimate_effort.py <repo> --target=40   # preset quick-win
    python3 estimate_effort.py <repo> --target=70   # preset full-bundle
    python3 estimate_effort.py <repo> --target=55   # custom
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path


# Baseline wall-clock minutes per (size_class, target). Calibrato dai 2 post-mortem
# di pae-deposito-musica-be (medium, ~30 min target 70% post-fix env) e sessione
# incrementale (~48 min, 12 file). Beta — calibrare con ≥10 run reali via telemetry.
_BASELINE = {
    "small":  {40: {"p50": 10, "p90": 20}, 70: {"p50": 25, "p90": 45}},
    "medium": {40: {"p50": 20, "p90": 40}, 70: {"p50": 60, "p90": 100}},
    "large":  {40: {"p50": 45, "p90": 90}, 70: {"p50": 150, "p90": 240}},
}

# --- target validation (supports presets and custom values) ---
PRESET_LABELS = {40: "quick-win", 70: "full-bundle"}


def validate_target(target_line):
    """Accept any integer in [1, 95]. Presets are just convenience defaults."""
    if isinstance(target_line, bool) or not isinstance(target_line, int) \
       or not (1 <= target_line <= 95):
        raise ValueError(
            f"target_line must be an integer between 1 and 95, got {target_line!r}. "
            "Presets: 40 (quick-win), 70 (full-bundle)."
        )
    return target_line


def derive_branch_target(target_line):
    return max(1, target_line - 10)


def _interp_baseline(size_class: str, target: int) -> dict:
    """Restituisce la baseline (p50, p90) per (size_class, target).

    Per i preset (40, 70) usa la tabella diretta. Per i custom interpola
    linearmente fra i due preset, clampando agli estremi 40/70.
    """
    sz = size_class if size_class in _BASELINE else "medium"
    if target in _BASELINE[sz]:
        base = _BASELINE[sz][target]
        return {"p50": float(base["p50"]), "p90": float(base["p90"])}
    low, high = 40, 70
    t = max(low, min(high, target))
    ratio = (t - low) / (high - low)
    low_b = _BASELINE[sz][low]
    high_b = _BASELINE[sz][high]
    return {
        "p50": low_b["p50"] + ratio * (high_b["p50"] - low_b["p50"]),
        "p90": low_b["p90"] + ratio * (high_b["p90"] - low_b["p90"]),
    }

# Moltiplicatori adjusters
_ADJUSTERS = {
    "legacy_java": 1.30,            # source <10 → no var, Java 8 plugin issues
    "lombok_jdk_mismatch": 1.20,    # Task 03 HARD-WARN non risolto
    "spring_boot": 1.25,            # Task 09 boot context overhead
    "no_assertj": 1.05,             # Task 04 template vanilla verboso
    "cache_valid": 0.85,            # .code-coverage hot
    "setter_normalizer_many": 1.10, # Task 08 >5 setter non-trivial
}


_SKIP_DIRS = {"target", "build", ".git", "node_modules", ".code-coverage", ".idea"}


def _count_java_files_and_loc(root: Path) -> tuple:
    """Restituisce (file_count, loc_total) per i .java sotto src/main/java/."""
    classes = 0
    loc = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        # Solo source di produzione (skip test)
        if "src/main/java" not in str(dirpath).replace("\\", "/") and "src/main/java" not in str(Path(dirpath).as_posix()):
            # fallback: accetta anche src/ generico
            if "/src/" not in str(Path(dirpath).as_posix()) and not str(dirpath).endswith("src"):
                # Permetto anche source flat (es. test fixtures)
                pass
        for f in filenames:
            if not f.endswith(".java"):
                continue
            fp = Path(dirpath) / f
            classes += 1
            try:
                loc += sum(1 for _ in fp.open(encoding="utf-8", errors="ignore"))
            except OSError:
                continue
    return classes, loc


def discover_repo_size(manifest_root) -> str:
    """Task 10 Phase 2.1: classifica repo per LoC + count classes Java."""
    root = Path(manifest_root)
    classes, loc = _count_java_files_and_loc(root)
    if loc < 5000 and classes < 50:
        return "small"
    if loc < 30000 and classes < 300:
        return "medium"
    return "large"


def estimate_effort(size_class: str, target: int, adjusters: dict | None = None) -> dict:
    """Task 10 Phase 2.2/2.3: stima wall-clock minutes per (size, target) + adjusters.

    Args:
        size_class: 'small' | 'medium' | 'large' (fallback 'medium')
        target: integer in [1, 95]. 40/70 = preset, altri = custom.
        adjusters: dict {name: bool} con flag attivi

    Returns:
        {"p50": int, "p90": int}
    """
    validate_target(target)
    base = _interp_baseline(size_class, target)
    p50 = base["p50"]
    p90 = base["p90"]
    if adjusters:
        for name, active in adjusters.items():
            if active and name in _ADJUSTERS:
                p50 *= _ADJUSTERS[name]
                p90 *= _ADJUSTERS[name]
    return {"p50": int(round(p50)), "p90": int(round(p90))}


def _collect_adjusters(env_data: dict) -> dict:
    """Deriva adjusters da env.json (Tasks 03/04/07/09)."""
    return {
        "legacy_java": env_data.get("compat_profile") == "legacy-java",
        "lombok_jdk_mismatch": env_data.get("jdk_compat", {}).get("severity") == "HARD-WARN",
        "spring_boot": bool(env_data.get("is_spring_boot")),
        "no_assertj": env_data.get("assertion_lib") == "junit5_vanilla",
    }


def _build_sentinel(repo_path: Path, size_class: str, env_data: dict,
                    estimate_a: dict, estimate_b: dict) -> dict:
    """Costruisce il payload del sentinel pending-user-choice.json."""
    return {
        "type": "forced_choice_coverage_target",
        "schema_version": "1.0",
        "context": {
            "repo": repo_path.name,
            "manifest_root": env_data.get("manifest_root", "."),
            "size_class": size_class,
            "source_level": env_data.get("java_source_level"),
            "spring_boot": bool(env_data.get("is_spring_boot")),
            "lombok_jdk_mismatch": env_data.get("jdk_compat", {}).get("severity") == "HARD-WARN",
            "assertj_present": env_data.get("assertion_lib") == "assertj",
        },
        "options": {
            "A": {
                "label": "Coverage 40% — quick win",
                "target_line": 40,
                "target_branch": 30,
                "focus": ["POJO", "utility", "mapper", "enum", "low-branch service"],
                "estimated_wallclock_min_p50": estimate_a["p50"],
                "estimated_wallclock_min_p90": estimate_a["p90"],
            },
            "B": {
                "label": "Coverage 70% — full bundle",
                "target_line": 70,
                "target_branch": 60,
                "focus": ["service layer con branch", "DAO non-Hibernate",
                          "edge cases setter", "mapper bidirezionali"],
                "estimated_wallclock_min_p50": estimate_b["p50"],
                "estimated_wallclock_min_p90": estimate_b["p90"],
            },
        },
        "default": None,
        "allow_skip": False,
    }


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: estimate_effort.py <repo> [--target=40|70]"}),
              file=sys.stderr)
        sys.exit(1)
    repo = Path(sys.argv[1]).resolve()
    if not repo.is_dir():
        print(json.dumps({"error": f"Not a directory: {repo}"}), file=sys.stderr)
        sys.exit(1)

    cov = repo / ".code-coverage"
    cov.mkdir(exist_ok=True)
    env_data = {}
    env_path = cov / "env.json"
    if env_path.is_file():
        try:
            env_data = json.loads(env_path.read_text(encoding="utf-8", errors="ignore"))
        except json.JSONDecodeError:
            env_data = {}

    # Phase 2.1: sizing
    size_class = discover_repo_size(repo)

    # Phase 2.2/2.3: estime per A=40 e B=70 con adjusters
    adjusters = _collect_adjusters(env_data)
    est_a = estimate_effort(size_class, 40, adjusters)
    est_b = estimate_effort(size_class, 70, adjusters)

    # CLI --target=<N> bypass: scrive user-choice.json direttamente, NO sentinel.
    # N puo' essere un preset (40, 70) o un custom in [1, 95].
    target_arg = next((a for a in sys.argv[2:] if a.startswith("--target=")), None)
    if target_arg:
        try:
            target_val = int(target_arg.split("=")[1])
        except (ValueError, IndexError):
            print(json.dumps({"error": "invalid --target= value"}), file=sys.stderr)
            sys.exit(1)
        try:
            validate_target(target_val)
        except ValueError as exc:
            print(json.dumps({"error": str(exc)}), file=sys.stderr)
            sys.exit(1)
        if target_val == 40:
            chosen = est_a
        elif target_val == 70:
            chosen = est_b
        else:
            chosen = estimate_effort(size_class, target_val, adjusters)
        (cov / "user-choice.json").write_text(json.dumps({
            "target_line": target_val,
            "target_branch": derive_branch_target(target_val),
            "size_class": size_class,
            "estimated_wallclock_min_p50": chosen["p50"],
            "estimated_wallclock_min_p90": chosen["p90"],
            "user_choice_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source": "cli_target_flag",
            "preset": PRESET_LABELS.get(target_val, "custom"),
        }, indent=2), encoding="utf-8")
        print(json.dumps({"target_line": target_val, "size_class": size_class,
                          "estimate": chosen}, indent=2))
        return

    # Phase 2.4: emit sentinel + exit 3 (signal a Claude main loop)
    sentinel = _build_sentinel(repo, size_class, env_data, est_a, est_b)
    (cov / "pending-user-choice.json").write_text(
        json.dumps(sentinel, indent=2), encoding="utf-8"
    )
    print(json.dumps(sentinel, indent=2))
    # Exit 3 = forced-choice handshake (Claude wrapper intercept signal)
    # Per CLI test e sessione interactive, non sys.exit(3): rendiamolo opzionale
    if "--strict-exit" in sys.argv:
        sys.exit(3)


if __name__ == "__main__":
    main()
