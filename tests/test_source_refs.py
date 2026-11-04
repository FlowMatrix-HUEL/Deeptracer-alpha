from __future__ import annotations

from deeptracer.server.analysis_service import _build_perf_tab, analyze_python_input
from deeptracer.server.source_refs import (
    EDITOR_FILE_ID,
    call_site_refs,
    hash_source,
    source_functions,
)


SOURCE = """def outer(value):
    return inner(value) + 1


def inner(value):
    return value * 2


outer(3)
"""


def test_source_functions_and_calls_have_stable_source_refs():
    digest = hash_source(SOURCE)
    functions = source_functions(SOURCE, digest)
    calls = call_site_refs(SOURCE, digest)

    outer = next(item for item in functions if item["name"] == "outer")
    inner_calls = calls["inner"]

    assert outer["sourceRef"]["fileId"] == EDITOR_FILE_ID
    assert outer["sourceRef"]["sourceHash"] == digest
    assert outer["sourceRef"]["startLine"] == 1
    assert outer["sourceRef"]["endLine"] == 2
    assert inner_calls[0]["startLine"] == 2


def test_analysis_payload_exposes_function_hotspot_and_anchor_locations():
    payload = analyze_python_input(
        source_code=(
            "def add(value):\n"
            "    print(value + 1)\n"
            "    return value + 1\n"
            "\n"
            "add(2)\n"
        ),
        display_name="locations.py",
    )

    digest = payload["meta"]["sourceHash"]
    function = payload["analysisMap"]["ast"]["functions"][0]
    suggestion = payload["suggestions"][0]
    anchors = suggestion["detail"]["codeAnchors"]

    assert payload["meta"]["fileId"] == EDITOR_FILE_ID
    assert function["sourceRef"]["sourceHash"] == digest
    assert anchors[0]["sourceRef"]["sourceHash"] == digest
    assert "deeptracer:reveal-source" in payload["visualizations"]["ast"]


def test_ast_visualization_embeds_source_refs():
    payload = analyze_python_input(
        source_code="def visible(value):\n    return value\n",
        display_name="visible.py",
    )

    html = payload["visualizations"]["ast"]

    assert '"sourceRef"' in html
    assert '"startLine": 1' in html
    assert "network.on(\"click\"" in html


def test_performance_rows_become_clickable_source_refs():
    digest = hash_source(SOURCE)
    runtime = {
        "duration_ms": 12.0,
        "error": None,
        "profile_rows": [
            {
                "label": "inner",
                "line": 6,
                "calls": 3,
                "total_ms": 4.0,
                "self_ms": 2.0,
            }
        ],
    }

    tab = _build_perf_tab(runtime, [], digest)

    assert tab["hotspots"][0]["sourceRef"]["startLine"] == 6
    assert tab["hotspots"][0]["sourceRef"]["origin"] == "performance"
