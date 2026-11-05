from __future__ import annotations

import asyncio

import httpx

from deeptracer.server.app import create_app


def _request(method: str, path: str, **kwargs):
    async def request():
        transport = httpx.ASGITransport(app=create_app())
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(request())


def test_analyze_endpoint_supports_display_name(monkeypatch):
    captured = {}

    def fake_build_analysis_payload(**kwargs):
        captured.update(kwargs)
        return {
            "heroMetrics": [],
            "analysisMap": {"workflow": {}, "ast": {}, "performance": {}, "memory": {}},
            "suggestions": [],
            "meta": {"taskId": "task-123", "targetPath": kwargs.get("display_name")},
        }

    monkeypatch.setattr("deeptracer.server.app.build_analysis_payload", fake_build_analysis_payload)

    async def immediate_threadpool(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(
        "deeptracer.server.app.run_in_threadpool",
        immediate_threadpool,
    )

    response = _request(
        "POST",
        "/api/analyze",
        json={"code": "print('hello')", "displayName": "demo.py"},
    )

    assert response.status_code == 200
    assert response.json()["meta"]["taskId"] == "task-123"
    assert captured["display_name"] == "demo.py"


def test_chat_stream_endpoint_returns_event_stream(monkeypatch):
    async def fake_stream(**_):
        for event in [
            "event: meta\ndata: {\"taskId\": \"task-1\"}\n\n",
            "event: chunk\ndata: {\"delta\": \"hello\"}\n\n",
            "event: done\ndata: {\"mode\": \"fallback\"}\n\n",
        ]:
            yield event

    monkeypatch.setattr(
        "deeptracer.server.app.stream_chat_events",
        fake_stream,
    )

    response = _request(
        "POST",
        "/api/chat/stream",
        json={
            "code": "print('hello')",
            "displayName": "demo.py",
            "messages": [{"role": "user", "content": "解释一下"}],
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: meta" in response.text
    assert "event: chunk" in response.text
    assert "event: done" in response.text


def test_tracer_endpoint_forwards_selected_functions(monkeypatch):
    captured = {}

    def fake_trace(**kwargs):
        captured.update(kwargs)
        return {"callCount": 1, "traceTree": [], "terminalOutput": "ok"}

    async def immediate_threadpool(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr("deeptracer.server.app.execute_tracer_trace", fake_trace)
    monkeypatch.setattr(
        "deeptracer.server.app.run_in_threadpool",
        immediate_threadpool,
    )

    response = _request(
        "POST",
        "/api/tracer/trace",
        json={
            "code": "def demo():\n    return 1\n",
            "functions": ["demo"],
            "options": {"timeTrace": True},
        },
    )

    assert response.status_code == 200
    assert response.json()["callCount"] == 1
    assert captured["functions"] == ["demo"]
    assert captured["options"]["timeTrace"] is True


def test_run_endpoint_returns_terminal_output(monkeypatch):
    async def immediate_threadpool(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(
        "deeptracer.server.app.execute_python_code",
        lambda **_: {
            "stdout": "hello\n",
            "stderr": "",
            "runtimeError": None,
            "durationMs": 1.2,
            "exitCode": 0,
        },
    )
    monkeypatch.setattr(
        "deeptracer.server.app.run_in_threadpool",
        immediate_threadpool,
    )

    response = _request(
        "POST",
        "/api/run",
        json={"code": "print('hello')"},
    )

    assert response.status_code == 200
    assert response.json()["stdout"] == "hello\n"


def test_edit_plan_endpoint_forwards_suggestion(monkeypatch):
    captured = {}

    def fake_generate(code, suggestion, **kwargs):
        captured["code"] = code
        captured["suggestion"] = suggestion
        captured["kwargs"] = kwargs
        return {"available": False, "reason": "needs model"}

    async def immediate_threadpool(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr("deeptracer.server.app.generate_patch_plan", fake_generate)
    monkeypatch.setattr(
        "deeptracer.server.app.run_in_threadpool",
        immediate_threadpool,
    )

    response = _request(
        "POST",
        "/api/edit/plan",
        json={
            "code": "print('hello')",
            "displayName": "demo.py",
            "suggestion": {"id": "split-function"},
            "allowModel": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["available"] is False
    assert captured["suggestion"]["id"] == "split-function"
    assert captured["kwargs"]["allow_model"] is False


def test_edit_apply_and_verify_endpoints(monkeypatch):
    async def immediate_threadpool(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(
        "deeptracer.server.app.run_in_threadpool",
        immediate_threadpool,
    )
    monkeypatch.setattr(
        "deeptracer.server.app.apply_patch_plan",
        lambda code, plan: {
            "code": "print('after')",
            "afterHash": "hash",
            "unifiedDiff": "--- before\n+++ after\n",
        },
    )
    monkeypatch.setattr(
        "deeptracer.server.app.verify_edit_pair",
        lambda before, after: {
            "behavior": "changed",
            "before": {"exitCode": 0},
            "after": {"exitCode": 0},
        },
    )

    applied = _request(
        "POST",
        "/api/edit/apply",
        json={
            "code": "print('before')",
            "plan": {"edits": []},
        },
    )
    verified = _request(
        "POST",
        "/api/edit/verify",
        json={
            "beforeCode": "print('before')",
            "afterCode": "print('after')",
        },
    )

    assert applied.status_code == 200
    assert applied.json()["code"] == "print('after')"
    assert verified.status_code == 200
    assert verified.json()["behavior"] == "changed"


def test_turtle_compile_endpoint_returns_execution_steps(monkeypatch):
    async def immediate_threadpool(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(
        "deeptracer.server.app.run_in_threadpool",
        immediate_threadpool,
    )
    monkeypatch.setattr(
        "deeptracer.server.app.compile_turtle_source",
        lambda source: {
            "ok": True,
            "steps": [{"line": 1, "standardLine": 27}],
            "commands": [],
            "generatedCode": "import turtle\n",
            "source": source,
        },
    )

    response = _request(
        "POST",
        "/api/turtle/compile",
        json={"source": "forward(50)"},
    )

    assert response.status_code == 200
    assert response.json()["steps"][0]["standardLine"] == 27
    assert response.json()["source"] == "forward(50)"


def test_api_docs_page_is_available():
    response = _request("GET", "/api-docs")

    assert response.status_code == 200
    assert "API 文档" in response.text
    assert "DeepTracer 主库" in response.text
    assert "Tracer 内置库" in response.text
    assert "interactive_on_event" in response.text


def test_local_frontend_assets_use_content_version_and_uncached_html():
    html = _request("GET", "/")
    docs = _request("GET", "/api-docs")

    assert html.status_code == 200
    assert "app.css?v=" in html.text
    assert "app.js?v=" in html.text
    assert "no-store" in html.headers["Cache-Control"]
    assert "app.css?v=" in docs.text
    assert "no-store" in docs.headers["Cache-Control"]


def test_legacy_tracer_docs_url_redirects_to_generic_api_docs():
    response = _request("GET", "/tracer-api-docs")

    assert response.status_code == 307
    assert response.headers["location"] == "/api-docs"
