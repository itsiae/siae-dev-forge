# Task 10 — F4e ROI v2 + Pydantic Validators

**Goal:** ROI v2 formula + validators.py con Pydantic AnalyticsConfigV2 + runtime invariants.
**AC coperti:** ROI v2 §5.11, NF6-NF7 (validation boundaries)
**Dipendenze:** Task 01
**Effort:** ~30 min
**Test nuovi:** 15

## File coinvolti

- `scripts/validators.py` — AnalyticsConfigV2 Pydantic + invariant decorators
- `scripts/compute_kpis.py` — aggiungi `kpi_roi_v2_index`
- `tests/test_validators.py` — 15 test

## Step 1 — validators.py

```python
"""Pydantic models + runtime invariants per siae-dev-analytics v2."""
from __future__ import annotations
from datetime import date
from typing import Literal, Union
from pydantic import BaseModel, Field, field_validator, model_validator


class ScopeConfigV2(BaseModel):
    repos: list[str] = Field(default_factory=list)
    teams: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)

    @field_validator("repos")
    @classmethod
    def _repos_format(cls, v: list[str]) -> list[str]:
        for r in v:
            if "/" not in r:
                raise ValueError(f"repo '{r}' must be 'owner/name' format")
        return v


class TimeWindowSingle(BaseModel):
    from_: str = Field(alias="from")
    to: str = "today"

    class Config:
        populate_by_name = True

    @model_validator(mode="after")
    def _validate_dates(self) -> "TimeWindowSingle":
        try:
            f = date.fromisoformat(self.from_)
        except Exception as e:
            raise ValueError(f"Invalid 'from' date: {e}. Usa formato ISO 2026-01-01.")
        if self.to != "today":
            try:
                t = date.fromisoformat(self.to)
            except Exception as e:
                raise ValueError(f"Invalid 'to' date: {e}.")
            if t < f:
                raise ValueError("Verifica config: 'to' deve essere >= 'from'.")
        return self


class TimeWindowDual(BaseModel):
    baseline: TimeWindowSingle
    current: TimeWindowSingle
    enable_ai_impact: bool = True

    @model_validator(mode="after")
    def _no_overlap(self) -> "TimeWindowDual":
        b_end = date.fromisoformat(self.baseline.to) if self.baseline.to != "today" else date.today()
        c_start = date.fromisoformat(self.current.from_)
        if b_end >= c_start:
            raise ValueError(
                "Verifica config: baseline.to deve essere PRIMA di current.from_. "
                "Esempio: baseline 2026-01-01/2026-02-14, current 2026-02-15/today."
            )
        return self


class DevelopersConfigV2(BaseModel):
    include: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)


class OptionsConfigV2(BaseModel):
    anonymize: bool = False
    min_commits_threshold: int = Field(default=5, ge=0)
    parallel_fetch: int = Field(default=4, ge=1, le=16)
    enable_branch_tracking: bool = True
    enable_review_tracking: bool = True
    enable_ai_impact: bool = True
    enable_cost_metrics: bool = True
    anthropic_org_id: str | None = None
    cost_per_dev_override: dict[str, float] = Field(default_factory=dict)


class OutputConfigV2(BaseModel):
    format: Literal["xlsx", "csv", "both"] = "xlsx"
    path: str = "./devforge-analytics-report.xlsx"


class AnalyticsConfigV2(BaseModel):
    version: Literal[1, 2] = 2
    scope: ScopeConfigV2
    time_window: Union[TimeWindowSingle, TimeWindowDual]
    developers: DevelopersConfigV2 = Field(default_factory=DevelopersConfigV2)
    options: OptionsConfigV2 = Field(default_factory=OptionsConfigV2)
    output: OutputConfigV2 = Field(default_factory=OutputConfigV2)

    @model_validator(mode="after")
    def _scope_not_empty(self) -> "AnalyticsConfigV2":
        s = self.scope
        if not (s.repos or s.teams or s.topics):
            raise ValueError("Configura scope: definisci almeno uno tra repos, teams, topics.")
        return self


def assert_rate_in_range(value: float, name: str = "rate") -> None:
    """Runtime invariant: 0 <= value <= 1."""
    if not (0 <= value <= 1):
        raise ValueError(f"Invariant {name} violato: deve essere in [0,1], got {value}")


def assert_finite(value: float, name: str = "score") -> None:
    """Runtime invariant: finite (not NaN/inf)."""
    import math
    if not math.isfinite(value):
        raise ValueError(f"Invariant {name} violato: deve essere finite, got {value}")
```

## Step 2 — kpi_roi_v2_index

```python
def kpi_roi_v2_index(
    features_shipped: dict[str, int],
    complexity_weight_by_dev: dict[str, float],
    compliance_rate_by_dev: dict[str, float],
    cost_by_dev: dict[str, float],
    seasonality_adj: float,
) -> dict[str, float]:
    """roi_v2 = (features × complexity × compliance) / (cost × seasonality_adj)."""
    from validators import assert_finite
    result = {}
    if seasonality_adj <= 0:
        seasonality_adj = 1.0
    for dev in set(features_shipped) | set(cost_by_dev):
        feat = features_shipped.get(dev, 0)
        cw = complexity_weight_by_dev.get(dev, 1.0)
        cr = compliance_rate_by_dev.get(dev, 0.0)
        cost = cost_by_dev.get(dev, 1.0) or 1.0  # cost=1 fallback se 0
        value = feat * cw * cr
        roi = value / (cost * seasonality_adj)
        assert_finite(roi, f"roi_v2[{dev}]")
        result[dev] = roi
    return result
```

## Step 3 — Test (15)

```python
# Happy
def test_config_v2_single_window_valid(): ...
def test_config_v2_dual_window_valid(): ...
def test_config_v2_scope_repos_only(): ...

# Validazione
def test_config_v2_repo_format_rejects_no_slash(): ...  # "invalid" → ValueError
def test_config_v2_invalid_date_format(): ...
def test_config_v2_to_before_from(): ...
def test_config_v2_dual_overlap_rejected(): ...
def test_config_v2_empty_scope_rejected(): ...
def test_config_v2_parallel_fetch_out_of_range(): ...  # 0 or 17 → ValueError
def test_config_v2_format_invalid(): ...  # "pdf" → ValueError

# Invariants
def test_assert_rate_in_range_valid(): ...
def test_assert_rate_in_range_invalid(): ...
def test_assert_finite_nan_raises(): ...
def test_assert_finite_inf_raises(): ...

# ROI v2
def test_roi_v2_index_happy_path(): ...
def test_roi_v2_index_zero_cost_uses_fallback(): ...
def test_roi_v2_index_zero_seasonality_uses_fallback(): ...
```

## Verify

```bash
PYTHONPATH=skills/siae-dev-analytics/scripts python3 -m pytest skills/siae-dev-analytics/tests/test_validators.py -v
```

Output: `15 passed`.

## Criteri accettazione

- [ ] AnalyticsConfigV2 accetta sia v1 (single window) che v2 (dual window)
- [ ] Validator rifiuta: overlap, invalid date, no scope, invalid repo format
- [ ] Error messages actionable ≥20 char + verbo (Usa/Verifica/Configura)
- [ ] assert_rate_in_range + assert_finite invariants disponibili a altri moduli
- [ ] roi_v2_index protegge division by zero
