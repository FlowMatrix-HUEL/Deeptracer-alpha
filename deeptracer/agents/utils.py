from __future__ import annotations

import json
from typing import Any

JSON_OUTPUT_INSTRUCTION = (
    "Return a valid JSON object that matches the required schema. "
    "Do not wrap the JSON in markdown."
)


def to_json_text(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def invoke_structured_or_fallback(chain, payload: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        result = chain.invoke(payload)
    except Exception:
        return fallback
    if hasattr(result, "model_dump"):
        return result.model_dump()
    if isinstance(result, dict):
        return result
    return fallback
