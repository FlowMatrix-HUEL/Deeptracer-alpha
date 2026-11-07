from __future__ import annotations

from deeptracer.breakpoints.models import Moment, MomentEvidence
from deeptracer.breakpoints.python import detect_python_moments
from deeptracer.breakpoints.ranking import rank_moments
from deeptracer.breakpoints.turtle import detect_turtle_moments


def test_moment_round_trip():
    moment = Moment(
        id="py-loop-last",
        world="python",
        kind="boundary",
        concepts=["repetition", "boundary"],
        severity="info",
        importance=0.9,
        step_index=42,
        line=7,
        source_ref={
            "fileId": "editor",
            "sourceHash": "abc",
            "startLine": 7,
            "endLine": 7,
        },
        label="最后一次迭代",
        why="循环体最后一次执行",
        evidence=[MomentEvidence(type="trace_step", step_index=42, line=7)],
    )
    payload = moment.model_dump()
    assert payload["id"] == "py-loop-last"
    assert payload["evidence"][0]["step_index"] == 42
    assert Moment.model_validate(payload).world == "python"


def _step(
    line: int,
    *,
    event: str = "step_line",
    globals_: dict | None = None,
    ordered: list[str] | None = None,
    stack: list | None = None,
) -> dict:
    return {
        "line": line,
        "event": event,
        "globals": globals_ or {},
        "ordered_globals": ordered or [],
        "stack_to_render": stack or [],
    }


LOOP_CODE = """\
total = 0
for i in range(5):
    total += i
print(total)
"""

LOOP_TRACE = [
    _step(1),
    _step(2, globals_={"total": 0}, ordered=["total"]),
    _step(3, globals_={"total": 0, "i": 0}, ordered=["total", "i"]),
    _step(2, globals_={"total": 0, "i": 1}, ordered=["total", "i"]),
    _step(3, globals_={"total": 1, "i": 1}, ordered=["total", "i"]),
    _step(2, globals_={"total": 10, "i": 4}, ordered=["total", "i"]),
    _step(3, globals_={"total": 10, "i": 4}, ordered=["total", "i"]),
    _step(2, globals_={"total": 16, "i": 5}, ordered=["total", "i"]),
    _step(4, globals_={"total": 16, "i": 5}, ordered=["total", "i"]),
]


def test_python_loop_marks_first_last_and_exit():
    moments = detect_python_moments(LOOP_TRACE, LOOP_CODE)

    assert any(
        moment.kind == "boundary" and moment.step_index == 2 for moment in moments
    )
    assert any(
        moment.kind == "boundary" and moment.step_index == 6 for moment in moments
    )
    exit_moment = next(
        moment for moment in moments if moment.id.endswith("loop-exit")
    )
    assert exit_moment.actual == {"i": 5} or exit_moment.actual.get("i") == 5


def test_python_zero_iteration_loop_is_marked():
    code = "for i in range(0):\n    print(i)\nprint('done')\n"
    trace = [_step(3)]
    moments = detect_python_moments(trace, code)
    assert any(moment.id.endswith("loop-zero") for moment in moments)


def test_python_exception_is_marked():
    code = "x = 1 / 0\n"
    trace = [
        {
            "line": 1,
            "event": "exception",
            "globals": {},
            "ordered_globals": [],
            "stack_to_render": [],
            "exception_msg": "ZeroDivisionError: division by zero",
        }
    ]
    moments = detect_python_moments(trace, code)
    exception = next(moment for moment in moments if moment.kind == "exception")
    assert exception.line == 1
    assert "ZeroDivisionError" in exception.label


def _turtle_step(index: int, line: int, x: float, y: float, heading: float) -> dict:
    return {
        "index": index,
        "line": line,
        "turtle": {
            "x": x,
            "y": y,
            "heading": heading,
            "penDown": True,
            "color": "#3370ff",
            "size": 2,
            "fillColor": "#3370ff",
            "filling": False,
        },
        "variables": [],
        "commandCount": index,
        "callStack": [],
    }


