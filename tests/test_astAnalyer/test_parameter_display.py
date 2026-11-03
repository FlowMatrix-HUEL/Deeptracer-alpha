from __future__ import annotations

import ast

from deeptracer.astAnalyer import AstAnalyer
from deeptracer.astAnalyer.signatures import (
    collect_parameters,
    format_function_signature,
)
from deeptracer.server.analysis_service import _collect_functions


SAMPLE = '''
def outer(a: int, b="x", /, c: float = 1.0, *args: int, flag=True, **kwargs: object) -> None:
    def inner(value):
        if value:
            return value
        return 0
    for item in args:
        if item:
            print(inner(item))
'''


def test_signature_model_preserves_parameter_kinds_and_defaults():
    node = ast.parse(SAMPLE).body[0]

    assert format_function_signature(node) == (
        "def outer(a: int, b='x', /, c: float=1.0, *args: int, "
        "flag=True, **kwargs: object) -> None"
    )
    parameters = collect_parameters(node)
    assert [item["kind"] for item in parameters] == [
        "positional-only",
        "positional-only",
        "positional-or-keyword",
        "var-positional",
        "keyword-only",
        "var-keyword",
    ]
    assert parameters[1]["default"] == "'x'"
    assert parameters[3]["annotation"] == "int"


def test_ast_visualization_contains_signature_and_parameter_nodes(tmp_path):
    source_path = tmp_path / "parameters.py"
    source_path.write_text(SAMPLE, encoding="utf-8")

    analyzer = AstAnalyer(str(source_path))
    labels = [attrs["label"] for _, attrs in analyzer.graph.nodes(data=True)]
    edge_labels = [attrs["label"] for _, _, attrs in analyzer.graph.edges(data=True)]

    assert any("def outer(" in label for label in labels)
    assert any(label.startswith("Parameter\nkwargs") for label in labels)
    assert "var-keyword" in edge_labels
    assert "body" in edge_labels

    html = analyzer.visualize()
    assert "def outer(" in html
    assert "**kwargs" in html


def test_nested_function_complexity_is_not_counted_in_parent():
    functions = _collect_functions(ast.parse(SAMPLE))
    by_name = {item["name"]: item for item in functions}

    assert by_name["outer"]["complexity"] == 3
    assert by_name["inner"]["complexity"] == 2
    assert by_name["inner"]["qualified_name"] == "outer.inner"
