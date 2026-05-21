#!/usr/bin/env python3
"""run_kappa_eval.py — Cohen's κ evaluator for the golden set.

Computes inter-rater agreement between the **expected** findings (the
ground truth annotated in `eval/golden_set/fixtures/*/expected_finding.json`)
and the **reported** findings (the skill's output for the same fixtures).

Modes
-----
1. **--reports-dir <DIR>**: read one `<fixture_name>.json` per fixture
   from <DIR>, each file a single Finding-shaped JSON object (the same
   schema as `expected_finding.json`).
2. **--negative-baseline**: bypass the skill and feed the
   `negative_example.json` of each fixture as the "reported" finding.
   Used in CI to verify κ correctly detects bad classifications.
3. **default (no flag)**: re-feed the `expected_finding.json` as the
   reported finding. Used to verify κ machinery is wired up (must
   produce κ_severity = 1.0, κ_category = 1.0).

Metrics
-------
- **κ_severity**: Cohen's κ on the 4-class label {SEV-1, SEV-2, SEV-3, SEV-4}.
- **κ_category**: Cohen's κ on the 10-class category label.
- **per-fixture agreement**: a boolean (severity_match AND category_match).

Thresholds (per FIX-9 spec)
---------------------------
- κ_severity ≥ 0.70 → pass
- κ_category ≥ 0.60 → pass

Exit codes
----------
0  both thresholds passed.
1  at least one threshold below.
2  I/O or schema error.

Python 3.9+ standard library only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SEVERITIES = ["SEV-1", "SEV-2", "SEV-3", "SEV-4"]
CATEGORIES = [
    "auth-bypass", "data-race", "toctou", "webhook-replay",
    "cache-staleness", "cursor-drift", "dst-skip",
    "input-validation", "business-logic", "other",
]


def cohen_kappa(labels1: list[str], labels2: list[str], classes: list[str]) -> float:
    """Cohen's κ on two equal-length sequences of categorical labels.

    Returns 1.0 on perfect agreement, 0.0 on chance-level agreement,
    negative on worse-than-chance. Implementation per Cohen (1960).
    """
    if not labels1:
        return float("nan")
    if len(labels1) != len(labels2):
        raise ValueError("label sequences must be equal length")

    n = len(labels1)
    # Observed agreement
    po = sum(1 for a, b in zip(labels1, labels2) if a == b) / n

    # Marginal probabilities
    pe = 0.0
    for c in classes:
        p1 = labels1.count(c) / n
        p2 = labels2.count(c) / n
        pe += p1 * p2

    if pe >= 1.0:
        # All annotators agree on every label being the same class.
        # κ is undefined; convention: 1.0 if also po == 1.0, 0.0 otherwise.
        return 1.0 if po >= 1.0 else 0.0
    return (po - pe) / (1.0 - pe)


def load_finding(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_fixtures(fixtures_dir: Path) -> list[Path]:
    return sorted(p for p in fixtures_dir.iterdir() if p.is_dir())


def get_reported_for(
    fixture_dir: Path,
    reports_dir: Path | None,
    negative_baseline: bool,
) -> dict[str, Any]:
    if reports_dir is not None:
        rpath = reports_dir / f"{fixture_dir.name}.json"
        if not rpath.is_file():
            raise FileNotFoundError(f"no report for fixture {fixture_dir.name} at {rpath}")
        return load_finding(rpath)
    if negative_baseline:
        npath = fixture_dir / "negative_example.json"
        neg = load_finding(npath)
        return neg["wrong_finding"]
    # Default: re-feed the expected finding (sanity / wiring test).
    return load_finding(fixture_dir / "expected_finding.json")


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--fixtures-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "golden_set" / "fixtures",
        help="Directory containing fixture_NNN_<name>/ subdirs.",
    )
    p.add_argument(
        "--reports-dir",
        type=Path,
        default=None,
        help="Optional directory with one <fixture_name>.json reported finding per fixture.",
    )
    p.add_argument(
        "--negative-baseline",
        action="store_true",
        help="Feed each fixture's negative_example.wrong_finding as the reported finding (κ should drop).",
    )
    p.add_argument("--kappa-severity-min", type=float, default=0.70)
    p.add_argument("--kappa-category-min", type=float, default=0.60)
    args = p.parse_args(argv)

    fixtures = collect_fixtures(args.fixtures_dir)
    if not fixtures:
        sys.stderr.write(f"[run_kappa_eval] no fixtures under {args.fixtures_dir}\n")
        return 2

    expected_sev: list[str] = []
    reported_sev: list[str] = []
    expected_cat: list[str] = []
    reported_cat: list[str] = []
    per_fixture: list[dict[str, Any]] = []

    for fx in fixtures:
        try:
            exp = load_finding(fx / "expected_finding.json")
            rep = get_reported_for(fx, args.reports_dir, args.negative_baseline)
        except (OSError, json.JSONDecodeError, FileNotFoundError, KeyError) as e:
            sys.stderr.write(f"[run_kappa_eval] cannot load {fx.name}: {e}\n")
            return 2

        e_sev = exp["severity"]
        r_sev = rep["severity"]
        e_cat = exp["category"]
        r_cat = rep["category"]

        expected_sev.append(e_sev)
        reported_sev.append(r_sev)
        expected_cat.append(e_cat)
        reported_cat.append(r_cat)

        per_fixture.append({
            "fixture": fx.name,
            "expected_severity": e_sev,
            "reported_severity": r_sev,
            "severity_match": e_sev == r_sev,
            "expected_category": e_cat,
            "reported_category": r_cat,
            "category_match": e_cat == r_cat,
        })

    k_sev = cohen_kappa(expected_sev, reported_sev, SEVERITIES)
    k_cat = cohen_kappa(expected_cat, reported_cat, CATEGORIES)

    print(json.dumps({
        "fixtures_evaluated": len(fixtures),
        "kappa_severity": round(k_sev, 4),
        "kappa_category": round(k_cat, 4),
        "thresholds": {
            "severity_min": args.kappa_severity_min,
            "category_min": args.kappa_category_min,
        },
        "per_fixture": per_fixture,
    }, indent=2))

    if k_sev < args.kappa_severity_min or k_cat < args.kappa_category_min:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
