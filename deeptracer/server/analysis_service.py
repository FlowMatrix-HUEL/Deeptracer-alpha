from __future__ import annotations

import ast
import json
import os
import signal
import subprocess
import sys
import tempfile
from collections import Counter
from html import escape as html_escape
from pathlib import Path

from deeptracer.astAnalyer.viztracer import AstAnalyer
from deeptracer.astAnalyer.signatures import (
    collect_parameters,
    format_function_signature,
    unparse,
)
from deeptracer.tracer_support import get_tracer_python_path


CONTROL_NODES = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.Try,
    ast.With,
    ast.AsyncWith,
    ast.BoolOp,
    ast.IfExp,
    ast.comprehension,
)

NOISE_CALLS = {"range", "len", "print", "enumerate", "append", "extend", "update", "add", "sleep"}


def analyze_python_input(
    path_text: str | None = None,
    source_code: str | None = None,
    display_name: str | None = None,
) -> dict:
    if source_code and source_code.strip():
        return _analyze_source_code(source_code, display_name=display_name)
    if path_text:
        return analyze_python_file(path_text)
    raise ValueError("需要提供 Python 文件路径或代码内容。")


def analyze_python_file(path_text: str) -> dict:
    target_path = _resolve_python_path(path_text)
    code = target_path.read_text(encoding="utf-8")
    return _build_report(code=code, execution_path=target_path, display_name=target_path.name)


def _analyze_source_code(source_code: str, display_name: str | None = None) -> dict:
    code = source_code.strip("\n")
    if not code.strip():
        raise ValueError("输入框里的代码为空，无法分析。")

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".py", delete=False) as temp_file:
        temp_file.write(code)
        temp_path = Path(temp_file.name)

    try:
        return _build_report(
            code=code,
            execution_path=temp_path,
            display_name=display_name or "编辑器中的 Python 代码",
        )
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass


def _build_report(code: str, execution_path: Path, display_name: str) -> dict:
    tree = ast.parse(code)
    source_lines = code.splitlines()
    functions = _collect_functions(tree)
    top_nodes = Counter(type(node).__name__ for node in ast.walk(tree)).most_common(4)
    print_line_numbers = _print_line_numbers(tree)
    print_calls = len(print_line_numbers)
    loop_calls = _collect_loop_calls(tree)
    runtime = _profile_script(execution_path, code)

    ast_tab = _build_ast_tab(functions, print_calls, source_lines)
    perf_tab = _build_perf_tab(runtime, loop_calls)
    memory_tab = _build_memory_tab(runtime)
    suggestions = _build_suggestions(
        functions,
        loop_calls,
        print_calls,
        runtime,
        display_name,
        source_lines,
        print_line_numbers,
    )
    workflow_tab = _build_dynamic_overview_tab(runtime, display_name, top_nodes, functions, loop_calls, suggestions)
    
    # 生成 AST 可视化 HTML
    ast_visualization_html = _generate_ast_visualization(code, display_name)
    
    # 生成性能分析 HTML
    perf_visualization_html = _generate_perf_visualization(runtime, display_name)

    most_complex = functions[0]["name"] if functions else "未发现函数"
    return {
        "heroMetrics": [
            {"label": "分析对象", "value": display_name, "note": "直接来自页面输入"},
            {"label": "代码行数", "value": str(len(source_lines)), "note": "按当前输入实时统计"},
            {"label": "重点函数", "value": most_complex, "note": "按结构复杂度排序"},
            {"label": "执行耗时", "value": f"{runtime['duration_ms']:.1f} ms", "note": "本地真实执行结果"},
        ],
        "analysisMap": {
            "workflow": workflow_tab,
            "ast": ast_tab,
            "performance": perf_tab,
            "memory": memory_tab,
        },
        "visualizations": {
            "ast": ast_visualization_html,
            "performance": perf_visualization_html,
        },
        "suggestions": suggestions,
        "stages": [
            ["输入代码", "从页面输入框读取当前 Python 代码。"],
            ["理解结构", "解析 AST 并抽取函数、控制流与热点。"],
            ["执行分析", "在本地执行代码并统计耗时与内存峰值。"],
            ["生成建议", "根据结果生成易懂的优化建议和差异预览。"],
        ],
        "meta": {
            "targetPath": display_name,
            "stdout": runtime["stdout"][:800],
            "runtimeError": runtime["error"],
            "pyinstrumentSamples": runtime.get("pyinstrument_sample_count", 0),
        },
    }


