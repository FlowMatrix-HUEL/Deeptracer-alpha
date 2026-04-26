from __future__ import annotations

from fastapi.testclient import TestClient

from deeptracer.server.app import create_app


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

    client = TestClient(create_app())
    response = client.post(
        "/api/analyze",
        json={"code": "print('hello')", "displayName": "demo.py"},
    )

    assert response.status_code == 200
    assert response.json()["meta"]["taskId"] == "task-123"
    assert captured["display_name"] == "demo.py"


def test_chat_stream_endpoint_returns_event_stream(monkeypatch):
    monkeypatch.setattr(
        "deeptracer.server.app.stream_chat_events",
        lambda **_: iter(
            [
                "event: meta\ndata: {\"taskId\": \"task-1\"}\n\n",
                "event: chunk\ndata: {\"delta\": \"hello\"}\n\n",
                "event: done\ndata: {\"mode\": \"fallback\"}\n\n",
            ]
        ),
    )

    client = TestClient(create_app())
    response = client.post(
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
