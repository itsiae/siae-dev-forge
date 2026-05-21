#!/usr/bin/env python3
"""path_feasibility.py — Phase 6 hypothesis feasibility filter.

Reads `hypotheses.json` and challenges each hypothesis against the actual
code surface discovered in Phase 4. A hypothesis is feasible when:

1. its `evidence_path` substring matches at least one file inside the
   analysed units (i.e. the path actually exists in scope);
2. AT LEAST ONE of its `path_predicates` (free-form keyword tokens) is
   found in the matched files (best-effort case-insensitive substring);
3. the hypothesis has at least one declared `actor_primitive` (a path
   without a reachable actor is not feasible by definition — there is
   no human who could trigger it).

The verdict is written back to each hypothesis as:

    {
      "verdict": "feasible" | "infeasible",
      "verdict_reason": "<short string>",
      "matched_files": ["<rel/path>", ...]
    }

Discarded hypotheses are NOT removed from the file — they stay with
`verdict: "infeasible"` and `verdict_reason` for traceability (per
SKILL.md "Phase 6"). The script is intentionally minimal: no AST, no
tree-sitter, no symbolic execution. Path predicates are tokens to grep
for, not SMT formulas. Deeper analysis remains an operator obligation;
this script provides the deterministic, grep-based first filter the
SKILL.md claims.

Usage
-----
    python3 path_feasibility.py \\
        --hypotheses /abs/output_dir/hypotheses.json \\
        --roots /abs/path/repoA /abs/path/repoB \\
        [--out /abs/output_dir/hypotheses.json]

When `--out` is omitted the script overwrites the input file in place.

Exit codes
----------
0  ran to completion (any feasible/infeasible mix).
1  no input file, malformed JSON, or zero hypotheses after parsing.
2  IO error writing the output file.

Python 3.9+ standard library only.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def _load_hypotheses(path: Path) -> list[dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "hypotheses" in raw:
        return raw["hypotheses"]
    if isinstance(raw, list):
        return raw
    raise ValueError(
        f"unexpected hypotheses.json shape (expected list or {{'hypotheses': [...]}}): {type(raw).__name__}"
    )


def _enumerate_files(roots: list[Path], skip_dirs: set[str]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in skip_dirs]
            for name in filenames:
                files.append(Path(dirpath) / name)
    return files


def _match_evidence_path(
    evidence_path: str | None,
    files: list[Path],
    roots: list[Path],
) -> list[str]:
    if not evidence_path:
        return []
    needle = evidence_path.strip()
    matched: list[str] = []
    for f in files:
        candidates = [str(f)]
        for r in roots:
            try:
                candidates.append(str(f.relative_to(r)))
            except ValueError:
                continue
        if any(needle in c for c in candidates):
            matched.append(str(f))
    return matched


def _predicate_present(predicate: str, matched_files: list[str]) -> bool:
    if not predicate:
        return False
    needle = predicate.lower()
    for fp in matched_files:
        try:
            with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                if needle in fh.read().lower():
                    return True
        except OSError:
            continue
    return False


def verdict_for(
    hypothesis: dict,
    files: list[Path],
    roots: list[Path],
) -> dict:
    actors = hypothesis.get("actor_primitives") or hypothesis.get("actor_primitive")
    if not actors:
        return {
            "verdict": "infeasible",
            "verdict_reason": "no_actor_primitive",
            "matched_files": [],
        }

    evidence_path = hypothesis.get("evidence_path") or hypothesis.get("source_path")
    matched = _match_evidence_path(evidence_path, files, roots)
    if not matched:
        return {
            "verdict": "infeasible",
            "verdict_reason": "evidence_path_not_in_scope",
            "matched_files": [],
        }

    predicates = hypothesis.get("path_predicates") or []
    if not predicates:
        return {
            "verdict": "feasible",
            "verdict_reason": "no_predicates_declared",
            "matched_files": matched[:10],
        }

    if any(_predicate_present(p, matched) for p in predicates):
        return {
            "verdict": "feasible",
            "verdict_reason": "at_least_one_predicate_matched",
            "matched_files": matched[:10],
        }
    return {
        "verdict": "infeasible",
        "verdict_reason": "no_predicate_matched",
        "matched_files": matched[:10],
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Phase 6 — path feasibility filter for functional-bug-hunter."
    )
    parser.add_argument("--hypotheses", required=True, type=Path)
    parser.add_argument("--roots", required=True, nargs="+", type=Path)
    parser.add_argument("--out", required=False, type=Path)
    parser.add_argument(
        "--skip-dirs",
        nargs="*",
        default=[
            ".git",
            "node_modules",
            "vendor",
            "target",
            "dist",
            "build",
            ".terraform",
            "__pycache__",
        ],
    )
    args = parser.parse_args(argv)

    try:
        hypotheses = _load_hypotheses(args.hypotheses)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"path_feasibility: cannot load hypotheses: {exc}", file=sys.stderr)
        return 1

    if not hypotheses:
        print("path_feasibility: zero hypotheses in input — nothing to verdict", file=sys.stderr)
        return 1

    files = _enumerate_files(args.roots, set(args.skip_dirs))

    feasible = 0
    infeasible = 0
    for h in hypotheses:
        v = verdict_for(h, files, args.roots)
        h["verdict"] = v["verdict"]
        h["verdict_reason"] = v["verdict_reason"]
        h["matched_files"] = v["matched_files"]
        if v["verdict"] == "feasible":
            feasible += 1
        else:
            infeasible += 1

    out_path = args.out or args.hypotheses
    try:
        out_path.write_text(json.dumps(hypotheses, indent=2), encoding="utf-8")
    except OSError as exc:
        print(f"path_feasibility: cannot write output: {exc}", file=sys.stderr)
        return 2

    print(
        f"path_feasibility: verdicts written to {out_path} "
        f"({feasible} feasible / {infeasible} infeasible / {len(hypotheses)} total)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
