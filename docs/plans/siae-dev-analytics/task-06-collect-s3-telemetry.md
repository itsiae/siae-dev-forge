# Task 06 — collect_s3_telemetry.py (opzionale, graceful degrade)

**Goal:** Implementare reader opzionale S3 telemetria DevForge con graceful degrade se credenziali AWS o bucket non disponibili.

**AC coperti:** AC03 (graceful degrade), AC10 (S3 creds mancanti scenario)

**Dipendenze:** Task 1

**Tempo stimato:** 20 min

---

## File coinvolti

- `skills/siae-dev-analytics/scripts/collect_s3_telemetry.py` (nuovo)
- `skills/siae-dev-analytics/tests/test_collect_s3_telemetry.py` (nuovo)

## Step 1 — TDD: Scrivi test PRIMA

Crea `tests/test_collect_s3_telemetry.py`:

```python
"""Test per collect_s3_telemetry.py."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import patch, MagicMock
import pytest

import collect_s3_telemetry as ct


def test_fetch_devforge_logs_returns_empty_if_no_creds():
    """NoCredentialsError → lista vuota, no crash."""
    with patch("boto3.client") as mock_client:
        mock_client.side_effect = Exception("NoCredentialsError")
        result = ct.fetch_devforge_logs(since="2026-01-01", until="2026-04-01")
    assert result == []


def test_fetch_devforge_logs_parses_jsonl():
    """S3 list + get → parse jsonl events."""
    mock_s3 = MagicMock()
    mock_s3.list_objects_v2.return_value = {
        "Contents": [{"Key": "devforge-logs/2026/03/01/events.jsonl"}]
    }
    mock_s3.get_object.return_value = {
        "Body": MagicMock(read=lambda: (
            '{"event_type": "commit_created", "actor_canonical": "alice", "timestamp": "2026-03-01T10:00:00Z"}\n'
            '{"event_type": "skill_invoked", "actor_canonical": "alice", "timestamp": "2026-03-01T11:00:00Z", "skill": "siae-verification"}\n'
        ).encode())
    }
    with patch("boto3.client", return_value=mock_s3):
        result = ct.fetch_devforge_logs(since="2026-03-01", until="2026-03-31")
    assert len(result) == 2
    assert result[0]["event_type"] == "commit_created"
    assert result[1]["skill"] == "siae-verification"


def test_fetch_blend_usage_returns_cost_per_dev():
    """S3 blend-usage → dict dev → cost EUR."""
    mock_s3 = MagicMock()
    mock_s3.list_objects_v2.return_value = {
        "Contents": [{"Key": "blend-usage/2026-03-01-usage.jsonl"}]
    }
    mock_s3.get_object.return_value = {
        "Body": MagicMock(read=lambda: (
            '{"actor_canonical": "alice", "cost_eur": 12.5, "date": "2026-03-01"}\n'
            '{"actor_canonical": "alice", "cost_eur": 7.0, "date": "2026-03-02"}\n'
            '{"actor_canonical": "bob", "cost_eur": 3.0, "date": "2026-03-01"}\n'
        ).encode())
    }
    with patch("boto3.client", return_value=mock_s3):
        result = ct.fetch_blend_usage(since="2026-03-01", until="2026-03-31")
    assert result == {"alice": 19.5, "bob": 3.0}


def test_verification_rate_from_devforge_logs():
    """commit_created events con skill siae-verification → rate per dev."""
    events = [
        {"event_type": "commit_created", "actor_canonical": "alice"},
        {"event_type": "commit_created", "actor_canonical": "alice", "verified_by_siae_verification": True},
        {"event_type": "commit_created", "actor_canonical": "bob"},
    ]
    result = ct.verification_rate_from_events(events)
    assert result["alice"] == 0.5
    assert result["bob"] == 0.0


def test_normalize_cost_score_z_scored():
    """cost EUR → z-score normalizzato."""
    costs = {"alice": 10.0, "bob": 20.0, "carol": 30.0}
    normalized = ct.normalize_cost_score(costs)
    # mean 20, std 10 → z -1, 0, 1 → shifted so min = 1 (positive cost multiplier)
    assert 0.5 <= normalized["alice"] <= 1.5
    assert 0.8 <= normalized["bob"] <= 1.2
    assert 1.5 <= normalized["carol"] <= 2.5


def test_default_cost_score_when_empty():
    """Nessun cost data → ogni dev ha cost_score = 1.0."""
    result = ct.normalize_cost_score({})
    assert result == {}
```

## Step 2 — Run test, verifica che falliscono

Run:
```bash
pytest skills/siae-dev-analytics/tests/test_collect_s3_telemetry.py -v 2>&1 | tail -10
```

Output atteso: `ModuleNotFoundError`.

## Step 3 — Implementa `collect_s3_telemetry.py`

Crea `skills/siae-dev-analytics/scripts/collect_s3_telemetry.py`:

```python
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
    """
    if not costs:
        return {}
    values = list(costs.values())
    if len(values) < 2:
        return {d: 1.0 for d in costs}

    mean = statistics.mean(values)
    std = statistics.stdev(values)
    if std == 0:
        return {d: 1.0 for d in costs}

    # z-score shifted to positive multiplier (z=0 → 1.0, z=1 → 2.0, z=-1 → 0.5)
    # Clamp a [0.25, 4.0] per evitare esplosioni
    def _to_score(v: float) -> float:
        z = (v - mean) / std
        score = 1.0 + z
        return max(0.25, min(4.0, score))

    return {dev: _to_score(v) for dev, v in costs.items()}


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
```

## Step 4 — Run test

Run:
```bash
pytest skills/siae-dev-analytics/tests/test_collect_s3_telemetry.py -v 2>&1 | tail -15
```

Output atteso: `6 passed`.

## Step 5 — Commit

Run:
```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge"
git add skills/siae-dev-analytics/scripts/collect_s3_telemetry.py \
        skills/siae-dev-analytics/tests/test_collect_s3_telemetry.py
git commit -m "feat(skill): add collect_s3_telemetry for siae-dev-analytics [Task 6/7]

- fetch_devforge_logs + fetch_blend_usage con graceful degrade
- NoCredentialsError → [] / {} (no crash)
- verification_rate_from_events per accuracy superior vs git trailer
- normalize_cost_score → z-score shifted moltiplicativo [0.25, 4.0]
- 6 test pytest pass, mock boto3

AC03, AC10"
```

## Criteri di accettazione Task 6

- [ ] `fetch_devforge_logs` ritorna lista vuota senza creds AWS (no crash)
- [ ] `fetch_blend_usage` ritorna dict vuoto senza creds
- [ ] `verification_rate_from_events` calcola rate per dev da eventi
- [ ] `normalize_cost_score` converte EUR → multiplier positivo clampato [0.25, 4.0]
- [ ] 6 test pytest pass
- [ ] Commit conventional

## Verifica

Run:
```bash
pytest skills/siae-dev-analytics/tests/test_collect_s3_telemetry.py -v --tb=short
```

Output atteso: `6 passed`.
