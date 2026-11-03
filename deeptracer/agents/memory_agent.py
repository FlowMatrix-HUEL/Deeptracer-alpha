from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from deeptracer.agents.schemas import MemoryAgentResult
from deeptracer.agents.utils import (
    JSON_OUTPUT_INSTRUCTION,
    agent_fallback,
    invoke_structured_or_fallback,
    to_json_text,
)
from deeptracer.modeling.llm import get_chat_model


def run_memory_agent(code: str, local_analysis: dict) -> dict:
    llm = get_chat_model(optional=True)
    memory_view = local_analysis["analysisMap"]["memory"]
    fallback = {
        "summary": memory_view["summary"],
        "focus_area": memory_view["cards"][0]["value"],
        "points": memory_view["points"],
    }

    if llm is None:
        return agent_fallback(fallback, error="model_not_configured")

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You explain Python memory behavior for beginners. "
                "Focus on whether the reported memory usage matters, why it happens, and how "
                "a learner should read it. Avoid jargon. "
                f"{JSON_OUTPUT_INSTRUCTION}",
            ),
            (
                "human",
                "Code:\n{code}\n\nMemory summary:\n{memory_view}\n\n"
                "Provide a memory summary, the main focus area, and three simple points.",
            ),
        ]
    )
    chain = prompt | llm.with_structured_output(MemoryAgentResult)
    return invoke_structured_or_fallback(
        chain,
        {"code": code, "memory_view": to_json_text(memory_view)},
        fallback,
    )
