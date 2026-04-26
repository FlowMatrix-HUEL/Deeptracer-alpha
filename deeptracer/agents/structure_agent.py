from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from deeptracer.agents.schemas import StructureAgentResult
from deeptracer.agents.utils import JSON_OUTPUT_INSTRUCTION, invoke_structured_or_fallback, to_json_text
from deeptracer.modeling.llm import get_chat_model


def run_structure_agent(code: str, local_analysis: dict) -> dict:
    llm = get_chat_model(optional=True)
    ast_view = local_analysis["analysisMap"]["ast"]
    fallback = {
        "summary": ast_view["summary"],
        "focus_function": ast_view["cards"][2]["value"],
        "points": ast_view["points"],
    }

    if llm is None:
        return fallback

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You explain Python code structure for beginners. "
                "Stay concise, grounded in the supplied AST summary, and avoid discussing "
                "performance or memory. "
                f"{JSON_OUTPUT_INSTRUCTION}",
            ),
            (
                "human",
                "Code:\n{code}\n\nAST summary:\n{ast_view}\n\n"
                "Provide a structural summary, the first function worth reading, and three simple points.",
            ),
        ]
    )
    chain = prompt | llm.with_structured_output(StructureAgentResult)
    return invoke_structured_or_fallback(
        chain,
        {"code": code, "ast_view": to_json_text(ast_view)},
        fallback,
    )
