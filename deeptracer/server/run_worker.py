from __future__ import annotations

import io
import json
import os
import sys
import traceback
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from time import perf_counter


_OUTPUT_LIMIT = 512_000


class LimitedBuffer(io.StringIO):
    def write(self, value: str) -> int:
        remaining = _OUTPUT_LIMIT - self.tell()
        if remaining <= 0:
            return 0
        return super().write(value[:remaining])


def run_script(path: Path) -> dict:
    code = path.read_text(encoding="utf-8")
    stdout = LimitedBuffer()
    stderr = LimitedBuffer()
    namespace = {
        "__file__": str(path),
        "__name__": "__main__",
        "__package__": None,
        "__cached__": None,
    }
    previous_cwd = os.getcwd()
    runtime_error = None
    traceback_text = ""
    started = perf_counter()

    try:
        sys.path.insert(0, str(path.parent))
        os.chdir(path.parent)
        compiled = compile(code, str(path), "exec")
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                exec(compiled, namespace)
            except BaseException as exc:
                runtime_error = f"{type(exc).__name__}: {exc}"
                traceback_text = traceback.format_exc(limit=8)
    finally:
        os.chdir(previous_cwd)
        if sys.path and sys.path[0] == str(path.parent):
            sys.path.pop(0)

    return {
        "durationMs": (perf_counter() - started) * 1000,
        "stdout": stdout.getvalue(),
        "stderr": stderr.getvalue(),
        "runtimeError": runtime_error,
        "traceback": traceback_text,
        "exitCode": 1 if runtime_error else 0,
    }


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: run_worker.py <python-file>")
    result = run_script(Path(sys.argv[1]).resolve())
    sys.__stdout__.write(json.dumps(result, ensure_ascii=False))
    sys.__stdout__.flush()


if __name__ == "__main__":
    main()
