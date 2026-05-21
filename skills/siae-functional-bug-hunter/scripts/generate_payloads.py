#!/usr/bin/env python3
"""generate_payloads.py — phase-3 cross-stack payload producer.

This script reads the entry-point list produced by `list_entry_points.py`
(or any compatible source) and emits one JSON file per entry point under
`--output-dir`. Each emitted file is consumed by the Phase 3 subagents
described in `references/subagent_contract.md` as the `{{PAYLOADS_SUMMARY}}`
prompt placeholder.

Contract
--------
Input:
    --entry-points <path>   JSON file with shape:
                            { "entry_points": [ { "id": "...", ... }, ... ] }
                            (the file emitted by list_entry_points.py).
    --output-dir <path>     Directory to write into. Created if missing.

Output:
    One file per entry point at <output-dir>/<entry_point_id>.json with
    shape:
        {
          "entry_point_id": "<id>",
          "boundary_id": "<id>",
          "schema_hints": [],
          "literal_payloads": [],
          "env_resolved_payloads": [],
          "notes": "stub: populate from cross-stack bridge resolver"
        }

    The path of the populated directory is printed on stdout so the caller
    can pipe it into `list_entry_points.py --payloads-dir <DIR>`.

This is intentionally a **stub** in v1: it builds the directory structure
and emits skeletons so the subagent contract is honoured (no silent
failure). Future versions will populate `schema_hints`,
`literal_payloads`, and `env_resolved_payloads` from
`references/cross_stack_bridges.md` resolution. The stub guarantees the
Phase 3 fan-out has a deterministic input even before that resolver lands.

Python 3.9+ standard library only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Local import (same scripts/ dir). Adding the script's dir keeps the
# import resolvable when invoked as `python3 scripts/generate_payloads.py`
# from the skill root.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from path_normalize import normalize_path  # noqa: E402


SCHEMA_VERSION = "1.0"


def build_payload(entry_point: dict[str, Any]) -> dict[str, Any]:
    """Build the per-entry-point payload skeleton.

    The skeleton is stable across runs given the same entry-point input,
    which is required by SKILL.md "Quality and determinism".

    When the entry point carries an HTTP path (e.g. as part of `trigger`
    or an explicit `http_path` field), the canonical form per
    references/cross_stack_bridges.md "Path Normalization Rules" is
    written to `canonical_http_path` so downstream bridge resolution
    matches stacks correctly.
    """
    canonical_path = None
    raw_path = entry_point.get("http_path")
    if isinstance(raw_path, str) and raw_path:
        canonical_path = normalize_path(raw_path)
    else:
        # Best-effort: many stacks pack METHOD + path into `trigger`.
        trig = entry_point.get("trigger")
        if isinstance(trig, str) and " " in trig:
            method, _, p = trig.partition(" ")
            if p.startswith("/"):
                canonical_path = f"{method} {normalize_path(p)}"

    return {
        "schema_version": SCHEMA_VERSION,
        "entry_point_id": entry_point["id"],
        "boundary_id": entry_point.get("boundary_id", entry_point["id"]),
        "kind": entry_point.get("kind"),
        "unit_id": entry_point.get("unit_id"),
        "canonical_http_path": canonical_path,
        "schema_hints": [],
        "literal_payloads": [],
        "env_resolved_payloads": [],
        "notes": "stub: populate from cross-stack bridge resolver",
    }


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--entry-points", required=True,
                   help="Path to entry_points.json (output of list_entry_points.py).")
    p.add_argument("--output-dir", required=True,
                   help="Directory to write payload skeletons into. Created if missing.")
    args = p.parse_args(argv)

    ep_path = Path(args.entry_points)
    if not ep_path.is_file():
        sys.stderr.write(f"[generate_payloads] entry-points file not found: {ep_path}\n")
        return 2

    try:
        data = json.loads(ep_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.stderr.write(f"[generate_payloads] invalid JSON in {ep_path}: {e}\n")
        return 2

    entry_points = data.get("entry_points") or []
    if not isinstance(entry_points, list):
        sys.stderr.write(f"[generate_payloads] expected 'entry_points' array in {ep_path}\n")
        return 2

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    written = 0
    skipped = 0
    for ep in entry_points:
        if not isinstance(ep, dict) or "id" not in ep:
            skipped += 1
            continue
        target = out_dir / f"{ep['id']}.json"
        target.write_text(
            json.dumps(build_payload(ep), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        written += 1

    if skipped:
        sys.stderr.write(
            f"[generate_payloads] skipped {skipped} malformed entry-point records\n"
        )

    sys.stdout.write(str(out_dir.resolve()) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
