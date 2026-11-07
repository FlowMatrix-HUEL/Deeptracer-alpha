from __future__ import annotations

from pathlib import Path

from deeptracer.partner import memory, session


def _temp_root(tmp_path: Path, monkeypatch) -> Path:
    root = tmp_path / "partner"
    monkeypatch.setattr(memory, "partner_root", lambda: root)
    monkeypatch.setattr(session, "partner_root", lambda: root)
    return root


def test_memory_saves_and_lists_cases(tmp_path, monkeypatch):
    _temp_root(tmp_path, monkeypatch)

    case = memory.save_case(
        {
            "title": "为什么循环少跑一次",
            "workbench": "python",
            "concepts": ["repetition", "boundary"],
            "question": "为什么 range(5) 的最后一次是 4？",
            "conclusion": "range(5) 产生 0..4，循环结束后 i 保留 4。",
            "status": "resolved",
        }
    )

    assert case["id"].startswith("case-")
    cases = memory.list_cases()
    assert cases[0]["title"] == "为什么循环少跑一次"
    assert cases[0]["status"] == "resolved"

    context = memory.build_memory_context("python")
    assert "为什么循环少跑一次" in context
    assert "0..4" in context


def test_memory_rejects_unknown_workbench(tmp_path, monkeypatch):
    _temp_root(tmp_path, monkeypatch)
    try:
        memory.save_case({"title": "x", "workbench": "unknown"})
    except ValueError as exc:
        assert "workbench" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_parse_action_blocks_extracts_actions_and_hint():
    text = (
        "先别急着答。看第 11 步。\n"
        '[ACTION]{"kind":"highlight","target":{"type":"line","line":3},"label":"看这里"}[/ACTION]\n'
        '[ACTION]{"kind":"evidence","refs":[{"type":"trace_step","stepIndex":11,"line":3,"label":"i=4"}]}[/ACTION]\n'
        "[HINT]H1[/HINT]"
    )

    cleaned, actions, hint = session._parse_action_blocks(text)

    assert "先别急着答" in cleaned
    assert "[ACTION]" not in cleaned
    assert len(actions) == 2
    assert actions[0]["kind"] == "highlight"
    assert actions[1]["kind"] == "evidence"
    assert hint == "H1"


def test_parse_action_blocks_drops_unknown_shape():
    cleaned, actions, hint = session._parse_action_blocks(
        '[ACTION]{"kind":"unknown","foo":"bar"}[/ACTION][HINT]H2[/HINT]'
    )
    assert cleaned == ""
    assert actions == []
    assert hint == "H2"


def test_stream_partner_falls_back_without_model(tmp_path, monkeypatch):
    _temp_root(tmp_path, monkeypatch)
    monkeypatch.setattr(session, "get_chat_model", lambda optional=False: None)
    monkeypatch.setattr(session, "append_thread", lambda turn: None)

    payload = {
        "workbench": "python",
        "mode": "co-investigate",
        "messages": [{"role": "user", "content": "为什么循环结束后 i 是 4？"}],
        "context": {
            "trace": {"line": 3, "lastStep": 11},
            "code": "for i in range(5):\n    pass\n",
        },
    }

    events = list(session.stream_partner_events(payload))
    joined = "".join(events)

    assert "event: meta" in joined
    assert "event: token" in joined
    assert "event: hint" in joined
    assert "event: done" in joined
    assert "fallback" in joined


def test_partner_memory_endpoint_round_trip(tmp_path, monkeypatch):
    _temp_root(tmp_path, monkeypatch)
    from fastapi.testclient import TestClient

    from deeptracer.server.app import create_app

    client = TestClient(create_app())
    saved = client.post(
        "/api/partner/memory",
        json={
            "title": "Shape 为什么对不上",
            "workbench": "netbrick",
            "conclusion": "Conv2d 改变了空间尺寸。",
        },
    )
    assert saved.status_code == 200
    assert saved.json()["title"] == "Shape 为什么对不上"

    listing = client.get("/api/partner/memory")
    assert listing.status_code == 200
    assert listing.json()["cases"][0]["title"] == "Shape 为什么对不上"


def test_partner_stream_endpoint_falls_back(tmp_path, monkeypatch):
    _temp_root(tmp_path, monkeypatch)
    monkeypatch.setattr(session, "get_chat_model", lambda optional=False: None)
    monkeypatch.setattr(session, "append_thread", lambda turn: None)
    from fastapi.testclient import TestClient

    from deeptracer.server.app import create_app

    client = TestClient(create_app())
    response = client.post(
        "/api/partner/stream",
        json={
            "workbench": "turtle",
            "messages": [{"role": "user", "content": "为什么图形没闭合？"}],
            "context": {
                "source": "forward(60)\nright(90)\n",
                "steps": [{"index": 0, "line": 1}],
            },
        },
    )
    assert response.status_code == 200
    assert "event: meta" in response.text
    assert "event: token" in response.text
    assert "event: done" in response.text


def test_stream_partner_model_actions_are_streamed(tmp_path, monkeypatch):
    _temp_root(tmp_path, monkeypatch)
    monkeypatch.setattr(session, "append_thread", lambda turn: None)

    class Chunk:
        def __init__(self, content):
            self.content = content

    class FakeModel:
        def stream(self, messages):
            yield Chunk("先看第 11 步。\n")
            yield Chunk(
                '[ACTION]{"kind":"jump","target":{"type":"step","stepIndex":11},"label":"跳过去"}[/ACTION]'
            )
            yield Chunk("[HINT]H1[/HINT]")

    monkeypatch.setattr(
        session, "get_chat_model", lambda optional=False: FakeModel()
    )
    monkeypatch.setattr(
        session, "build_partner_system_prompt", lambda **kwargs: "system"
    )

    payload = {
        "workbench": "python",
        "messages": [{"role": "user", "content": "为什么？"}],
        "context": {"code": "for i in range(5):\n    pass\n"},
    }
    joined = "".join(session.stream_partner_events(payload))

    assert "先看第 11 步" in joined
    assert '"kind": "jump"' in joined
    assert '"stepIndex": 11' in joined
    assert "event: hint" in joined
    assert "event: done" in joined
