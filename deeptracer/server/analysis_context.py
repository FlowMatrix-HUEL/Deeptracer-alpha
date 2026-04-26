from __future__ import annotations

import ast
from collections import OrderedDict
from pathlib import Path
from threading import Lock
from typing import Any

from deeptracer.graph.workflow import run_analysis_graph_for_input


_CACHE_LIMIT = 24
_cache_lock = Lock()
_analysis_cache: OrderedDict[str, dict[str, Any]] = OrderedDict()


def _resolve_source_code(
    source_code: str | None = None, path_text: str | None = None
) -> str:
    if source_code and source_code.strip():
        return source_code
    if path_text:
        target = Path(path_text).expanduser()
        if target.exists():
            return target.read_text(encoding="utf-8")
    return ""


def _cache_get_record(task_id: str | None) -> dict[str, Any] | None:
    if not task_id:
        return None
    with _cache_lock:
        record = _analysis_cache.get(task_id)
        if record is None:
            return None
        _analysis_cache.move_to_end(task_id)
        return record


def _store_analysis_record(payload: dict[str, Any], source_code: str) -> dict[str, Any]:
    task_id = str(payload.get("meta", {}).get("taskId") or "").strip()
    if not task_id:
        return payload
    with _cache_lock:
        _analysis_cache[task_id] = {"payload": payload, "code": source_code}
        _analysis_cache.move_to_end(task_id)
        while len(_analysis_cache) > _CACHE_LIMIT:
            _analysis_cache.popitem(last=False)
    return payload


def _build_anchor_snippet(
    source_lines: list[str], line: int | None, radius: int = 1
) -> str:
    if not line:
        return ""
    start = max(1, line - radius)
    end = min(len(source_lines), line + radius)
    snippet_lines = []
    for current in range(start, end + 1):
        snippet_lines.append(f"{current}: {source_lines[current - 1]}")
    return "\n".join(snippet_lines)


def _extract_code_anchors(source_code: str) -> list[dict[str, Any]]:
    if not source_code.strip():
        return []

    source_lines = source_code.splitlines()
    anchors: list[dict[str, Any]] = []
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return anchors

    seen: set[tuple[str, str, int | None]] = set()

    def add_anchor(kind: str, label: str, line: int | None) -> None:
        key = (kind, label, line)
        if key in seen or not label:
            return
        seen.add(key)
        anchors.append(
            {
                "kind": kind,
                "label": label,
                "line": line,
                "snippet": _build_anchor_snippet(source_lines, line),
            }
        )

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            add_anchor("function", node.name, getattr(node, "lineno", None))
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    add_anchor("variable", target.id, getattr(target, "lineno", None))
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                add_anchor("call", node.func.id, getattr(node, "lineno", None))

    return anchors[:12]


def build_grounding_bundle(
    payload: dict[str, Any], source_code: str, display_name: str
) -> dict[str, Any]:
    analysis_map = payload.get("analysisMap", {})
    suggestions = payload.get("suggestions", [])
    suggestion_anchors = []
    for suggestion in suggestions[:3]:
        detail = suggestion.get("detail") or {}
        anchors = detail.get("codeAnchors") or suggestion.get("anchors") or []
        suggestion_anchors.extend(anchor for anchor in anchors if isinstance(anchor, dict))

    code_anchors = _extract_code_anchors(source_code)
    merged_anchors = []
    seen: set[tuple[str, str, int | None]] = set()
    for anchor in suggestion_anchors + code_anchors:
        key = (anchor.get("kind"), anchor.get("label"), anchor.get("line"))
        if key in seen:
            continue
        seen.add(key)
        merged_anchors.append(anchor)

    return {
        "displayName": display_name,
        "code": source_code,
        "analysisSummary": {
            "workflow": analysis_map.get("workflow", {}).get("summary", ""),
            "ast": analysis_map.get("ast", {}).get("summary", ""),
            "performance": analysis_map.get("performance", {}).get("summary", ""),
            "memory": analysis_map.get("memory", {}).get("summary", ""),
        },
        "anchors": merged_anchors[:10],
        "suggestions": suggestions[:3],
    }


def build_analysis_payload(
    *,
    path_text: str | None = None,
    source_code: str | None = None,
    display_name: str | None = None,
    task_id: str | None = None,
    analysis_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cached_record = _cache_get_record(task_id)
    if cached_record is not None:
        return cached_record["payload"]

    snapshot_task_id = (
        str(analysis_snapshot.get("meta", {}).get("taskId") or "").strip()
        if analysis_snapshot
        else ""
    )
    if (
        analysis_snapshot
        and analysis_snapshot.get("analysisMap")
        and (not task_id or snapshot_task_id == task_id or not snapshot_task_id)
    ):
        resolved_code = _resolve_source_code(source_code=source_code, path_text=path_text)
        return _store_analysis_record(analysis_snapshot, resolved_code)

    resolved_code = _resolve_source_code(source_code=source_code, path_text=path_text)
    payload = run_analysis_graph_for_input(
        path_text=path_text,
        source_code=source_code,
        display_name=display_name,
    )
    return _store_analysis_record(payload, resolved_code)


def build_chat_context(
    *,
    path_text: str | None = None,
    source_code: str | None = None,
    display_name: str | None = None,
    task_id: str | None = None,
    analysis_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cached_record = _cache_get_record(task_id)
    payload = build_analysis_payload(
        path_text=path_text,
        source_code=source_code,
        display_name=display_name,
        task_id=task_id,
        analysis_snapshot=analysis_snapshot,
    )
    meta = payload.get("meta", {})
    resolved_code = (
        source_code
        or (cached_record or {}).get("code")
        or _resolve_source_code(source_code=source_code, path_text=path_text)
    )
    resolved_display_name = display_name or meta.get("targetPath") or "当前代码"
    grounding = build_grounding_bundle(payload, resolved_code, resolved_display_name)
    return {
        "taskId": meta.get("taskId"),
        "displayName": resolved_display_name,
        "analysis": payload,
        "code": resolved_code,
        "grounding": grounding,
    }
