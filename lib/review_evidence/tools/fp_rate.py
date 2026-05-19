"""FP rate measurement protocol — ADR-005a.

Tool che misura il false positive rate per ogni rule SIAE.
Definition FP: finding suppresso OR finding marcato `// nosemgrep reason=false-positive*`.

Cadence: weekly cron via .github/workflows/fp-rate-weekly.yml + snapshot 30gg.
CLI: `python -m lib.review_evidence.tools.fp_rate --rule siae.x --corpus <dir>`.
Thresholds (ADR-005a):
  fp_rate < 5%   → PROMOTE (WARNING→ERROR safe)
  fp_rate 5-10%  → RETRY (re-measure +30gg)
  fp_rate >= 10% → REWORK (rule rework required)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from lib.review_evidence.suppression import load_suppressions


FP_REASON_RE = re.compile(r"reason=false-positive", re.IGNORECASE)
NOSEMGREP_RE = re.compile(r"//\s*nosemgrep:\s*([\w.\-]+)")

PROMOTE_THRESHOLD = 0.05
REWORK_THRESHOLD = 0.10

_SOURCE_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".py", ".java", ".sql"}


@dataclass
class FpRateReport:
    rule_id: str
    n_findings: int
    n_suppressed: int
    n_nosemgrep_fp: int
    fp_rate: float
    measured_on: str
    corpus_root: str

    def to_dict(self) -> dict:
        return asdict(self)


def is_false_positive_marker(line: str) -> bool:
    """Detect nosemgrep comment with reason=false-positive*."""
    if "nosemgrep" not in line:
        return False
    return bool(FP_REASON_RE.search(line))


def count_nosemgrep_fp(scan_root: Path, rule_id: str) -> int:
    """Count `// nosemgrep: <rule_id> reason=false-positive*` occurrences."""
    count = 0
    if not scan_root.is_dir():
        return 0
    for path in scan_root.rglob("*"):
        if not path.is_file() or path.suffix not in _SOURCE_SUFFIXES:
            continue
        try:
            for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
                m = NOSEMGREP_RE.search(line)
                if m and m.group(1) == rule_id and FP_REASON_RE.search(line):
                    count += 1
        except (OSError, UnicodeDecodeError):
            continue
    return count


def count_suppressions_for_rule(suppressions_file: Path, rule_id: str) -> int:
    """Count entries in suppressions.yaml matching rule_id + reason=false-positive*."""
    suppressions = load_suppressions(suppressions_file)
    return sum(
        1 for s in suppressions
        if s.rule_id == rule_id and FP_REASON_RE.search(s.reason)
    )


def measure_fp_rate(
    rule_id: str,
    findings: list[dict],
    suppressions_file: Path,
    scan_root: Path,
) -> FpRateReport:
    """Compute FP rate per rule_id (rate = (suppressed + nosemgrep_fp) / n_findings)."""
    n_total = sum(1 for f in findings if f.get("check_id") == rule_id)
    n_suppressed = count_suppressions_for_rule(suppressions_file, rule_id)
    n_nosemgrep = count_nosemgrep_fp(scan_root, rule_id)

    fp_rate = (n_suppressed + n_nosemgrep) / n_total if n_total else 0.0

    return FpRateReport(
        rule_id=rule_id,
        n_findings=n_total,
        n_suppressed=n_suppressed,
        n_nosemgrep_fp=n_nosemgrep,
        fp_rate=fp_rate,
        measured_on=date.today().isoformat(),
        corpus_root=str(scan_root),
    )


def threshold_decision(fp_rate: float) -> str:
    """ADR-005a threshold mapping (<5% / 5-10% / >=10%)."""
    if fp_rate < PROMOTE_THRESHOLD:
        return "PROMOTE"
    if fp_rate < REWORK_THRESHOLD:
        return "RETRY"
    return "REWORK"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Measure false-positive rate for a SIAE Semgrep rule (ADR-005a)."
    )
    parser.add_argument("--rule", required=True, help="rule_id (es. siae.formula-injection.ts.csv-row-join-naive)")
    parser.add_argument("--corpus", required=True, type=Path, help="Corpus root dir")
    parser.add_argument(
        "--suppressions",
        type=Path,
        default=Path("rules/semgrep/siae/suppressions.yaml"),
    )
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    # Findings: piped JSON from semgrep --json (results array)
    findings: list[dict] = []
    if not sys.stdin.isatty():
        try:
            data = json.loads(sys.stdin.read() or "{}")
            findings = data.get("results", []) if isinstance(data, dict) else []
        except json.JSONDecodeError:
            findings = []

    report = measure_fp_rate(args.rule, findings, args.suppressions, args.corpus)
    out_path = args.output or Path(f"reports/fp_rate_{args.rule}_{date.today()}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report.to_dict(), indent=2))
    decision = threshold_decision(report.fp_rate)
    print(f"FP rate {report.fp_rate:.2%} → {decision}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
