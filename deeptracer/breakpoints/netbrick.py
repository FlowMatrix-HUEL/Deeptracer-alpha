from __future__ import annotations

from typing import Any

from .models import Moment, MomentEvidence


def _valid_shape(shape: Any) -> bool:
    return isinstance(shape, list) and len(shape) > 0


def _shape_text(shape: Any) -> str:
    if not _valid_shape(shape):
        return "—"
    return "[" + ", ".join(str(item) for item in shape) + "]"


def _step_index(step: dict[str, Any], fallback: int = 0) -> int:
    index = step.get("index")
    return index if isinstance(index, int) else fallback


def _first_last_moments(
    steps: list[dict[str, Any]],
) -> list[Moment]:
    if not steps:
        return []
    first = steps[0]
    last = steps[-1]
    moments = [
        Moment(
            id="nb-first-step",
            world="netbrick",
            kind="boundary",
            concepts=["sequence"],
            severity="info",
            importance=0.35,
            step_index=_step_index(first),
            node_id=first.get("node_id"),
            label="输入进入网络",
            why="结构追踪从这里开始。",
            evidence=[
                MomentEvidence(
                    type="shape",
                    step_index=_step_index(first),
                    node_id=first.get("node_id"),
                    value=first.get("output_shape"),
                )
            ],
            tags=["start"],
        )
    ]
    if len(steps) > 1:
        moments.append(
            Moment(
                id="nb-last-step",
                world="netbrick",
                kind="boundary",
                concepts=["sequence"],
                severity="info",
                importance=0.4,
                step_index=_step_index(last, len(steps) - 1),
                node_id=last.get("node_id"),
                label="输出离开网络",
                why="结构追踪在这里结束。",
                evidence=[
                    MomentEvidence(
                        type="shape",
                        step_index=_step_index(last, len(steps) - 1),
                        node_id=last.get("node_id"),
                        value=last.get("output_shape"),
                    )
                ],
                tags=["end"],
            )
        )
    return moments


def detect_netbrick_moments(trace: dict[str, Any]) -> list[Moment]:
    """Detect key moments from a NetBrick trace preview payload.

    Works from `TraceResponse.steps` and `TraceResponse.diagnostics`; it never
    creates tensors or calls a model.
    """

    steps = [step for step in (trace.get("steps") or []) if isinstance(step, dict)]
    diagnostics = [
        item for item in (trace.get("diagnostics") or []) if isinstance(item, dict)
    ]
    moments: list[Moment] = []
    moments.extend(_first_last_moments(steps))

    for position, step in enumerate(steps):
        index = _step_index(step, position)
        node_id = step.get("node_id")
        label = str(step.get("label") or node_id or "节点")
        input_shape = step.get("input_shape")
        output_shape = step.get("output_shape")
        input_shapes = step.get("input_shapes")

        if (
            _valid_shape(input_shape)
            and _valid_shape(output_shape)
            and input_shape != output_shape
        ):
            rank_change = len(input_shape) != len(output_shape)
            moments.append(
                Moment(
                    id=f"nb-shape-{index}-{node_id or 'node'}",
                    world="netbrick",
                    kind="shape_change",
                    concepts=["shape", "dataflow"],
                    severity="info",
                    importance=0.75 if rank_change else 0.6,
                    step_index=index,
                    node_id=node_id,
                    label=f"Shape: {_shape_text(input_shape)} → {_shape_text(output_shape)}",
                    why=(
                        f"{label} 把张量从 {_shape_text(input_shape)} "
                        f"变成 {_shape_text(output_shape)}。"
                        + (" rank 发生了变化。" if rank_change else "")
                    ),
                    evidence=[
                        MomentEvidence(
                            type="shape",
                            step_index=index,
                            node_id=node_id,
                            value={
                                "input": input_shape,
                                "output": output_shape,
                                "rankChange": rank_change,
                            },
                        )
                    ],
                    tags=["shape", "rank-change" if rank_change else "shape-change"],
                )
            )

        if isinstance(input_shapes, list) and len(input_shapes) >= 2:
            valid_inputs = [shape for shape in input_shapes if _valid_shape(shape)]
            if len(valid_inputs) >= 2:
                moments.append(
                    Moment(
                        id=f"nb-merge-{index}-{node_id or 'node'}",
                        world="netbrick",
                        kind="merge",
                        concepts=["dataflow", "merge"],
                        severity="info",
                        importance=0.65,
                        step_index=index,
                        node_id=node_id,
                        label=f"合并 {len(valid_inputs)} 路输入",
                        why=f"{label} 把多路张量合成一路。",
                        evidence=[
                            MomentEvidence(
                                type="shape",
                                step_index=index,
                                node_id=node_id,
                                value=valid_inputs,
                            )
                        ],
                        tags=["merge", "dataflow"],
                    )
                )

        if label.startswith("control.") or label.startswith("control_"):
            moments.append(
                Moment(
                    id=f"nb-control-{index}-{node_id or 'node'}",
                    world="netbrick",
                    kind="control_flow",
                    concepts=["control"],
                    severity="info",
                    importance=0.6,
                    step_index=index,
                    node_id=node_id,
                    label=f"控制流：{label}",
                    why="这里进入或退出一个结构化控制流区域。",
                    evidence=[
                        MomentEvidence(
                            type="shape",
                            step_index=index,
                            node_id=node_id,
                            value=step.get("output_shape"),
                        )
                    ],
                    tags=["control-flow"],
                )
            )

        note = str(step.get("note") or "")
        if "复合" in note:
            moments.append(
                Moment(
                    id=f"nb-composite-{index}-{node_id or 'node'}",
                    world="netbrick",
                    kind="boundary",
                    concepts=["abstraction", "composite"],
                    severity="info",
                    importance=0.6,
                    step_index=index,
                    node_id=node_id,
                    label="复合模块边界",
                    why=f"{label} 是一个可复用的复合模块。",
                    evidence=[
                        MomentEvidence(
                            type="shape",
                            step_index=index,
                            node_id=node_id,
                            value=step.get("output_shape"),
                        )
                    ],
                    tags=["composite"],
                )
            )

    step_by_node = {
        step.get("node_id"): step
        for step in steps
        if isinstance(step.get("node_id"), str) and step.get("node_id")
    }
    for position, diagnostic in enumerate(diagnostics):
        node_id = diagnostic.get("node_id")
        step = step_by_node.get(node_id) if isinstance(node_id, str) else None
        severity = str(diagnostic.get("severity") or "info")
        if severity not in {"info", "warning", "error"}:
            severity = "info"
        code = str(diagnostic.get("code") or "diagnostic")
        message = str(diagnostic.get("message") or code)
        if len(message) > 100:
            message = message[:97] + "..."
        teaching_tip = str(diagnostic.get("teaching_tip") or "").strip()
        moments.append(
            Moment(
                id=f"nb-diagnostic-{node_id or position}-{code}",
                world="netbrick",
                kind="diagnostic",
                concepts=["failure"],
                severity=severity,
                importance=1.0 if severity == "error" else 0.7,
                step_index=_step_index(step, position) if step else None,
                node_id=node_id if isinstance(node_id, str) else None,
                label=f"诊断：{message}",
                why=teaching_tip or message,
                evidence=[
                    MomentEvidence(
                        type="diagnostic",
                        step_index=_step_index(step, position) if step else None,
                        node_id=node_id if isinstance(node_id, str) else None,
                        value=code,
                    )
                ],
                tags=["diagnostic", severity],
            )
        )

    return sorted(
        moments,
        key=lambda moment: (
            moment.step_index if moment.step_index is not None else 10**9,
            -moment.importance,
        ),
    )
