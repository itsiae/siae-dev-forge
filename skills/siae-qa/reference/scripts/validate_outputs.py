#!/usr/bin/env python3
"""Validate siae-qa workflow outputs (M_FINAL, TC_DRAFT, coverage_certificate, xray_id_mapping)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import jsonschema  # type: ignore
    from jsonschema import Draft202012Validator

    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"
SCHEMA_FILES = {
    "m_final": SCHEMAS_DIR / "m_final.schema.json",
    "tc_draft": SCHEMAS_DIR / "tc_draft.schema.json",
    "certificate": SCHEMAS_DIR / "coverage_certificate.schema.json",
    "mapping": SCHEMAS_DIR / "xray_id_mapping.schema.json",
}

JIRA_KEY_RE = re.compile(r"^[A-Z]+-[0-9]+$")
TITLE_PREFIX_RE = re.compile(r"^\[(POS|NEG|EDGE|ROLE)\] .+")
MATRIX_ROW_ID_RE = re.compile(r"^(?:[A-Z]-[0-9]{3}|J5-gap-G[0-9]{2}|developer-[0-9]{3})$")


def load_schema(name: str) -> dict[str, Any]:
    """Read and parse a schema file by logical name."""
    return json.loads(SCHEMA_FILES[name].read_text(encoding="utf-8"))


def parse_json_file(path: Path) -> Any:
    """Load JSON from disk; fallback to markdown table heuristic for .md inputs."""
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".md":
        return _parse_markdown_matrix(text, path.name)
    return json.loads(text)


def _parse_markdown_matrix(text: str, filename: str) -> dict[str, Any]:
    """Heuristic parser for MFINAL.md / TC_DRAFT.md markdown tables."""
    lower = filename.lower()
    rows: list[dict[str, Any]] = []
    in_table = False
    headers: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("|") and line.endswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if not in_table:
                headers = [c.lower().replace(" ", "_") for c in cells]
                in_table = True
                continue
            if all(set(c) <= {"-", ":"} for c in cells):
                continue
            row = dict(zip(headers, cells))
            rows.append(row)
        else:
            in_table = False
    if "mfinal" in lower:
        return {"story_id": "UNKNOWN-0", "timestamp": "1970-01-01T00:00:00Z", "rows": rows}
    return {"story_id": "UNKNOWN-0", "timestamp": "1970-01-01T00:00:00Z", "test_cases": rows}


def validate_with_schema(instance: Any, schema: dict[str, Any]) -> list[str]:
    """Return list of validation error messages; empty list means valid."""
    if HAS_JSONSCHEMA:
        validator = Draft202012Validator(schema)
        return [f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
                for e in validator.iter_errors(instance)]
    return _fallback_validate(instance, schema)


def _fallback_validate(instance: Any, schema: dict[str, Any]) -> list[str]:
    """Minimal semantic checks when jsonschema is unavailable."""
    errors: list[str] = []
    title = schema.get("title", "")
    if title == "M_FINAL":
        errors.extend(_check_m_final(instance))
    elif title == "TC_DRAFT":
        errors.extend(_check_tc_draft(instance))
    elif title == "CoverageCertificate":
        errors.extend(_check_certificate(instance))
    elif title == "XrayIdMapping":
        errors.extend(_check_mapping(instance))
    return errors


def _check_m_final(obj: dict[str, Any]) -> list[str]:
    """Fallback structural checks for M_FINAL."""
    errors: list[str] = []
    for key in ("story_id", "timestamp", "rows"):
        if key not in obj:
            errors.append(f"missing required field: {key}")
    if "story_id" in obj and not JIRA_KEY_RE.match(obj["story_id"]):
        errors.append(f"story_id '{obj['story_id']}' does not match Jira key pattern")
    for idx, row in enumerate(obj.get("rows", [])):
        for f in ("matrix_row_id", "entity", "field", "condition", "test_type", "source_ref"):
            if f not in row:
                errors.append(f"rows[{idx}].{f}: missing")
        if row.get("test_type") not in {"POS", "NEG", "EDGE", "ROLE"}:
            errors.append(f"rows[{idx}].test_type invalid: {row.get('test_type')}")
        if "matrix_row_id" in row and not MATRIX_ROW_ID_RE.match(row["matrix_row_id"]):
            errors.append(f"rows[{idx}].matrix_row_id pattern: {row['matrix_row_id']}")
    return errors


def _check_tc_draft(obj: dict[str, Any]) -> list[str]:
    """Fallback structural checks for TC_DRAFT."""
    errors: list[str] = []
    for key in ("story_id", "timestamp", "test_cases"):
        if key not in obj:
            errors.append(f"missing required field: {key}")
    for idx, tc in enumerate(obj.get("test_cases", [])):
        for f in ("id", "matrix_row_id", "title", "entity", "field", "test_type",
                  "description", "preconditions", "steps", "automazione", "nrt"):
            if f not in tc:
                errors.append(f"test_cases[{idx}].{f}: missing")
        if "title" in tc and not TITLE_PREFIX_RE.match(tc["title"]):
            errors.append(f"test_cases[{idx}].title missing [POS|NEG|EDGE|ROLE] prefix: {tc['title']!r}")
        desc = tc.get("description", "")
        for marker in ("matrix_row_id:", "entity:", "field:"):
            if marker not in desc:
                errors.append(f"test_cases[{idx}].description missing marker {marker!r}")
        if not isinstance(tc.get("steps"), list) or not tc.get("steps"):
            errors.append(f"test_cases[{idx}].steps must be non-empty array")
    return errors


def _check_certificate(obj: dict[str, Any]) -> list[str]:
    """Fallback structural checks for CoverageCertificate."""
    errors: list[str] = []
    if obj.get("stato") not in {"FULL_PASS", "CONDITIONAL_PASS", "FAIL"}:
        errors.append(f"stato invalid: {obj.get('stato')}")
    score = obj.get("coverage_score")
    if not isinstance(score, int) or not 0 <= score <= 100:
        errors.append(f"coverage_score out of range: {score}")
    for gate in ("gate_1", "gate_2"):
        g = obj.get(gate, {})
        if g.get("status") not in {"PASS", "FAIL"}:
            errors.append(f"{gate}.status invalid: {g.get('status')}")
    return errors


def _check_mapping(obj: dict[str, Any]) -> list[str]:
    """Fallback structural checks for XrayIdMapping."""
    errors: list[str] = []
    if obj.get("tier") not in {"tier_1_mcp", "tier_2_doc", "tier_3_csv"}:
        errors.append(f"tier invalid: {obj.get('tier')}")
    if not isinstance(obj.get("complete"), bool):
        errors.append("complete must be boolean")
    return errors


def cross_check_mfinal_tcdraft(m_final: dict[str, Any], tc_draft: dict[str, Any]) -> list[str]:
    """Verify TC<->M_FINAL bijection."""
    errors: list[str] = []
    mf_ids = {r.get("matrix_row_id") for r in m_final.get("rows", [])}
    tc_ids = [tc.get("matrix_row_id") for tc in tc_draft.get("test_cases", [])]
    if len(tc_ids) != len(mf_ids):
        errors.append(f"bijection count mismatch: M_FINAL rows={len(mf_ids)} TC={len(tc_ids)}")
    orphan_tc = [t for t in tc_ids if t not in mf_ids]
    if orphan_tc:
        errors.append(f"TC with unknown matrix_row_id: {orphan_tc}")
    return errors


def cross_check_certificate(cert: dict[str, Any]) -> list[str]:
    """Verify internal consistency of the certificate."""
    errors: list[str] = []
    expected = cert.get("m_final_rows", 0) + cert.get("tc_added_post_j5", 0)
    if cert.get("tc_generated") != expected:
        errors.append(
            f"tc_generated ({cert.get('tc_generated')}) != m_final_rows+tc_added_post_j5 ({expected})"
        )
    if cert.get("stato") == "FULL_PASS":
        if cert.get("gate_1", {}).get("status") != "PASS":
            errors.append("FULL_PASS requires gate_1.status=PASS")
        if cert.get("gate_2", {}).get("status") != "PASS":
            errors.append("FULL_PASS requires gate_2.status=PASS")
        if cert.get("coverage_score", 0) < 90:
            errors.append(f"FULL_PASS requires coverage_score>=90, got {cert.get('coverage_score')}")
    return errors


def _report(label: str, errors: list[str]) -> bool:
    """Print PASS/FAIL block for a single artifact and return success boolean."""
    if not errors:
        print(f"[PASS] {label}")
        return True
    print(f"[FAIL] {label} ({len(errors)} errors)")
    for e in errors:
        print(f"   - {e}")
    return False


def main(argv: list[str] | None = None) -> int:
    """Entrypoint: parse args, validate inputs, run cross-checks, return exit code."""
    parser = argparse.ArgumentParser(description="Validate siae-qa workflow outputs")
    parser.add_argument("--m-final", type=Path, help="Path to M_FINAL JSON or markdown")
    parser.add_argument("--tc-draft", type=Path, help="Path to TC_DRAFT JSON or markdown")
    parser.add_argument("--certificate", type=Path, help="Path to coverage_certificate.json")
    parser.add_argument("--mapping", type=Path, help="Path to xray_id_mapping.json")
    args = parser.parse_args(argv)

    if not any([args.m_final, args.tc_draft, args.certificate, args.mapping]):
        parser.error("at least one of --m-final/--tc-draft/--certificate/--mapping is required")

    if not HAS_JSONSCHEMA:
        print("[WARN] jsonschema not installed: using fallback semantic checks", file=sys.stderr)

    ok = True
    m_final_obj: dict[str, Any] | None = None
    tc_draft_obj: dict[str, Any] | None = None
    certificate_obj: dict[str, Any] | None = None

    if args.m_final:
        m_final_obj = parse_json_file(args.m_final)
        ok &= _report(f"M_FINAL ({args.m_final})", validate_with_schema(m_final_obj, load_schema("m_final")))
    if args.tc_draft:
        tc_draft_obj = parse_json_file(args.tc_draft)
        ok &= _report(f"TC_DRAFT ({args.tc_draft})", validate_with_schema(tc_draft_obj, load_schema("tc_draft")))
    if args.certificate:
        certificate_obj = parse_json_file(args.certificate)
        ok &= _report(
            f"CERTIFICATE ({args.certificate})",
            validate_with_schema(certificate_obj, load_schema("certificate")),
        )
    if args.mapping:
        mapping_obj = parse_json_file(args.mapping)
        ok &= _report(
            f"MAPPING ({args.mapping})",
            validate_with_schema(mapping_obj, load_schema("mapping")),
        )

    if m_final_obj is not None and tc_draft_obj is not None:
        ok &= _report("CROSS: M_FINAL<->TC_DRAFT bijection",
                      cross_check_mfinal_tcdraft(m_final_obj, tc_draft_obj))
    if certificate_obj is not None:
        ok &= _report("CROSS: certificate consistency", cross_check_certificate(certificate_obj))

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
