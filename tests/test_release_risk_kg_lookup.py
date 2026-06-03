import subprocess
from lib.release_risk.kg_lookup import (
    lookup_criticality, service_matches_kg, derive_criticality_from_kg,
)


def test_service_matches_kg_positive():
    assert service_matches_kg("sport-gestione-licenze-service")
    assert service_matches_kg("pop-be")
    assert service_matches_kg("ciam-auth-service")


def test_service_not_matches_kg():
    assert not service_matches_kg("random-other-service")
    assert not service_matches_kg("siae-dev-forge")


def test_heuristic_payment_chain():
    assert derive_criticality_from_kg({"has_payment_chain": True}, "sport-x") == "YES"


def test_heuristic_auth_chain():
    assert derive_criticality_from_kg({"auth_chain_length": 4}, "sport-x") == "YES"


def test_heuristic_ciam_name():
    assert derive_criticality_from_kg({}, "ciam-auth-service") == "YES"


def test_heuristic_traffic_high():
    assert derive_criticality_from_kg({"traffic_rps_p95": 150}, "sport-x") == "YES"


def test_heuristic_drools_heavy():
    assert derive_criticality_from_kg({"drools_rules_count": 10}, "sport-x") == "YES"


def test_heuristic_weak_signals_combinatorial():
    # called_by >= 3 AND traffic > 10 → YES
    assert derive_criticality_from_kg(
        {"called_by_count": 5, "traffic_rps_p95": 20}, "sport-x"
    ) == "YES"


def test_heuristic_no_criticality():
    assert derive_criticality_from_kg(
        {"traffic_rps_p95": 5, "called_by_count": 1}, "sport-low-traffic"
    ) == "NO"


def test_lookup_service_not_in_prefix():
    r = lookup_criticality("siae-dev-forge")
    assert r.status == "REQUIRES_INPUT"
    assert "not in KG prefix" in r.evidence[0]


def test_lookup_no_mcp_invoker():
    r = lookup_criticality("sport-x-service")
    assert r.status == "TOOL_UNAVAILABLE"


def test_lookup_mcp_returns_critical():
    def fake_mcp(name):
        return {"has_payment_chain": True, "traffic_rps_p95": 200}
    r = lookup_criticality("sport-payment-service", mcp_invoker=fake_mcp)
    assert r.status == "YES"
    assert r.weight == 3
    assert "heuristic_match=YES" in r.evidence


def test_lookup_mcp_timeout():
    def fake_mcp_timeout(name):
        raise subprocess.TimeoutExpired(cmd="mcp", timeout=5)
    r = lookup_criticality("sport-x-service", mcp_invoker=fake_mcp_timeout)
    assert r.status == "TOOL_UNAVAILABLE"
    assert "TimeoutExpired" in r.evidence[0]


def test_lookup_mcp_empty_result():
    def fake_mcp_empty(name):
        return None
    r = lookup_criticality("sport-x-service", mcp_invoker=fake_mcp_empty)
    assert r.status == "REQUIRES_INPUT"
    assert "not found in KG" in r.evidence[0]


# Task-12b: bridge MCP → CLI via JSON prefetch file
import json
from lib.release_risk.kg_lookup import mcp_invoker_from_json_file


def test_invoker_from_json_file_hit(tmp_path):
    p = tmp_path / "kg.json"
    p.write_text(json.dumps({
        "service_name": "sport-x-service",
        "describe_service": {"has_payment_chain": True, "auth_chain_length": 4},
        "service_health": {"traffic_rps_p95": 200},
    }))
    invoker = mcp_invoker_from_json_file(p)
    result = invoker("sport-x-service")
    assert result["has_payment_chain"] is True
    assert result["auth_chain_length"] == 4
    assert result["traffic_rps_p95"] == 200


def test_invoker_from_json_file_name_mismatch(tmp_path):
    p = tmp_path / "kg.json"
    p.write_text(json.dumps({"service_name": "other", "describe_service": {}}))
    invoker = mcp_invoker_from_json_file(p)
    assert invoker("sport-x-service") is None


def test_invoker_from_missing_file(tmp_path):
    p = tmp_path / "nonexistent.json"
    assert mcp_invoker_from_json_file(p) is None


def test_invoker_from_corrupted_json(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("not valid {{{")
    assert mcp_invoker_from_json_file(p) is None


# Task-03: Criterion 5 KG-unavailable propagation (RED tests)
def test_invoker_propagates_kg_status_unavailable_on_describe_error(tmp_path):
    """JSON prefetch con describe_service.error -> invoker ritorna _kg_status=unavailable."""
    payload = {
        "service_name": "pae-deposito-musica-fe",
        "describe_service": {"error": "Service 'pae-deposito-musica-fe' not found"},
        "service_health": {"status": "CRITICO"},
    }
    p = tmp_path / "kg.json"
    p.write_text(json.dumps(payload))
    invoker = mcp_invoker_from_json_file(p)
    assert invoker is not None
    result = invoker("pae-deposito-musica-fe")
    assert result is not None
    assert result.get("_kg_status") == "unavailable"
    assert "not found" in (result.get("_kg_error") or "")


def test_lookup_returns_requires_input_on_kg_unavailable(tmp_path):
    """lookup_criticality con invoker che ritorna _kg_status=unavailable → REQUIRES_INPUT."""
    payload = {
        "service_name": "pae-x",
        "describe_service": {"error": "Service not found"},
        "service_health": {},
    }
    p = tmp_path / "kg.json"
    p.write_text(json.dumps(payload))
    invoker = mcp_invoker_from_json_file(p)
    r = lookup_criticality("pae-x", mcp_invoker=invoker)
    assert r.status == "REQUIRES_INPUT"
    assert r.weight == 3
    assert "kg_unavailable" in r.evidence[0]


def test_lookup_returns_requires_input_on_es_unreachable(tmp_path):
    """VPN down → service_health.error present → REQUIRES_INPUT (non NO da zeri)."""
    payload = {
        "service_name": "sport-x-service",
        "describe_service": {"has_payment_chain": False, "auth_chain_length": 0},
        "service_health": {"error": "ES non raggiungibile — VPN non attiva", "sample_size": 0},
    }
    p = tmp_path / "kg.json"
    p.write_text(json.dumps(payload))
    invoker = mcp_invoker_from_json_file(p)
    r = lookup_criticality("sport-x-service", mcp_invoker=invoker)
    assert r.status == "REQUIRES_INPUT", f"Expected REQUIRES_INPUT on ES unreachable, got {r.status}"
    assert "kg_unavailable" in r.evidence[0]
