# Task 03 — Test red: Criterion 5 KG-unavailable propagation

**Goal:** Aggiungere 3 test fallenti che asseriscono che `mcp_invoker_from_json_file` propaga il field `_kg_status="unavailable"` quando `describe_service.error` o `service_health.error` sono presenti, e che `lookup_criticality` ritorna `REQUIRES_INPUT` in quel caso.

## File coinvolti

- Modifica: `tests/test_release_risk_kg_lookup.py` (aggiungi 3 test + import)

## Step TDD

### Step 1 — Aggiungi test in `tests/test_release_risk_kg_lookup.py`

Append a fondo file (assicurati l'import `mcp_invoker_from_json_file` sia presente — se non c'è, aggiungilo):

```python
import json
from pathlib import Path
from lib.release_risk.kg_lookup import mcp_invoker_from_json_file


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
```

### Step 2 — Verifica che i 3 test FALLISCANO

Run:
```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge" && \
source .venv-analytics/bin/activate && \
pytest tests/test_release_risk_kg_lookup.py::test_invoker_propagates_kg_status_unavailable_on_describe_error \
       tests/test_release_risk_kg_lookup.py::test_lookup_returns_requires_input_on_kg_unavailable \
       tests/test_release_risk_kg_lookup.py::test_lookup_returns_requires_input_on_es_unreachable \
       -v
```

Output atteso (RED):
```
FAILED ... test_invoker_propagates_kg_status_unavailable_on_describe_error - AssertionError: result.get('_kg_status') == None != 'unavailable'
FAILED ... test_lookup_returns_requires_input_on_kg_unavailable - AssertionError: r.status == 'NO' != 'REQUIRES_INPUT'
FAILED ... test_lookup_returns_requires_input_on_es_unreachable - AssertionError: r.status == 'NO' != 'REQUIRES_INPUT'
```

### Step 3 — Commit (NO implementazione ancora)

```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge" && \
git add tests/test_release_risk_kg_lookup.py && \
git commit -m "test(release-risk): red tests for c5 kg-unavailable propagation

- mcp_invoker_from_json_file must propagate _kg_status='unavailable' on error
- lookup_criticality must return REQUIRES_INPUT on _kg_status='unavailable'
- Cover both describe_service.error and service_health.error (VPN down)

Refs: docs/plans/2026-05-16-release-risk-silent-no-fix-design.md"
```

## Criteri di accettazione

- [ ] 3 nuovi test aggiunti
- [ ] Comando pytest mostra 3 FAILED (red)
- [ ] Commit creato con messaggio `test(release-risk):`
- [ ] Nessuna modifica a `lib/release_risk/kg_lookup.py`
