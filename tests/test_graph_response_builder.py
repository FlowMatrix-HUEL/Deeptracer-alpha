from __future__ import annotations

from deeptracer.graph.response_builder import _merge_suggestions, build_frontend_response


def test_build_frontend_response_adds_optional_runtime_fields():
    state = {
        "task_id": "task-123",
        "timings": {"total_ms": 12.5, "core_agents_ms": 3.4},
        "local_analysis": {
            "heroMetrics": [{"label": "分析对象", "value": "demo.py"}],
            "analysisMap": {
                "workflow": {
                    "title": "概览",
                    "summary": "旧概览",
                    "points": ["a", "b", "c"],
                },
                "ast": {
                    "title": "结构",
                    "summary": "旧结构",
                    "points": ["ast"],
                    "cards": [{}, {}, {"value": "fallback_func"}],
                },
                "performance": {
                    "title": "性能",
                    "summary": "旧性能",
                    "points": ["perf"],
                },
                "memory": {
                    "title": "内存",
                    "summary": "旧内存",
                    "points": ["mem"],
                },
            },
            "suggestions": [{"id": "local", "title": "本地建议"}],
            "stages": [["输入代码", "说明"]],
            "visualizations": {"ast": "<html></html>", "performance": ""},
            "meta": {"targetPath": "demo.py"},
        },
        "structure_result": {
            "summary": "新结构",
            "points": ["结构说明"],
            "focus_function": "focus_func",
        },
        "performance_result": {
            "summary": "新性能",
            "points": ["性能说明"],
            "hottest_function": "focus_func",
        },
        "memory_result": {"summary": "新内存", "points": ["内存说明"]},
        "refactor_result": {
            "suggestions": [{"id": "refactor", "title": "重构建议", "explanation": "解释"}]
        },
        "teaching_result": {
            "overview": "教学概览",
            "beginner_tip": "教学提示",
            "next_step": "教学下一步",
        },
    }

    payload = build_frontend_response(state)

    assert payload["analysisMap"]["ast"]["focusFunction"] == "focus_func"
    assert payload["analysisMap"]["workflow"]["summary"] == "教学概览"
    assert payload["teachingPanels"][0]["id"] == "inspect-first"
    assert payload["analysisSources"]
    assert payload["runtimeBanner"]["mode"] in {"agents-on", "agents-partial", "agents-off"}
    assert payload["meta"]["taskId"] == "task-123"
    assert payload["meta"]["timings"]["core_agents_ms"] == 3.4
    assert payload["suggestions"][0]["id"] == "refactor"


def test_merge_suggestions_binds_anchors_by_stable_id_not_array_order():
    local = [
        {
            "id": "split-primary",
            "title": "拆分主函数",
            "detail": {
                "codeAnchors": [{"id": "primary", "label": "primary"}],
            },
        },
        {
            "id": "loop-secondary",
            "title": "检查次函数循环",
            "detail": {
                "codeAnchors": [{"id": "secondary", "label": "secondary"}],
            },
        },
    ]
    refactor = [
        {
            "id": "loop-secondary",
            "based_on_suggestion_id": "loop-secondary",
            "anchor_ids": ["secondary"],
            "title": "检查次函数循环",
        },
        {
            "id": "split-primary",
            "based_on_suggestion_id": "split-primary",
            "anchor_ids": ["primary"],
            "title": "拆分主函数",
        },
    ]

    merged = _merge_suggestions(local, refactor)

    assert merged[0]["anchors"][0]["id"] == "secondary"
    assert merged[1]["anchors"][0]["id"] == "primary"


def test_unknown_model_suggestion_does_not_inherit_unrelated_anchor():
    local = [
        {
            "id": "known",
            "detail": {"codeAnchors": [{"id": "known-anchor", "label": "known"}]},
        }
    ]
    refactor = [
        {
            "id": "new-idea",
            "based_on_suggestion_id": "",
            "anchor_ids": ["invented-anchor"],
            "title": "新建议",
        }
    ]

    merged = _merge_suggestions(local, refactor)

    assert merged[0]["anchors"] == []
