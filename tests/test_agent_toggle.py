from __future__ import annotations

from unittest.mock import Mock, patch

from deeptracer.agents.utils import agent_fallback
from deeptracer.graph.response_builder import _build_runtime_banner
from deeptracer.modeling import llm


def test_disabled_agents_never_create_a_model_client(monkeypatch):
    monkeypatch.setenv("DEEPTRACER_AGENTS_ENABLED", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(llm, "_load_local_model_env", lambda: "")
    llm.get_chat_model.cache_clear()
    chat_model = Mock()

    try:
        with patch("langchain_openai.ChatOpenAI", chat_model) as constructor:
            assert llm.get_chat_model(optional=True) is None
            constructor.assert_not_called()

        runtime = llm.describe_model_runtime()
        assert runtime["agentsEnabled"] is False
        assert runtime["llmConfigured"] is False
    finally:
        llm.get_chat_model.cache_clear()


def test_disabled_agent_banner_reports_local_only_mode():
    banner = _build_runtime_banner(
        {
            "agentsEnabled": False,
            "llmConfigured": False,
            "provider": "openai",
            "model": "test-model",
            "agentMode": "agents-off",
            "agentStatuses": {
                "structure": "fallback",
                "performance": "fallback",
                "memory": "fallback",
                "refactor": "fallback",
                "teaching": "fallback",
            },
        }
    )

    assert banner["mode"] == "agents-off"
    assert "Agent 已关闭" in banner["title"]
    assert "不会创建模型客户端" in banner["body"]
    assert agent_fallback({"summary": "local"})["_agentStatus"] == "fallback"
