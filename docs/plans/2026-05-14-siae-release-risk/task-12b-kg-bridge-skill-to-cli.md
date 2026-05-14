# Task 12b — Bridge MCP sport-kg → CLI via JSON prefetch file

**Stato:** [PENDING]
**SP:** 1.5 Human / 0.75 Augmented
**Dipendenze:** task-12 (kg_lookup), task-13 (test file `tests/test_release_risk_kg_lookup.py` esistente — Step 4 di questo task aggiunge 4 test al file esistente)

## Goal

Risolvere il gap architetturale: `kg_lookup.py` accetta `mcp_invoker` callable iniettabile, ma il CLI Python non può chiamare direttamente MCP tools (sono disponibili solo via Claude Code sessione). Il bridge è: **SKILL.md prefetcha KG data via MCP tool e scrive JSON in `--kg-data-file`; CLI legge JSON e costruisce `mcp_invoker` lambda**.

Senza questo bridge, Criterion 5 ritorna sempre `TOOL_UNAVAILABLE` per repo KG-mappati (ADR-2 inesigibile su 80% repo SIAE).

## File coinvolti

- Edit: `lib/release_risk/kg_lookup.py` (factory function da JSON)
- Edit: `lib/release_risk/cli.py` (argparse `--kg-data-file` + load)
- Edit: `skills/siae-release-risk/SKILL.md` (Step 4c prefetch via MCP)

## Step

### Step 1 — Add factory in kg_lookup.py

Edit `lib/release_risk/kg_lookup.py` (append):
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
    """
    if not kg_data_path or not kg_data_path.exists():
        return None
    try:
        import json
        data = json.loads(kg_data_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    def invoker(name: str) -> Optional[dict]:
        if data.get("service_name") != name:
            return None
        ds = data.get("describe_service") or {}
        sh = data.get("service_health") or {}
        # Normalizza in dict piatto consumato da derive_criticality_from_kg
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

### Step 2 — Wire in cli.py

Edit `lib/release_risk/cli.py`:

(a) Aggiungi argparse arg:
```python
a.add_argument("--kg-data-file",
               help="Path to JSON pre-fetched MCP sport-kg output (see SKILL.md Step 4c)")
```

(b) In `assess()`, prima del Criterion 5:
```python
from lib.release_risk.kg_lookup import lookup_criticality, mcp_invoker_from_json_file
kg_data_path = Path(args.kg_data_file) if args.kg_data_file else None
mcp_invoker = mcp_invoker_from_json_file(kg_data_path)

# Cambia chiamata a Criterion 5:
criterion_5_critical_service_stub(
    service,
    kg_lookup_fn=lambda name: lookup_criticality(name, mcp_invoker=mcp_invoker),
),
```

### Step 3 — Aggiorna SKILL.md Step 4c prefetch

Edit `skills/siae-release-risk/SKILL.md` (inserisci nuovo Step 4c PRIMA dello Step 5 pre-flight card):

```markdown
### Step 4c — Prefetch KG data (se servizio mappato)  🟢 SICURO

Se `$SERVICE` matcha uno dei prefix KG (`sport-*|pop-*|pae-*|ciam-*|dol-be|digital-channels-sport-*|esb-sport-*|esb-sso-*|mag-concertini-*|portal-apigateway-*|ttpp-*`):

1. Invoca MCP tool `mcp__sport-kg__describe_service` con `service_name=$SERVICE` (timeout 5s)
2. Invoca MCP tool `mcp__sport-kg__service_health` con `service_name=$SERVICE` (timeout 5s)
3. Scrivi entrambi gli output in `/tmp/release-risk-kg-${SERVICE}.json`:
   ```json
   {
     "service_name": "...",
     "describe_service": {...},
     "service_health": {...}
   }
   ```
4. Passa `--kg-data-file /tmp/release-risk-kg-${SERVICE}.json` al CLI

Se MCP unavailable o timeout → skip prefetch (Criterion 5 fallback `REQUIRES_INPUT` con AskUserQuestion silent nel CLI).

Se `$SERVICE` non matcha prefix KG → skip Step 4c (Criterion 5 fallback `REQUIRES_INPUT`).
```

### Step 4 — Test bridge

Add test in `tests/test_release_risk_kg_lookup.py`:
```python
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
```

### Step 5 — Commit

```bash
git add lib/release_risk/kg_lookup.py lib/release_risk/cli.py \
        skills/siae-release-risk/SKILL.md tests/test_release_risk_kg_lookup.py
git commit -m "feat(release-risk): bridge MCP sport-kg → CLI via JSON prefetch (resolve ADR-2)"
```

## Criteri di accettazione

- [ ] Factory `mcp_invoker_from_json_file` in kg_lookup.py funzionante
- [ ] CLI arg `--kg-data-file` wired
- [ ] SKILL.md Step 4c documenta prefetch sequence
- [ ] 4 test addizionali in test_release_risk_kg_lookup.py PASS
- [ ] Criterion 5 ritorna `YES`/`NO` (non `TOOL_UNAVAILABLE`) quando `--kg-data-file` provided con dati validi
- [ ] Fallback graceful: missing file / corrupted / name mismatch → invoker None
- [ ] Commit eseguito

## Note ADR

Questo task chiude **BLOCK-1 plan-review iter 1**: ADR-2 (MCP sport-kg lookup) richiede un meccanismo runtime per passare i tool MCP — disponibili solo nella sessione Claude Code, non in subprocess Python — al CLI. Bridge via JSON prefetch è il pattern più semplice e zero-coupling.
