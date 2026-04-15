"""Optional S3 telemetry reader for DevForge events + blend usage.

Graceful degrade: se creds AWS mancanti o bucket vuoto → ritorna [] / {}.
"""
from __future__ import annotations

import json
import logging
import statistics
from collections import defaultdict
from datetime import datetime

log = logging.getLogger(__name__)

BUCKET = "siae-devforge-telemetry"
DEVFORGE_PREFIX = "devforge-logs/"
BLEND_PREFIX = "blend-usage/"


def _s3_client():
    """Lazy boto3 client. Raises on any error."""
    import boto3  # noqa: lazy import
    return boto3.client("s3")


def _list_objects(prefix: str, since: str, until: str) -> list[str]:
    """Lista key in bucket/prefix (best-effort, filtra per data nel path)."""
    try:
        s3 = _s3_client()
    except Exception as e:
        log.warning("S3 client unavailable: %s", e)
        return []

    try:
        resp = s3.list_objects_v2(Bucket=BUCKET, Prefix=prefix)
    except Exception as e:
        log.warning("S3 list_objects_v2 failed: %s", e)
        return []

    keys = [obj["Key"] for obj in resp.get("Contents", [])]
    # Filtro opzionale sul path per evitare fetch inutili (assume YYYY/MM/DD nel path)
    since_dt = datetime.fromisoformat(since).date()
    until_dt = datetime.fromisoformat(until).date() if until != "today" else datetime.today().date()

    filtered = []
    for k in keys:
        # Best-effort date extraction (fallback: include all)
        date_parts = [p for p in k.split("/") if p.isdigit()]
        if len(date_parts) >= 3:
            try:
                key_date = datetime(int(date_parts[0]), int(date_parts[1]), int(date_parts[2])).date()
                if since_dt <= key_date <= until_dt:
                    filtered.append(k)
                continue
            except Exception:
                pass
        filtered.append(k)
    return filtered


def fetch_devforge_logs(since: str, until: str) -> list[dict]:
    """Fetch devforge-logs events dal S3. Empty list se S3 non disponibile."""
    keys = _list_objects(DEVFORGE_PREFIX, since, until)
    if not keys:
        return []

    try:
        s3 = _s3_client()
    except Exception:
        return []

    events = []
    for key in keys:
        try:
            body = s3.get_object(Bucket=BUCKET, Key=key)["Body"].read().decode()
            for line in body.splitlines():
                if line.strip():
                    events.append(json.loads(line))
        except Exception as e:
            log.warning("failed to read %s: %s", key, e)
    return events


def fetch_blend_usage(since: str, until: str) -> dict[str, float]:
    """Fetch blend-usage cost per dev. Dict {dev: total_eur}."""
    keys = _list_objects(BLEND_PREFIX, since, until)
    if not keys:
        return {}

    try:
        s3 = _s3_client()
    except Exception:
        return {}

    costs: dict[str, float] = defaultdict(float)
    for key in keys:
        try:
            body = s3.get_object(Bucket=BUCKET, Key=key)["Body"].read().decode()
            for line in body.splitlines():
                if not line.strip():
                    continue
                rec = json.loads(line)
                dev = rec.get("actor_canonical")
                if dev:
                    costs[dev] += float(rec.get("cost_eur", 0))
        except Exception as e:
            log.warning("failed to read %s: %s", key, e)
    return dict(costs)


def verification_rate_from_events(events: list[dict]) -> dict[str, float]:
    """Calcola verification_rate da eventi DevForge (superior accuracy vs git trailer)."""
    by_dev: dict[str, list[bool]] = defaultdict(list)
    for ev in events:
        if ev.get("event_type") != "commit_created":
            continue
        dev = ev.get("actor_canonical")
        if not dev:
            continue
        by_dev[dev].append(bool(ev.get("verified_by_siae_verification", False)))

    return {dev: sum(vs) / len(vs) for dev, vs in by_dev.items() if vs}


def normalize_cost_score(costs: dict[str, float]) -> dict[str, float]:
    """Normalizza cost EUR → cost_score moltiplicativo (≈1.0 = team median).

    Output: dict {dev: cost_score}.
    Se N<2 → cost_score = 1.0 per tutti.
    Formula: dev_spend / median_team_spend, clampato a [0.25, 4.0].
    """
    if not costs:
        return {}
    values = list(costs.values())
    if len(values) < 2:
        return {d: 1.0 for d in costs}

    med = statistics.median(values)
    if med == 0:
        return {d: 1.0 for d in costs}

    # Ratio vs median: 1.0 = median spender, >1 = above median, <1 = below
    # Clamp a [0.25, 4.0] per evitare esplosioni
    return {dev: max(0.25, min(4.0, v / med)) for dev, v in costs.items()}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", required=True)
    parser.add_argument("--until", default="today")
    args = parser.parse_args()

    events = fetch_devforge_logs(args.since, args.until)
    costs = fetch_blend_usage(args.since, args.until)
    print(json.dumps({
        "events_count": len(events),
        "devs_with_cost": len(costs),
        "total_cost_eur": sum(costs.values()),
    }, indent=2))
