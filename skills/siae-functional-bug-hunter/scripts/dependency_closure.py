#!/usr/bin/env python3
"""dependency_closure.py — phase-2 boundary registry &amp; closure check.

Ingests `inventory.json` plus per-unit boundary observations (collected
by phase 1/3 subagents) and builds the `boundary_identifier_registry`
that lets phase 4 resolve cross-unit references. Also emits
`dependency_closure.md` describing what is missing.

Python 3.9+ standard library only.

Boundary kinds correspond to references/cross_stack_bridges.md.

Usage:
    python3 dependency_closure.py \
        --inventory inventory.json \
        --observations observations_dir \
        --registry-out boundary_identifier_registry.json \
        --closure-out dependency_closure.md
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

VALID_KINDS = {
    "http-path", "grpc-service-method", "graphql-field", "queue-name",
    "topic-name", "bucket-key", "event-bus-source-detail", "lambda-arn",
    "sfn-arn", "dbt-source", "db-table", "iam-role-arn", "feature-flag-key",
}


def normalize(kind: str, identifier: str) -> str:
    """Normalize identifier shape for stable registry keying."""
    if kind == "http-path":
        # collapse double slashes, strip trailing slash unless root
        ident = identifier.strip()
        if " " in ident:
            method, path = ident.split(" ", 1)
            path = "/" + "/".join(p for p in path.split("/") if p)
            if path == "/":
                path = "/"
            return f"{method.upper()} {path}"
        return ident
    if kind in ("queue-name", "topic-name"):
        # strip ARN to last segment when present
        if ":" in identifier:
            return identifier.rsplit(":", 1)[-1]
        return identifier
    return identifier


def build_registry(observations: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Build the registry keyed by `<kind>::<identifier>`.

    Each entry records: producers (units emitting it), consumers (units
    handling it), resolution status (matched / partial / unresolved),
    confidence ("high" if literal match on both sides, "low_partial"
    otherwise).
    """
    registry: dict[str, dict[str, Any]] = {}
    for obs in observations:
        kind = obs.get("kind")
        ident = obs.get("identifier")
        if kind not in VALID_KINDS or not ident:
            continue
        key = f"{kind}::{normalize(kind, ident)}"
        role = obs.get("role")  # "producer" or "consumer"
        unit_id = obs.get("unit_id")
        if not unit_id or role not in ("producer", "consumer"):
            continue
        entry = registry.setdefault(
            key,
            {
                "kind": kind,
                "identifier": normalize(kind, ident),
                "producers": [],
                "consumers": [],
                "evidence": [],
            },
        )
        bucket = entry["producers"] if role == "producer" else entry["consumers"]
        if unit_id not in bucket:
            bucket.append(unit_id)
        ev = obs.get("evidence")
        if ev:
            entry["evidence"].append(ev)
    # compute resolution status
    for entry in registry.values():
        prods = entry["producers"]
        cons = entry["consumers"]
        if prods and cons:
            entry["status"] = "matched"
            entry["confidence"] = "high"
        elif prods and not cons:
            entry["status"] = "unresolved-consumer"
            entry["confidence"] = "low_partial"
        elif cons and not prods:
            entry["status"] = "unresolved-producer"
            entry["confidence"] = "low_partial"
        else:
            entry["status"] = "orphan"
            entry["confidence"] = "low_partial"
    return registry


def gather_observations(observations_dir: Path) -> list[dict[str, Any]]:
    obs: list[dict[str, Any]] = []
    for f in sorted(observations_dir.glob("*.json")):
        try:
            payload = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for o in payload.get("boundary_observations", []):
            if isinstance(o, dict):
                obs.append(o)
    return obs


def render_closure(registry: dict[str, dict[str, Any]], inventory: dict[str, Any]) -> str:
    """Emit dependency_closure.md content."""
    lines: list[str] = []
    lines.append("# Dependency closure")
    lines.append("")
    lines.append(
        "This file summarizes what crosses unit boundaries and what does "
        "NOT have a counterpart within the analyzed roots. Closure gaps "
        "on critical-path entry points trigger a STOP decision in "
        "interactive mode (see SKILL.md)."
    )
    lines.append("")
    lines.append("## Units in scope")
    lines.append("")
    for u in inventory.get("units", []):
        stacks = ", ".join(u.get("stack_ids", []) or [])
        lines.append(f"- `{u['unit_id']}` ({stacks})")
    lines.append("")

    by_status: dict[str, list[dict[str, Any]]] = {}
    for entry in registry.values():
        by_status.setdefault(entry["status"], []).append(entry)

    lines.append("## Closure summary")
    lines.append("")
    lines.append("| status | count |")
    lines.append("|---|---|")
    for status in ("matched", "unresolved-consumer", "unresolved-producer", "orphan"):
        lines.append(f"| {status} | {len(by_status.get(status, []))} |")
    lines.append("")

    for status in ("unresolved-consumer", "unresolved-producer", "orphan"):
        items = by_status.get(status, [])
        if not items:
            continue
        lines.append(f"## {status} ({len(items)})")
        lines.append("")
        lines.append("| kind | identifier | producers | consumers |")
        lines.append("|---|---|---|---|")
        for entry in sorted(items, key=lambda e: (e["kind"], e["identifier"])):
            lines.append(
                f"| {entry['kind']} | `{entry['identifier']}` | "
                f"{', '.join(entry['producers']) or '—'} | "
                f"{', '.join(entry['consumers']) or '—'} |"
            )
        lines.append("")

    if by_status.get("matched"):
        lines.append("## Matched bridges")
        lines.append("")
        lines.append("| kind | identifier | producers | consumers |")
        lines.append("|---|---|---|---|")
        for entry in sorted(by_status["matched"], key=lambda e: (e["kind"], e["identifier"])):
            lines.append(
                f"| {entry['kind']} | `{entry['identifier']}` | "
                f"{', '.join(entry['producers'])} | {', '.join(entry['consumers'])} |"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--inventory", required=True)
    p.add_argument("--observations", required=True)
    p.add_argument("--registry-out", required=True)
    p.add_argument("--closure-out", required=True)
    args = p.parse_args(argv)

    inv = json.loads(Path(args.inventory).read_text(encoding="utf-8"))
    obs_dir = Path(args.observations)
    if not obs_dir.is_dir():
        sys.stderr.write(f"observations dir not found: {obs_dir}\n")
        return 2

    obs = gather_observations(obs_dir)
    registry = build_registry(obs)

    Path(args.registry_out).write_text(
        json.dumps(registry, indent=2, sort_keys=True), encoding="utf-8"
    )
    Path(args.closure_out).write_text(render_closure(registry, inv), encoding="utf-8")
    stats = {
        "observations_total": len(obs),
        "registry_entries": len(registry),
        "matched": sum(1 for e in registry.values() if e["status"] == "matched"),
        "unresolved": sum(1 for e in registry.values() if e["status"].startswith("unresolved")),
        "orphan": sum(1 for e in registry.values() if e["status"] == "orphan"),
    }
    sys.stdout.write(json.dumps(stats, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
