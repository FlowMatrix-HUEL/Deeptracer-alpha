from __future__ import annotations

import os
from functools import lru_cache

from deeptracer.workflow.env_utils import build_env_local


@lru_cache(maxsize=1)
def _load_local_model_env() -> str:
    builder = build_env_local()
    return str(builder.load(override=False))


def agents_enabled() -> bool:
    value = os.getenv("DEEPTRACER_AGENTS_ENABLED", "true").strip().lower()
    return value not in {"0", "false", "no", "off", "disabled"}


@lru_cache(maxsize=1)
def get_chat_model(optional: bool = False):
    _load_local_model_env()
    if not agents_enabled():
        if optional:
            return None
        raise ValueError("DeepTracer agents are disabled by configuration.")
    provider = os.getenv("DEEPTRACER_MODEL_PROVIDER", "openai").lower().strip()
    model_name = os.getenv("DEEPTRACER_MODEL_NAME") or os.getenv("OPENAI_MODEL") or "gpt-4.1-mini"

    if provider != "openai":
        if optional:
            return None
        raise ValueError(f"Unsupported model provider: {provider}")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        if optional:
            return None
        raise ValueError("OPENAI_API_KEY is missing. Please configure your model API first.")

    try:
        from langchain_openai import ChatOpenAI

        kwargs = {
            "model": model_name,
            "temperature": float(os.getenv("DEEPTRACER_MODEL_TEMPERATURE", "0.2")),
            "api_key": api_key,
            "timeout": float(os.getenv("DEEPTRACER_MODEL_TIMEOUT_SECONDS", "3.0")),
            "max_retries": int(os.getenv("DEEPTRACER_MODEL_MAX_RETRIES", "0")),
        }
        base_url = os.getenv("OPENAI_BASE_URL")
        if base_url:
            kwargs["base_url"] = base_url

        return ChatOpenAI(**kwargs)
    except Exception:
        if optional:
            return None
        raise


def describe_model_runtime() -> dict[str, object]:
    _load_local_model_env()
    provider = os.getenv("DEEPTRACER_MODEL_PROVIDER", "openai").lower().strip()
    model_name = os.getenv("DEEPTRACER_MODEL_NAME") or os.getenv("OPENAI_MODEL") or "gpt-4.1-mini"
    has_api_key = bool(os.getenv("OPENAI_API_KEY"))
    enabled = agents_enabled()
    return {
        "provider": provider,
        "model": model_name,
        "agentsEnabled": enabled,
        "llmConfigured": enabled and has_api_key and provider == "openai",
    }
