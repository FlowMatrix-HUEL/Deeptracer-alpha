from __future__ import annotations

import json
import os
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from deeptracer import DEEPTRACER_DEV_ROOT
from deeptracer.netbrick_support import get_netbrick_app, get_netbrick_dist
from deeptracer.server.analysis_context import build_analysis_payload
from deeptracer.server.chat_service import stream_chat_events
from deeptracer.server.edit_service import (
    apply_patch_plan,
    generate_patch_plan,
    verify_edit_pair,
)
from deeptracer.server.pytutor_service import (
    execute_python_tutor_trace,
    get_pytutor_static_dir,
    is_pytutor_available,
)
from deeptracer.server.run_service import execute_python_code
from deeptracer.server.tracer_service import execute_tracer_trace


HOST = "127.0.0.1"
PORT = 8000


def _disable_html_cache(response):
    response.headers["Cache-Control"] = "no-store, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


def _asset_version(static_path: str) -> str:
    versions = []
    for filename in ("app.css", "app.js"):
        candidate = os.path.join(static_path, filename)
        try:
            versions.append(str(os.stat(candidate).st_mtime_ns))
        except OSError:
            versions.append("0")
    return "-".join(versions)


def create_app() -> FastAPI:
    app = FastAPI(
        title="deeptracer",
        description="Python code analysis workspace",
    )

    static_path = os.path.join(DEEPTRACER_DEV_ROOT, "deeptracer", "static")
    templates_path = os.path.join(DEEPTRACER_DEV_ROOT, "deeptracer", "templates")
    os.makedirs(static_path, exist_ok=True)
    os.makedirs(templates_path, exist_ok=True)

    app.mount("/static", StaticFiles(directory=static_path), name="static")
    if is_pytutor_available():
        app.mount(
            "/tutor-assets",
            StaticFiles(directory=str(get_pytutor_static_dir())),
            name="tutor-assets",
        )
    templates = Jinja2Templates(directory=templates_path)
    netbrick_dist = get_netbrick_dist()

    if netbrick_dist is not None:
        try:
            netbrick_app = get_netbrick_app()
            for route in netbrick_app.router.routes:
                route_path = getattr(route, "path", "")
                if route_path.startswith("/api/v1"):
                    app.router.routes.append(route)
        except Exception as exc:
            print(f"NetBrick API integration failed: {exc}")
            netbrick_dist = None

    @app.get("/netbrick", include_in_schema=False)
    async def netbrick_redirect():
        return RedirectResponse(url="/netbrick/", status_code=307)

    @app.get("/netbrick/", response_class=HTMLResponse, include_in_schema=False)
    async def netbrick_page():
        if netbrick_dist is None:
            raise HTTPException(status_code=404, detail="NetBrick frontend is unavailable.")
        html = (netbrick_dist / "index.html").read_text(encoding="utf-8")
        html = html.replace('"/assets/', '"/netbrick-assets/assets/')
        html = html.replace('"/favicon.svg', '"/netbrick-assets/favicon.svg')
        return HTMLResponse(html)

    @app.get("/netbrick-assets/{asset_path:path}", include_in_schema=False)
    async def netbrick_asset(asset_path: str):
        if netbrick_dist is None:
            raise HTTPException(status_code=404, detail="NetBrick frontend is unavailable.")
        candidate = (netbrick_dist / asset_path).resolve()
        try:
            candidate.relative_to(netbrick_dist.resolve())
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="Asset not found.") from exc
        if not candidate.is_file():
            raise HTTPException(status_code=404, detail="Asset not found.")
        return FileResponse(candidate)

    @app.get("/", response_class=HTMLResponse, summary="Web workspace")
    async def index(request: Request):
        try:
            return _disable_html_cache(
                templates.TemplateResponse(
                    request=request,
                    name="index.html",
                    context={"asset_version": _asset_version(static_path)},
                )
            )
        except Exception:
            return HTMLResponse(content="<h1>404 - File Not Found</h1>", status_code=404)

    @app.get(
        "/api-docs",
        response_class=HTMLResponse,
        summary="DeepTracer API documentation",
    )
    async def api_docs(request: Request):
        return _disable_html_cache(
            templates.TemplateResponse(
                request=request,
                name="api_docs.html",
                context={"asset_version": _asset_version(static_path)},
            )
        )

    @app.get("/tracer-api-docs", include_in_schema=False)
    async def legacy_tracer_api_docs():
        return RedirectResponse(url="/api-docs", status_code=307)

    async def _run_analysis(payload: dict[str, str]):
        target_path = (payload.get("path") or "").strip()
        source_code = payload.get("code") or ""
        display_name = (payload.get("displayName") or "").strip() or None
        task_id = (payload.get("taskId") or "").strip() or None
        analysis_snapshot = payload.get("analysis")
        if not isinstance(analysis_snapshot, dict):
            analysis_snapshot = None
        if not target_path and not source_code.strip():
            raise HTTPException(status_code=400, detail="Missing required field: code or path")

        try:
            return await run_in_threadpool(
                build_analysis_payload,
                path_text=target_path or None,
                source_code=source_code or None,
                display_name=display_name,
                task_id=task_id,
                analysis_snapshot=analysis_snapshot,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc

    @app.post("/api/analyze", summary="Analyze Python code with the LangGraph workflow")
    async def analyze(payload: dict[str, str]):
        return await _run_analysis(payload)

    @app.post("/api/analyze/session", summary="Backward-compatible analysis endpoint")
    async def analyze_session(payload: dict[str, str]):
        return await _run_analysis(payload)

    @app.post("/api/chat/stream", summary="Stream grounded educational chat responses")
    async def chat_stream(payload: dict[str, Any]):
        target_path = (payload.get("path") or "").strip()
        source_code = payload.get("code") or ""
        display_name = (payload.get("displayName") or "").strip() or None
        task_id = (payload.get("taskId") or "").strip() or None
        analysis_snapshot = payload.get("analysis")
        if not isinstance(analysis_snapshot, dict):
            analysis_snapshot = None
        messages = payload.get("messages")
        if not target_path and not source_code.strip():
            raise HTTPException(status_code=400, detail="Missing required field: code or path")
        if not isinstance(messages, list) or not messages:
            raise HTTPException(status_code=400, detail="Missing required field: messages")

        headers = {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
        return StreamingResponse(
            stream_chat_events(
                path_text=target_path or None,
                source_code=source_code or None,
                display_name=display_name,
                task_id=task_id,
                analysis_snapshot=analysis_snapshot,
                messages=messages,
            ),
            media_type="text/event-stream",
            headers=headers,
        )

    @app.get("/api/tutor/status", summary="Check local Python Tutor availability")
    async def tutor_status():
        return {
            "available": is_pytutor_available(),
            "embedUrl": "/tutor/iframe-embed.html" if is_pytutor_available() else None,
        }

    @app.post("/api/tracer/trace", summary="Trace selected function calls with Tracer")
    async def tracer_trace(payload: dict[str, Any]):
        code = payload.get("code") or ""
        functions = payload.get("functions") or []
        options = payload.get("options")
        if not isinstance(functions, list):
            raise HTTPException(status_code=400, detail="functions must be a list")
        if options is not None and not isinstance(options, dict):
            raise HTTPException(status_code=400, detail="options must be an object")
        try:
            return await run_in_threadpool(
                execute_tracer_trace,
                source_code=code,
                functions=[str(item) for item in functions],
                options=options or {},
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except TimeoutError as exc:
            raise HTTPException(status_code=504, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Tracer execution failed: {exc}",
            ) from exc

    @app.post("/api/run", summary="Run Python code and return terminal output")
    async def run_python(payload: dict[str, Any]):
        code = payload.get("code") or ""
        try:
            return await run_in_threadpool(
                execute_python_code,
                source_code=code,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except TimeoutError as exc:
            raise HTTPException(status_code=504, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Run failed: {exc}",
            ) from exc

    @app.post("/api/edit/plan", summary="Generate a validated source edit plan")
    async def edit_plan(payload: dict[str, Any]):
        code = str(payload.get("code") or "")
        suggestion = payload.get("suggestion")
        if not code.strip():
            raise HTTPException(status_code=400, detail="Missing required field: code")
        if not isinstance(suggestion, dict):
            raise HTTPException(status_code=400, detail="suggestion must be an object")
        try:
            return await run_in_threadpool(
                generate_patch_plan,
                code,
                suggestion,
                display_name=str(payload.get("displayName") or "当前代码"),
                allow_model=bool(payload.get("allowModel", True)),
            )
        except SyntaxError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Source code has invalid syntax: {exc}",
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Patch planning failed: {exc}",
            ) from exc

    @app.post("/api/edit/apply", summary="Validate and apply a structured source patch")
    async def edit_apply(payload: dict[str, Any]):
        code = str(payload.get("code") or "")
        plan = payload.get("plan")
        if not code.strip():
            raise HTTPException(status_code=400, detail="Missing required field: code")
        if not isinstance(plan, dict):
            raise HTTPException(status_code=400, detail="plan must be an object")
        try:
            return await run_in_threadpool(apply_patch_plan, code, plan)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Patch application failed: {exc}",
            ) from exc

    @app.post("/api/edit/verify", summary="Compare runtime behavior before and after an edit")
    async def edit_verify(payload: dict[str, Any]):
        before_code = str(payload.get("beforeCode") or "")
        after_code = str(payload.get("afterCode") or "")
        if not before_code.strip() or not after_code.strip():
            raise HTTPException(
                status_code=400,
                detail="beforeCode and afterCode are required",
            )
        return await run_in_threadpool(
            verify_edit_pair,
            before_code,
            after_code,
        )

    @app.post("/api/tutor/trace", summary="Generate a Python Tutor trace for embedded rendering")
    async def tutor_trace(payload: dict[str, Any]):
        code = (payload.get("code") or "").strip()
        if not code:
            raise HTTPException(status_code=400, detail="Missing required field: code")

        options = payload.get("options") or {}

        try:
            return JSONResponse(
                execute_python_tutor_trace(
                    user_script=code,
                    raw_input_json=json.dumps(payload.get("rawInput", []), ensure_ascii=False),
                    options_json=json.dumps(options, ensure_ascii=False),
                )
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Python Tutor execution failed: {exc}") from exc

    @app.get("/tutor/iframe-embed.html", response_class=HTMLResponse, summary="Minimal local Python Tutor frame")
    async def tutor_iframe():
        if not is_pytutor_available():
            raise HTTPException(status_code=404, detail="Python Tutor local runtime is not available.")

        return HTMLResponse(
            content="""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DeepTracer Tutor Embed</title>
  <script src="/tutor-assets/build/iframe-embed.bundle.js?5f90f543ad" charset="utf-8"></script>
  <style>
    html, body {
      margin: 0;
      background: #f7f9fc;
      overflow: hidden;
    }
    #vizDiv, #frontendErrorOutput {
      margin: 0;
    }
  </style>
</head>
<body>
  <div id="vizDiv"></div>
  <div id="frontendErrorOutput"></div>
</body>
</html>"""
        )

    @app.get("/tutor/web_exec_py3.py", summary="Local Python Tutor Python 3 execution")
    async def tutor_exec_py3(
        user_script: str,
        raw_input_json: str = "[]",
        options_json: str = "{}",
    ):
        try:
            payload = execute_python_tutor_trace(
                user_script=user_script,
                raw_input_json=raw_input_json,
                options_json=options_json,
            )
            return JSONResponse(payload)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Python Tutor execution failed: {exc}") from exc

    @app.get("/{full_path:path}", response_class=HTMLResponse)
    async def catch_all(request: Request, full_path: Any = None):
        try:
            return templates.TemplateResponse(request=request, name="index.html")
        except Exception:
            return HTMLResponse(content="<h1>404 - File Not Found</h1>", status_code=404)

    return app


def main() -> None:
    uvicorn.run(
        app=create_app(),
        host=HOST,
        port=PORT,
        log_level="info",
    )


def start(astAnalyer=None, speedAnalyer=None, workflow=None) -> None:
    # Keep backward compatibility with the original server entrypoint.
    main()


if __name__ == "__main__":
    main()
