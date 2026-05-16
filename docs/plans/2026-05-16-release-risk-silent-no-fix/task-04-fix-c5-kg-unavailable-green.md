# Task 04 — Fix green: `mcp_invoker_from_json_file` + `lookup_criticality`

**Goal:** Implementare il fix che porta a verde i 3 test del task 03 senza rompere i 134 test esistenti.

## File coinvolti

- Modifica: `lib/release_risk/kg_lookup.py` (funzioni `mcp_invoker_from_json_file` + `lookup_criticality`)

## Step TDD

### Step 1 — Modifica `lib/release_risk/kg_lookup.py` righe 96-129 (`mcp_invoker_from_json_file`)

Sostituisci la chiusura `invoker` con la versione che propaga `_kg_status`:

```python
def mcp_invoker_from_json_file(kg_data_path: Optional[Path]):
    """Construct mcp_invoker callable from a JSON file pre-populated by SKILL.md.

    JSON schema:
    {
      "service_name": "sport-x-service",
      "describe_service": { ...output di mcp__sport-kg__describe_service... },
      "service_health": { ...output di mcp__sport-kg__service_health... }
    }

    Returns None se file non esiste (CLI degraderà a TOOL_UNAVAILABLE).

    Se describe_service o service_health contengono field 'error' (es. service
    not found, VPN down, ES unreachable), il dict propagato contiene
    _kg_status='unavailable' invece di valori normalizzati a zero — evita
    silent-NO in lookup_criticality.
    """
    if not kg_data_path or not kg_data_path.exists():
        return None
    try:
        data = json.loads(kg_data_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    def invoker(name: str) -> Optional[dict]:
        if data.get("service_name") != name:
            return None
        ds = data.get("describe_service") or {}
        sh = data.get("service_health") or {}
        # Propaga error esplicito invece di normalizzare zeri (anti silent-NO)
        ds_error = ds.get("error")
        sh_error = sh.get("error")
        if ds_error or sh_error:
            return {
                "_kg_status": "unavailable",
                "_kg_error": ds_error or sh_error,
            }
        return {
            "service_name": name,
            "has_payment_chain": ds.get("has_payment_chain", False),
            "auth_chain_length": ds.get("auth_chain_length", 0),
            "traffic_rps_p95": sh.get("traffic_rps_p95", 0),
            "drools_rules_count": ds.get("drools_rules_count", 0),
            "called_by_count": ds.get("called_by_count", 0),
        }
    return invoker
```

### Step 2 — Modifica `lookup_criticality` righe 72-93

Inserisci dopo `kg_data = mcp_invoker(service_name)` (riga 73) e PRIMA del check `if not kg_data` (riga 80), un nuovo branch:

```python
    try:
        kg_data = mcp_invoker(service_name)
    except (subprocess.TimeoutExpired, Exception) as e:
        return CriterionResult(
            id=5, name="Critical service", status="TOOL_UNAVAILABLE", weight=3,
            evidence=[f"mcp_error: {type(e).__name__}"], source="mcp:sport-kg",
        )

    # NEW: propagazione _kg_status="unavailable" da JSON prefetch (anti silent-NO)
    if kg_data and kg_data.get("_kg_status") == "unavailable":
        return CriterionResult(
            id=5, name="Critical service", status="REQUIRES_INPUT", weight=3,
            evidence=[f"kg_unavailable: {kg_data.get('_kg_error', 'unknown')}"],
            source="mcp:sport-kg",
        )

    if not kg_data:
        return CriterionResult(
            id=5, name="Critical service", status="REQUIRES_INPUT", weight=3,
            evidence=["service not found in KG"], source="mcp:sport-kg",
        )

    crit = derive_criticality_from_kg(kg_data, service_name)
    # ... resto invariato
```

### Step 3 — Verifica RED → GREEN

Run:
```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge" && \
source .venv-analytics/bin/activate && \
pytest tests/test_release_risk_kg_lookup.py -v 2>&1 | tail -20
```

Output atteso:
```
test_invoker_propagates_kg_status_unavailable_on_describe_error PASSED
test_lookup_returns_requires_input_on_kg_unavailable PASSED
test_lookup_returns_requires_input_on_es_unreachable PASSED
====== N passed in X.YZs ======
```

### Step 4 — Full regression

```bash
pytest tests/test_release_risk_ -v 2>&1 | tail -10
```

Output atteso: tutti i 134+7 = 141 test PASS (assumendo tasks 01-02 già completati).

### Step 5 — Commit

```bash
git add lib/release_risk/kg_lookup.py && \
git commit -m "fix(release-risk): c5 propagates REQUIRES_INPUT on KG unavailable

- mcp_invoker_from_json_file emits _kg_status='unavailable' when
  describe_service.error or service_health.error present
- lookup_criticality maps _kg_status='unavailable' to REQUIRES_INPUT
- Closes silent-NO on KG miss (e.g., service not in graph) and VPN down

Refs: docs/plans/2026-05-16-release-risk-silent-no-fix-design.md"
```

## Criteri di accettazione

- [ ] I 3 test del task 03 passano (GREEN)
- [ ] Tutti i test pre-esistenti continuano a passare (no regression)
- [ ] `_kg_status` field documentato in docstring di `mcp_invoker_from_json_file`
- [ ] Commit con messaggio `fix(release-risk):`
