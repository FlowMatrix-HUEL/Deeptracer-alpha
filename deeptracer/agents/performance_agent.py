from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from deeptracer.agents.schemas import PerformanceAgentResult
from deeptracer.agents.utils import (
    JSON_OUTPUT_INSTRUCTION,
    agent_fallback,
    invoke_structured_or_fallback,
    to_json_text,
)
from deeptracer.modeling.llm import get_chat_model


def run_performance_agent(code: str, local_analysis: dict) -> dict:
    llm = get_chat_model(optional=True)
    perf_view = local_analysis["analysisMap"]["performance"]
    fallback = {
        "summary": perf_view["summary"],
        "hottest_function": perf_view["cards"][1]["value"],
        "points": perf_view["points"],
    }

    if llm is None:
        return agent_fallback(fallback, error="model_not_configured")

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You explain Python performance findings for beginners. "
                "Stay grounded in the provided data, avoid exaggeration, and focus on whether "
                "an optimization is worth attention. "
                f"{JSON_OUTPUT_INSTRUCTION}",
            ),
            (
                "human",
                "Code:\n{code}\n\nPerformance summary:\n{perf_view}\n\n"
                "Provide a performance summary, the main hotspot, and three simple points.",
            ),
        ]
    )
    chain = prompt | llm.with_structured_output(PerformanceAgentResult)
    return invoke_structured_or_fallback(
        chain,
        {"code": code, "perf_view": to_json_text(perf_view)},
        fallback,
    )
