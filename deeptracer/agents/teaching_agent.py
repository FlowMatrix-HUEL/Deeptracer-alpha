from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from deeptracer.agents.schemas import TeachingAgentResult
from deeptracer.agents.utils import (
    JSON_OUTPUT_INSTRUCTION,
    agent_fallback,
    invoke_structured_or_fallback,
    to_json_text,
)
from deeptracer.modeling.llm import get_chat_model


def run_teaching_agent(code: str, structure: dict, performance: dict, memory: dict, refactor: dict) -> dict:
    llm = get_chat_model(optional=True)
    focus = structure.get("focus_function", "the current code")
    fallback = {
        "overview": f"先阅读 {focus}，理解它的职责和输入参数，再决定是否需要优化。",
        "beginner_tip": "如果一段代码难以阅读，先确认每个函数的职责和参数是否清楚。",
        "next_step": "打开第一条建议，确认它为什么会被推荐，再从最小改动开始。",
    }

    if llm is None:
        return agent_fallback(fallback, error="model_not_configured")

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You translate Python analysis results into beginner-friendly guidance. "
                "Be concise, plainspoken, and direct. "
                f"{JSON_OUTPUT_INSTRUCTION}",
            ),
            (
                "human",
                "Code:\n{code}\n\nStructure result:\n{structure}\n\nPerformance result:\n{performance}\n\n"
                "Memory result:\n{memory}\n\nRefactor result:\n{refactor}\n\n"
                "Provide an overview, a beginner tip, and the best next step.",
            ),
        ]
    )
    chain = prompt | llm.with_structured_output(TeachingAgentResult)
    return invoke_structured_or_fallback(
        chain,
        {
            "code": code,
            "structure": to_json_text(structure),
            "performance": to_json_text(performance),
            "memory": to_json_text(memory),
            "refactor": to_json_text(refactor),
        },
        fallback,
    )
