from __future__ import annotations

import pytest

from deeptracer.agents import (
    memory_agent,
    performance_agent,
    refactor_agent,
    structure_agent,
    teaching_agent,
)


class _FakeResult:
    def model_dump(self) -> dict:
        return {"ok": True}


class _FakeChain:
    def invoke(self, payload: dict) -> _FakeResult:
        return _FakeResult()


class _FakePrompt:
    def __or__(self, other) -> _FakeChain:
        return _FakeChain()


class _FakePromptFactory:
    def __init__(self) -> None:
        self.messages = None

    def from_messages(self, messages):
        self.messages = messages
        return _FakePrompt()


class _FakeLlm:
    def with_structured_output(self, schema):
        return object()


def _install_fakes(monkeypatch: pytest.MonkeyPatch, module):
    prompt_factory = _FakePromptFactory()
    monkeypatch.setattr(module, "ChatPromptTemplate", prompt_factory)
    monkeypatch.setattr(module, "get_chat_model", lambda optional=True: _FakeLlm())
    return prompt_factory


@pytest.mark.parametrize(
    ("module", "runner", "args"),
    [
        (
            structure_agent,
            structure_agent.run_structure_agent,
            (
                "def demo():\n    return 1\n",
                {"analysisMap": {"ast": {"summary": "s", "cards": [{}, {}, {"value": "demo"}], "points": []}}},
            ),
        ),
        (
            memory_agent,
            memory_agent.run_memory_agent,
            (
                "def demo():\n    return 1\n",
                {"analysisMap": {"memory": {"summary": "s", "cards": [{"value": "heap"}], "points": []}}},
            ),
        ),
        (
            performance_agent,
            performance_agent.run_performance_agent,
            (
                "def demo():\n    return 1\n",
                {"analysisMap": {"performance": {"summary": "s", "cards": [{}, {"value": "demo"}], "points": []}}},
            ),
        ),
        (
            refactor_agent,
            refactor_agent.run_refactor_agent,
            (
                "def demo():\n    return 1\n",
                {"suggestions": []},
                {"summary": "structure"},
                {"summary": "performance"},
                {"summary": "memory"},
            ),
        ),
        (
            teaching_agent,
            teaching_agent.run_teaching_agent,
            (
                "def demo():\n    return 1\n",
                {"focus_function": "demo"},
                {"summary": "performance"},
                {"summary": "memory"},
                {"suggestions": []},
            ),
        ),
    ],
)
def test_structured_output_prompts_include_json(monkeypatch: pytest.MonkeyPatch, module, runner, args):
    prompt_factory = _install_fakes(monkeypatch, module)

    runner(*args)

    assert prompt_factory.messages is not None
    rendered = " ".join(content for _, content in prompt_factory.messages).lower()
    assert "json" in rendered
