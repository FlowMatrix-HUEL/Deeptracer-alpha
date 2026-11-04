from __future__ import annotations

import ast
import difflib
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from deeptracer.server.run_service import execute_python_code
from deeptracer.server.source_refs import hash_source


class SourceEdit(BaseModel):
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=0)
    expected_text: str
    replacement_text: str
    reason: str = ""


class PatchPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: f"patch-{uuid4()}")
    source_hash: str = ""
    suggestion_id: str
    title: str
    summary: str = ""
    risk: str = "medium"
    confidence: str = "medium"
    edits: list[SourceEdit]
    verification_notes: list[str] = Field(default_factory=list)


def generate_patch_plan(
    source_code: str,
    suggestion: dict[str, Any],
    *,
    display_name: str = "当前代码",
    allow_model: bool = True,
) -> dict[str, Any]:
    tree = ast.parse(source_code)
    suggestion_id = str(suggestion.get("id") or "").strip()
    local_plan = _generate_local_plan(tree, source_code, suggestion)
    if local_plan is not None:
        return _plan_payload(local_plan, source_code, mode="local-rule")

    if not allow_model:
        return _unavailable(
            suggestion_id,
            "该建议需要模型辅助生成候选修改，当前调用不允许模型。",
        )

    model_plan, reason = _generate_model_plan(
        source_code,
        suggestion,
        display_name=display_name,
    )
    if model_plan is None:
        return _unavailable(suggestion_id, reason)
    return _plan_payload(model_plan, source_code, mode="model-assisted")


def apply_patch_plan(source_code: str, plan_data: dict[str, Any]) -> dict[str, Any]:
    plan = PatchPlan.model_validate(plan_data)
    current_hash = hash_source(source_code)
    if plan.source_hash != current_hash:
        raise ValueError("代码在生成 Patch 后已经变化，请重新生成修改方案。")
    if not plan.edits:
        raise ValueError("Patch 不包含任何修改。")

    source_lines = source_code.splitlines()
    ordered_edits = sorted(
        plan.edits,
        key=lambda edit: (edit.start_line, edit.end_line),
        reverse=True,
    )
    previous_start: int | None = None
    for edit in ordered_edits:
        if edit.end_line < edit.start_line - 1:
            raise ValueError("Patch 行范围无效。")
        if previous_start is not None and edit.end_line >= previous_start:
            raise ValueError("Patch 中包含重叠的修改范围。")
        expected_lines = edit.expected_text.splitlines()
        start_index = edit.start_line - 1
        end_index = edit.end_line

        if edit.end_line == edit.start_line - 1:
            actual_lines: list[str] = []
            insert_index = start_index
        else:
            actual_lines = source_lines[start_index:end_index]
            insert_index = start_index
        if actual_lines != expected_lines:
            raise ValueError(
                f"第 {edit.start_line}-{edit.end_line} 行的原代码与 Patch 基线不一致。"
            )

        replacement_lines = (
            edit.replacement_text.splitlines()
            if edit.replacement_text
            else []
        )
        source_lines[insert_index:end_index] = replacement_lines
        previous_start = edit.start_line

    patched_code = "\n".join(source_lines)
    if source_code.endswith("\n"):
        patched_code += "\n"
    try:
        ast.parse(patched_code)
    except SyntaxError as exc:
        raise ValueError(f"Patch 应用后生成无效 Python：{exc.msg}（第 {exc.lineno} 行）") from exc

    unified_diff = "".join(
        difflib.unified_diff(
            source_code.splitlines(keepends=True),
            patched_code.splitlines(keepends=True),
            fromfile="before.py",
            tofile="after.py",
        )
    )
    return {
        "planId": plan.plan_id,
        "beforeHash": current_hash,
        "afterHash": hash_source(patched_code),
        "code": patched_code,
        "unifiedDiff": unified_diff,
        "appliedEdits": len(plan.edits),
    }


def verify_edit_pair(
    before_code: str,
    after_code: str,
) -> dict[str, Any]:
    before_syntax_error = _syntax_error(before_code)
    after_syntax_error = _syntax_error(after_code)
    syntax_passed = before_syntax_error is None and after_syntax_error is None
    before_result = _safe_run(before_code)
    after_result = _safe_run(after_code)
    behavior = _behavior_status(before_result, after_result)
    return {
        "syntax": {
            "passed": syntax_passed,
            "beforeError": before_syntax_error,
            "afterError": after_syntax_error,
        },
        "runtime": {
            "passed": bool(after_result.get("exitCode") == 0),
        },
        "tests": {
            "available": False,
            "mode": "smoke",
            "note": (
                "当前验证会分别运行修改前后代码；浏览器上传文件没有项目路径，"
                "因此不会自动发现旁边的 pytest/unittest 文件。"
            ),
        },
        "before": before_result,
        "after": after_result,
        "behavior": behavior,
        "performance": {
            "durationDeltaMs": round(
                float(after_result.get("durationMs") or 0)
                - float(before_result.get("durationMs") or 0),
                2,
            ),
        },
    }


