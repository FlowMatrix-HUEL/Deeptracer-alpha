from __future__ import annotations

import os
from unittest.mock import patch

from deeptracer.config_cli import configure
from deeptracer.workflow.env_utils import build_env_local


def test_config_command_writes_model_settings(tmp_path):
    builder = build_env_local(tmp_path)

    config_path = configure(
        [
            "--api-key",
            "test-api-key",
            "--base-url",
            "https://example.com/v1",
            "--model",
            "test-model",
            "--temperature",
            "0.3",
        ],
        builder=builder,
    )

    entries = builder._read_entries()
    assert config_path == tmp_path / ".env.local"
    assert entries["OPENAI_API_KEY"] == "test-api-key"
    assert entries["OPENAI_BASE_URL"] == "https://example.com/v1"
    assert entries["OPENAI_MODEL"] == "test-model"
    assert entries["DEEPTRACER_MODEL_NAME"] == "test-model"
    assert entries["DEEPTRACER_MODEL_TEMPERATURE"] == "0.3"
    if os.name == "posix":
        assert config_path.stat().st_mode & 0o777 == 0o600


def test_config_show_masks_api_key(tmp_path, capsys):
    builder = build_env_local(tmp_path)
    builder.save_model_config(
        api_key="sk-1234567890abcdef",
        base_url="https://example.com/v1",
        model_name="test-model",
    )

    configure(["--show"], builder=builder)

    output = capsys.readouterr().out
    assert "sk-1234567890abcdef" not in output
    assert "sk-1...cdef" in output
    assert "test-model" in output


def test_interactive_config_prompts_for_hidden_api_key(tmp_path):
    builder = build_env_local(tmp_path)

    with (
        patch("deeptracer.config_cli.getpass.getpass", return_value="hidden-key"),
        patch(
            "builtins.input",
            side_effect=[
                "https://example.com/v1",
                "interactive-model",
                "0.4",
                "openai",
            ],
        ),
    ):
        configure([], builder=builder)

    entries = builder._read_entries()
    assert entries["OPENAI_API_KEY"] == "hidden-key"
    assert entries["DEEPTRACER_MODEL_NAME"] == "interactive-model"
    assert entries["DEEPTRACER_MODEL_TEMPERATURE"] == "0.4"


def test_agent_toggle_preserves_existing_model_config(tmp_path, capsys):
    builder = build_env_local(tmp_path)
    builder.save_model_config(
        api_key="test-api-key",
        base_url="https://example.com/v1",
        model_name="test-model",
    )

    configure(["--disable-agents"], builder=builder)
    assert builder._read_entries()["DEEPTRACER_AGENTS_ENABLED"] == "false"
    assert builder._read_entries()["OPENAI_API_KEY"] == "test-api-key"

    configure(["--show"], builder=builder)
    output = capsys.readouterr().out
    assert "Agent：已关闭（仅本地分析）" in output

    configure(["--enable-agents"], builder=builder)
    assert builder._read_entries()["DEEPTRACER_AGENTS_ENABLED"] == "true"
