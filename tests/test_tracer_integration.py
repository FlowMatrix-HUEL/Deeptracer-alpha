from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO

import deeptracer
from deeptracer.server.analysis_service import analyze_python_input
from deeptracer.server.tracer_service import build_trace_tree, execute_tracer_trace
from deeptracer.tracing import Tracer, tracer


TRACE_SOURCE = '''
def add(x, y):
    return x + y


def chain(n):
    if n <= 1:
        return add(1, 1)
    return add(n, chain(n - 1))


print(chain(3))
'''


def test_tracer_library_is_available_from_deeptracer():
    def add(x, y):
        return x + y

    output = StringIO()
    with redirect_stdout(output):
        with Tracer(trace_fn=[add]):
            assert add(1, 2) == 3

    assert Tracer.__module__ == "tracer.core.Tracer"
    assert tracer.__module__ == "tracer.core.Tracer"
    assert deeptracer.Tracer is Tracer
    assert deeptracer.tracer is tracer
    assert "add returned 3" in output.getvalue()


def test_tracer_service_builds_nested_call_tree():
    result = execute_tracer_trace(
        source_code=TRACE_SOURCE,
        functions=["chain", "add"],
        options={"timeTrace": True, "useColor": False},
    )

    assert result["runtimeError"] is None
    assert result["callCount"] == 6
    assert result["traceTree"][0]["name"] == "chain"
    assert result["traceTree"][0]["children"][0]["name"] == "chain"
    assert result["statistics"]["add"]["calls"] == 3
    assert "Function Trace Statistics Report" in result["terminalOutput"]
    assert result["sourceHash"]
    root = result["traceTree"][0]
    assert root["sourceRef"]["startLine"] > 0
    assert root["definitionRef"]["startLine"] > 0
    assert root["sourceRef"]["sourceHash"] == result["sourceHash"]
    assert root["sourcePrecision"] in {"call", "definition"}


def test_trace_tree_parser_preserves_nested_returns_and_costs():
    roots = build_trace_tree(
        [
            "-> outer()",
            "|  -> inner(x=1)",
            "|  |  <- inner returned 2 | cost=0.000010s",
            "|  <- outer returned 2 | cost=0.000020s",
        ]
    )

    assert roots[0]["returned"] == "2"
    assert roots[0]["costSeconds"] == 0.00002
    assert roots[0]["argumentText"] == "()"
    assert roots[0]["children"][0]["returned"] == "2"
    assert roots[0]["children"][0]["argumentText"] == "(x=1)"


def test_tracer_tolerates_uninitialized_local_variables_at_call_event():
    result = execute_tracer_trace(
        source_code=(
            "def summarize(values):\n"
            "    total = sum(values)\n"
            "    return total / len(values)\n"
            "\n"
            "print(summarize([1, 2, 3]))\n"
        ),
        functions=["summarize"],
        options={"timeTrace": True},
    )

    assert result["runtimeError"] is None
    assert result["traceTree"][0]["returned"] == "2.0"


def test_analyzed_user_code_can_import_local_tracer():
    result = analyze_python_input(
        source_code=(
            "from tracer import Tracer, tracer\n"
            "print(Tracer.__name__, tracer.__name__)\n"
        ),
        display_name="tracer_import.py",
    )

    assert result["meta"]["runtimeError"] is None
    assert result["meta"]["stdout"].strip() == "Tracer tracer"
