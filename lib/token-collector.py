#!/usr/bin/env python3
"""DevForge Token Collector — incremental session token counter."""
from __future__ import annotations

import glob
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE_DIR = Path(os.path.expanduser(os.environ.get("DEVFORGE_STATE_DIR", "~/.claude")))

# cache write: 5m = 1.25x base input, 1h = 2x base input (prezzi Anthropic)
PRICING_USD_PER_1M: dict[str, dict[str, float]] = {
    "claude-opus-4-8":    {"input": 5.0, "output": 25.0, "cache_read": 0.50, "cache_write_5m": 6.25, "cache_write_1h": 10.0},
    "claude-opus-4-7":    {"input": 5.0, "output": 25.0, "cache_read": 0.50, "cache_write_5m": 6.25, "cache_write_1h": 10.0},
    "claude-opus-4-6":    {"input": 5.0, "output": 25.0, "cache_read": 0.50, "cache_write_5m": 6.25, "cache_write_1h": 10.0},
    "claude-sonnet-4-6":  {"input": 3.0, "output": 15.0, "cache_read": 0.30, "cache_write_5m": 3.75, "cache_write_1h": 6.0},
    "claude-haiku-4-5":   {"input": 1.0, "output": 5.0,  "cache_read": 0.10, "cache_write_5m": 1.25, "cache_write_1h": 2.0},
    "default":            {"input": 3.0, "output": 15.0, "cache_read": 0.30, "cache_write_5m": 3.75, "cache_write_1h": 6.0},
}

# Legacy alias list for canonical_model prefix matching
MODEL_PREFIXES: tuple[str, ...] = (
    "claude-opus-4-8",
    "claude-opus-4-7",
    "claude-opus-4-6",
    "claude-opus-4-5",
    "claude-opus-4-1",
    "claude-opus-4",
    "claude-sonnet-4-6",
    "claude-sonnet-4-5",
    "claude-sonnet-4",
    "claude-sonnet-3-7",
    "claude-haiku-4-5",
    "claude-haiku-3-5",
    "claude-haiku-3",
)
def resolve_eur_rate() -> float:
    """USD→EUR rate from DEVFORGE_USD_EUR_RATE env var. Fallback 0.91 on absent/malformed/<=0."""
    raw = os.environ.get("DEVFORGE_USD_EUR_RATE", "")
    if not raw:
        return 0.91
    try:
        value = float(raw)
    except (ValueError, TypeError):
        return 0.91
    return value if value > 0 else 0.91


USD_TO_EUR = resolve_eur_rate()
TOKEN_FIELDS = (
    "input",
    "output",
    "cache_read",
    "cache_write_5m",
    "cache_write_1h",
    "cache_write",
    "total",
)


def project_hash() -> str:
    """Compute the Claude Code project hash for the current working directory."""
    return re.sub(r"[^a-zA-Z0-9]", "-", os.getcwd())


def session_dir() -> str | None:
    """Return DEVFORGE_SESSION_DIR if set and exists, else None."""
    sd = os.environ.get("DEVFORGE_SESSION_DIR", "")
    if sd and os.path.isdir(sd):
        return sd
    return None


def cursor_file() -> Path:
    sd = session_dir()
    if sd:
        return Path(os.path.join(sd, "token-cursor"))
    return STATE_DIR / f".devforge-token-cursor-{project_hash()}"


def stats_file() -> Path:
    sd = session_dir()
    if sd:
        return Path(os.path.join(sd, "token-stats.json"))
    return STATE_DIR / f".devforge-token-stats-{project_hash()}"


def usage_index_file() -> Path:
    sd = session_dir()
    if sd:
        return Path(os.path.join(sd, "token-usage-index.json"))
    return STATE_DIR / f".devforge-token-usage-index-{project_hash()}"


