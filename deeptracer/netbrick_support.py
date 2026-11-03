from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path


def get_netbrick_root(*, required: bool = False) -> Path | None:
    configured = os.getenv("DEEPTRACER_NETBRICK_ROOT")
    candidates = [
        Path(configured).expanduser() if configured else None,
        Path(__file__).resolve().parents[1] / "NetBrick",
        Path.home() / "NetBrick",
    ]
    for candidate in candidates:
        if candidate is not None and (candidate / "backend" / "app.py").exists():
            return candidate.resolve()
    if required:
        raise ImportError(
            "找不到 NetBrick。请将 NetBrick 放在项目根目录，"
            "或设置 DEEPTRACER_NETBRICK_ROOT。"
        )
    return None


def get_netbrick_dist() -> Path | None:
    root = get_netbrick_root()
    if root is None:
        return None
    dist = root / "frontend" / "dist"
    return dist if (dist / "index.html").exists() else None


@lru_cache(maxsize=1)
def get_netbrick_app():
    root = get_netbrick_root(required=True)
    root_text = str(root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    from backend.app import app

    return app
