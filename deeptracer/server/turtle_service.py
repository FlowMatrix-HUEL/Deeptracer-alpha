from __future__ import annotations

import ast
import json
import math
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any

from deeptracer.tracer_support import get_tracer_python_path


_STUDENT_PREAMBLE = """import turtle


def draw_scene(artist, screen):
    # 绘图逻辑集中在函数中，便于复用和测试。
    forward = artist.forward
    backward = artist.backward
    back = artist.backward
    left = artist.left
    right = artist.right
    penup = artist.penup
    pendown = artist.pendown
    pencolor = artist.pencolor
    pensize = artist.pensize
    fillcolor = artist.fillcolor
    begin_fill = artist.begin_fill
    end_fill = artist.end_fill
    circle = artist.circle
    goto = artist.goto
    setheading = artist.setheading
    dot = artist.dot
    speed = artist.speed

"""

_STUDENT_SUFFIX = """
def main():
    screen = turtle.Screen()
    screen.title("我的 Turtle 图形")
    artist = turtle.Turtle()
    artist.speed(3)
    draw_scene(artist, screen)
    screen.mainloop()


if __name__ == "__main__":
    main()
"""


def compile_turtle_source(source: str) -> dict[str, Any]:
    code = source.strip("\n")
    if not code.strip():
        return _empty_result("请输入至少一条 Turtle 指令。")

    generated_code, source_start_line = build_standard_code(code)
    program_features = analyze_program_features(code)
    timeout_seconds = float(os.getenv("DEEPTRACER_TURTLE_TIMEOUT_SECONDS", "4"))
    project_root = str(Path(__file__).resolve().parents[2])
    environment = os.environ.copy()
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
        [sys.executable, "-m", "deeptracer.server.turtle_worker"],
        cwd=project_root,
        env=environment,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        start_new_session=os.name == "posix",
    )
    try:
        stdout, stderr = process.communicate(
            json.dumps({"source": code}, ensure_ascii=False),
            timeout=max(0.1, timeout_seconds),
        )
    except subprocess.TimeoutExpired:
        _terminate_process_tree(process)
        process.communicate()
        return {
            **_empty_result("程序运行超时，请检查是否存在无限循环。"),
            "generatedCode": generated_code,
            "sourceStartLine": source_start_line,
            "lineMap": _line_map(code, source_start_line),
            "programFeatures": program_features,
        }

    if process.returncode != 0:
        detail = (stderr or stdout or "").strip()
        return {
            **_empty_result(
                "Turtle 教学执行器异常退出"
                + (f"：{detail[-800:]}" if detail else "")
            ),
            "generatedCode": generated_code,
            "sourceStartLine": source_start_line,
            "lineMap": _line_map(code, source_start_line),
            "programFeatures": program_features,
        }

    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return {
            **_empty_result("Turtle 教学执行器没有返回有效结果。"),
            "generatedCode": generated_code,
            "sourceStartLine": source_start_line,
            "lineMap": _line_map(code, source_start_line),
            "programFeatures": program_features,
        }

    source_lines = code.splitlines()
    steps = payload.get("steps") or []
    for step in steps:
        line = int(step.get("line") or 1)
        step["standardLine"] = source_start_line + max(0, line - 1)
        step["sourceText"] = source_lines[line - 1] if 0 < line <= len(source_lines) else ""
    payload["steps"] = steps
    payload["generatedCode"] = generated_code
    payload["sourceStartLine"] = source_start_line
    payload["lineMap"] = _line_map(code, source_start_line)
    payload["programFeatures"] = program_features
    if payload.get("error"):
        payload["error"] = translate_turtle_error(payload["error"])
    return payload


def analyze_program_features(source: str) -> dict[str, Any]:
    """Return lightweight teaching metadata without executing user code."""
    features: dict[str, Any] = {
        "validSyntax": True,
        "loops": 0,
        "loopIterations": [],
        "functions": [],
        "calls": [],
        "conditionals": 0,
        "assignments": 0,
        "eventBindings": [],
    }
    try:
        tree = ast.parse(source)
    except SyntaxError:
        features["validSyntax"] = False
        return features

    calls: list[str] = []
    event_bindings: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
            features["loops"] += 1
            if isinstance(node, ast.For) and _range_iteration_count(node.iter) is not None:
                features["loopIterations"].append(_range_iteration_count(node.iter))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            features["functions"].append(node.name)
        elif isinstance(node, ast.If):
            features["conditionals"] += 1
        elif isinstance(node, ast.Assign):
            features["assignments"] += len(node.targets)
        elif isinstance(node, ast.Call):
            name = _call_name(node.func)
            if name:
                calls.append(name)
                if name in {"onkeypress", "onkey", "onscreenclick", "onclick", "listen"}:
                    event_bindings.append(name)
    features["calls"] = sorted(set(calls))
    features["eventBindings"] = sorted(set(event_bindings))
    return features


