from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


World = Literal["python", "turtle", "netbrick"]
MomentKind = Literal[
    "boundary",
    "state_change",
    "call",
    "exception",
    "branch",
    "hotspot",
    "shape_change",
    "merge",
    "control_flow",
    "closure",
    "style",
    "diagnostic",
]
Severity = Literal["info", "warning", "error"]
EvidenceType = Literal[
    "trace_step",
    "source_line",
    "variable",
    "shape",
    "diagnostic",
    "command",
    "call",
    "profile",
]


class BreakpointModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MomentEvidence(BreakpointModel):
    type: EvidenceType
    step_index: int | None = None
    node_id: str | None = None
    line: int | None = None
    field: str | None = None
    value: Any | None = None
    source_ref: dict[str, Any] | None = None


class Moment(BreakpointModel):
    id: str
    world: World
    kind: MomentKind
    concepts: list[str] = Field(default_factory=list)
    severity: Severity = "info"
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    step_index: int | None = None
    node_id: str | None = None
    line: int | None = None
    source_ref: dict[str, Any] | None = None
    label: str
    why: str = ""
    question: str | None = None
    evidence: list[MomentEvidence] = Field(default_factory=list)
    expected: Any | None = None
    actual: Any | None = None
    tags: list[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    enriched: bool = False


class MomentList(BreakpointModel):
    moments: list[Moment] = Field(default_factory=list)
