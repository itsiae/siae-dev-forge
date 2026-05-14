"""Schema dataclass per lib/release_risk.

Type-safe via Literal. Schema v1 (questo PR).
Forward-compat via _safe_kwargs pattern (vedi lib/review_evidence/schema.py).
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional, Literal
import json

SCHEMA_VERSION = "1.0"

CriterionStatus = Literal["YES", "NO", "REQUIRES_INPUT", "TOOL_UNAVAILABLE"]
Level = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
Decision = Literal["GO", "GO_WITH_MONITORING", "POSTPONE_WITHOUT_TL", "NO_GO_WITHOUT_CAB"]
TriggerSource = Literal["pr-open", "manual", "cli"]


@dataclass
class CriterionResult:
    id: int  # 1..18
    name: str
    status: CriterionStatus
    weight: int  # +3, +2, +1, -1
    evidence: list[str] = field(default_factory=list)
    source: str = "unknown"  # "diff:grep", "mcp:sport-kg", "evidence:coverage", ...
    notes: Optional[str] = None


@dataclass
class ScoreCard:
    total_score: int  # 0..36
    level: Level
    decision: Decision
    decision_rationale: str
    suggested_followups: list[str] = field(default_factory=list)
    partial: bool = False


@dataclass
class GenesisInfo:
    merge_commits: list[dict] = field(default_factory=list)
    user_confirmed: Optional[list[str]] = None
    unexpected: Optional[list[str]] = None
    anomaly: Optional[bool] = None
    declined: bool = False
    no_merges_found: bool = False


@dataclass
class ReleaseRiskReport:
    service: str
    release_branch: str
    target_branch: str  # "main"
    diff_hash: str
    baseline_main_sha: Optional[str]
    diff_summary: dict
    identification: dict
    genesis: GenesisInfo
    criteria: list[CriterionResult]
    scorecard: ScoreCard
    generated_at: str  # ISO8601
    output_path: str
    cached: bool = False
    trigger: TriggerSource = "manual"
    schema_version: str = SCHEMA_VERSION

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, default=str)

    @classmethod
    def from_json(cls, data: str) -> "ReleaseRiskReport":
        d = json.loads(data)
        d["genesis"] = GenesisInfo(**d["genesis"])
        d["criteria"] = [CriterionResult(**c) for c in d["criteria"]]
        d["scorecard"] = ScoreCard(**d["scorecard"])
        return cls(**d)
