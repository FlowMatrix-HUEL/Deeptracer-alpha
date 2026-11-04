from __future__ import annotations

import pytest

import deeptracer.server.edit_service as edit_service
import deeptracer.modeling.llm as llm_module
from deeptracer.server.edit_service import (
    apply_patch_plan,
    generate_patch_plan,
    verify_edit_pair,
)
from deeptracer.server.source_refs import hash_source


PRINT_SOURCE = (
    "def report():\n"
    "    print('one')\n"
    "    print('two')\n"
    "    return 3\n"
    "\n"
    "report()\n"
)


def test_local_print_suggestion_generates_a_validated_patch():
    plan = generate_patch_plan(
        PRINT_SOURCE,
        {"id": "reduce-print", "title": "收一收输出"},
        allow_model=False,
    )

    assert plan["available"] is True
    assert plan["generationMode"] == "local-rule"
    assert plan["plan"]["source_hash"] == hash_source(PRINT_SOURCE)
    assert len(plan["plan"]["edits"]) == 2
    assert "--- before.py" in plan["previewDiff"]

    applied = apply_patch_plan(PRINT_SOURCE, plan["plan"])
    assert "# [DeepTracer] print('one')" in applied["code"]
    assert applied["afterHash"] == hash_source(applied["code"])


def test_print_only_block_gets_pass_to_remain_valid_python():
    source = "def report():\n    print('only')\n"
    result = generate_patch_plan(
        source,
        {"id": "reduce-print"},
        allow_model=False,
    )

    assert result["available"] is True
    applied = apply_patch_plan(source, result["plan"])
    assert "# [DeepTracer] print('only')" in applied["code"]
    assert "    pass" in applied["code"]


def test_complex_suggestion_does_not_invent_a_model_free_patch():
    result = generate_patch_plan(
        PRINT_SOURCE,
        {"id": "split-function", "title": "拆分函数"},
        allow_model=False,
    )

    assert result["available"] is False
    assert "模型辅助" in result["reason"]


def test_complex_suggestion_without_model_reports_unavailable(monkeypatch):
    monkeypatch.setattr(llm_module, "get_chat_model", lambda optional=True: None)

    result = generate_patch_plan(
        PRINT_SOURCE,
        {"id": "split-function", "title": "拆分函数"},
        allow_model=True,
    )

    assert result["available"] is False
    assert "未启用" in result["reason"] or "未配置" in result["reason"]


def test_patch_rejects_stale_source_hash():
    plan = generate_patch_plan(
        PRINT_SOURCE,
        {"id": "reduce-print"},
        allow_model=False,
    )["plan"]

    with pytest.raises(ValueError, match="已经变化"):
        apply_patch_plan(PRINT_SOURCE + "\n# changed\n", plan)


def test_patch_rejects_mismatched_expected_source():
    plan = generate_patch_plan(
        PRINT_SOURCE,
        {"id": "reduce-print"},
        allow_model=False,
    )["plan"]
    plan["edits"][0]["expected_text"] = "    print('different')"

    with pytest.raises(ValueError, match="原代码与 Patch 基线不一致"):
        apply_patch_plan(PRINT_SOURCE, plan)


def test_verify_edit_pair_compares_before_and_after(monkeypatch):
    outputs = iter(
        [
            {
                "durationMs": 10.0,
                "stdout": "hello\n",
                "stderr": "",
                "runtimeError": None,
                "traceback": "",
                "exitCode": 0,
            },
            {
                "durationMs": 8.0,
                "stdout": "hello\n",
                "stderr": "",
                "runtimeError": None,
                "traceback": "",
                "exitCode": 0,
            },
        ]
    )
    monkeypatch.setattr(edit_service, "execute_python_code", lambda code: next(outputs))

    result = verify_edit_pair("print('hello')", "print('hello')  # faster")

    assert result["syntax"]["passed"] is True
    assert result["runtime"]["passed"] is True
    assert result["behavior"] == "unchanged"
    assert result["performance"]["durationDeltaMs"] == -2.0