def _range_iteration_count(node: ast.AST) -> int | None:
    if not isinstance(node, ast.Call) or _call_name(node.func) != "range":
        return None
    if not node.args or any(isinstance(argument, ast.Starred) for argument in node.args):
        return None
    values = []
    for argument in node.args[:3]:
        if not isinstance(argument, ast.Constant) or not isinstance(argument.value, int):
            return None
        values.append(argument.value)
    if len(values) == 1:
        return max(0, values[0])
    if len(values) == 2:
        start, stop = values
        return max(0, stop - start)
    start, stop, step = values
    if step == 0:
        return None
    return max(0, math.ceil((stop - start) / step))


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def build_standard_code(source: str) -> tuple[str, int]:
    source_lines = source.splitlines()
    preamble_lines = _STUDENT_PREAMBLE.splitlines()
    source_start_line = len(preamble_lines) + 1
    indented_source = [
        f"    {line}" if line.strip() else ""
        for line in source_lines
    ]
    generated = "\n".join(
        [*preamble_lines, *indented_source, *_STUDENT_SUFFIX.splitlines()]
    )
    return generated, source_start_line


def translate_turtle_error(error: dict[str, Any]) -> dict[str, Any]:
    error_type = str(error.get("type") or "Error")
    message = str(error.get("message") or "")
    line = error.get("line")
    category = "runtime"
    title = f"{error_type}: {message}" if message else error_type
    hint = "检查出错位置附近的代码，再单步观察变量变化。"

    if error_type in {"SyntaxError", "IndentationError", "TabError"}:
        category = "syntax"
        if error_type in {"IndentationError", "TabError"} or "indent" in message.lower():
            title = "这一行的缩进不正确"
            hint = "for、if、def 后面的代码需要统一缩进；语句块不能为空。"
        elif "expected ':'" in message:
            title = "语句末尾缺少冒号"
            hint = "for、if、def 或 else 语句末尾需要添加英文冒号 :。"
        elif "was never closed" in message or "unexpected EOF" in message:
            title = "括号或引号没有闭合"
            hint = "检查左右括号和字符串引号是否成对。"
        else:
            title = f"语法错误：{message}"
            hint = "先检查当前行的拼写、括号、冒号和缩进。"
    elif error_type == "NameError":
        category = "runtime"
        title = "使用了还没有定义的变量或函数"
        hint = "先给变量赋值，或检查函数名是否拼写正确。"
    elif error_type == "ZeroDivisionError":
        title = "除数不能为 0"
        hint = "检查除法或 range 步长中的数值。"
    elif error_type in {"TypeError", "ValueError"}:
        title = f"这一步的参数类型或数值不合适：{message}"
        hint = "检查 forward、right、range 等函数收到的参数。"
    elif error_type == "RecursionError":
        title = "递归调用层级过深"
        hint = "确认递归存在终止条件，并且每轮都会接近终止条件。"

    return {
        **error,
        "category": category,
        "title": title,
        "hint": hint,
        "line": line,
    }


def _line_map(source: str, source_start_line: int) -> dict[str, int]:
    return {
        str(line): source_start_line + line - 1
        for line in range(1, len(source.splitlines()) + 1)
    }


def _empty_result(message: str) -> dict[str, Any]:
    return {
        "ok": False,
        "steps": [],
        "commands": [],
        "finalState": {
            "x": 0,
            "y": 0,
            "heading": 0,
            "penDown": True,
            "color": "#3370ff",
            "size": 2,
            "fillColor": "#3370ff",
            "filling": False,
        },
        "variables": [],
        "programFeatures": {
            "validSyntax": True,
            "loops": 0,
            "loopIterations": [],
            "functions": [],
            "calls": [],
            "conditionals": 0,
            "assignments": 0,
            "eventBindings": [],
        },
        "error": {
            "type": "TurtleInputError",
            "message": message,
            "category": "syntax",
            "title": message,
            "hint": "输入一条指令后重新运行。",
            "line": None,
        },
    }


def _terminate_process_tree(process: subprocess.Popen) -> None:
    try:
        if os.name == "posix":
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        else:
            process.kill()
    except (OSError, ProcessLookupError):
        pass
