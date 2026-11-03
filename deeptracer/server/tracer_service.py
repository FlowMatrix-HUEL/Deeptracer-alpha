from __future__ import annotations

import ast
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from deeptracer.tracer_support import get_tracer_python_path


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_CALL_RE = re.compile(r"^(?P<prefix>(?:\|  )*)-> (?P<body>.+)$")
_RETURN_RE = re.compile(
    r"^(?P<prefix>(?:\|  )*)<- (?P<name>\S+) returned (?P<value>.*?)"
    r"(?: \| cost=(?P<cost>[0-9.eE+-]+)s)?$"
)
_RAISE_RE = re.compile(
    r"^(?P<prefix>(?:\|  )*)<- (?P<name>\S+) raised (?P<error>.*)$"
)


def execute_tracer_trace(
    *,
    source_code: str,
    functions: list[str],
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    code = source_code.strip("\n")
    if not code.strip():
        raise ValueError("代码为空，无法执行调用追踪。")
    tree = ast.parse(code)
    available_names = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    target_names = []
    for function_name in functions:
        base_name = str(function_name).rsplit(".", 1)[-1]
        if base_name not in available_names:
            raise ValueError(f"找不到可追踪函数：{function_name}")
        if base_name not in target_names:
            target_names.append(base_name)
    if not target_names:
        raise ValueError("请至少选择一个需要追踪的函数。")

    normalized_options = _normalize_options(options)
    timeout_seconds = float(
        os.getenv("DEEPTRACER_TRACER_TIMEOUT_SECONDS", "8")
    )
    with tempfile.TemporaryDirectory(prefix="deeptracer-trace-") as temp_dir:
        source_path = Path(temp_dir) / "traced_script.py"
        source_path.write_text(code + "\n", encoding="utf-8")
        environment = os.environ.copy()
        project_root = str(Path(__file__).resolve().parents[2])
        python_paths = [
            project_root,
            get_tracer_python_path(),
            environment.get("PYTHONPATH"),
        ]
        environment["PYTHONPATH"] = os.pathsep.join(
            item for item in python_paths if item
        )
        environment["PYTHONIOENCODING"] = "utf-8"
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "deeptracer.server.tracer_worker",
                str(source_path),
            ],
            cwd=temp_dir,
            env=environment,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            start_new_session=os.name == "posix",
        )
        payload = {
            "targetNames": target_names,
            "options": normalized_options,
        }
        try:
            stdout, stderr = process.communicate(
                json.dumps(payload, ensure_ascii=False),
                timeout=max(0.1, timeout_seconds),
            )
        except subprocess.TimeoutExpired:
            _terminate_process_tree(process)
            process.communicate()
            raise TimeoutError(
                f"调用追踪超过 {timeout_seconds:g} 秒，已终止执行。"
            )

    if process.returncode != 0:
        detail = (stderr or stdout or "").strip()
        raise RuntimeError(
            "Tracer 执行失败"
            + (f"：{detail[-1000:]}" if detail else f"（退出码 {process.returncode}）")
        )
    try:
        result = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Tracer 返回了无效结果。") from exc
    if not isinstance(result, dict):
        raise RuntimeError("Tracer 返回了无效结果。")

    roots = build_trace_tree(result.get("traceLines") or [])
    return {
        **result,
        "traceTree": roots,
        "callCount": _count_nodes(roots),
        "selectedFunctions": functions,
        "options": normalized_options,
    }


def build_trace_tree(trace_lines: list[str]) -> list[dict[str, Any]]:
    roots: list[dict[str, Any]] = []
    stack: list[dict[str, Any]] = []
    for raw_line in trace_lines:
        line = _ANSI_RE.sub("", str(raw_line))
        call_match = _CALL_RE.match(line)
        if call_match:
            depth = len(call_match.group("prefix")) // 3
            body = call_match.group("body")
            function_name = body.split("(", 1)[0]
            node = {
                "kind": "call",
                "name": function_name,
                "arguments": body,
                "argumentText": body[len(function_name):] or "()",
                "returned": None,
                "costSeconds": None,
                "error": None,
                "children": [],
            }
            stack = stack[:depth]
            if depth > 0 and stack:
                stack[-1]["children"].append(node)
            else:
                roots.append(node)
            stack.append(node)
            continue

        return_match = _RETURN_RE.match(line)
        if return_match:
            depth = len(return_match.group("prefix")) // 3
            index = depth - 1
            if 0 <= index < len(stack):
                node = stack[index]
                stack = stack[:index]
            elif stack:
                node = stack.pop()
            else:
                continue
            node["returned"] = return_match.group("value")
            cost = return_match.group("cost")
            node["costSeconds"] = float(cost) if cost else None
            continue

        raise_match = _RAISE_RE.match(line)
        if raise_match:
            depth = len(raise_match.group("prefix")) // 3
            index = depth - 1
            if 0 <= index < len(stack):
                node = stack[index]
                stack = stack[:index]
            elif stack:
                node = stack.pop()
            else:
                continue
            node["error"] = raise_match.group("error")
    return roots


def _normalize_options(options: dict[str, Any] | None) -> dict[str, bool]:
    options = options or {}
    exception_trace = bool(options.get("exceptionTrace", False))
    return {
        "timeTrace": bool(options.get("timeTrace", False)),
        "useColor": bool(options.get("useColor", False)),
        "exceptionTrace": exception_trace,
        "showLocals": exception_trace and bool(options.get("showLocals", False)),
    }


def _count_nodes(nodes: list[dict[str, Any]]) -> int:
    return sum(1 + _count_nodes(node.get("children") or []) for node in nodes)


def _terminate_process_tree(process: subprocess.Popen) -> None:
    try:
        if os.name == "posix":
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        else:
            process.kill()
    except OSError:
        pass