def find_session_jsonl() -> Path | None:
    override = os.environ.get("DEVFORGE_TOKEN_SESSION_JSONL")
    if override:
        path = Path(os.path.expanduser(override))
        return path if path.is_file() else None

    project_dir = STATE_DIR / "projects" / project_hash()
    if not project_dir.is_dir():
        return None

    jsonl_files = [Path(path) for path in glob.glob(str(project_dir / "*.jsonl"))]
    if not jsonl_files:
        return None

    return max(jsonl_files, key=lambda path: path.stat().st_mtime)


def empty_stats() -> dict[str, Any]:
    return {
        "input": 0,
        "output": 0,
        "cache_read": 0,
        "cache_write": 0,
        "cache_write_5m": 0,
        "cache_write_1h": 0,
        "total": 0,
        "cost_eur": 0.0,
        "by_model": {},
        "model_prevalent": "",
        "updated_at": "",
    }


def normalize_stats(raw: dict[str, Any] | None) -> dict[str, Any]:
    stats = empty_stats()
    if not isinstance(raw, dict):
        return stats

    for key, default in stats.items():
        value = raw.get(key, default)
        if isinstance(default, float):
            stats[key] = float(value or 0.0)
        elif isinstance(default, int):
            stats[key] = int(value or 0)
        else:
            stats[key] = value or default

    raw_by_model = raw.get("by_model")
    stats["by_model"] = dict(raw_by_model) if isinstance(raw_by_model, dict) else {}
    stats["model_prevalent"] = raw.get("model_prevalent") or ""

    stats["cache_write"] = int(stats["cache_write_5m"] + stats["cache_write_1h"])
    stats["total"] = int(
        stats["input"]
        + stats["output"]
        + stats["cache_read"]
        + stats["cache_write"]
    )
    return stats


def read_stats() -> dict[str, Any]:
    try:
        return normalize_stats(json.loads(stats_file().read_text(encoding="utf-8")))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return empty_stats()


def read_cursor() -> tuple[str, int]:
    try:
        raw = cursor_file().read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return "", 0

    if not raw:
        return "", 0

    parts = raw.split("\t")
    if len(parts) != 2:
        return "", 0

    try:
        return parts[0], int(parts[1])
    except ValueError:
        return "", 0


def read_usage_index() -> dict[str, dict[str, Any]]:
    try:
        raw = json.loads(usage_index_file().read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}

    if not isinstance(raw, dict):
        return {}

    normalized: dict[str, dict[str, Any]] = {}
    for usage_id, snapshot in raw.items():
        if not isinstance(usage_id, str) or not isinstance(snapshot, dict):
            continue
        normalized[usage_id] = normalize_usage_snapshot(snapshot)
    return normalized


def write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def write_cursor(path: str, offset: int) -> None:
    write_atomic(cursor_file(), f"{path}\t{offset}")


def write_stats(stats: dict[str, Any]) -> None:
    write_atomic(stats_file(), json.dumps(stats, separators=(",", ":"), sort_keys=True))


def write_usage_index(index: dict[str, dict[str, Any]]) -> None:
    write_atomic(usage_index_file(), json.dumps(index, separators=(",", ":"), sort_keys=True))


def canonical_model(model: str | None) -> str:
    if not model or not isinstance(model, str):
        return ""
    for prefix in MODEL_PREFIXES:
        if model.startswith(prefix):
            return prefix
    return ""


def pricing_for_model(model: str | None) -> dict[str, float]:
    """Return pricing rates for a model. Falls back to 'default' pricing."""
    family = canonical_model(model)
    if family in PRICING_USD_PER_1M:
        return PRICING_USD_PER_1M[family]
    # Map legacy model families to their closest current pricing
    if family.startswith("claude-opus"):
        return PRICING_USD_PER_1M["claude-opus-4-6"]
    if family.startswith("claude-sonnet"):
        return PRICING_USD_PER_1M["claude-sonnet-4-6"]
    if family.startswith("claude-haiku"):
        return PRICING_USD_PER_1M["claude-haiku-4-5"]
    return PRICING_USD_PER_1M["default"]


def iter_usage_sources(event: dict[str, Any]):
    yield event
    data = event.get("data")
    if isinstance(data, dict):
        message = data.get("message")
        if isinstance(message, dict):
            yield message


