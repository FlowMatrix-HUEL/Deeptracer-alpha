from __future__ import annotations

import ast
from typing import Any


def unparse(node: ast.AST | None, fallback: str = "") -> str:
    if node is None:
        return fallback
    try:
        return ast.unparse(node)
    except (AttributeError, TypeError, ValueError):
        return fallback


def collect_parameters(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[dict[str, Any]]:
    """Return an ordered, JSON-friendly description of a function signature."""
    arguments = node.args
    positional = [*arguments.posonlyargs, *arguments.args]
    first_default = len(positional) - len(arguments.defaults)
    parameters: list[dict[str, Any]] = []

    for index, argument in enumerate(positional):
        default_node = (
            arguments.defaults[index - first_default]
            if index >= first_default
            else None
        )
        parameters.append(
            _parameter(
                argument,
                kind=(
                    "positional-only"
                    if index < len(arguments.posonlyargs)
                    else "positional-or-keyword"
                ),
                default=default_node,
            )
        )

    if arguments.vararg is not None:
        parameters.append(_parameter(arguments.vararg, kind="var-positional"))

    for argument, default_node in zip(arguments.kwonlyargs, arguments.kw_defaults):
        parameters.append(
            _parameter(argument, kind="keyword-only", default=default_node)
        )

    if arguments.kwarg is not None:
        parameters.append(_parameter(arguments.kwarg, kind="var-keyword"))

    return parameters


def format_function_signature(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    include_async: bool = True,
) -> str:
    prefix = "async def" if include_async and isinstance(node, ast.AsyncFunctionDef) else "def"
    returns = f" -> {unparse(node.returns)}" if node.returns is not None else ""
    return f"{prefix} {node.name}({unparse(node.args)}){returns}"


def _parameter(
    argument: ast.arg,
    *,
    kind: str,
    default: ast.AST | None = None,
) -> dict[str, Any]:
    return {
        "name": argument.arg,
        "kind": kind,
        "annotation": unparse(argument.annotation) or None,
        "default": unparse(default) if default is not None else None,
        "required": default is None and kind not in {"var-positional", "var-keyword"},
    }