def _resolve_python_path(path_text: str) -> Path:
    target = Path(path_text).expanduser()
    if not target.is_absolute():
        target = (Path.cwd() / target).resolve()
    if not target.exists():
        raise FileNotFoundError(f"文件不存在：{target}")
    if target.suffix.lower() != ".py":
        raise ValueError(f"仅支持 Python 文件：{target}")
    return target


def _collect_functions(tree: ast.AST) -> list[dict]:
    functions: list[dict] = []

    def visit(node: ast.AST, scope: tuple[str, ...]) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end_lineno = getattr(node, "end_lineno", node.lineno)
            qualified_name = ".".join((*scope, node.name))
            functions.append(
                {
                    "name": node.name,
                    "qualified_name": qualified_name,
                    "scope": ".".join(scope) or None,
                    "signature": format_function_signature(node),
                    "parameters": collect_parameters(node),
                    "decorators": [unparse(item) for item in node.decorator_list],
                    "returns": unparse(node.returns) or None,
                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                    "lineno": node.lineno,
                    "end_lineno": end_lineno,
                    "line_span": max(1, end_lineno - node.lineno + 1),
                    "complexity": _function_complexity(node),
                }
            )
            for child in node.body:
                visit(child, (*scope, node.name))
            return

        if isinstance(node, ast.ClassDef):
            for child in node.body:
                visit(child, (*scope, node.name))
            return

        for child in ast.iter_child_nodes(node):
            visit(child, scope)

    visit(tree, ())
    functions.sort(key=lambda item: (item["complexity"], item["line_span"]), reverse=True)
    return functions


