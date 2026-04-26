from __future__ import annotations

import deeptracer.server.chat_service as chat_service


def test_normalize_chat_messages_filters_invalid_entries():
    messages = [
        {"role": "user", "content": "  为什么这里慢  "},
        {"role": "assistant", "content": "因为循环里有重复调用。"},
        {"role": "tool", "content": "ignore"},
        {"role": "user", "content": ""},
        "bad",
    ]

    normalized = chat_service.normalize_chat_messages(messages)

    assert normalized == [
        {"role": "user", "content": "为什么这里慢"},
        {"role": "assistant", "content": "因为循环里有重复调用。"},
    ]


def test_stream_chat_events_falls_back_without_model(monkeypatch):
    monkeypatch.setattr(
        chat_service,
        "build_chat_context",
        lambda **_: {
            "taskId": "task-001",
            "displayName": "demo.py",
            "analysis": {
                "analysisMap": {
                    "workflow": {"summary": "先理解整体结构。"},
                    "ast": {"summary": "重点看主函数。"},
                    "performance": {"summary": "热点集中在循环调用。"},
                    "memory": {"summary": "内存压力不高。"},
                },
                "suggestions": [{"title": "先看热点循环", "explanation": "先把重复调用看懂。"}],
            },
        },
    )
    monkeypatch.setattr(chat_service, "get_chat_model", lambda optional=True: None)
    monkeypatch.setattr(
        chat_service,
        "describe_model_runtime",
        lambda: {"provider": "openai", "model": "demo", "llmConfigured": False},
    )

    events = list(
        chat_service.stream_chat_events(
            source_code="print('hi')",
            display_name="demo.py",
            messages=[{"role": "user", "content": "为什么这里慢？"}],
        )
    )

    joined = "".join(events)
    assert "event: meta" in joined
    assert "event: chunk" in joined
    assert "event: done" in joined
    assert "为什么这里慢" in joined
