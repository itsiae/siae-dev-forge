#!/usr/bin/env python3
"""list_entry_points.py — phase-3 entry-point post-processor.

This script does NOT extract entry points from source code (that is the
runtime's responsibility via Claude's Grep/Read tools, dispatching to
references/stacks/<id>.md). Instead, it:

  1. ingests `inventory.json` (phase 1) and a list of per-subagent
     entry-point payloads collected during phase 3,
  2. validates each canonical_record against the schema declared in
     SKILL.md phase 3,
  3. applies deterministic dedup (by source_ref + kind),
  4. applies the `max_entry_points_per_unit` cap, recording overflow,
  5. emits a single `entry_points.json` ready for phase 4.

Python 3.9+ standard library only.

Usage:
    python3 list_entry_points.py \
        --inventory inventory.json \
        --payloads payloads_dir \
        --max-per-unit 50 \
        --out entry_points.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = {
    "id", "unit_id", "kind", "actor", "trigger", "inputs",
    "downstream_calls", "side_effects", "source_ref",
}
REQUIRED_SOURCE_REF_FIELDS = {"file", "line_start", "line_end", "sha", "dirty_flag"}

VALID_KINDS = {
    "http-route", "graphql-resolver", "grpc-method", "message-consumer",
    "cli-command", "scheduled-job", "ui-screen", "iac-apply-surface",
    "sfn-start", "dbt-model", "db-trigger", "batch-runner", "event-publisher",
}

VALID_ACTORS = {
    "ui-user", "api-caller", "event-publisher", "scheduler",
    "iac-operator", "batch-runner", "db-operator", "observer",
}


def validate(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = REQUIRED_FIELDS - record.keys()
    if missing:
        errors.append(f"missing fields: {sorted(missing)}")
    if record.get("kind") not in VALID_KINDS:
        errors.append(f"invalid kind: {record.get('kind')!r}")
    if record.get("actor") not in VALID_ACTORS:
        errors.append(f"invalid actor: {record.get('actor')!r}")
    src = record.get("source_ref", {})
    if not isinstance(src, dict):
        errors.append("source_ref must be an object")
    else:
        missing_src = REQUIRED_SOURCE_REF_FIELDS - src.keys()
        if missing_src:
            errors.append(f"source_ref missing fields: {sorted(missing_src)}")
    return errors


def complexity_score(record: dict[str, Any]) -> int:
    """Descending complexity score — used to pick top-N when capping."""
    inputs = record.get("inputs") or []
    downstream = record.get("downstream_calls") or []
    side_effects = record.get("side_effects") or []
    src = record.get("source_ref") or {}
    span = (src.get("line_end", 0) - src.get("line_start", 0))
    return (
        3 * len(downstream)
        + 2 * len(side_effects)
        + 1 * len(inputs)
        + (span // 10)
    )


def dedup_key(record: dict[str, Any]) -> str:
    src = record.get("source_ref") or {}
    payload = "".join(
        [
            str(record.get("unit_id", "")),
            str(record.get("kind", "")),
            str(src.get("file", "")),
            str(src.get("line_start", "")),
            str(record.get("trigger", "")),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--inventory", required=True)
    p.add_argument(
        "--payloads",
        "--payloads-dir",
        dest="payloads",
        required=True,
        help="directory containing subagent return payloads (*.json); produced by generate_payloads.py",
    )
    p.add_argument("--max-per-unit", type=int, default=50)
    p.add_argument("--out", required=True)
    args = p.parse_args(argv)

    inventory = json.loads(Path(args.inventory).read_text(encoding="utf-8"))
    known_units = {u["unit_id"] for u in inventory.get("units", [])}

    payload_dir = Path(args.payloads)
    payload_files: list[Path] = []
    if not payload_dir.is_dir():
        sys.stderr.write(
            f"[list_entry_points] WARN payloads dir not found: {payload_dir} — "
            "continuing with empty payload set (see subagent_contract.md 'Payloads dir — producer')\n"
        )
    else:
        payload_files = sorted(payload_dir.glob("*.json"))
        if not payload_files:
            sys.stderr.write(
                f"[list_entry_points] WARN payloads dir empty: {payload_dir} — "
                "continuing with empty payload set\n"
            )

    all_records: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    for f in payload_files:
        try:
            payload = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            invalid.append({"file": str(f), "error": str(e)})
            continue
        for rec in payload.get("findings", []) or payload.get("entry_points", []) or []:
            if not isinstance(rec, dict):
                continue
            errs = validate(rec)
            if errs:
                invalid.append({"file": str(f), "record_id": rec.get("id"), "errors": errs})
                continue
            if rec["unit_id"] not in known_units:
                invalid.append({
                    "file": str(f),
                    "record_id": rec.get("id"),
                    "errors": [f"unit_id {rec['unit_id']!r} not in inventory"],
                })
                continue
            all_records.append(rec)

    # Dedup by canonical key (keep first occurrence in stable order).
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for rec in all_records:
        k = dedup_key(rec)
        if k in seen:
            continue
        seen.add(k)
        deduped.append(rec)

    # Apply per-unit cap, overflow tracked.
    by_unit: dict[str, list[dict[str, Any]]] = {}
    for rec in deduped:
        by_unit.setdefault(rec["unit_id"], []).append(rec)

    kept: list[dict[str, Any]] = []
    overflow: list[dict[str, Any]] = []
    for unit_id, recs in by_unit.items():
        recs.sort(key=lambda r: (-complexity_score(r), r["id"]))
        kept.extend(recs[: args.max_per_unit])
        overflow.extend(recs[args.max_per_unit:])

    # Final canonical ordering for downstream determinism.
    kept.sort(key=lambda r: (r["unit_id"], r["kind"], r["id"]))

    out = {
        "entry_points": kept,
        "overflow": overflow,
        "invalid_records": invalid,
        "stats": {
            "total_seen": len(all_records),
            "after_dedup": len(deduped),
            "kept": len(kept),
            "overflow": len(overflow),
            "invalid": len(invalid),
            "cap_per_unit": args.max_per_unit,
        },
    }
    Path(args.out).write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
    sys.stdout.write(json.dumps(out["stats"], indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
