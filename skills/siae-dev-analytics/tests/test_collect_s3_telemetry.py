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