def _function_complexity(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> int:
    complexity = 1

    def visit(current: ast.AST) -> None:
        nonlocal complexity
        for child in ast.iter_child_nodes(current):
            if isinstance(
                child,
                (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda),
            ):
                continue
            if isinstance(child, CONTROL_NODES):
                complexity += 1
            visit(child)

    for child in node.body:
        if isinstance(
            child,
            (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda),
        ):
            continue
        if isinstance(child, CONTROL_NODES):
            complexity += 1
        visit(child)
    return complexity


def _collect_loop_calls(tree: ast.AST) -> list[dict]:
    loop_calls = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
            counts = Counter()
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    name = _call_name(child)
                    if name and name not in NOISE_CALLS:
                        counts[name] += 1
            for name, count in counts.most_common(3):
                loop_calls.append({"name": name, "count": count, "line": getattr(node, "lineno", 1)})
    loop_calls.sort(key=lambda item: item["count"], reverse=True)
    return loop_calls[:4]


def _print_line_numbers(tree: ast.AST) -> list[int]:
    return [
        getattr(node, "lineno", 1)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "print"
    ][:3]


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _build_snippet(source_lines: list[str], line: int | None, radius: int = 1) -> str:
    if not line:
        return ""
    start = max(1, line - radius)
    end = min(len(source_lines), line + radius)
    return "\n".join(
        f"{current}: {source_lines[current - 1]}" for current in range(start, end + 1)
    )


def _anchor(kind: str, label: str, line: int | None, source_lines: list[str]) -> dict:
    return {
        "id": f"{kind}:{label}:{line or ''}",
        "kind": kind,
        "label": label,
        "line": line,
        "snippet": _build_snippet(source_lines, line),
    }


def _context_diff(
    source_lines: list[str],
    line: int | None,
    radius: int = 2,
) -> list[list]:
    if not line:
        return []
    start = max(1, line - radius)
    end = min(len(source_lines), line + radius)
    return [
        [current, " ", source_lines[current - 1], "context"]
        for current in range(start, end + 1)
    ]


def _find_enclosing_function(functions: list[dict], line: int | None) -> dict | None:
    if not line:
        return None
    for item in functions:
        start = item.get("lineno", 0)
        end = item.get("end_lineno", start)
        if start <= line <= end:
            return item
    return None


def _profile_script(path: Path, code: str) -> dict:
    del code  # The worker reads the file so it shares the exact analyzed source.
    timeout_seconds = float(os.getenv("DEEPTRACER_EXECUTION_TIMEOUT_SECONDS", "5"))
    command = [
        sys.executable,
        "-m",
        "deeptracer.server.execution_worker",
        str(path),
    ]
    environment = os.environ.copy()
    project_root = str(Path(__file__).resolve().parents[2])
    existing_python_path = environment.get("PYTHONPATH")
    python_paths = [
        project_root,
        get_tracer_python_path(),
        existing_python_path,
    ]
    environment["PYTHONPATH"] = os.pathsep.join(
        item for item in python_paths if item
    )
    environment["PYTHONIOENCODING"] = "utf-8"

    process = subprocess.Popen(
        command,
        cwd=str(path.parent),
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        start_new_session=os.name == "posix",
    )
    try:
        stdout, stderr = process.communicate(timeout=max(0.1, timeout_seconds))
    except subprocess.TimeoutExpired:
        _terminate_process_tree(process)
        stdout, stderr = process.communicate()
        return _empty_runtime(
            f"执行超时：代码运行超过 {timeout_seconds:g} 秒，已终止独立分析进程。"
        )

    if process.returncode != 0:
        detail = (stderr or stdout or "").strip()
        return _empty_runtime(
            "用户代码进程异常退出"
            + (f"：{detail[-800:]}" if detail else f"（退出码 {process.returncode}）")
        )
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return _empty_runtime(
            "分析进程没有返回有效结果"
            + (f"：{(stderr or stdout).strip()[-800:]}" if stderr or stdout else "")
        )
    if not isinstance(payload, dict):
        return _empty_runtime("分析进程返回了无效结果。")
    return {
        "duration_ms": float(payload.get("duration_ms") or 0.0),
        "peak_mb": float(payload.get("peak_mb") or 0.0),
        "profile_rows": payload.get("profile_rows") or [],
        "memory_rows": payload.get("memory_rows") or [],
        "pyinstrument_html": str(payload.get("pyinstrument_html") or ""),
        "pyinstrument_sample_count": int(
            payload.get("pyinstrument_sample_count") or 0
        ),
        "stdout": str(payload.get("stdout") or ""),
        "error": payload.get("error"),
    }


def _terminate_process_tree(process: subprocess.Popen) -> None:
    try:
        if os.name == "posix":
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        else:
            process.kill()
    except (OSError, ProcessLookupError):
        pass


def _empty_runtime(error: str | None = None) -> dict:
    return {
        "duration_ms": 0.0,
        "peak_mb": 0.0,
        "profile_rows": [],
        "memory_rows": [],
        "pyinstrument_html": "",
        "pyinstrument_sample_count": 0,
        "stdout": "",
        "error": error,
    }


def _build_overview_tab(runtime: dict, display_name: str, top_nodes: list[tuple[str, int]]) -> dict:
    bars = [
        {"label": "输入完成", "value": 25},
        {"label": "结构分析", "value": 55},
        {"label": "执行统计", "value": 82 if not runtime["error"] else 64},
        {"label": "建议生成", "value": 100 if not runtime["error"] else 88},
    ]
    top_node_text = "、".join(name for name, _ in top_nodes[:3]) if top_nodes else "无"
    return {
        "title": "概览",
        "summary": "先看整体结果，再决定要不要继续看性能、内存或结构细节。",
        "cards": [
            {"label": "当前对象", "value": display_name},
            {"label": "执行状态", "value": "已完成" if not runtime["error"] else "部分完成"},
            {"label": "常见语法", "value": top_node_text},
        ],
        "bars": bars,
        "points": [
            "这份结果来自你刚刚输入的代码，不需要先保存成文件。",
            "如果代码能运行，页面会展示真实的耗时和内存摘要。",
            "如果代码报错，页面也会尽量保留错误发生前拿到的分析结果。"
        ],
    }


def _build_ast_tab(functions: list[dict], print_calls: int, source_lines: list[str]) -> dict:
    top_function = functions[0]["name"] if functions else "未发现函数"
    bars = [{"label": item["name"], "value": min(100, item["complexity"] * 10)} for item in functions[:4]]
    if not bars:
        bars = [{"label": "当前代码较短", "value": 12}]
    return {
        "title": "结构",
        "summary": "用更容易理解的方式看函数数量、代码规模和结构复杂度。",
        "cards": [
            {"label": "代码行数", "value": str(len(source_lines))},
            {"label": "函数数量", "value": str(len(functions))},
            {"label": "重点函数", "value": top_function},
        ],
        "bars": bars,
        "functions": sorted(functions, key=lambda item: item["lineno"]),
        "points": [
            "函数越长、分支越多，后续维护通常越吃力。",
            f"当前最值得先读懂的是：{top_function}。",
            f"这段代码里共检测到 {print_calls} 处输出语句。"
        ],
    }


def _build_perf_tab(runtime: dict, loop_calls: list[dict]) -> dict:
    total = sum(item["total_ms"] for item in runtime["profile_rows"]) or 1
    bars = [
        {"label": f"{item['label']} @ 第 {item['line']} 行", "value": round(item["total_ms"] / total * 100, 1)}
        for item in runtime["profile_rows"][:4]
    ]
    if not bars:
        bars = [{"label": "当前没有明显热点", "value": 0}]
    hottest = runtime["profile_rows"][0]["label"] if runtime["profile_rows"] else "未发现明显热点"
    points = [
        f"本次真实执行耗时约 {runtime['duration_ms']:.1f} ms。",
        f"当前最耗时的位置更接近：{hottest}。",
    ]
    if loop_calls:
        points.append(f"循环中最值得留意的调用是 {loop_calls[0]['name']}。")
    if runtime["error"]:
        points.append(f"执行时报错：{runtime['error']}。")
    return {
        "title": "性能",
        "summary": "不需要先理解全部代码，先看哪里最慢就够了。",
        "cards": [
            {"label": "执行耗时", "value": f"{runtime['duration_ms']:.1f} ms"},
            {"label": "热点函数", "value": hottest},
            {"label": "可见样本", "value": str(len(runtime["profile_rows"]))},
        ],
        "bars": bars,
        "points": points,
    }


def _build_memory_tab(runtime: dict) -> dict:
    bars = [
        {"label": f"{item['label']} ({item['size_kb']} KB)", "value": item["value"]}
        for item in runtime["memory_rows"]
    ]
    if not bars:
        bars = [{"label": "当前没有明显热点", "value": 0}]
    return {
        "title": "内存",
        "summary": "这部分帮助你判断代码是不是持有了过多不必要的数据。",
        "cards": [
            {"label": "峰值内存", "value": f"{runtime['peak_mb']:.2f} MB"},
            {"label": "热点位置", "value": str(len(runtime["memory_rows"]))},
            {"label": "运行状态", "value": "有异常" if runtime["error"] else "正常"},
        ],
        "bars": bars,
        "points": [
            "内存数据来自 Python 标准库 tracemalloc。",
            "如果这里的峰值很高，通常说明有大对象存在时间过长。",
            "这能帮助初学者先找到问题位置，再考虑更深入优化。"
        ],
    }


def _build_suggestions(
    functions: list[dict],
    loop_calls: list[dict],
    print_calls: int,
    runtime: dict,
    display_name: str,
    source_lines: list[str],
    print_line_numbers: list[int],
) -> list[dict]:
    suggestions = []

    if functions:
        target = functions[0]
        suggestions.append(
            {
                "id": "split-function",
                "title": f"先把 {target['name']} 拆小一点",
                "priority": "优先看看",
                "confidence": "高",
                "impact": f"复杂度约 {target['complexity']}",
                "risk": "低到中",
                "file": display_name,
                "note": "函数太长或分支太多时，先拆清楚职责最容易看懂。",
                "explanation": "如果一段函数同时负责读取、判断和输出，初学者会很难定位问题。先拆出更小的步骤，通常比直接做性能优化更容易理解。",
                "detail": {
                    "whySelected": f"`{target['name']}` 是当前最复杂的函数之一，复杂度约 {target['complexity']}，跨度约 {target['line_span']} 行，因此它最值得优先理解。",
                    "codeAnchors": [
                        _anchor("function", target["name"], target["lineno"], source_lines)
                    ],
                    "riskIfUnchanged": "如果继续把多种职责堆在同一个函数里，后续定位 bug、解释热点和做小范围修改都会越来越困难。",
                    "nextChange": "先把这个函数拆成职责更单一的小步骤，再重新跑一轮分析确认复杂度和热点是否下降。",
                    "mode": "local-anchored",
                },
                "diff": _context_diff(source_lines, target["lineno"], radius=3),
            }
        )

    if loop_calls:
        loop_target = loop_calls[0]
        enclosing = _find_enclosing_function(functions, loop_target["line"])
        loop_anchors = [
            _anchor("call", loop_target["name"], loop_target["line"], source_lines)
        ]
        if enclosing:
            loop_anchors.insert(
                0,
                _anchor("function", enclosing["name"], enclosing["lineno"], source_lines),
            )
        suggestions.append(
            {
                "id": "loop-hotspot",
                "title": f"留意循环里的 {loop_target['name']} 调用",
                "priority": "值得关注",
                "confidence": "中高",
                "impact": "可能影响整体速度",
                "risk": "低",
                "file": display_name,
                "note": f"在第 {loop_target['line']} 行附近，循环内重复调用了 {loop_target['name']}。",
                "explanation": "当同一个操作在循环中反复出现时，速度往往会受到影响。这里不一定要立刻优化，但值得先看懂它是不是重复做了相同事情。",
                "detail": {
                    "whySelected": f"在第 {loop_target['line']} 行附近，循环里重复出现了 `{loop_target['name']}` 调用，这通常就是热点集中和解释难度上升的来源。",
                    "codeAnchors": loop_anchors,
                    "riskIfUnchanged": "如果循环中的重复调用没有先被理解清楚，你后面很容易只看到“慢”，却不知道慢在重复计算、重复查找还是重复构造数据。",
                    "nextChange": "先确认这次调用是否每轮都必须重新执行；如果输入没变，优先考虑缓存中间结果或提前搬出循环。",
                    "mode": "local-anchored",
                },
                "diff": _context_diff(source_lines, loop_target["line"]),
            }
        )

    if print_calls:
        print_line = print_line_numbers[0] if print_line_numbers else None
        suggestions.append(
            {
                "id": "reduce-print",
                "title": "把调试输出收一收",
                "priority": "顺手优化",
                "confidence": "高",
                "impact": f"检测到 {print_calls} 处输出",
                "risk": "低",
                "file": display_name,
                "note": "如果输出很多，页面和终端都会更难读。",
                "explanation": "print 本身没有错，但太多输出会让你很难只盯住真正重要的信息。先让输出更克制，通常会让调试更轻松。",
                "detail": {
                    "whySelected": f"当前检测到 {print_calls} 处输出语句，它们会直接影响运行时输出噪音，也会干扰你观察真正重要的数据变化。",
                    "codeAnchors": [
                        _anchor("output", "print", print_line, source_lines)
                    ]
                    if print_line
                    else [],
                    "riskIfUnchanged": "如果调试输出持续堆积，你在对比结果时会越来越难分辨哪一行是真正的业务输出，哪一行只是临时调试信息。",
                    "nextChange": "先把临时输出收进条件分支、日志开关或局部调试块，再看运行结果是否更容易阅读。",
                    "mode": "local-anchored",
                },
                "diff": _context_diff(source_lines, print_line),
            }
        )

    if runtime["peak_mb"] >= 1 and len(suggestions) < 3:
        memory_line = None
        if runtime["memory_rows"]:
            digits = "".join(ch for ch in runtime["memory_rows"][0]["label"] if ch.isdigit())
            memory_line = int(digits) if digits else None
        suggestions.append(
            {
                "id": "trim-memory",
                "title": "减少长时间保留的大对象",
                "priority": "可以留意",
                "confidence": "中",
                "impact": f"峰值约 {runtime['peak_mb']:.2f} MB",
                "risk": "低到中",
                "file": display_name,
                "note": "内存峰值偏高时，通常可以先检查大列表、大字典是否存在太久。",
                "explanation": "如果某个大对象在程序里存活太久，内存就会一直被占着。把它拆成更短的使用周期，常常就能缓和这个问题。",
                "detail": {
                    "whySelected": f"这次运行的峰值内存约为 {runtime['peak_mb']:.2f} MB，并且热点内存行提示有对象被长时间保留，因此它值得单独检查。",
                    "codeAnchors": [
                        _anchor("memory-hotspot", "memory-hotspot", memory_line, source_lines)
                    ]
                    if memory_line
                    else [],
                    "riskIfUnchanged": "如果大对象生命周期过长，代码规模继续变大时，内存占用会更难控制，也更难解释为什么会升高。",
                    "nextChange": "先确认大列表、大字典是否真的需要一直保留；如果只是中间产物，优先缩短作用域或改成分步处理。",
                    "mode": "local-anchored",
                },
                "diff": _context_diff(source_lines, memory_line),
            }
        )

    if not suggestions:
        top_anchor = (
            _anchor("function", functions[0]["name"], functions[0]["lineno"], source_lines)
            if functions
            else None
        )
        suggestions.append(
            {
                "id": "keep-simple",
                "title": "先保持代码清晰，再决定要不要优化",
                "priority": "默认建议",
                "confidence": "中",
                "impact": "提升可读性",
                "risk": "低",
                "file": display_name,
                "note": "当前没有特别尖锐的问题，先把代码说明清楚会更有帮助。",
                "explanation": "当代码本身不复杂时，最好的下一步往往不是立刻优化，而是先让变量名、函数职责和输入输出更清楚。",
                "detail": {
                    "whySelected": "当前这段代码没有暴露出明显的单点瓶颈，所以与其过早优化，不如先把最主要的函数职责讲清楚。",
                    "codeAnchors": [top_anchor] if top_anchor else [],
                    "riskIfUnchanged": "如果在结构还不清晰的时候直接做性能或内存级优化，后面会更难判断改动到底是在优化还是在增加复杂度。",
                    "nextChange": "先给主要函数和关键变量补上更清晰的命名或注释，再重新看是否还需要进一步优化。",
                    "mode": "local-anchored",
                },
                "diff": _context_diff(source_lines, 1),
            }
        )

    return suggestions[:3]


def _build_dynamic_overview_tab(
    runtime: dict,
    display_name: str,
    top_nodes: list[tuple[str, int]],
    functions: list[dict],
    loop_calls: list[dict],
    suggestions: list[dict],
) -> dict:
    top_node_text = "、".join(name for name, _ in top_nodes[:3]) if top_nodes else "暂时不明显"
    status_text = "已完成" if not runtime["error"] else "部分完成"
    return {
        "title": "概览",
        "summary": "先看整体结果，再决定要不要继续深入结构、性能或内存细节。",
        "cards": [
            {
                "label": "结构复杂度",
                "value": str(_complexity_score(functions)),
                "note": f"基于 {len(functions)} 个函数和最复杂函数综合计算。",
            },
            {
                "label": "热点集中度",
                "value": str(_hotspot_score(runtime)),
                "note": "数值越高，说明耗时越集中在少数关键逻辑上。",
            },
            {
                "label": "内存压力",
                "value": str(_memory_score(runtime)),
                "note": f"当前峰值约 {runtime['peak_mb']:.2f} MB，会结合热点分布一起判断。",
            },
            {
                "label": "修改空间",
                "value": str(_refactor_score(functions, loop_calls, suggestions, runtime)),
                "note": f"当前共生成 {len(suggestions)} 条建议，执行状态为 {status_text}。",
            },
        ],
        "bars": [],
        "points": [
            f"当前分析对象是：{display_name}，常见语法主要集中在 {top_node_text}。",
            "如果代码可以成功运行，页面会展示真实的耗时与内存摘要；如果报错，也会尽量保留已有分析结果。",
            "概览里的四个数值越高，通常越值得你优先点开对应标签继续看。"
        ],
    }


def _complexity_score(functions: list[dict]) -> int:
    if not functions:
        return 8
    max_complexity = max(item["complexity"] for item in functions)
    average_span = sum(item["line_span"] for item in functions) / len(functions)
    raw_score = max_complexity * 8 + len(functions) * 6 + average_span * 1.5
    return max(6, min(100, round(raw_score)))


def _hotspot_score(runtime: dict) -> int:
    rows = runtime["profile_rows"]
    if not rows:
        return 0
    total_ms = sum(item["total_ms"] for item in rows) or 1
    hottest_share = rows[0]["total_ms"] / total_ms
    return max(4, min(100, round(hottest_share * 100)))


def _memory_score(runtime: dict) -> int:
    peak_component = min(65, runtime["peak_mb"] * 18)
    hotspot_component = runtime["memory_rows"][0]["value"] if runtime["memory_rows"] else 0
    raw_score = peak_component + hotspot_component * 0.55
    return max(3, min(100, round(raw_score)))


def _refactor_score(functions: list[dict], loop_calls: list[dict], suggestions: list[dict], runtime: dict) -> int:
    raw_score = len(suggestions) * 24 + len(loop_calls) * 9 + max(0, len(functions) - 1) * 5
    if runtime["error"]:
        raw_score += 12
    return max(12, min(100, round(raw_score)))


def _generate_ast_visualization(code: str, display_name: str) -> str:
    """
    生成 AST 可视化 HTML
    
    Args:
        code: Python 代码字符串
        display_name: 显示名称
    
    Returns:
        AST 可视化的 HTML 字符串
    """
    try:
        # 使用临时文件来创建 AstAnalyer
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".py", delete=False) as temp_file:
            temp_file.write(code)
            temp_path = Path(temp_file.name)
        
        try:
            analyzer = AstAnalyer(pythonScript=str(temp_path), open=True)
            html_content = analyzer.visualize()
            return html_content or ""
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
    except Exception as e:
        print(f"AST 可视化生成失败：{e}")
        return ""


