from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

from deeptracer import DEEPTRACER_DEV_ROOT
from deeptracer.breakpoints.python import detect_python_moments
from deeptracer.breakpoints.ranking import rank_moments
from deeptracer.tracer_support import get_tracer_python_path


@lru_cache(maxsize=1)
def _vendor_root() -> Path:
    return Path(DEEPTRACER_DEV_ROOT) / "vendor" / "pathrise-python-tutor" / "v5-unity"


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

    options = json.loads(options_json or "{}")
    payload = {
        "userScript": user_script,
        "rawInputJson": raw_input_json or "[]",
        "cumulativeMode": bool(options.get("cumulative_mode", False)),
        "heapPrimitives": bool(options.get("heap_primitives", False)),
    }
    environment = os.environ.copy()
    project_root = str(Path(__file__).resolve().parents[2])
    existing_python_path = environment.get("PYTHONPATH")
    python_paths = [
        project_root,
        get_tracer_python_path(),
        existing_python_path,
    ]
    environment["PYTHONPATH"] = os.pathsep.join(
        item for item in python_paths if item
    )
    environment["PYTHONIOENCODING"] = "utf-8"
    timeout_seconds = float(os.getenv("DEEPTRACER_TUTOR_TIMEOUT_SECONDS", "8"))
    process = subprocess.Popen(
        [sys.executable, "-m", "deeptracer.server.pytutor_worker"],
        cwd=project_root,
        env=environment,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        start_new_session=os.name == "posix",
    )
    try:
        stdout, stderr = process.communicate(
            json.dumps(payload, ensure_ascii=False),
            timeout=max(0.1, timeout_seconds),
        )
    except subprocess.TimeoutExpired:
        _terminate_process_tree(process)
        process.communicate()
        raise TimeoutError(
            f"Python Tutor execution exceeded {timeout_seconds:g} seconds."
        )

    if process.returncode != 0:
        detail = (stderr or stdout or "").strip()
        raise RuntimeError(
            "Python Tutor execution failed"
            + (f": {detail[-800:]}" if detail else f" (exit code {process.returncode})")
        )
    try:
        result = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Python Tutor returned invalid JSON.") from exc
    if not isinstance(result, dict):
        raise RuntimeError("Python Tutor returned an invalid trace.")
    moments = rank_moments(
        detect_python_moments(result.get("trace") or [], user_script),
        limit=5,
    )
    result["moments"] = [moment.model_dump() for moment in moments]
    return result


def _terminate_process_tree(process: subprocess.Popen) -> None:
    try:
        if os.name == "posix":
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        else:
            process.kill()
    except OSError:
        pass
