"""Stub orchestrator — replaced by Task 04.

Emits a minimal valid evidence file so Task 03 integration tests can pass.
Task 04 will replace this with the real collector (coverage/lint/spec-drift).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sha", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--dirty", default="0")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    evidence = {
        "schema_version": "1.0",
        "sha": args.sha,
        "branch": "unknown",
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "dirty_tree": args.dirty == "1",
        "base_branch": args.base,
        "stack_detected": [],
        "metrics": {},
        "spec_drift": None,
        "verdict": {
            "block": False,
            "block_reasons": [],
            "warnings": ["stub: Task 04 not yet implemented"],
        },
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
