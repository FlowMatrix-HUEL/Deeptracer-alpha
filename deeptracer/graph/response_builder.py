from __future__ import annotations

from typing import Any

from deeptracer.modeling.llm import describe_model_runtime


def _build_teaching_panels(
    structure: dict[str, Any],
    performance: dict[str, Any],
    memory: dict[str, Any],
    refactor: dict[str, Any],
    teaching: dict[str, Any],
    local_analysis: dict[str, Any],
) -> list[dict[str, Any]]:
    suggestions = refactor.get("suggestions") or local_analysis.get("suggestions") or []
    first_suggestion = suggestions[0] if suggestions else None
    return [
        {
            "id": "inspect-first",
            "label": "先看哪里",
            "title": structure.get("focus_function", "先看当前代码的主函数"),
            "body": teaching.get("overview")
            or structure.get("summary")
            or "先看函数职责和结构层级。",
            "hint": teaching.get("beginner_tip") or "先确认每个函数是否只做一件事。",
        },
        {
            "id": "why-it-matters",
            "label": "为什么重要",
            "title": performance.get("hottest_function", "先看最明显的热点"),
            "body": performance.get("summary") or "热点函数通常最值得优先理解。",
            "hint": memory.get("summary")
            or "如果热点和内存问题叠在一起，优先看同一段逻辑。",
        },
        {
            "id": "optimize-next",
            "label": "先改哪条",
            "title": (
                first_suggestion.get("title", "先打开第一条建议")
                if first_suggestion
                else "先打开第一条建议"
            ),
            "body": (
                first_suggestion.get(
                    "explanation", teaching.get("next_step", "先查看建议详情。")
                )
                if first_suggestion
                else teaching.get("next_step", "先查看建议详情。")
            ),
            "hint": (
                first_suggestion.get(
                    "note", "用最小改动先跑通一轮理解 -> 修改 -> 验证。"
                )
                if first_suggestion
                else "用最小改动先跑通一轮理解 -> 修改 -> 验证。"
            ),
        },
    ]


def _build_analysis_sources(runtime_meta: dict[str, Any]) -> list[dict[str, str]]:
    llm_configured = bool(runtime_meta.get("llmConfigured"))
    provider = runtime_meta.get("provider") or "openai"
    model = runtime_meta.get("model") or "default"
    if llm_configured:
        return [
            {
                "id": "ast",
                "label": "AST 结构",
                "source": f"本地 AST + Structure Agent（{provider}/{model}）",
            },
            {
                "id": "performance",
                "label": "性能",
                "source": f"本地性能分析 + Performance Agent（{provider}/{model}）",
            },
            {
                "id": "memory",
                "label": "内存",
                "source": f"本地内存分析 + Memory Agent（{provider}/{model}）",
            },
            {
                "id": "suggestions",
                "label": "优化建议",
                "source": f"Refactor Agent 综合结构/性能/内存结果（{provider}/{model}）",
            },
            {
                "id": "teaching",
                "label": "教学引导",
                "source": f"Teaching Agent 基于多智能体结果生成（{provider}/{model}）",
            },
        ]
    return [
        {"id": "ast", "label": "AST 结构", "source": "本地 AST 分析"},
        {"id": "performance", "label": "性能", "source": "本地性能分析"},
        {"id": "memory", "label": "内存", "source": "本地内存分析"},
        {"id": "suggestions", "label": "优化建议", "source": "本地规则建议"},
        {"id": "teaching", "label": "教学引导", "source": "本地教学回退文案"},
    ]


def _build_runtime_banner(runtime_meta: dict[str, Any]) -> dict[str, Any]:
    llm_configured = bool(runtime_meta.get("llmConfigured"))
    provider = runtime_meta.get("provider") or "openai"
    model = runtime_meta.get("model") or "default"
    if llm_configured:
        return {
            "title": "当前为模型 API 驱动的多智能体分析",
            "body": f"已接入 {provider}/{model}。Structure、Performance、Memory、Refactor、Teaching 五个 agent 会基于本地分析结果补充解释和建议。",
            "mode": "agents-on",
        }
    return {
        "title": "当前为本地回退模式",
        "body": "未检测到模型 API。当前页面仍会显示本地结构、性能、内存分析和教学回退结果，但不会触发模型驱动的多智能体解释。",
        "mode": "agents-off",
    }


