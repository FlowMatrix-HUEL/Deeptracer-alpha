from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from deeptracer.agents.schemas import RefactorAgentResult
from deeptracer.agents.utils import JSON_OUTPUT_INSTRUCTION, invoke_structured_or_fallback, to_json_text
from deeptracer.modeling.llm import get_chat_model


def run_refactor_agent(code: str, local_analysis: dict, structure: dict, performance: dict, memory: dict) -> dict:
    llm = get_chat_model(optional=True)
    local_suggestions = local_analysis.get("suggestions", [])
    fallback = {"suggestions": local_suggestions}

    if llm is None:
        return fallback

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You propose one to three concrete Python refactor suggestions for beginners. "
                "Use the structure, performance, and memory findings together. Keep each "
                "suggestion practical, explainable, and low-drama. "
                f"{JSON_OUTPUT_INSTRUCTION}",
            ),
            (
                "human",
                "Code:\n{code}\n\nStructure result:\n{structure}\n\nPerformance result:\n{performance}\n\n"
                "Memory result:\n{memory}\n\nLocal suggestion draft:\n{local_suggestions}\n\n"
                "Provide the structured suggestion list.",
            ),
        ]
    )
    chain = prompt | llm.with_structured_output(RefactorAgentResult)
    return invoke_structured_or_fallback(
        chain,
        {
            "code": code,
            "structure": to_json_text(structure),
            "performance": to_json_text(performance),
            "memory": to_json_text(memory),
            "local_suggestions": to_json_text({"suggestions": local_suggestions}),
        },
        fallback,
    )
