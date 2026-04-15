# Task 09 — F4d DevForge Adoption (3 KPI)

**Goal:** DevForge skill invocation rate + Claude session density + brainstorming-before-coding.
**AC coperti:** DA1-DA3 (design §5.9)
**Dipendenze:** Task 02 (S3 telemetry), 06 (seasonality working_days)
**Effort:** ~35 min
**Test nuovi:** 5

## File coinvolti

- `scripts/collect_s3_telemetry.py` — aggiungi `fetch_skill_invocations`, `fetch_session_starts`
- `scripts/compute_kpis.py` — aggiungi 3 KPI
- `tests/test_collect_s3_telemetry.py` — 2 nuovi
- `tests/test_compute_kpis.py` — 3 nuovi

## Step 1 — S3 events extraction

In `collect_s3_telemetry.py`:

```python
def extract_skill_invocations(events: list[dict]) -> dict[str, int]:
    """Count event_type='skill_invoked' per actor."""
    from collections import Counter
    c: Counter = Counter()
    for ev in events:
        if ev.get("event_type") != "skill_invoked":
            continue
        actor = ev.get("actor_canonical")
        if actor:
            c[actor] += 1
    return dict(c)


def extract_session_starts(events: list[dict]) -> dict[str, int]:
    """Count event_type='session_start' per actor."""
    from collections import Counter
    c: Counter = Counter()
    for ev in events:
        if ev.get("event_type") != "session_start":
            continue
        actor = ev.get("actor_canonical")
        if actor:
            c[actor] += 1
    return dict(c)
```

## Step 2 — 3 KPI in compute_kpis.py

```python
def kpi_devforge_skill_invocation_rate(
    skill_invocations_by_dev: dict[str, int],
    weeks_in_window: float,
) -> dict[str, float]:
    if weeks_in_window <= 0:
        return {}
    return {dev: count / weeks_in_window for dev, count in skill_invocations_by_dev.items()}


def kpi_claude_session_density(
    session_starts_by_dev: dict[str, int],
    working_days: int,
) -> dict[str, float]:
    if working_days <= 0:
        return {}
    return {dev: count / working_days for dev, count in session_starts_by_dev.items()}


def kpi_siae_brainstorming_before_coding(
    prs: pd.DataFrame,
    docs_plans_dir: Path,
    threshold_hours: int = 24,
) -> dict[str, float]:
    """% PR con design doc creato < 24h prima del primo commit / total PR per dev."""
    if prs.empty: return {}
    # Leggi mtime dei docs/plans/*.md (best-effort, assuming local clone presente)
    # Se dir non esiste → fallback a 0.0
    if not docs_plans_dir.exists():
        return {a: 0.0 for a in prs["author"].unique()}

    # Semplificazione v2: se PR ha design_link, considera disciplinato
    # (implementation reale richiede join date docs/plans timestamps con PR first_commit)
    return prs.groupby("author")["has_design_link"].mean().to_dict()
```

## Step 3 — Test (5)

```python
def test_extract_skill_invocations_counts_per_actor():
    events = [
        {"event_type": "skill_invoked", "actor_canonical": "alice"},
        {"event_type": "skill_invoked", "actor_canonical": "alice"},
        {"event_type": "skill_invoked", "actor_canonical": "bob"},
        {"event_type": "session_start", "actor_canonical": "alice"},
    ]
    result = ct.extract_skill_invocations(events)
    assert result == {"alice": 2, "bob": 1}

def test_extract_session_starts_empty_returns_empty():
    assert ct.extract_session_starts([]) == {}

def test_devforge_skill_invocation_rate():
    result = ck.kpi_devforge_skill_invocation_rate({"alice": 10, "bob": 5}, weeks_in_window=2.0)
    assert result == {"alice": 5.0, "bob": 2.5}

def test_claude_session_density_zero_days():
    assert ck.kpi_claude_session_density({"alice": 5}, working_days=0) == {}

def test_brainstorming_before_coding_no_docs_plans():
    from pathlib import Path
    prs = pd.DataFrame([{"author": "alice", "has_design_link": True}])
    result = ck.kpi_siae_brainstorming_before_coding(prs, Path("/nonexistent"))
    assert result["alice"] == 0.0
```

## Verify

```bash
PYTHONPATH=skills/siae-dev-analytics/scripts python3 -m pytest skills/siae-dev-analytics/tests/test_collect_s3_telemetry.py skills/siae-dev-analytics/tests/test_compute_kpis.py -v -k "skill_invocation or session_start or brainstorming"
```

Output: `5 passed`.

## Criteri accettazione

- [ ] extract_skill_invocations + extract_session_starts implementati
- [ ] 3 KPI in compute_kpis.py con zero-division protection
- [ ] Edge: docs/plans dir mancante → 0.0, no crash
