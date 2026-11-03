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
    llm_configured = bool(
        runtime_meta.get("agentsEnabled", True)
        and runtime_meta.get("llmConfigured")
    )
    provider = runtime_meta.get("provider") or "openai"
    model = runtime_meta.get("model") or "default"
    statuses = runtime_meta.get("agentStatuses") or {}

    def source(agent: str, label: str, local: str, model_source: str) -> dict[str, str]:
        if llm_configured and statuses.get(agent) == "model":
            return {"id": agent, "label": label, "source": f"{model_source}（{provider}/{model}）"}
        return {"id": agent, "label": label, "source": local}

    return [
        source("structure", "AST 结构", "本地 AST 分析", "本地 AST + Structure Agent"),
        source("performance", "性能", "本地性能分析", "本地性能分析 + Performance Agent"),
        source("memory", "内存", "本地内存分析", "本地内存分析 + Memory Agent"),
        source(
            "refactor",
            "优化建议",
            "本地规则建议",
            "Refactor Agent 综合结构/性能/内存结果",
        ),
        source(
            "teaching",
            "教学引导",
            "本地教学回退文案",
            "Teaching Agent 基于多智能体结果生成",
        ),
    ]


def _build_runtime_banner(runtime_meta: dict[str, Any]) -> dict[str, Any]:
    agents_enabled = bool(runtime_meta.get("agentsEnabled", True))
    llm_configured = bool(runtime_meta.get("llmConfigured"))
    provider = runtime_meta.get("provider") or "openai"
    model = runtime_meta.get("model") or "default"
    mode = runtime_meta.get("agentMode")
    statuses = runtime_meta.get("agentStatuses") or {}
    fallback_agents = [
        agent
        for agent, status in statuses.items()
        if status == "fallback"
    ]
    model_count = sum(status == "model" for status in statuses.values())
    if not agents_enabled:
        return {
            "title": "Agent 已关闭，当前仅运行本地分析",
            "body": "模型配置会保留，但本轮不会创建模型客户端或发送网络请求。结构、性能、内存、规则建议和 AI 答疑均使用本地回退。",
            "mode": "agents-off",
        }
    if mode == "agents-on":
        return {
            "title": "当前为模型 API 驱动的多智能体分析",
            "body": f"已接入 {provider}/{model}。Structure、Performance、Memory、Refactor、Teaching 五个 agent 会基于本地分析结果补充解释和建议。",
            "mode": "agents-on",
        }
    if llm_configured and fallback_agents:
        agent_names = {
            "structure": "结构 Agent",
            "performance": "性能 Agent",
            "memory": "内存 Agent",
            "refactor": "重构 Agent",
            "teaching": "教学 Agent",
        }
        names = "、".join(agent_names.get(agent, agent) for agent in fallback_agents)
        return {
            "title": (
                "模型调用未成功，已自动使用本地回退"
                if model_count == 0
                else "模型部分不可用，已自动使用本地回退"
            ),
            "body": f"已配置 {provider}/{model}，但 {names} 没有返回有效的模型结果。页面中的相应内容来自本地分析，不会伪装成模型结论。",
            "mode": "agents-partial",
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

    local_by_id = {
        str(item.get("id")): item
        for item in local_suggestions
        if item.get("id")
    }
    anchors_by_id = {
        str(anchor.get("id")): anchor
        for item in local_suggestions
        for anchor in (
            (item.get("detail") or {}).get("codeAnchors")
            or item.get("anchors")
            or []
        )
        if isinstance(anchor, dict) and anchor.get("id")
    }

    merged: list[dict[str, Any]] = []
    for suggestion in refactor_suggestions:
        basis_id = (
            suggestion.get("based_on_suggestion_id")
            or suggestion.get("id")
            or ""
        )
        local_fallback = local_by_id.get(str(basis_id), {})
        detail = suggestion.get("detail")
        if not isinstance(detail, dict):
            detail = local_fallback.get("detail") or {}

        requested_anchor_ids = suggestion.get("anchor_ids") or []
        anchors = [
            anchors_by_id[anchor_id]
            for anchor_id in requested_anchor_ids
            if str(anchor_id) in anchors_by_id
        ]
        if not anchors and local_fallback:
            anchors = (
                (local_fallback.get("detail") or {}).get("codeAnchors")
                or local_fallback.get("anchors")
                or []
            )
        merged.append(
            {
                **local_fallback,
                **suggestion,
                "detail": detail,
                "anchors": anchors,
                "anchor_ids": [
                    anchor.get("id") for anchor in anchors if anchor.get("id")
                ],
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
    agent_results = {
        "structure": structure,
        "performance": performance,
        "memory": memory,
        "refactor": refactor,
        "teaching": teaching,
    }
    agent_statuses = {
        name: result.get("_agentStatus", "fallback")
        for name, result in agent_results.items()
    }
    model_count = sum(status == "model" for status in agent_statuses.values())
    runtime_meta["agentStatuses"] = agent_statuses
    if model_count == len(agent_statuses):
        runtime_meta["agentMode"] = "agents-on"
    elif model_count:
        runtime_meta["agentMode"] = "agents-partial"
    else:
        runtime_meta["agentMode"] = "agents-off"

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
            "timings": timings,
            **runtime_meta,
        },
    }