def _generate_perf_visualization(runtime: dict, display_name: str) -> str:
    pyinstrument_html = runtime.get("pyinstrument_html")
    if pyinstrument_html:
        if not runtime.get("pyinstrument_sample_count"):
            warning = (
                "<div style='padding:12px 18px;border-bottom:1px solid #d8dee9;"
                "background:#fff7d6;color:#5c4813;font-family:sans-serif'>"
                "代码执行时间过短，PyInstrument 未采集到样本。"
                "可降低 DEEPTRACER_PYINSTRUMENT_INTERVAL_SECONDS 或增加代码执行时间。"
                "</div>"
            )
            if "<body>" in pyinstrument_html:
                pyinstrument_html = pyinstrument_html.replace(
                    "<body>",
                    f"<body>{warning}",
                    1,
                )
        return pyinstrument_html

    rows = runtime.get("profile_rows") or []
    total = sum(float(row.get("total_ms") or 0) for row in rows) or 1.0
    bars = []
    for row in rows:
        width = max(0.0, min(100.0, float(row.get("total_ms") or 0) / total * 100))
        label = f"{row.get('label', 'unknown')} · 第 {row.get('line', '?')} 行"
        bars.append(
            "<div class='bar-row'>"
            f"<div class='bar-label'>{html_escape(str(label))}</div>"
            f"<div class='bar-track'><span style='width:{width:.1f}%'></span></div>"
            f"<strong>{float(row.get('total_ms') or 0):.2f} ms</strong>"
            "</div>"
        )
    if not bars:
        bars.append("<p class='empty'>当前没有可展示的性能热点。</p>")
    error = runtime.get("error")
    error_html = (
        f"<p class='error'>执行信息：{html_escape(str(error))}</p>"
        if error
        else ""
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>DeepTracer 性能分析</title>
<style>
body {{ margin: 0; padding: 24px; background: #f7f9fc; color: #172033; font-family: sans-serif; }}
h1 {{ margin: 0 0 8px; font-size: 22px; }}
.meta {{ color: #667085; margin-bottom: 20px; }}
.bar-row {{ display: grid; grid-template-columns: minmax(180px, 1.2fr) minmax(180px, 3fr) 90px; gap: 14px; align-items: center; margin: 12px 0; }}
.bar-label {{ overflow-wrap: anywhere; }}
.bar-track {{ height: 12px; border-radius: 999px; background: #e8edf5; overflow: hidden; }}
.bar-track span {{ display: block; height: 100%; border-radius: inherit; background: #4f7cff; }}
.empty, .error {{ padding: 12px; border-radius: 10px; background: #eef2f8; }}
.error {{ color: #9b2c2c; background: #fff1f1; }}
</style>
</head>
<body>
<h1>性能热点</h1>
<div class="meta">{html_escape(display_name)} · 总耗时 {runtime['duration_ms']:.2f} ms</div>
{''.join(bars)}
{error_html}
</body>
</html>"""