def _merge_suggestions(
    local_suggestions: list[dict[str, Any]],
    refactor_suggestions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not refactor_suggestions:
        return local_suggestions

    merged: list[dict[str, Any]] = []
    for index, suggestion in enumerate(refactor_suggestions):
        local_fallback = local_suggestions[index] if index < len(local_suggestions) else {}
        detail = suggestion.get("detail") or local_fallback.get("detail")
        anchors = (
            (detail or {}).get("codeAnchors")
            or suggestion.get("anchors")
            or local_fallback.get("anchors")
            or (local_fallback.get("detail") or {}).get("codeAnchors")
            or []
        )
        merged.append(
            {
                **local_fallback,
                **suggestion,
                "detail": detail,
                "anchors": anchors,
            }
        )
    return merged


def build_frontend_response(state: dict[str, Any]) -> dict[str, Any]:
    local_analysis = state["local_analysis"]
    timings = state.get("timings", {})
    structure = state.get("structure_result", {})
    performance = state.get("performance_result", {})
    memory = state.get("memory_result", {})
    refactor = state.get("refactor_result", {})
    teaching = state.get("teaching_result", {})

    analysis_map = local_analysis["analysisMap"]
    analysis_map["ast"]["summary"] = structure.get(
        "summary", analysis_map["ast"]["summary"]
    )
    analysis_map["ast"]["points"] = structure.get(
        "points", analysis_map["ast"]["points"]
    )
    ast_cards = analysis_map["ast"].get("cards", [])
    focus_fallback = ast_cards[2]["value"] if len(ast_cards) >= 3 else "当前主函数"
    analysis_map["ast"]["focusFunction"] = structure.get(
        "focus_function", focus_fallback
    )

    analysis_map["performance"]["summary"] = performance.get(
        "summary", analysis_map["performance"]["summary"]
    )
    analysis_map["performance"]["points"] = performance.get(
        "points", analysis_map["performance"]["points"]
    )

    analysis_map["memory"]["summary"] = memory.get(
        "summary", analysis_map["memory"]["summary"]
    )
    analysis_map["memory"]["points"] = memory.get(
        "points", analysis_map["memory"]["points"]
    )

    analysis_map["workflow"]["summary"] = teaching.get(
        "overview", analysis_map["workflow"]["summary"]
    )
    analysis_map["workflow"]["points"] = [
        teaching.get("overview", analysis_map["workflow"]["points"][0]),
        teaching.get("beginner_tip", analysis_map["workflow"]["points"][1]),
        teaching.get("next_step", analysis_map["workflow"]["points"][2]),
    ]

    runtime_meta = describe_model_runtime()
    local_suggestions = local_analysis.get("suggestions", [])
    final_suggestions = _merge_suggestions(
        local_suggestions,
        refactor.get("suggestions", []),
    )

    return {
        "heroMetrics": local_analysis["heroMetrics"],
        "analysisMap": analysis_map,
        "suggestions": final_suggestions,
        "stages": local_analysis["stages"],
        "visualizations": local_analysis.get(
            "visualizations", {"ast": "", "performance": ""}
        ),
        "teaching": teaching,
        "teachingPanels": _build_teaching_panels(
            structure, performance, memory, refactor, teaching, local_analysis
        ),
        "analysisSources": _build_analysis_sources(runtime_meta),
        "runtimeBanner": _build_runtime_banner(runtime_meta),
        "meta": {
            **local_analysis.get("meta", {}),
            "taskId": state["task_id"],
            "agentMode": "langgraph",
            "timings": timings,
            **runtime_meta,
        },
    }
