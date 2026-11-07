from __future__ import annotations

import hashlib
import math
from typing import Any

from .models import Moment, MomentEvidence


_EPSILON = 1e-6
_TURN_EPSILON = 1.0


def _source_hash(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _source_ref(line: int, source_hash: str) -> dict[str, Any]:
    return {
        "fileId": "turtle",
        "sourceHash": source_hash,
        "startLine": line,
        "endLine": line,
        "origin": "breakpoints",
    }


def _step_line(step: dict[str, Any]) -> int:
    line = step.get("line")
    return line if isinstance(line, int) and line > 0 else 1


def _turtle_state(step: dict[str, Any]) -> dict[str, Any]:
    state = step.get("turtle")
    return state if isinstance(state, dict) else {}


def _x(step: dict[str, Any]) -> float:
    try:
        return float(_turtle_state(step).get("x") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _y(step: dict[str, Any]) -> float:
    try:
        return float(_turtle_state(step).get("y") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _heading(step: dict[str, Any]) -> float:
    try:
        return float(_turtle_state(step).get("heading") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _distance(ax: float, ay: float, bx: float, by: float) -> float:
    return math.hypot(ax - bx, ay - by)


def _angle_delta(before: float, after: float) -> float:
    return ((after - before + 180.0) % 360.0) - 180.0


def _first_step_index(steps: list[dict[str, Any]]) -> int:
    return 0 if steps else 0


def _error_moment(
    result: dict[str, Any],
    steps: list[dict[str, Any]],
    source_hash: str,
) -> list[Moment]:
    error = result.get("error")
    if not isinstance(error, dict):
        return []
    line = error.get("line")
    if not isinstance(line, int) or line <= 0:
        line = _step_line(steps[0]) if steps else 1
    step_index = None
    for index, step in enumerate(steps):
        if isinstance(step, dict) and _step_line(step) == line:
            step_index = index
            break
    if step_index is None and steps:
        step_index = len(steps) - 1
    category = str(error.get("category") or "runtime")
    title = str(error.get("title") or error.get("message") or "程序执行失败")
    if len(title) > 80:
        title = title[:77] + "..."
    return [
        Moment(
            id=f"turtle-error-{line}",
            world="turtle",
            kind="exception",
            concepts=["failure"],
            severity="error",
            importance=1.0,
            step_index=step_index,
            line=line,
            source_ref=_source_ref(line, source_hash),
            label=f"运行出错：{title}",
            why=f"第 {line} 行的{category}错误让执行停在这里。",
            evidence=[
                MomentEvidence(
                    type="trace_step",
                    step_index=step_index,
                    line=line,
                    value=title,
                )
            ],
            tags=["error", category],
        )
    ]


def _first_last_moments(
    steps: list[dict[str, Any]],
    source_hash: str,
) -> list[Moment]:
    if not steps:
        return []
    first = steps[0]
    last = steps[-1]
    moments = [
        Moment(
            id="turtle-first-step",
            world="turtle",
            kind="boundary",
            concepts=["sequence"],
            severity="info",
            importance=0.35,
            step_index=0,
            line=_step_line(first),
            source_ref=_source_ref(_step_line(first), source_hash),
            label="程序开始",
            why="海龟从起点出发。",
            evidence=[MomentEvidence(type="trace_step", step_index=0, line=_step_line(first))],
            tags=["start"],
        )
    ]
    if len(steps) > 1:
        moments.append(
            Moment(
                id="turtle-last-step",
                world="turtle",
                kind="boundary",
                concepts=["sequence"],
                severity="info",
                importance=0.4,
                step_index=len(steps) - 1,
                line=_step_line(last),
                source_ref=_source_ref(_step_line(last), source_hash),
                label="程序结束",
                why="执行到这里结束。",
                evidence=[
                    MomentEvidence(
                        type="trace_step",
                        step_index=len(steps) - 1,
                        line=_step_line(last),
                    )
                ],
                tags=["end"],
            )
        )
    return moments


def _closure_moments(
    steps: list[dict[str, Any]],
    source_hash: str,
) -> list[Moment]:
    if len(steps) < 4:
        return []
    start_x = _x(steps[0])
    start_y = _y(steps[0])
    previous_x = start_x
    previous_y = start_y
    moves = 0
    for index in range(1, len(steps)):
        step = steps[index]
        x = _x(step)
        y = _y(step)
        if _distance(previous_x, previous_y, x, y) > _EPSILON:
            moves += 1
        previous_x, previous_y = x, y
        if moves >= 3 and _distance(start_x, start_y, x, y) <= _EPSILON:
            return [
                Moment(
                    id=f"turtle-closure-{index}",
                    world="turtle",
                    kind="closure",
                    concepts=["closure", "geometry", "boundary"],
                    severity="info",
                    importance=0.95,
                    step_index=index,
                    line=_step_line(step),
                    source_ref=_source_ref(_step_line(step), source_hash),
                    label="图形在这里闭合",
                    why="海龟回到起点，路径闭合。",
                    evidence=[
                        MomentEvidence(
                            type="trace_step",
                            step_index=index,
                            line=_step_line(step),
                            value={"x": round(x, 3), "y": round(y, 3)},
                        ),
                        MomentEvidence(
                            type="command",
                            value={"type": "closure", "moves": moves},
                        ),
                    ],
                    tags=["closure", "geometry"],
                )
            ]
    return []


def _turn_moments(
    steps: list[dict[str, Any]],
    source_hash: str,
) -> list[Moment]:
    moments: list[Moment] = []
    first_turn: tuple[int, float] | None = None
    largest_turn: tuple[int, float] | None = None
    for index in range(1, len(steps)):
        delta = _angle_delta(_heading(steps[index - 1]), _heading(steps[index]))
        if abs(delta) < _TURN_EPSILON:
            continue
        if first_turn is None:
            first_turn = (index, delta)
        if largest_turn is None or abs(delta) > abs(largest_turn[1]):
            largest_turn = (index, delta)

    if first_turn is not None:
        index, delta = first_turn
        step = steps[index]
        moments.append(
            Moment(
                id=f"turtle-turn-{index}",
                world="turtle",
                kind="state_change",
                concepts=["state", "geometry"],
                severity="info",
                importance=0.5,
                step_index=index,
                line=_step_line(step),
                source_ref=_source_ref(_step_line(step), source_hash),
                label=f"转向 {delta:+.0f}°",
                why=(
                    f"海龟朝向从 {_heading(steps[index - 1]):.0f}° "
                    f"变成 {_heading(step):.0f}°。"
                ),
                evidence=[
                    MomentEvidence(
                        type="trace_step",
                        step_index=index,
                        line=_step_line(step),
                        value={"heading": round(_heading(step), 3)},
                    )
                ],
                tags=["turn", "geometry"],
            )
        )

    if (
        largest_turn is not None
        and first_turn is not None
        and largest_turn[0] != first_turn[0]
        and abs(largest_turn[1]) >= 45
    ):
        index, delta = largest_turn
        step = steps[index]
        moments.append(
            Moment(
                id=f"turtle-turn-largest-{index}",
                world="turtle",
                kind="state_change",
                concepts=["state", "geometry"],
                severity="info",
                importance=0.55,
                step_index=index,
                line=_step_line(step),
                source_ref=_source_ref(_step_line(step), source_hash),
                label=f"最大转向 {delta:+.0f}°",
                why="这是整段绘图里角度变化最大的一次转向。",
                evidence=[
                    MomentEvidence(
                        type="trace_step",
                        step_index=index,
                        line=_step_line(step),
                        value={"heading": round(_heading(step), 3)},
                    )
                ],
                tags=["turn", "geometry"],
            )
        )
    return moments


def _line_has_commands(steps: list[dict[str, Any]], indexes: list[int]) -> bool:
    for index in indexes:
        current = steps[index]
        current_count = int(current.get("commandCount") or 0)
        if index == 0:
            if current_count > 0:
                return True
            continue
        previous = steps[index - 1]
        if current_count > int(previous.get("commandCount") or 0):
            return True
    return False


def _merge_repeated_groups(
    repeated: list[tuple[int, list[int]]],
) -> list[tuple[list[int], list[int]]]:
    merged: list[tuple[list[int], list[int], int]] = []
    for line, indexes in repeated:
        if merged:
            lines, merged_indexes, count = merged[-1]
            if line == lines[-1] + 1 and len(indexes) == count:
                lines.append(line)
                merged_indexes.extend(indexes)
                continue
        merged.append(([line], list(indexes), len(indexes)))
    return [(lines, indexes) for lines, indexes, _ in merged]


def _loop_moments(
    steps: list[dict[str, Any]],
    source_hash: str,
) -> list[Moment]:
    groups: dict[int, list[int]] = {}
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        groups.setdefault(_step_line(step), []).append(index)

    repeated = [
        (line, indexes)
        for line, indexes in groups.items()
        if len(indexes) >= 2
        # The `for` header repeats once more than the body but emits no drawing
        # command; only mark lines that actually changed the drawing state.
        and _line_has_commands(steps, indexes)
    ]
    repeated.sort(key=lambda item: item[0])
    groups_to_show = _merge_repeated_groups(repeated)[:2]

    moments: list[Moment] = []
    for lines, indexes in groups_to_show:
        line = lines[0]
        iterations = max(1, len(indexes) // max(1, len(lines)))
        first_index = min(indexes)
        last_index = max(indexes)
        moments.append(
            Moment(
                id=f"turtle-loop-{line}-first",
                world="turtle",
                kind="boundary",
                concepts=["repetition", "boundary"],
                severity="info",
                importance=0.65,
                step_index=first_index,
                line=line,
                source_ref=_source_ref(line, source_hash),
                label="循环第 1 次执行",
                why=f"第 {line} 行开始的循环体一共执行了 {iterations} 次。",
                evidence=[
                    MomentEvidence(
                        type="trace_step",
                        step_index=first_index,
                        line=line,
                    )
                ],
                tags=["loop", "first-iteration"],
            )
        )
        if last_index != first_index:
            moments.append(
                Moment(
                    id=f"turtle-loop-{line}-last",
                    world="turtle",
                    kind="boundary",
                    concepts=["repetition", "boundary"],
                    severity="info",
                    importance=0.7,
                    step_index=last_index,
                    line=line,
                    source_ref=_source_ref(line, source_hash),
                    label="循环最后一次执行",
                    why=f"循环体的第 {iterations} 次执行。",
                    evidence=[
                        MomentEvidence(
                            type="trace_step",
                            step_index=last_index,
                            line=line,
                        )
                    ],
                    tags=["loop", "last-iteration"],
                )
            )
    return moments


def _open_shape_moment(
    steps: list[dict[str, Any]],
    source_hash: str,
) -> list[Moment]:
    if len(steps) < 5:
        return []
    start_x = _x(steps[0])
    start_y = _y(steps[0])
    previous_x = start_x
    previous_y = start_y
    moves: list[float] = []
    turns: list[float] = []
    for index in range(1, len(steps)):
        step = steps[index]
        x = _x(step)
        y = _y(step)
        distance = _distance(previous_x, previous_y, x, y)
        if distance > _EPSILON:
            moves.append(distance)
        turn = _angle_delta(_heading(steps[index - 1]), _heading(step))
        if abs(turn) >= _TURN_EPSILON:
            turns.append(turn)
        previous_x, previous_y = x, y

    final = steps[-1]
    if _distance(start_x, start_y, _x(final), _y(final)) <= _EPSILON:
        return []
    if len(moves) < 3 or len(turns) < 3:
        return []

    mean_move = sum(moves) / len(moves)
    if mean_move <= 0:
        return []
    if any(abs(value - mean_move) > mean_move * 0.1 for value in moves):
        return []
    mean_turn = sum(turns) / len(turns)
    if abs(mean_turn) < 1:
        return []
    if any(abs(value - mean_turn) > 5 for value in turns):
        return []

    index = len(steps) - 1
    return [
        Moment(
            id="turtle-open-shape",
            world="turtle",
            kind="closure",
            concepts=["closure", "geometry", "boundary"],
            severity="warning",
            importance=0.85,
            step_index=index,
            line=_step_line(final),
            source_ref=_source_ref(_step_line(final), source_hash),
            label="图形没有闭合",
            why=(
                f"海龟走了 {len(moves)} 条边、转了 {len(turns)} 次，"
                "但最后没有回到起点。"
            ),
            evidence=[
                MomentEvidence(
                    type="command",
                    value={
                        "moves": len(moves),
                        "turns": len(turns),
                        "meanTurn": round(mean_turn, 3),
                    },
                )
            ],
            tags=["closure", "open-shape", "off-by-one"],
        )
    ]


def _style_moments(
    steps: list[dict[str, Any]],
    source_hash: str,
) -> list[Moment]:
    moments: list[Moment] = []
    fields = {
        "penDown": "抬笔/落笔",
        "color": "画笔颜色",
        "size": "画笔粗细",
        "filling": "填充状态",
    }
    seen: set[str] = set()
    previous = _turtle_state(steps[0]) if steps else {}
    for index in range(1, len(steps)):
        current = _turtle_state(steps[index])
        for field, label in fields.items():
            if field in seen:
                continue
            if previous.get(field) == current.get(field):
                continue
            seen.add(field)
            step = steps[index]
            moments.append(
                Moment(
                    id=f"turtle-style-{field}-{index}",
                    world="turtle",
                    kind="style",
                    concepts=["state"],
                    severity="info",
                    importance=0.45,
                    step_index=index,
                    line=_step_line(step),
                    source_ref=_source_ref(_step_line(step), source_hash),
                    label=f"{label}改变",
                    why=f"{label}从 {previous.get(field)} 变成 {current.get(field)}。",
                    evidence=[
                        MomentEvidence(
                            type="trace_step",
                            step_index=index,
                            line=_step_line(step),
                            field=field,
                            value=current.get(field),
                        )
                    ],
                    tags=["style", field],
                )
            )
        previous = current
        if len(moments) >= 3:
            break
    return moments


def _variable_moments(
    steps: list[dict[str, Any]],
    source_hash: str,
) -> list[Moment]:
    moments: list[Moment] = []
    seen: set[str] = set()
    for index, step in enumerate(steps):
        for variable in step.get("variables") or []:
            if not isinstance(variable, dict):
                continue
            name = variable.get("name")
            type_name = str(variable.get("type") or "")
            if not isinstance(name, str) or name in seen:
                continue
            if type_name not in {"int", "float", "bool", "str"}:
                continue
            seen.add(name)
            line = _step_line(step)
            moments.append(
                Moment(
                    id=f"turtle-var-{name}-{index}",
                    world="turtle",
                    kind="state_change",
                    concepts=["state"],
                    severity="info",
                    importance=0.4,
                    step_index=index,
                    line=line,
                    source_ref=_source_ref(line, source_hash),
                    label=f"{name} = {variable.get('value')}",
                    why=f"变量 {name} 第一次出现。",
                    evidence=[
                        MomentEvidence(
                            type="variable",
                            step_index=index,
                            line=line,
                            field=name,
                            value=variable.get("value"),
                        )
                    ],
                    tags=["variable", "first-appearance"],
                )
            )
            if len(moments) >= 3:
                return moments
    return moments


def detect_turtle_moments(
    result: dict[str, Any],
    *,
    source: str | None = None,
) -> list[Moment]:
    """Detect key moments from a Turtle compile result.

    Works from the existing `steps`/`error` payload only; it never re-executes
    the program and never calls a model.
    """

    steps = [step for step in (result.get("steps") or []) if isinstance(step, dict)]
    source_text = source or str(result.get("source") or result.get("generatedCode") or "")
    source_hash = _source_hash(source_text)

    moments: list[Moment] = []
    moments.extend(_error_moment(result, steps, source_hash))
    moments.extend(_first_last_moments(steps, source_hash))
    moments.extend(_closure_moments(steps, source_hash))
    if not any(moment.kind == "closure" for moment in moments):
        moments.extend(_open_shape_moment(steps, source_hash))
    moments.extend(_turn_moments(steps, source_hash))
    moments.extend(_loop_moments(steps, source_hash))
    moments.extend(_style_moments(steps, source_hash))
    moments.extend(_variable_moments(steps, source_hash))

    return sorted(
        moments,
        key=lambda moment: (
            moment.step_index if moment.step_index is not None else 10**9,
            -moment.importance,
        ),
    )