def _generate_local_plan(
    tree: ast.AST,
    source_code: str,
    suggestion: dict[str, Any],
) -> PatchPlan | None:
    suggestion_id = str(suggestion.get("id") or "")
    source_lines = source_code.splitlines()
    edits: list[SourceEdit] = []
    if suggestion_id == "reduce-print":
        parent_by_child = {
            child: parent
            for parent in ast.walk(tree)
            for child in ast.iter_child_nodes(parent)
        }
        print_nodes = [
            node
            for node in ast.walk(tree)
            if (
                isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == "print"
            )
        ]
        print_node_ids = {id(node) for node in print_nodes}
        needs_pass: set[int] = set()
        for node in print_nodes:
            parent = parent_by_child.get(node)
            body = getattr(parent, "body", None)
            if not isinstance(body, list):
                continue
            if all(
                statement is node or id(statement) in print_node_ids
                for statement in body
            ):
                needs_pass.add(id(node))

        pass_added: set[int] = set()
        for node in print_nodes:
            start = getattr(node, "lineno", None)
            end = getattr(node, "end_lineno", start)
            if not start or not end or start != end:
                continue
            expected = source_lines[start - 1]
            stripped = expected.lstrip()
            if stripped.startswith("#"):
                continue
            prefix = expected[: len(expected) - len(stripped)]
            parent = parent_by_child.get(node)
            if id(node) in needs_pass and id(parent) not in pass_added:
                replacement = f"{prefix}# [DeepTracer] {stripped}\n{prefix}pass"
                pass_added.add(id(parent))
            else:
                replacement = f"{prefix}# [DeepTracer] {stripped}"
            edits.append(
                SourceEdit(
                    start_line=start,
                    end_line=end,
                    expected_text=expected,
                    replacement_text=replacement,
                    reason="将临时调试输出注释掉，减少运行输出噪音。",
                )
            )
        if edits:
            return PatchPlan(
                source_hash=hash_source(source_code),
                suggestion_id=suggestion_id,
                title="注释临时调试输出",
                summary=f"准备注释 {len(edits)} 处单行 print 调用。",
                risk="low",
                confidence="high",
                edits=edits,
                verification_notes=[
                    "应用后会运行修改前后代码并比较 stdout/stderr。",
                    "这是行为修改，请确认这些 print 不是程序必要输出。",
                ],
            )
    return None


def _generate_model_plan(
    source_code: str,
    suggestion: dict[str, Any],
    *,
    display_name: str,
) -> tuple[PatchPlan | None, str]:
    try:
        from langchain_core.prompts import ChatPromptTemplate

        from deeptracer.agents.utils import JSON_OUTPUT_INSTRUCTION, to_json_text
        from deeptracer.modeling.llm import get_chat_model

        llm = get_chat_model(optional=True)
        if llm is None:
            return None, "Agent 未启用或未配置模型，复杂建议无法生成候选 Patch。"
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You produce a minimal, reviewable Python source patch for the supplied "
                    "suggestion. Return exact 1-indexed inclusive line ranges, the exact "
                    "expected source text, and replacement text. Never invent code that is not "
                    "grounded in the supplied file. If a safe patch is not possible, return an "
                    "empty edits list. "
                    f"{JSON_OUTPUT_INSTRUCTION}",
                ),
                (
                    "human",
                    "File: {display_name}\nSuggestion:\n{suggestion}\n\nSource:\n{code}\n\n"
                    "Return the structured PatchPlan.",
                ),
            ]
        )
        plan = (prompt | llm.with_structured_output(PatchPlan)).invoke(
            {
                "display_name": display_name,
                "suggestion": to_json_text(suggestion),
                "code": source_code,
            }
        )
        if not plan.edits:
            return None, "模型认为该建议没有足够安全的最小 Patch，请将其作为咨询建议处理。"
        plan.source_hash = hash_source(source_code)
        plan.suggestion_id = str(suggestion.get("id") or plan.suggestion_id)
        apply_patch_plan(source_code, plan.model_dump())
        return plan, ""
    except Exception as exc:
        return None, f"候选 Patch 生成或校验失败：{type(exc).__name__}: {exc}"


def _plan_payload(
    plan: PatchPlan,
    source_code: str,
    *,
    mode: str,
) -> dict[str, Any]:
    preview = apply_patch_plan(source_code, plan.model_dump())
    return {
        "available": True,
        "generationMode": mode,
        "plan": plan.model_dump(),
        "previewDiff": preview["unifiedDiff"],
        "afterCode": preview["code"],
        "afterHash": preview["afterHash"],
    }


def _unavailable(suggestion_id: str, reason: str) -> dict[str, Any]:
    return {
        "available": False,
        "suggestionId": suggestion_id,
        "reason": reason,
    }


def _syntax_error(source_code: str) -> str | None:
    try:
        ast.parse(source_code)
    except SyntaxError as exc:
        return f"{exc.msg}（第 {exc.lineno} 行）"
    return None


def _safe_run(source_code: str) -> dict[str, Any]:
    try:
        result = execute_python_code(source_code)
    except Exception as exc:
        return {
            "durationMs": 0,
            "stdout": "",
            "stderr": "",
            "runtimeError": f"{type(exc).__name__}: {exc}",
            "traceback": "",
            "exitCode": 1,
        }
    return {
        key: result.get(key)
        for key in (
            "durationMs",
            "stdout",
            "stderr",
            "runtimeError",
            "traceback",
            "exitCode",
        )
    }


def _behavior_status(
    before_result: dict[str, Any],
    after_result: dict[str, Any],
) -> str:
    before_exit = before_result.get("exitCode")
    after_exit = after_result.get("exitCode")
    if before_exit == 0 and after_exit != 0:
        return "regressed"
    if before_exit != 0 and after_exit == 0:
        return "improved"
    before_output = (
        before_result.get("stdout") or "",
        before_result.get("stderr") or "",
        before_result.get("runtimeError") or "",
    )
    after_output = (
        after_result.get("stdout") or "",
        after_result.get("stderr") or "",
        after_result.get("runtimeError") or "",
    )
    return "unchanged" if before_output == after_output else "changed"