def extract_usage(source: dict[str, Any]) -> dict[str, Any] | None:
    usage = None
    if source.get("type") == "assistant":
        usage = source.get("message", {}).get("usage") or source.get("usage")
    elif source.get("type") == "message":
        usage = source.get("usage") or source.get("message", {}).get("usage")
    elif isinstance(source.get("message"), dict):
        usage = source["message"].get("usage")
    elif "usage" in source:
        usage = source.get("usage")
    return usage if isinstance(usage, dict) else None


def usage_identity(source: dict[str, Any]) -> str:
    message = source.get("message")
    if isinstance(message, dict):
        message_id = message.get("id")
        if isinstance(message_id, str) and message_id:
            return message_id

    for key in ("requestId", "uuid", "messageId"):
        value = source.get(key)
        if isinstance(value, str) and value:
            return value

    return json.dumps(source, sort_keys=True, separators=(",", ":"))


def extract_model(source: dict[str, Any]) -> str:
    message = source.get("message")
    if isinstance(message, dict):
        model = message.get("model")
        if isinstance(model, str):
            return model
    model = source.get("model")
    return model if isinstance(model, str) else ""


def usage_tokens(usage: dict[str, Any]) -> dict[str, int]:
    cache_creation = usage.get("cache_creation")
    cache_write_5m = 0
    cache_write_1h = 0
    if isinstance(cache_creation, dict):
        cache_write_5m = int(cache_creation.get("ephemeral_5m_input_tokens", 0) or 0)
        cache_write_1h = int(cache_creation.get("ephemeral_1h_input_tokens", 0) or 0)

    if cache_write_5m == 0 and cache_write_1h == 0:
        cache_write_5m = int(usage.get("cache_creation_input_tokens", 0) or 0)

    cache_write = cache_write_5m + cache_write_1h
    input_tokens = int(usage.get("input_tokens", 0) or 0)
    output_tokens = int(usage.get("output_tokens", 0) or 0)
    cache_read = int(usage.get("cache_read_input_tokens", 0) or 0)

    return {
        "input": input_tokens,
        "output": output_tokens,
        "cache_read": cache_read,
        "cache_write_5m": cache_write_5m,
        "cache_write_1h": cache_write_1h,
        "cache_write": cache_write,
        "total": input_tokens + output_tokens + cache_read + cache_write,
    }


def usage_cost_eur(metrics: dict[str, int], model: str | None) -> float:
    rates = pricing_for_model(model)

    cost_usd = (
        metrics["input"] * rates["input"] / 1_000_000
        + metrics["output"] * rates["output"] / 1_000_000
        + metrics["cache_read"] * rates["cache_read"] / 1_000_000
        + metrics["cache_write_5m"] * rates["cache_write_5m"] / 1_000_000
        + metrics["cache_write_1h"] * rates["cache_write_1h"] / 1_000_000
    )
    return round(cost_usd * resolve_eur_rate(), 6)


def normalize_usage_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        field: int(snapshot.get(field, 0) or 0)
        for field in TOKEN_FIELDS
    }
    normalized["cache_write"] = normalized["cache_write_5m"] + normalized["cache_write_1h"]
    normalized["total"] = (
        normalized["input"]
        + normalized["output"]
        + normalized["cache_read"]
        + normalized["cache_write"]
    )
    normalized["model"] = snapshot.get("model") or ""
    normalized["cost_eur"] = float(snapshot.get("cost_eur", 0.0) or 0.0)
    return normalized


def build_usage_snapshot(source: dict[str, Any], usage: dict[str, Any]) -> dict[str, Any]:
    metrics = usage_tokens(usage)
    model = extract_model(source)
    snapshot = dict(metrics)
    snapshot["model"] = model
    snapshot["cost_eur"] = usage_cost_eur(metrics, model)
    return snapshot


