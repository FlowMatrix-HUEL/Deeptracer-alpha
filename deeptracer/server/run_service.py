from __future__ import annotations

import ast
import json
import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from deeptracer.tracer_support import get_tracer_python_path


def execute_python_code(source_code: str) -> dict[str, Any]:
    code = source_code.strip("\n")
    if not code.strip():
        raise ValueError("代码为空，无法运行。")
    ast.parse(code)
    timeout_seconds = float(os.getenv("DEEPTRACER_RUN_TIMEOUT_SECONDS", "5"))

    with tempfile.TemporaryDirectory(prefix="deeptracer-run-") as temp_dir:
        source_path = Path(temp_dir) / "run_script.py"
        source_path.write_text(code + "\n", encoding="utf-8")
        environment = os.environ.copy()
        project_root = str(Path(__file__).resolve().parents[2])
        python_paths = [
            project_root,
            get_tracer_python_path(),
            environment.get("PYTHONPATH"),
        ]
        environment["PYTHONPATH"] = os.pathsep.join(
            item for item in python_paths if item
        )
        environment["PYTHONIOENCODING"] = "utf-8"
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "deeptracer.server.run_worker",
                str(source_path),
            ],
            cwd=temp_dir,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            start_new_session=os.name == "posix",
        )
        try:
            stdout, stderr = process.communicate(timeout=max(0.1, timeout_seconds))
        except subprocess.TimeoutExpired:
            _terminate_process_tree(process)
            process.communicate()
            raise TimeoutError(
                f"代码运行超过 {timeout_seconds:g} 秒，已终止执行。"
            )

    if process.returncode != 0:
        detail = (stderr or stdout or "").strip()
        raise RuntimeError(
            "运行进程异常退出"
            + (f"：{detail[-1000:]}" if detail else f"（退出码 {process.returncode}）")
        )
    try:
        result = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("运行进程返回了无效结果。") from exc
    if not isinstance(result, dict):
        raise RuntimeError("运行进程返回了无效结果。")
    return result


def _terminate_process_tree(process: subprocess.Popen) -> None:
    try:
        if os.name == "posix":
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        else:
            process.kill()
    except OSError:
        pass
