# Task 12 — kg_lookup.py (MCP sport-kg + heuristic) — Criterion 5

**Stato:** [PENDING]
**SP:** 2 Human / 1 Augmented
**Dipendenze:** task-04 (schema), task-01 (verifica MCP)

## Goal

Implementare `lib/release_risk/kg_lookup.py` con detection automatica criticality servizio via MCP sport-kg + fallback AskUserQuestion. Heuristic 6 condizioni come da design ADR-2.

## File coinvolti

- Create: `lib/release_risk/kg_lookup.py`

## Step

### Step 1 — Scrivi kg_lookup.py

Write `lib/release_risk/kg_lookup.py`:
```python
"""Criterion 5: Critical service detection via MCP sport-kg + fallback ask user."""
import os
import subprocess
import json
from pathlib import Path
from typing import Optional
from lib.release_risk.schema import CriterionResult

KG_PREFIXES = [
    # Allineato a design ADR-2 (single source of truth dei prefix SIAE mappati nel KG)
    "sport-",                       # cattura sport-*-service, sport-gestione-*, sport-*-drools
    "pop-",                         # pop-*-service, pop-be
    "pae-",
    "ciam-",
    "dol-be",
    "digital-channels-sport-",
    "esb-sport-",
    "esb-sso-",
    "mag-concertini-",
    "portal-apigateway-",
    "ttpp-",                        # ttpp-*-bff-service
]

# Env-overridable timeout per MCP lookup
KG_TIMEOUT_SEC = int(os.environ.get("DEVFORGE_RELEASE_RISK_KG_TIMEOUT_SEC", "5"))


def service_matches_kg(service_name: str) -> bool:
    """True se service_name matcha uno dei prefix mappati nel KG."""
    return any(service_name.lower().startswith(p) for p in KG_PREFIXES)


def derive_criticality_from_kg(kg_data: dict, service_name: str) -> str:
    """Returns YES/NO/UNKNOWN. Heuristic 6 condizioni (design ADR-2)."""
    if kg_data.get("has_payment_chain"): return "YES"
    if kg_data.get("auth_chain_length", 0) >= 3: return "YES"
    if "ciam" in service_name.lower(): return "YES"
    if kg_data.get("traffic_rps_p95", 0) > 100: return "YES"
    if kg_data.get("drools_rules_count", 0) > 5: return "YES"
    if (kg_data.get("called_by_count", 0) >= 3 and
        kg_data.get("traffic_rps_p95", 0) > 10):
        return "YES"
    return "NO"


def lookup_criticality(service_name: str, mcp_invoker=None) -> CriterionResult:
    """Criterion 5 main entry.

    Args:
        service_name: nome del repo (es. "sport-gestione-licenze-service")
        mcp_invoker: callable opzionale che invoca describe_service.
                     Signature: (name: str) -> Optional[dict]. Iniettabile per test.

    Returns:
        CriterionResult con weight=3.
    """
    if not service_matches_kg(service_name):
        return CriterionResult(
            id=5, name="Critical service", status="REQUIRES_INPUT", weight=3,
            evidence=[f"service '{service_name}' not in KG prefix list"],
            source="ask:user",
        )

    if mcp_invoker is None:
        return CriterionResult(
            id=5, name="Critical service", status="TOOL_UNAVAILABLE", weight=3,
            evidence=["mcp_invoker not provided"], source="mcp:sport-kg",
        )

    try:
        kg_data = mcp_invoker(service_name)
    except (subprocess.TimeoutExpired, Exception) as e:
        return CriterionResult(
            id=5, name="Critical service", status="TOOL_UNAVAILABLE", weight=3,
            evidence=[f"mcp_error: {type(e).__name__}"], source="mcp:sport-kg",
        )

    if not kg_data:
        return CriterionResult(
            id=5, name="Critical service", status="REQUIRES_INPUT", weight=3,
            evidence=["service not found in KG"], source="mcp:sport-kg",
        )

    crit = derive_criticality_from_kg(kg_data, service_name)
    return CriterionResult(
        id=5, name="Critical service", status=crit, weight=3,
        evidence=[f"heuristic_match={crit}",
                  f"traffic_rps_p95={kg_data.get('traffic_rps_p95', 0)}",
                  f"auth_chain_length={kg_data.get('auth_chain_length', 0)}"],
        source="mcp:sport-kg",
    )
```

### Step 2 — Verifica

Run:
```bash
python3 -c "from lib.release_risk.kg_lookup import lookup_criticality, service_matches_kg, derive_criticality_from_kg; print(service_matches_kg('sport-gestione-licenze-service'))"
```
Output atteso: `True`

### Step 3 — Commit

```bash
git add lib/release_risk/kg_lookup.py
git commit -m "feat(release-risk): kg_lookup criticality via MCP sport-kg + heuristic 6-condizioni"
```

## Criteri di accettazione

- [ ] 3 funzioni: `service_matches_kg`, `derive_criticality_from_kg`, `lookup_criticality`
- [ ] Heuristic 6-condizioni implementata
- [ ] `mcp_invoker` injectable per test
- [ ] Timeout + exception → TOOL_UNAVAILABLE
- [ ] Service non in prefix → REQUIRES_INPUT
- [ ] Commit eseguito
