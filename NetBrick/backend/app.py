from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from . import __version__
from .catalog import catalog_response
from .codegen import CodegenError, generate_code
from .composites import build_composite_resource, composite_depth
from .course import create_package, validate_package
from .files import (
    SavePythonRequest,
    SavePythonResponse,
    save_python_with_native_dialog,
)
from .importer import import_pytorch
from .inference import analyze, trace_preview
from .models import (
    AnalysisResult,
    CapabilityResponse,
    CodegenRequest,
    CodegenResponse,
    CompositeValidateResponse,
    CourseImportRequest,
    CoursePack,
    CourseValidateResponse,
    Diagnostic,
    HealthResponse,
    ImportRequest,
    ImportResponse,
    IRDocument,
    PortContract,
    PublishCompositeRequest,
    TraceRequest,
    TraceResponse,
)
from .samples import SAMPLES


ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "frontend" / "dist"

app = FastAPI(
    title="NetBrick API",
    version=__version__,
    description="可视化深度学习教学模型的结构校验与代码生成服务",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _capabilities() -> CapabilityResponse:
    return CapabilityResponse(
        version=__version__,
        python=sys.version.split()[0],
        runtime_note="当前模式不执行 PyTorch/Paddle；shape 为结构模拟，Python 产物仅做语法校验。",
    )


@app.get("/api/v1/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(capabilities=_capabilities())


@app.get("/api/v1/catalog")
def catalog():
    return catalog_response()


@app.get("/api/v1/samples")
def samples():
    return [
        {
            "id": sample["id"],
            "title": sample["title"],
            "description": sample["description"],
        }
        for sample in SAMPLES.values()
    ]


@app.get("/api/v1/samples/{sample_id}", response_model=IRDocument)
def sample(sample_id: str) -> IRDocument:
    entry = SAMPLES.get(sample_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="示例不存在")
    factory = entry["ir"]
    return factory()  # type: ignore[operator]


@app.post("/api/v1/graphs/validate", response_model=AnalysisResult)
def validate_graph(ir: IRDocument) -> AnalysisResult:
    return analyze(ir)


@app.post("/api/v1/graphs/infer/static", response_model=AnalysisResult)
def infer_static(ir: IRDocument) -> AnalysisResult:
    return analyze(ir)


@app.post("/api/v1/graphs/trace-preview", response_model=TraceResponse)
def trace_graph(request: TraceRequest) -> TraceResponse:
    return trace_preview(request.ir)


@app.post("/api/v1/graphs/codegen", response_model=CodegenResponse)
def codegen(request: CodegenRequest) -> CodegenResponse:
    try:
        return generate_code(request.ir, request.framework, request.include_demo)
    except CodegenError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "message": str(exc),
                "diagnostics": [item.model_dump(mode="json") for item in exc.diagnostics],
            },
        ) from exc


@app.post("/api/v1/composites/validate", response_model=CompositeValidateResponse)
@app.post("/api/v1/composites/publish", response_model=CompositeValidateResponse)
def publish_composite(request: PublishCompositeRequest) -> CompositeValidateResponse:
    analysis = analyze(request.ir)
    if not analysis.valid or analysis.normalized_ir is None:
        return CompositeValidateResponse(
            valid=False,
            diagnostics=analysis.diagnostics,
        )
    normalized = analysis.normalized_ir
    node_analysis = {item.node_id: item for item in analysis.nodes}
    outputs: list[PortContract] = []
    for node in normalized.graph.nodes:
        if node.op != "Output":
            continue
        ports = node_analysis[node.id].ports if node.id in node_analysis else []
        input_port = next(
            (
                port
                for port in ports
                if port.io == "in"
            ),
            None,
        )
        outputs.append(
            PortContract(
                name=str(node.params.get("name", node.id)),
                data_type=str(node.params.get("data_type", "Tensor")),  # type: ignore[arg-type]
                shape=input_port.shape if input_port else None,
                dtype=input_port.dtype if input_port else None,
                required=True,
            )
        )
    try:
        resource = build_composite_resource(
            request.model_copy(update={"ir": normalized}),
            outputs,
        )
        depth = composite_depth(resource)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"message": str(exc), "diagnostics": []},
        ) from exc
    if depth > 3:
        return CompositeValidateResponse(
            valid=False,
            diagnostics=[
                Diagnostic(
                    code="COMPOSITE_DEPTH_EXCEEDED",
                    message="复合资源嵌套超过 3 层",
                    teaching_tip="将深层结构整理成更小的独立复合资源。",
                )
            ],
        )
    return CompositeValidateResponse(
        valid=True,
        resource=resource,
        parameter_count=len(resource.parameter_defaults),
    )


@app.post("/api/v1/graphs/import/pytorch", response_model=ImportResponse)
def import_model(request: ImportRequest) -> ImportResponse:
    return import_pytorch(request)


@app.post("/api/v1/course-packages/validate", response_model=CourseValidateResponse)
def course_validate(request: CourseImportRequest) -> CourseValidateResponse:
    return validate_package(request)


@app.post("/api/v1/course-packages/export")
def course_export(pack: CoursePack) -> Response:
    content = create_package(pack)
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="netbrick-course.netbrick"'},
    )


@app.post("/api/v1/course-packages/inspect-zip")
def inspect_zip(pack: CoursePack):
    # Kept as an explicit inspection route for debugging generated package contents.
    content = create_package(pack)
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        return {
            "files": archive.namelist(),
            "size": len(content),
        }


@app.post("/api/v1/files/save-python", response_model=SavePythonResponse)
def save_python_file(request: SavePythonRequest) -> SavePythonResponse:
    return save_python_with_native_dialog(request)


if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="frontend")


def main() -> None:
    import uvicorn

    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