def test_turtle_closure_is_marked():
    result = {
        "steps": [
            _turtle_step(0, 1, 0, 0, 0),
            _turtle_step(1, 2, 100, 0, 0),
            _turtle_step(2, 3, 100, 100, 90),
            _turtle_step(3, 4, 0, 100, 180),
            _turtle_step(4, 5, 0, 0, 270),
        ],
        "commands": [],
        "programFeatures": {"loopIterations": [], "loops": 0},
        "error": None,
    }
    moments = detect_turtle_moments(result)
    assert any(moment.kind == "closure" for moment in moments)
    assert any(moment.step_index == 4 for moment in moments if moment.kind == "closure")


def test_turtle_error_is_marked():
    result = {
        "steps": [_turtle_step(0, 1, 0, 0, 0)],
        "commands": [],
        "programFeatures": {},
        "error": {"line": 1, "category": "runtime", "title": "boom"},
    }
    moments = detect_turtle_moments(result)
    assert any(
        moment.kind == "exception" and moment.line == 1 for moment in moments
    )


def test_rank_moments_limits_and_prioritizes_errors():
    moments = [
        Moment(
            id=f"m{i}",
            world="python",
            kind="state_change",
            concepts=[],
            severity="info",
            importance=0.1,
            label="x",
            why="x",
        )
        for i in range(10)
    ]
    moments.append(
        Moment(
            id="err",
            world="python",
            kind="exception",
            concepts=[],
            severity="error",
            importance=0.1,
            label="e",
            why="e",
        )
    )
    ranked = rank_moments(moments, limit=3)
    assert len(ranked) == 3
    assert ranked[0].id == "err"


def test_turtle_compile_returns_moments():
    from deeptracer.server.turtle_service import compile_turtle_source

    result = compile_turtle_source("forward(100)\nright(90)\nforward(100)\n")
    assert "moments" in result
    assert isinstance(result["moments"], list)


def test_python_tutor_trace_returns_moments():
    from deeptracer.server.pytutor_service import execute_python_tutor_trace

    result = execute_python_tutor_trace(
        "total = 0\nfor i in range(3):\n    total += i\n"
    )
    assert isinstance(result.get("moments"), list)
    assert any(moment.get("kind") == "boundary" for moment in result["moments"])


def test_tracer_error_node_is_marked():
    from deeptracer.breakpoints.python import detect_tracer_moments

    tree = [
        {
            "kind": "call",
            "name": "f",
            "error": "ValueError: bad",
            "costSeconds": 0.1,
            "sourceRef": {
                "fileId": "editor",
                "sourceHash": "abc",
                "startLine": 1,
                "endLine": 1,
            },
            "children": [],
        }
    ]
    moments = detect_tracer_moments(tree)
    assert any(moment.kind == "exception" for moment in moments)


def test_netbrick_shape_change_is_marked():
    from deeptracer.breakpoints.netbrick import detect_netbrick_moments

    trace = {
        "steps": [
            {
                "index": 0,
                "node_id": "input",
                "label": "Input",
                "output_shape": [1, 784],
            },
            {
                "index": 1,
                "node_id": "linear",
                "label": "nn.Linear",
                "input_shape": [1, 784],
                "output_shape": [1, 128],
            },
        ],
        "diagnostics": [],
    }
    moments = detect_netbrick_moments(trace)
    assert any(
        moment.kind == "shape_change" and moment.node_id == "linear"
        for moment in moments
    )


def test_breakpoints_endpoint_returns_netbrick_moments():
    from fastapi.testclient import TestClient

    from deeptracer.server.app import create_app

    client = TestClient(create_app())
    response = client.post(
        "/api/breakpoints",
        json={
            "world": "netbrick",
            "trace": {
                "steps": [
                    {
                        "index": 0,
                        "node_id": "input",
                        "label": "Input",
                        "output_shape": [1, 784],
                    },
                    {
                        "index": 1,
                        "node_id": "linear",
                        "label": "nn.Linear",
                        "input_shape": [1, 784],
                        "output_shape": [1, 128],
                    },
                ],
                "diagnostics": [],
            },
        },
    )
    assert response.status_code == 200
    assert response.json()["moments"]


