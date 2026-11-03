from __future__ import annotations

import os
import sys
from pathlib import Path


def get_tracer_root(*, required: bool = False) -> Path | None:
    configured = os.getenv("DEEPTRACER_TRACER_ROOT")
    candidates = [
        Path(configured).expanduser() if configured else None,
        Path(__file__).resolve().parents[1] / "Tracer",
        Path.home() / "Tracer",
    ]
    for candidate in candidates:
        if candidate is not None and (candidate / "tracer" / "__init__.py").exists():
            return candidate.resolve()
    if required:
        raise ImportError(
            "找不到本地 Tracer 库。请将 Tracer 目录放在项目根目录，"
            "或设置 DEEPTRACER_TRACER_ROOT。"
        )
    return None


def ensure_tracer_importable() -> Path:
    tracer_root = get_tracer_root(required=True)
    root_text = str(tracer_root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    return tracer_root


def get_tracer_python_path() -> str | None:
    tracer_root = get_tracer_root()
    return str(tracer_root) if tracer_root is not None else None
