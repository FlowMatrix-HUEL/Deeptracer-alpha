from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


IR_VERSION = "0.3"
COMPOSITE_RESOURCE_VERSION = "1.0"
DATA_TYPES = {
    "Tensor",
    "ScalarBool",
    "ScalarInt",
    "Module",
    "Dataset",
    "Loss",
    "Optimizer",
}
PORT_ROLES = {
    "logits",
    "label",
    "input_img",
    "grad_out",
    "pred",
    "condition",
    "value",
}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Position(StrictModel):
    x: float = 0
    y: float = 0


class UiState(StrictModel):
    positions: dict[str, Position] = Field(default_factory=dict)
    zoom: float = Field(default=1, ge=0.25, le=2)


class GraphMeta(StrictModel):
    name: str = Field(default="未命名模型", min_length=1, max_length=120)
    author: str = Field(default="", max_length=80)
    is_composite: bool = False
    composite_version_tag: str | None = None
    note: str = Field(default="", max_length=2000)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Node(StrictModel):
    id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    op: str = Field(min_length=1, max_length=80)
    params: dict[str, Any] = Field(default_factory=dict)
    teaching_note: str = Field(default="", max_length=1000)
    composite_ref: "CompositeRef | None" = None
    param_overrides: dict[str, Any] = Field(default_factory=dict)
    region_refs: dict[str, str] = Field(default_factory=dict)
    state_contract: "StateContract | None" = None


class EdgeEndpoint(StrictModel):
    node_id: str
    port: str = "x"


class Edge(StrictModel):
    id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    source: EdgeEndpoint
    target: EdgeEndpoint


class Graph(StrictModel):
    nodes: list[Node] = Field(default_factory=list, max_length=200)
    edges: list[Edge] = Field(default_factory=list, max_length=200)


class PortContract(StrictModel):
    name: str = Field(min_length=1, max_length=80)
    data_type: Literal["Tensor", "ScalarBool", "ScalarInt"] = "Tensor"
    shape: list[int | None] | None = None
    dtype: str | None = "float32"
    required: bool = True
    role: str | None = None


class StateContract(StrictModel):
    inputs: list[PortContract] = Field(default_factory=list)
    outputs: list[PortContract] = Field(default_factory=list)


class CompositeRef(StrictModel):
    resource_id: str
    revision: int = Field(ge=1)


class GraphRegion(StrictModel):
    id: str = Field(pattern=r"^[A-Za-z0-9_.-]+$")
    kind: Literal["composite", "predicate", "then", "else", "body"]
    graph: Graph = Field(default_factory=Graph)
    ui: UiState = Field(default_factory=UiState)
    inputs: list[PortContract] = Field(default_factory=list)
    outputs: list[PortContract] = Field(default_factory=list)
    read_only: bool = False


class CompositeResource(StrictModel):
    schema_version: Literal["1.0"] = COMPOSITE_RESOURCE_VERSION
    resource_id: str = Field(pattern=r"^[A-Za-z0-9_.-]+$")
    name: str = Field(min_length=1, max_length=120)
    revision: int = Field(ge=1)
    description: str = Field(default="", max_length=2000)
    author: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    graph: Graph
    regions: dict[str, GraphRegion] = Field(default_factory=dict)
    ui: UiState = Field(default_factory=UiState)
    inputs: list[PortContract] = Field(default_factory=list)
    outputs: list[PortContract] = Field(default_factory=list)
    dependencies: list["CompositeResource"] = Field(default_factory=list)
    parameter_defaults: dict[str, Any] = Field(default_factory=dict)


class CheckInfo(StrictModel):
    static_shape_pass: bool = False
    error_count: int = 0
    checked_at: datetime | None = None


class IRDocument(StrictModel):
    ir_version: Literal["0.2", "0.3"] = IR_VERSION
    target_framework: Literal["pytorch", "paddle"] = "pytorch"
    graph_meta: GraphMeta = Field(default_factory=GraphMeta)
    graph: Graph = Field(default_factory=Graph)
    regions: dict[str, GraphRegion] = Field(default_factory=dict)
    resources: list[CompositeResource] = Field(default_factory=list)
    ui: UiState = Field(default_factory=UiState)
    check_info: CheckInfo | None = None