def test_enrich_falls_back_when_model_missing(monkeypatch):
    from deeptracer.breakpoints import enrich

    monkeypatch.setattr(enrich, "get_chat_model", lambda optional=False: None)
    moments = [
        {
            "id": "m1",
            "world": "python",
            "kind": "boundary",
            "label": "old",
            "why": "old",
            "question": None,
        }
    ]
    result = enrich.enrich_moments(moments, code="x = 1", world="python")
    assert result[0]["label"] == "old"
    assert result[0]["enriched"] is False


def test_python_detector_stays_fast_on_long_trace():
    import time

    code = "total = 0\nfor i in range(2500):\n    total += i\nprint(total)\n"
    trace = [
        {
            "line": 1,
            "event": "step_line",
            "globals": {},
            "ordered_globals": [],
            "stack_to_render": [],
        }
    ]
    for index in range(2500):
        trace.append(
            {
                "line": 2,
                "event": "step_line",
                "globals": {"total": index, "i": index},
                "ordered_globals": ["total", "i"],
                "stack_to_render": [],
            }
        )
        trace.append(
            {
                "line": 3,
                "event": "step_line",
                "globals": {"total": index, "i": index},
                "ordered_globals": ["total", "i"],
                "stack_to_render": [],
            }
        )
    trace.append(
        {
            "line": 4,
            "event": "step_line",
            "globals": {"total": 0, "i": 2499},
            "ordered_globals": ["total", "i"],
            "stack_to_render": [],
        }
    )

    started = time.perf_counter()
    moments = detect_python_moments(trace, code)
    elapsed = time.perf_counter() - started

    assert moments
    assert elapsed < 0.05


def test_enrich_only_updates_known_ids_and_keeps_evidence(monkeypatch):
    from langchain_core.runnables import RunnableLambda

    from deeptracer.breakpoints import enrich
    from deeptracer.breakpoints.enrich import (
        MomentEnrichment,
        MomentEnrichmentList,
    )

    class FakeModel:
        model_name = "fake-model"

        def with_structured_output(self, schema):
            def invoke(_payload):
                return schema(
                    moments=[
                        MomentEnrichment(
                            id="m1",
                            label="new label",
                            why="new why",
                            question="what is i?",
                        ),
                        MomentEnrichment(
                            id="ghost",
                            label="ghost",
                            why="ghost",
                        ),
                    ]
                )

            return RunnableLambda(invoke)

    monkeypatch.setattr(
        enrich, "get_chat_model", lambda optional=False: FakeModel()
    )
    moments = [
        {
            "id": "m1",
            "label": "old",
            "why": "old",
            "step_index": 7,
            "line": 3,
            "question": None,
        },
        {
            "id": "m2",
            "label": "old2",
            "why": "old2",
            "step_index": 8,
            "line": 4,
            "question": None,
        },
    ]
    result = enrich.enrich_moments(
        moments, code="unique-code-for-enrich-test", world="python"
    )

    assert result[0]["label"] == "new label"
    assert result[0]["why"] == "new why"
    assert result[0]["step_index"] == 7
    assert result[0]["line"] == 3
    assert result[0]["enriched"] is True
    assert result[1]["label"] == "old2"
    assert result[1]["enriched"] is False
    assert all(moment["id"] != "ghost" for moment in result)


def test_enrich_endpoint_falls_back(monkeypatch):
    from fastapi.testclient import TestClient

    from deeptracer.breakpoints import enrich as enrich_module
    from deeptracer.server.app import create_app

    monkeypatch.setattr(enrich_module, "get_chat_model", lambda optional=False: None)
    client = TestClient(create_app())
    response = client.post(
        "/api/breakpoints/enrich",
        json={
            "world": "python",
            "code": "x = 1",
            "moments": [
                {
                    "id": "m1",
                    "label": "old",
                    "why": "old",
                    "question": None,
                }
            ],
        },
    )
    assert response.status_code == 200
    assert response.json()["moments"][0]["enriched"] is False
