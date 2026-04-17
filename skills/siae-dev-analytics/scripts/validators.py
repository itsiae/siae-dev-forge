"""Pydantic v2 config models per siae-dev-analytics v2.

Modelli:
    ScopeConfigV2       -- repos (owner/name), teams, topics
    TimeWindowSingle    -- from/to ISO date (v1 compat)
    TimeWindowDual      -- baseline + current (v2 AI Impact)
    DevelopersConfigV2  -- include/exclude
    OptionsConfigV2     -- tutti i campi v2
    OutputConfigV2      -- format + path
    AnalyticsConfigV2   -- root config (version 1|2)

Runtime invariants:
    assert_rate_in_range  -- 0 <= x <= 1
    assert_finite         -- not NaN/inf
"""
from __future__ import annotations

import math
import re
from typing import Dict, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ────────────────────────────────────────────────────────
# Scope
# ────────────────────────────────────────────────────────

_REPO_RE = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")


class ScopeConfigV2(BaseModel):
    """Scope: almeno uno tra repos, teams, topics deve essere non-vuoto."""

    repos: list[str] = Field(default_factory=list)
    teams: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)

    @field_validator("repos", mode="after")
    @classmethod
    def _validate_repo_format(cls, v: list[str]) -> list[str]:
        for repo in v:
            if not _REPO_RE.match(repo):
                raise ValueError(
                    f"Usa il formato owner/name per il repo '{repo}' "
                    f"(es. itsiae/my-service)"
                )
        return v


# ────────────────────────────────────────────────────────
# Time windows
# ────────────────────────────────────────────────────────

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class TimeWindowSingle(BaseModel):
    """Finestra temporale singola (v1 compatibile)."""

    model_config = ConfigDict(populate_by_name=True)

    from_: str = Field(alias="from")
    to: str

    @field_validator("from_", "to", mode="after")
    @classmethod
    def _validate_iso_date(cls, v: str) -> str:
        if not _ISO_DATE_RE.match(v):
            raise ValueError(
                f"Usa il formato ISO YYYY-MM-DD per la data '{v}' "
                f"(es. 2026-01-15)"
            )
        return v

    @model_validator(mode="after")
    def _validate_to_gte_from(self) -> TimeWindowSingle:
        if self.from_ and self.to and self.to < self.from_:
            raise ValueError(
                f"Verifica che 'to' sia >= 'from': "
                f"from={self.from_}, to={self.to}"
            )
        return self


class TimeWindowDual(BaseModel):
    """Finestra duale baseline + current per AI Impact comparison."""

    baseline: TimeWindowSingle
    current: TimeWindowSingle
    enable_ai_impact: bool = False

    @model_validator(mode="after")
    def _validate_no_overlap(self) -> TimeWindowDual:
        if self.baseline.to >= self.current.from_:
            raise ValueError(
                f"Configura baseline.to < current.from per evitare overlap: "
                f"baseline.to={self.baseline.to}, current.from={self.current.from_}"
            )
        return self


# ────────────────────────────────────────────────────────
# Developers
# ────────────────────────────────────────────────────────

class DevelopersConfigV2(BaseModel):
    """Filtro include/exclude sviluppatori."""

    include: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)


# ────────────────────────────────────────────────────────
# Options
# ────────────────────────────────────────────────────────

class OptionsConfigV2(BaseModel):
    """Opzioni di configurazione v2 con tutti i campi."""

    anonymize: bool = False
    min_commits_threshold: int = Field(default=5, ge=0)
    parallel_fetch: int = Field(default=4, ge=1, le=16)
    enable_branch_tracking: bool = False
    enable_review_tracking: bool = False
    enable_ai_impact: bool = False
    enable_cost_metrics: bool = False
    anthropic_org_id: Optional[str] = None
    cost_per_dev_override: Dict[str, float] = Field(default_factory=dict)


# ────────────────────────────────────────────────────────
# Output
# ────────────────────────────────────────────────────────

class OutputConfigV2(BaseModel):
    """Configurazione output: formato e percorso."""

    format: Literal["xlsx", "csv", "both"] = "xlsx"
    path: str = "./devforge-analytics-report.xlsx"


# ────────────────────────────────────────────────────────
# Root config
# ────────────────────────────────────────────────────────

class AnalyticsConfigV2(BaseModel):
    """Root config v2. Supporta sia TimeWindowSingle (v1) che TimeWindowDual (v2)."""

    version: Literal[1, 2] = 2
    scope: ScopeConfigV2
    time_window: Union[TimeWindowSingle, TimeWindowDual]
    developers: DevelopersConfigV2 = Field(default_factory=DevelopersConfigV2)
    options: OptionsConfigV2 = Field(default_factory=OptionsConfigV2)
    output: OutputConfigV2 = Field(default_factory=OutputConfigV2)

    @model_validator(mode="after")
    def _validate_scope_not_empty(self) -> AnalyticsConfigV2:
        if not (self.scope.repos or self.scope.teams or self.scope.topics):
            raise ValueError(
                "Configura almeno uno tra repos, teams, topics nello scope "
                "(es. repos: ['itsiae/my-service'])"
            )
        return self


# ────────────────────────────────────────────────────────
# Runtime invariants
# ────────────────────────────────────────────────────────

def assert_rate_in_range(value: float, name: str) -> None:
    """Verifica che un rate sia compreso tra 0 e 1 (inclusi).

    Raises ValueError con messaggio actionable se fuori range.
    """
    if not (0.0 <= value <= 1.0):
        raise ValueError(
            f"Verifica che {name} sia compreso tra 0 e 1: "
            f"valore attuale {value}"
        )


def assert_finite(value: float, name: str) -> None:
    """Verifica che un valore sia finito (non NaN, non inf).

    Raises ValueError con messaggio actionable se NaN o infinito.
    """
    if math.isnan(value) or math.isinf(value):
        raise ValueError(
            f"Verifica che {name} sia un numero finito: "
            f"valore attuale {value}"
        )
