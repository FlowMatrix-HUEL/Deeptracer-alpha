from __future__ import annotations

from deeptracer.server.analysis_context import build_grounding_bundle
from deeptracer.server.analysis_service import analyze_python_input
from deeptracer.server import chat_service


SAMPLE_ALPHA = """
def normalize_scores(values):
    cleaned = [max(0, value) for value in values]
    return [value / 100 for value in cleaned]


def summarize_scores(values):
    normalized = normalize_scores(values)
    return sum(normalized) / len(normalized)


print(summarize_scores([120, -3, 50]))
"""


SAMPLE_BETA = """
def render_invoice(items):
    lines = []
    total = 0
    for name, price in items:
        total += price
        lines.append(f"{name}:{price}")
    return lines, total


print(render_invoice([("pen", 3), ("book", 15)]))
"""


def test_grounding_bundle_extracts_code_anchors():
    payload = analyze_python_input(source_code=SAMPLE_ALPHA, display_name="alpha.py")

    bundle = build_grounding_bundle(payload, SAMPLE_ALPHA, "alpha.py")

    labels = {anchor["label"] for anchor in bundle["anchors"]}
    assert "normalize_scores" in labels
    assert "summarize_scores" in labels
    assert bundle["code"].strip().startswith("def normalize_scores")


def test_suggestions_differ_for_distinct_code_samples():
    alpha_payload = analyze_python_input(source_code=SAMPLE_ALPHA, display_name="alpha.py")
    beta_payload = analyze_python_input(source_code=SAMPLE_BETA, display_name="beta.py")

    alpha_detail = alpha_payload["suggestions"][0]["detail"]
    beta_detail = beta_payload["suggestions"][0]["detail"]

    alpha_labels = {anchor["label"] for anchor in alpha_detail["codeAnchors"]}
    beta_labels = {anchor["label"] for anchor in beta_detail["codeAnchors"]}

    assert alpha_labels != beta_labels
    assert "normalize_scores" in alpha_labels or "summarize_scores" in alpha_labels
    assert "render_invoice" in beta_labels


def test_local_suggestion_diff_is_source_context_not_fabricated_edits():
    payload = analyze_python_input(source_code=SAMPLE_ALPHA, display_name="alpha.py")
    diff_rows = payload["suggestions"][0]["diff"]

    assert diff_rows
    assert all(row[3] == "context" for row in diff_rows)
    source_lines = SAMPLE_ALPHA.strip("\n").splitlines()
    assert all(row[2] == source_lines[row[0] - 1] for row in diff_rows)


def test_model_backed_chat_grounding_includes_raw_code_and_anchor(monkeypatch):
    captured = {}

    class FakeLLM:
        def stream(self, messages):
            captured["system_prompt"] = messages[0].content
            yield type("Chunk", (), {"content": "done"})()

    monkeypatch.setattr(chat_service, "get_chat_model", lambda optional=True: FakeLLM())
    monkeypatch.setattr(
        chat_service,
        "describe_model_runtime",
        lambda: {"provider": "openai", "model": "demo", "llmConfigured": True},
    )
    monkeypatch.setattr(
        chat_service,
        "build_chat_context",
        lambda **_: {
            "taskId": "task-1",
            "displayName": "alpha.py",
            "analysis": {"analysisMap": {}, "suggestions": []},
            "code": SAMPLE_ALPHA,
            "grounding": {
                "displayName": "alpha.py",
                "code": SAMPLE_ALPHA,
                "analysisSummary": {
                    "workflow": "先看 summarize_scores。",
                    "ast": "重点函数是 summarize_scores。",
                    "performance": "热点集中在 summarize_scores。",
                    "memory": "内存压力不高。",
                },
                "anchors": [
                    {
                        "kind": "function",
                        "label": "summarize_scores",
                        "line": 7,
                        "snippet": "7: def summarize_scores(values):",
                    }
                ],
                "suggestions": [{"title": "先看 summarize_scores"}],
            },
        },
    )

    events = list(
        chat_service.stream_chat_events(
            source_code=SAMPLE_ALPHA,
            display_name="alpha.py",
            messages=[{"role": "user", "content": "为什么这里值得先看？"}],
        )
    )

    assert "summarize_scores" in captured["system_prompt"]
    assert "```python" in captured["system_prompt"]
    assert "normalize_scores" in captured["system_prompt"]
    assert any("event: done" in event for event in events)
