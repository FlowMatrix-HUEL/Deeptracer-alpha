from __future__ import annotations

import ast
import hashlib
from typing import Any

from .models import Moment, MomentEvidence


_PRIMITIVE_TYPES = (bool, int, float, str)


def _source_hash(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _source_ref(line: int, source_hash: str) -> dict[str, Any]:
    return {
        "fileId": "editor",
        "sourceHash": source_hash,
        "startLine": line,
        "endLine": line,
        "origin": "breakpoints",
    }


def _decode_value(value: Any) -> Any:
    if value is None or isinstance(value, _PRIMITIVE_TYPES):
        return value
    if isinstance(value, list) and value:
        tag = str(value[0])
        if tag in {"LIST", "TUPLE", "SET"}:
            return f"{tag}[{max(0, len(value) - 1)}]"
        if tag in {"DICT", "INSTANCE", "CLASS"}:
            return f"{tag}[{max(0, len(value) - 1)}]"
        if tag == "REF" and len(value) > 1:
            return f"REF[{value[1]}]"
        return f"{tag}[{len(value)}]"
    return type(value).__name__


def _visible_variables(step: dict[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    globals_raw = step.get("globals")
    ordered = step.get("ordered_globals") or []
    if isinstance(ordered, list):
        for item in ordered:
            if isinstance(item, str) and isinstance(globals_raw, dict) and item in globals_raw:
                values[item] = _decode_value(globals_raw[item])
            elif isinstance(item, dict):
                name = item.get("name")
                if isinstance(name, str) and name:
                    values[name] = item.get("value")
    if isinstance(globals_raw, dict):
        for name, value in globals_raw.items():
            if isinstance(name, str):
                values.setdefault(name, _decode_value(value))
    for frame in step.get("stack_to_render") or []:
        if not isinstance(frame, dict):
            continue
        locals_raw = frame.get("encoded_locals") or {}
        ordered_locals = frame.get("ordered_varnames") or list(locals_raw)
        if not isinstance(locals_raw, dict):
            continue
        for name in ordered_locals:
            if name == "__return__" or not isinstance(name, str):
                continue
            if name in locals_raw:
                values[name] = _decode_value(locals_raw[name])
    return values


def _stack_depth(step: dict[str, Any]) -> int:
    stack = step.get("stack_to_render")
    return len(stack) if isinstance(stack, list) else 0


def _format_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    return str(value)


def _target_names(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, (ast.Tuple, ast.List)):
        names: list[str] = []
        for element in node.elts:
            names.extend(_target_names(element))
        return names
    if isinstance(node, ast.Attribute):
        return [node.attr]
    return []


def _range_info(node: ast.AST) -> dict[str, Any] | None:
    if (
        not isinstance(node, ast.Call)
        or not isinstance(node.func, ast.Name)
        or node.func.id != "range"
    ):
        return None
    if any(isinstance(argument, ast.Starred) for argument in node.args):
        return None
    values: list[int] = []
    for argument in node.args:
        if isinstance(argument, ast.Constant) and isinstance(argument.value, int):
            values.append(argument.value)
        else:
            return None
    if not values or len(values) > 3:
        return None
    raw = list(values)
    if len(values) == 1:
        start, stop, step = 0, values[0], 1
    elif len(values) == 2:
        start, stop = values
        step = 1
    else:
        start, stop, step = values
    if step == 0:
        return None
    display = (
        f"range({raw[0]})"
        if len(raw) == 1
        else f"range({raw[0]}, {raw[1]})"
        if len(raw) == 2
        else f"range({raw[0]}, {raw[1]}, {raw[2]})"
    )
    return {
        "start": start,
        "stop": stop,
        "step": step,
        "count": len(range(start, stop, step)),
        "display": display,
    }


def _range_description(info: dict[str, Any]) -> str:
    values = list(range(info["start"], info["stop"], info["step"]))
    if not values:
        return f"{info['display']} 是空的"
    return (
        f"{info['display']} 产生 "
        f"{values[0]}..{values[-1]}，共 {info['count']} 个值"
    )


def _loop_descriptors(code: str) -> list[dict[str, Any]]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    loops: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
            continue
        body = list(getattr(node, "body", []) or [])
        if not body:
            continue
        body_start = min(getattr(item, "lineno", 1) for item in body)
        body_end = max(
            getattr(item, "end_lineno", None) or getattr(item, "lineno", body_start)
            for item in body
        )
        targets = _target_names(node.target) if isinstance(node, (ast.For, ast.AsyncFor)) else []
        range_info = (
            _range_info(node.iter)
            if isinstance(node, (ast.For, ast.AsyncFor))
            else None
        )
        loops.append(
            {
                "line": getattr(node, "lineno", 1),
                "end_line": getattr(node, "end_lineno", None) or body_end,
                "body_start": body_start,
                "body_end": body_end,
                "targets": targets,
                "kind": "for" if isinstance(node, (ast.For, ast.AsyncFor)) else "while",
                "range": range_info,
            }
        )
    # Innermost loops first so a shared step is attributed to the tighter loop.
    loops.sort(key=lambda item: (item["body_end"] - item["body_start"], item["line"]))
    return loops


def _body_step_indexes(
    trace: list[dict[str, Any]], body_start: int, body_end: int
) -> list[int]:
    indexes: list[int] = []
    for index, step in enumerate(trace):
        if not isinstance(step, dict):
            continue
        if step.get("event") != "step_line":
            continue
        line = step.get("line")
        if isinstance(line, int) and body_start <= line <= body_end:
            indexes.append(index)
    return indexes


def _first_step_index(trace: list[dict[str, Any]]) -> int | None:
    return 0 if trace else None


def _loop_moments(
    trace: list[dict[str, Any]],
    code: str,
    source_hash: str,
    used_boundaries: set[tuple[str, int]],
    used_variable_steps: set[str],
) -> list[Moment]:
    moments: list[Moment] = []
    for loop in _loop_descriptors(code):
        prefix = f"py-loop-{loop['line']}"
        body_indexes = _body_step_indexes(trace, loop["body_start"], loop["body_end"])
        targets = [name for name in loop["targets"] if isinstance(name, str) and name]

        if not body_indexes:
            step_index = _first_step_index(trace)
            moments.append(
                Moment(
                    id=f"{prefix}-loop-zero",
                    world="python",
                    kind="boundary",
                    concepts=["repetition", "boundary"],
                    severity="warning",
                    importance=0.85,
                    step_index=step_index,
                    line=loop["line"],
                    source_ref=_source_ref(loop["line"], source_hash),
                    label="循环一次都没执行",
                    why=f"第 {loop['line']} 行的循环条件一开始就不成立。",
                    evidence=[
                        MomentEvidence(
                            type="source_line",
                            line=loop["line"],
                            source_ref=_source_ref(loop["line"], source_hash),
                        )
                    ],
                    tags=["loop", "zero-iteration"],
                )
            )
            continue

        first_index = body_indexes[0]
        last_index = body_indexes[-1]
        first_step = trace[first_index]
        last_step = trace[last_index]
        first_vars = _visible_variables(first_step)
        last_vars = _visible_variables(last_step)

        if ("first", first_index) not in used_boundaries:
            used_boundaries.add(("first", first_index))
            target_text = _target_text(targets, first_vars)
            moments.append(
                Moment(
                    id=f"{prefix}-first",
                    world="python",
                    kind="boundary",
                    concepts=["repetition", "boundary"],
                    severity="info",
                    importance=0.8,
                    step_index=first_index,
                    line=first_step.get("line"),
                    source_ref=_source_ref(
                        int(first_step.get("line") or loop["body_start"]), source_hash
                    ),
                    label="第 1 次迭代",
                    why=f"循环体第一次执行{f'，{target_text}' if target_text else ''}。",
                    evidence=[
                        MomentEvidence(
                            type="trace_step",
                            step_index=first_index,
                            line=first_step.get("line"),
                            value={name: first_vars.get(name) for name in targets if name in first_vars}
                            or None,
                        )
                    ],
                    tags=["loop", "first-iteration"],
                )
            )

        if ("last", last_index) not in used_boundaries:
            used_boundaries.add(("last", last_index))
            target_text = _target_text(targets, last_vars)
            range_info = loop.get("range")
            range_text = (
                _range_description(range_info)
                if isinstance(range_info, dict) and range_info.get("count", 0) > 0
                else ""
            )
            last_why = f"循环体最后一次执行{f'，{target_text}' if target_text else ''}。"
            if range_text:
                last_why += f"{range_text}。"
            moments.append(
                Moment(
                    id=f"{prefix}-last",
                    world="python",
                    kind="boundary",
                    concepts=["repetition", "boundary"],
                    severity="info",
                    importance=0.85,
                    step_index=last_index,
                    line=last_step.get("line"),
                    source_ref=_source_ref(
                        int(last_step.get("line") or loop["body_end"]), source_hash
                    ),
                    label="最后一次迭代",
                    why=last_why,
                    evidence=[
                        MomentEvidence(
                            type="trace_step",
                            step_index=last_index,
                            line=last_step.get("line"),
                            value={name: last_vars.get(name) for name in targets if name in last_vars}
                            or None,
                        )
                    ],
                    tags=["loop", "last-iteration"],
                )
            )

        exit_index = _find_exit_index(trace, last_index, loop["body_start"], loop["body_end"])
        if exit_index is not None and targets:
            exit_step = trace[exit_index]
            exit_vars = _visible_variables(exit_step)
            changed = {
                name: (last_vars.get(name), exit_vars.get(name))
                for name in targets
                if name in last_vars
                and name in exit_vars
                and _is_primitive(last_vars.get(name))
                and _is_primitive(exit_vars.get(name))
                and last_vars.get(name) != exit_vars.get(name)
            }
            if changed:
                name, (before, after) = next(iter(changed.items()))
                moment_id = f"{prefix}-loop-exit"
                if moment_id not in used_variable_steps:
                    used_variable_steps.add(moment_id)
                    moments.append(
                        Moment(
                            id=moment_id,
                            world="python",
                            kind="boundary",
                            concepts=["repetition", "boundary"],
                            severity="warning",
                            importance=0.9,
                            step_index=exit_index,
                            line=exit_step.get("line"),
                            source_ref=_source_ref(
                                int(exit_step.get("line") or loop["body_end"]), source_hash
                            ),
                            label=f"循环结束后 {name}={_format_value(after)}",
                            why=(
                                f"最后一次迭代时 {name}={_format_value(before)}；"
                                f"退出后变成 {_format_value(after)}。留意边界。"
                            ),
                            question=f"循环结束后 {name} 是多少？",
                            evidence=[
                                MomentEvidence(
                                    type="variable",
                                    step_index=last_index,
                                    line=last_step.get("line"),
                                    field=name,
                                    value=before,
                                ),
                                MomentEvidence(
                                    type="variable",
                                    step_index=exit_index,
                                    line=exit_step.get("line"),
                                    field=name,
                                    value=after,
                                ),
                            ],
                            expected={name: before},
                            actual={name: after},
                            tags=["loop", "off-by-one", "boundary"],
                        )
                    )

    return moments


def _target_text(targets: list[str], values: dict[str, Any]) -> str:
    parts = []
    for name in targets:
        if name in values:
            parts.append(f"{name}={_format_value(values[name])}")
    return "，".join(parts)


def _is_primitive(value: Any) -> bool:
    return value is None or isinstance(value, _PRIMITIVE_TYPES)


def _find_exit_index(
    trace: list[dict[str, Any]],
    last_body_index: int,
    body_start: int,
    body_end: int,
) -> int | None:
    for index in range(last_body_index + 1, len(trace)):
        step = trace[index]
        if not isinstance(step, dict):
            continue
        if step.get("event") in {"step_line", "return", "exception", "uncaught_exception"}:
            line = step.get("line")
            if not isinstance(line, int) or line < body_start or line > body_end:
                return index
    return None


def _variable_moments(
    trace: list[dict[str, Any]],
    source_hash: str,
    used_steps: set[int],
) -> list[Moment]:
    moments: list[Moment] = []
    seen: set[str] = set()
    previous: dict[str, Any] = {}
    for index, step in enumerate(trace):
        if not isinstance(step, dict) or step.get("event") != "step_line":
            continue
        values = _visible_variables(step)
        for name, value in values.items():
            if name.startswith("_") or not _is_primitive(value):
                continue
            if name not in previous and name not in seen:
                seen.add(name)
                line = step.get("line")
                moments.append(
                    Moment(
                        id=f"py-var-{name}-{index}",
                        world="python",
                        kind="state_change",
                        concepts=["state"],
                        severity="info",
                        importance=0.42,
                        step_index=index,
                        line=line,
                        source_ref=_source_ref(int(line or 1), source_hash),
                        label=f"{name} 第一次出现",
                        why=f"{name} 在这里变成 {_format_value(value)}。",
                        evidence=[
                            MomentEvidence(
                                type="variable",
                                step_index=index,
                                line=line,
                                field=name,
                                value=value,
                            )
                        ],
                        tags=["variable", "first-appearance"],
                    )
                )
            previous[name] = value
    return moments[:5]


def _call_moments(
    trace: list[dict[str, Any]],
    source_hash: str,
) -> list[Moment]:
    moments: list[Moment] = []
    previous_depth = 0
    seen_call = False
    seen_return = False
    seen_recursion = False
    for index, step in enumerate(trace):
        if not isinstance(step, dict):
            continue
        depth = _stack_depth(step)
        line = step.get("line")
        func_name = step.get("func_name") or "函数"
        if depth > previous_depth and not seen_call:
            seen_call = True
            moments.append(
                Moment(
                    id=f"py-call-{index}",
                    world="python",
                    kind="call",
                    concepts=["call"],
                    severity="info",
                    importance=0.55,
                    step_index=index,
                    line=line,
                    source_ref=_source_ref(int(line or 1), source_hash),
                    label=f"进入函数 {func_name}",
                    why="调用栈在这里加深。",
                    evidence=[MomentEvidence(type="call", step_index=index, line=line, value=func_name)],
                    tags=["call"],
                )
            )
        elif depth > previous_depth and not seen_recursion and func_name:
            stack_names = [
                str(frame.get("func_name"))
                for frame in step.get("stack_to_render") or []
                if isinstance(frame, dict)
            ]
            if stack_names.count(str(func_name)) > 1:
                seen_recursion = True
                moments.append(
                    Moment(
                        id=f"py-recursion-{index}",
                        world="python",
                        kind="call",
                        concepts=["call", "recursion"],
                        severity="info",
                        importance=0.7,
                        step_index=index,
                        line=line,
                        source_ref=_source_ref(int(line or 1), source_hash),
                        label=f"递归调用 {func_name}",
                        why="同一个函数在调用栈里再次出现。",
                        evidence=[
                            MomentEvidence(type="call", step_index=index, line=line, value=func_name)
                        ],
                        tags=["recursion"],
                    )
                )
        elif depth < previous_depth and not seen_return:
            seen_return = True
            moments.append(
                Moment(
                    id=f"py-return-{index}",
                    world="python",
                    kind="call",
                    concepts=["call"],
                    severity="info",
                    importance=0.45,
                    step_index=index,
                    line=line,
                    source_ref=_source_ref(int(line or 1), source_hash),
                    label="函数返回",
                    why="调用栈在这里变浅。",
                    evidence=[MomentEvidence(type="call", step_index=index, line=line)],
                    tags=["return"],
                )
            )
        previous_depth = depth
    return moments


def _exception_moments(
    trace: list[dict[str, Any]],
    source_hash: str,
) -> list[Moment]:
    for index, step in enumerate(trace):
        if not isinstance(step, dict):
            continue
        if step.get("event") not in {"exception", "uncaught_exception"}:
            continue
        line = step.get("line")
        if not isinstance(line, int):
            line = _previous_line(trace, index) or 1
        message = str(step.get("exception_msg") or "异常")
        if len(message) > 80:
            message = message[:77] + "..."
        return [
            Moment(
                id=f"py-exception-{index}",
                world="python",
                kind="exception",
                concepts=["failure"],
                severity="error",
                importance=1.0,
                step_index=index,
                line=line,
                source_ref=_source_ref(line, source_hash),
                label=f"异常：{message}",
                why="执行在这里中断。",
                evidence=[
                    MomentEvidence(
                        type="trace_step",
                        step_index=index,
                        line=line,
                        value=message,
                    )
                ],
                tags=["exception"],
            )
        ]
    return []


def _previous_line(trace: list[dict[str, Any]], index: int) -> int | None:
    for cursor in range(index - 1, -1, -1):
        step = trace[cursor]
        if isinstance(step, dict) and isinstance(step.get("line"), int):
            return step["line"]
    return None


def _branch_moments(
    trace: list[dict[str, Any]],
    code: str,
    source_hash: str,
    used_steps: set[int],
) -> list[Moment]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    moments: list[Moment] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        for label, body in (("if", node.body), ("else", node.orelse)):
            if not body:
                continue
            start = min(getattr(item, "lineno", 1) for item in body)
            end = max(
                getattr(item, "end_lineno", None) or getattr(item, "lineno", start)
                for item in body
            )
            for index, step in enumerate(trace):
                if not isinstance(step, dict) or step.get("event") != "step_line":
                    continue
                line = step.get("line")
                if isinstance(line, int) and start <= line <= end and index not in used_steps:
                    used_steps.add(index)
                    moments.append(
                        Moment(
                            id=f"py-branch-{node.lineno}-{label}",
                            world="python",
                            kind="branch",
                            concepts=["condition"],
                            severity="info",
                            importance=0.5,
                            step_index=index,
                            line=line,
                            source_ref=_source_ref(line, source_hash),
                            label=f"进入 {label} 分支",
                            why="条件判断后执行了这条分支。",
                            evidence=[MomentEvidence(type="trace_step", step_index=index, line=line)],
                            tags=["branch", label],
                        )
                    )
                    break
            if len(moments) >= 2:
                return moments
    return moments


def _walk_trace_nodes(nodes: list[dict[str, Any]]):
    for node in nodes or []:
        if not isinstance(node, dict):
            continue
        yield node
        yield from _walk_trace_nodes(node.get("children") or [])


def detect_tracer_moments(
    trace_tree: list[dict[str, Any]],
) -> list[Moment]:
    """Detect errors, hotspots, and recursion in a Tracer call tree."""

    moments: list[Moment] = []
    for index, node in enumerate(_walk_trace_nodes(trace_tree)):
        name = str(node.get("name") or "function")
        reference = node.get("sourceRef")
        line = reference.get("startLine") if isinstance(reference, dict) else None
        error = node.get("error")
        if error:
            message = str(error)
            if len(message) > 100:
                message = message[:97] + "..."
            moments.append(
                Moment(
                    id=f"tracer-error-{index}",
                    world="python",
                    kind="exception",
                    concepts=["failure"],
                    severity="error",
                    importance=1.0,
                    line=line,
                    source_ref=reference if isinstance(reference, dict) else None,
                    label=f"函数 {name} 抛出异常",
                    why=message,
                    evidence=[
                        MomentEvidence(
                            type="call",
                            line=line,
                            field=name,
                            value=message,
                            source_ref=reference if isinstance(reference, dict) else None,
                        )
                    ],
                    tags=["tracer", "exception"],
                )
            )
            continue

        cost = node.get("costSeconds")
        if isinstance(cost, (int, float)) and cost >= 0.05:
            moments.append(
                Moment(
                    id=f"tracer-hotspot-{index}",
                    world="python",
                    kind="hotspot",
                    concepts=["performance"],
                    severity="warning",
                    importance=0.7,
                    line=line,
                    source_ref=reference if isinstance(reference, dict) else None,
                    label=f"热点：{name} 耗时 {cost:.3f}s",
                    why="这个调用比同级调用更耗时。",
                    evidence=[
                        MomentEvidence(
                            type="call",
                            line=line,
                            field=name,
                            value=cost,
                            source_ref=reference if isinstance(reference, dict) else None,
                        )
                    ],
                    tags=["tracer", "hotspot"],
                )
            )

        children = node.get("children") or []
        if any(
            isinstance(child, dict) and child.get("name") == node.get("name")
            for child in children
        ):
            moments.append(
                Moment(
                    id=f"tracer-recursion-{index}",
                    world="python",
                    kind="call",
                    concepts=["call", "recursion"],
                    severity="info",
                    importance=0.7,
                    line=line,
                    source_ref=reference if isinstance(reference, dict) else None,
                    label=f"递归：{name} 调用自己",
                    why="同一个函数在调用树里直接递归。",
                    evidence=[
                        MomentEvidence(
                            type="call",
                            line=line,
                            field=name,
                            source_ref=reference if isinstance(reference, dict) else None,
                        )
                    ],
                    tags=["tracer", "recursion"],
                )
            )
    return moments


def detect_python_moments(
    trace: list[dict[str, Any]],
    code: str,
    *,
    analysis: dict[str, Any] | None = None,
) -> list[Moment]:
    """Detect key moments from a Python Tutor trace.

    The detector is intentionally rule-based and single-pass over the trace so it
    can run inside the existing trace response without adding perceptible latency.
    """

    if not trace:
        return []

    source_hash = _source_hash(code)
    used_boundaries: set[tuple[str, int]] = set()
    used_variable_steps: set[str] = set()
    used_steps: set[int] = set()

    moments: list[Moment] = []
    moments.extend(
        _loop_moments(
            trace,
            code,
            source_hash,
            used_boundaries,
            used_variable_steps,
        )
    )
    for moment in moments:
        if moment.step_index is not None:
            used_steps.add(moment.step_index)

    moments.extend(_exception_moments(trace, source_hash))
    moments.extend(_branch_moments(trace, code, source_hash, used_steps))
    moments.extend(_call_moments(trace, source_hash))
    moments.extend(_variable_moments(trace, source_hash, used_steps))

    return _sort_moments(moments)


def _sort_moments(moments: list[Moment]) -> list[Moment]:
    return sorted(
        moments,
        key=lambda moment: (
            moment.step_index if moment.step_index is not None else 10**9,
            -moment.importance,
        ),
    )
