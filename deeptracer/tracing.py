"""DeepTracer integration for the local Tracer library.

The Tracer source remains independent and unchanged. This module only adds its
repository root to the import path and exposes the public API.
"""

from __future__ import annotations

from typing import Any

from deeptracer.tracer_support import (
    ensure_tracer_importable,
    get_tracer_python_path,
    get_tracer_root,
)

__all__ = [
    "Tracer",
    "get_tracer_python_path",
    "get_tracer_root",
    "tracer",
]


def __getattr__(name: str) -> Any:
    if name in {"Tracer", "tracer"}:
        ensure_tracer_importable()
        from tracer import Tracer, tracer

        exports = {"Tracer": Tracer, "tracer": tracer}
        globals().update(exports)
        return exports[name]
    raise AttributeError(name)