def add_usage_delta(stats: dict[str, Any], previous: dict[str, Any] | None, current: dict[str, Any]) -> bool:
    previous = previous or normalize_usage_snapshot({})
    changed = False

    for field in ("input", "output", "cache_read", "cache_write_5m", "cache_write_1h"):
        current_value = int(current.get(field, 0) or 0)
        previous_value = int(previous.get(field, 0) or 0)
        delta = current_value - previous_value
        if delta > 0:
            stats[field] += delta
            changed = True

    cost_delta = float(current.get("cost_eur", 0.0) or 0.0) - float(previous.get("cost_eur", 0.0) or 0.0)
    if cost_delta > 0:
        stats["cost_eur"] = round(float(stats.get("cost_eur", 0.0)) + cost_delta, 6)
        changed = True

    model = current.get("model") or ""
    if model:
        delta_total = sum(
            max(int(current.get(field, 0) or 0) - int(previous.get(field, 0) or 0), 0)
            for field in ("input", "output", "cache_read", "cache_write_5m", "cache_write_1h")
        )
        if delta_total > 0:
            by_model = stats.setdefault("by_model", {})
            by_model[model] = int(by_model.get(model, 0)) + delta_total
            changed = True

    stats["cache_write"] = int(stats["cache_write_5m"] + stats["cache_write_1h"])
    stats["total"] = int(stats["input"] + stats["output"] + stats["cache_read"] + stats["cache_write"])
    return changed


def finalize_model_prevalent(stats: dict[str, Any]) -> None:
    """Set stats['model_prevalent'] to the model with most tokens (tie-break: alphabetical)."""
    by_model = stats.get("by_model") or {}
    if not by_model:
        stats["model_prevalent"] = ""
        return
    stats["model_prevalent"] = min(
        by_model.items(), key=lambda kv: (-int(kv[1]), kv[0])
    )[0]


def init() -> None:
    jsonl_path = find_session_jsonl()
    if not jsonl_path:
        write_stats(empty_stats())
        write_cursor("", 0)
        write_usage_index({})
        return

    offset = jsonl_path.stat().st_size
    write_cursor(str(jsonl_path), offset)
    write_stats(empty_stats())
    write_usage_index({})


def update() -> None:
    jsonl_path_raw, offset = read_cursor()
    jsonl_path = Path(jsonl_path_raw) if jsonl_path_raw else None

    if jsonl_path is None or not jsonl_path_raw:
        jsonl_path = find_session_jsonl()
        if jsonl_path is None:
            return
        offset = 0
        write_cursor(str(jsonl_path), offset)

    if not jsonl_path.is_file():
        return

    file_size = jsonl_path.stat().st_size
    if file_size < offset:
        offset = 0
    elif file_size == offset:
        stats = read_stats()
        if stats["total"] == 0:
            newer = find_session_jsonl()
            if newer is not None and newer != jsonl_path:
                jsonl_path = newer
                offset = 0
                write_cursor(str(jsonl_path), offset)
            else:
                return
        else:
            return

    stats = read_stats()
    usage_index = read_usage_index()
    index_changed = False

    with jsonl_path.open("r", encoding="utf-8", errors="ignore") as handle:
        handle.seek(offset)
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            for source in iter_usage_sources(event):
                usage = extract_usage(source)
                if not usage:
                    continue

                current_snapshot = build_usage_snapshot(source, usage)
                if current_snapshot["total"] <= 0:
                    continue

                usage_id = usage_identity(source)
                previous_snapshot = usage_index.get(usage_id)
                if add_usage_delta(stats, previous_snapshot, current_snapshot):
                    usage_index[usage_id] = current_snapshot
                    index_changed = True
                elif usage_id not in usage_index:
                    usage_index[usage_id] = current_snapshot
                    index_changed = True

        new_offset = handle.tell()

    finalize_model_prevalent(stats)
    stats["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    stats["cost_eur"] = round(float(stats.get("cost_eur", 0.0)), 6)
    write_stats(stats)
    write_cursor(str(jsonl_path), new_offset)
    if index_changed:
        write_usage_index(usage_index)


def flush() -> None:
    update()
    print(json.dumps(read_stats(), separators=(",", ":"), sort_keys=True))


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else "update"
    if command == "init":
        init()
    elif command == "flush":
        flush()
    else:
        update()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
