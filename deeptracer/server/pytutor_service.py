from __future__ import annotations

import json
import sys
import types
from functools import lru_cache
from io import StringIO
from pathlib import Path

from deeptracer import DEEPTRACER_DEV_ROOT


@lru_cache(maxsize=1)
def _vendor_root() -> Path:
    return Path(DEEPTRACER_DEV_ROOT) / "vendor" / "pathrise-python-tutor" / "v5-unity"


@lru_cache(maxsize=1)
def _load_pg_logger():
    vendor_root = _vendor_root()
    vendor_path = str(vendor_root)
    if vendor_path not in sys.path:
        sys.path.insert(0, vendor_path)

    # Python Tutor's legacy backend still imports the removed stdlib `imp`.
    if "imp" not in sys.modules:
        imp_module = types.ModuleType("imp")
        imp_module.new_module = types.ModuleType
        sys.modules["imp"] = imp_module

    import pg_logger  # type: ignore

    return pg_logger


def get_pytutor_static_dir() -> Path:
    return _vendor_root()


def is_pytutor_available() -> bool:
    vendor_root = _vendor_root()
    return vendor_root.exists() and (vendor_root / "iframe-embed.html").exists()


def execute_python_tutor_trace(
    user_script: str,
    raw_input_json: str = "[]",
    options_json: str = "{}",
) -> dict:
    if not is_pytutor_available():
        raise FileNotFoundError("Python Tutor local runtime is not available.")

    pg_logger = _load_pg_logger()
    out = StringIO()
    options = json.loads(options_json or "{}")

    def json_finalizer(input_code: str, output_trace: list[dict]) -> None:
        payload = {"code": input_code, "trace": output_trace}
        out.write(json.dumps(payload, ensure_ascii=False))

    pg_logger.exec_script_str_local(
        user_script,
        raw_input_json or "[]",
        bool(options.get("cumulative_mode", False)),
        options.get("heap_primitives", False),
        json_finalizer,
    )
    return json.loads(out.getvalue())
