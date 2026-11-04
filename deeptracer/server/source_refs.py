from __future__ import annotations

import ast
import hashlib
from typing import Any


EDITOR_FILE_ID = "editor"


def hash_source(source_code: str) -> str:
    return hashlib.sha256(source_code.encode("utf-8")).hexdigest()


def source_ref(
    source_hash: str,
    *,
    start_line: int,
    end_line: int | None = None,
    start_col: int | None = None,
    end_col: int | None = None,
    symbol: str | None = None,
    origin: str = "source",
    **metadata: Any,
) -> dict[str, Any]:
    start = max(1, int(start_line or 1))
    end = max(start, int(end_line or start))
    reference = {
        "fileId": EDITOR_FILE_ID,
        "sourceHash": source_hash,
        "startLine": start,
        "startCol": max(0, int(start_col or 0)),
        "endLine": end,
        "endCol": max(0, int(end_col or 0)),
        "symbol": symbol,
        "origin": origin,
    }
    if metadata:
        reference.update(metadata)
    return reference


def source_functions(source_code: str, source_hash: str) -> list[dict[str, Any]]:
    tree = ast.parse(source_code)
    functions: list[dict[str, Any]] = []

    def visit(node: ast.AST, scope: tuple[str, ...]) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            qualified_name = ".".join((*scope, node.name))
            start_line = getattr(node, "lineno", 1)
            end_line = getattr(node, "end_lineno", start_line)
            functions.append(
                {
                    "name": node.name,
                    "qualifiedName": qualified_name,
                    "lineno": start_line,
                    "endLineno": end_line,
                    "sourceRef": source_ref(
                        source_hash,
                        start_line=start_line,
                        end_line=end_line,
                        start_col=getattr(node, "col_offset", 0),
                        end_col=getattr(node, "end_col_offset", 0),
                        symbol=qualified_name,
                        origin="function",
                    ),
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
    return functions


def call_site_refs(
    source_code: str, source_hash: str
) -> dict[str, list[dict[str, Any]]]:
    tree = ast.parse(source_code)
    result: dict[str, list[dict[str, Any]]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node.func)
        if not name:
            continue
        line = getattr(node, "lineno", 1)
        result.setdefault(name, []).append(
            source_ref(
                source_hash,
                start_line=line,
                end_line=getattr(node, "end_lineno", line),
                start_col=getattr(node, "col_offset", 0),
                end_col=getattr(node, "end_col_offset", 0),
                symbol=name,
                origin="tracer",
                sourcePrecision="call",
            )
        )
    for references in result.values():
        references.sort(key=lambda item: item["startLine"])
    return result


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None