class Diagnostic(StrictModel):
    code: str
    severity: Literal["error", "warning", "info"] = "error"
    node_id: str | None = None
    edge_id: str | None = None
    field: str | None = None
    message: str
    teaching_tip: str = ""


class PortInfo(StrictModel):
    name: str
    io: Literal["in", "out"]
    data_type: Literal[
        "Tensor",
        "ScalarBool",
        "ScalarInt",
        "Module",
        "Dataset",
        "Loss",
        "Optimizer",
    ] = "Tensor"
    role: str | None = None
    shape: list[int | None] | None = None
    dtype: str | None = None


class NodeAnalysis(StrictModel):
    node_id: str
    label: str
    ports: list[PortInfo] = Field(default_factory=list)


class AnalysisResult(StrictModel):
    valid: bool
    normalized_ir: IRDocument | None = None
    nodes: list[NodeAnalysis] = Field(default_factory=list)
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    chain_count: int = 0


class CodegenRequest(StrictModel):
    ir: IRDocument
    framework: Literal["pytorch", "paddle"] = "pytorch"
    include_demo: bool = True


class CodegenResponse(StrictModel):
    filename: str
    source: str
    syntax_valid: bool
    warnings: list[Diagnostic] = Field(default_factory=list)


class TraceRequest(StrictModel):
    ir: IRDocument
    seed: int = Field(default=42, ge=0, le=2**31 - 1)


class TraceStep(StrictModel):
    index: int
    node_id: str
    label: str
    input_shape: list[int | None] | None = None
    input_shapes: list[list[int | None]] | None = None
    output_shape: list[int | None] | None = None
    dtype: str | None = None
    note: str = ""


class TraceResponse(StrictModel):
    mode: Literal["structure_preview"] = "structure_preview"
    message: str = "结构模拟：未执行 PyTorch/Paddle 张量运算"
    steps: list[TraceStep]
    diagnostics: list[Diagnostic] = Field(default_factory=list)


class ImportRequest(StrictModel):
    source: str = Field(min_length=1, max_length=200_000)
    source_name: str = "model.py"
    default_shape: list[int] = Field(default_factory=lambda: [1, 784])
    shape: list[int] = Field(default_factory=lambda: [1, 784])
    dtype: Literal["float32", "float64", "int64", "uint8"] = "float32"


class ImportResponse(StrictModel):
    ir: IRDocument | None = None
    diagnostics: list[Diagnostic] = Field(default_factory=list)


class CourseStep(StrictModel):
    title: str
    markdown: str
    focus_node_ids: list[str] = Field(default_factory=list)


class CoursePack(StrictModel):
    title: str = "NetBrick 课堂示例"
    author: str = ""
    description: str = ""
    ir: IRDocument
    steps: list[CourseStep] = Field(default_factory=list)


class CourseImportRequest(StrictModel):
    content_base64: str


class CourseValidateResponse(StrictModel):
    valid: bool
    pack: CoursePack | None = None
    diagnostics: list[Diagnostic] = Field(default_factory=list)


class CapabilityResponse(StrictModel):
    status: Literal["ok"] = "ok"
    version: str
    python: str
    framework_runtime: Literal["disabled"] = "disabled"
    runtime_note: str


class HealthResponse(StrictModel):
    status: Literal["ok"] = "ok"
    capabilities: CapabilityResponse


class CompositeValidateResponse(StrictModel):
    valid: bool
    resource: CompositeResource | None = None
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    parameter_count: int = 0


class PublishCompositeRequest(StrictModel):
    resource_id: str
    name: str
    author: str = ""
    description: str = ""
    revision: int = Field(default=1, ge=1)
    ir: IRDocument


Node.model_rebuild()
IRDocument.model_rebuild()
CompositeResource.model_rebuild()
