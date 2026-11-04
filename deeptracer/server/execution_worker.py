from __future__ import annotations

import ast
import cProfile
import io
import json
import os
import pstats
import sys
import tracemalloc
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from time import perf_counter

from pyinstrument import Profiler
from pyinstrument.renderers import HTMLRenderer


_OUTPUT_LIMIT = 64_000


class LimitedBuffer(io.StringIO):
    def write(self, value: str) -> int:
        remaining = _OUTPUT_LIMIT - self.tell()
        if remaining <= 0:
            return 0
        return super().write(value[:remaining])


def profile_script(path: Path) -> dict:
    code = path.read_text(encoding="utf-8")
    profiler = cProfile.Profile()
    configured_interval = os.getenv("DEEPTRACER_PYINSTRUMENT_INTERVAL_SECONDS")
    if configured_interval:
        pyinstrument_interval = float(configured_interval)
    else:
        has_imports = any(
            isinstance(node, (ast.Import, ast.ImportFrom))
            for node in ast.walk(ast.parse(code))
        )
        pyinstrument_interval = 0.0005 if has_imports else 0.0002
    pyinstrument_max_samples = max(
        1,
        int(os.getenv("DEEPTRACER_PYINSTRUMENT_MAX_SAMPLES", "2000")),
    )
    pyinstrument_profiler = Profiler(interval=pyinstrument_interval)
    output = LimitedBuffer()
    peak_bytes = 0
    duration_ms = 0.0
    profile_rows: list[dict] = []
    memory_rows: list[dict] = []
    pyinstrument_html = ""
    pyinstrument_sample_count = 0
    error_message = None
    cwd = os.getcwd()
    parent_text = str(path.parent)
    globals_dict = {
        "__file__": str(path),
        "__name__": "__main__",
        "__package__": None,
        "__cached__": None,
    }

    try:
        sys.path.insert(0, parent_text)
        os.chdir(path.parent)
        compiled = compile(code, str(path), "exec")
        tracemalloc.start()
        start = perf_counter()
        with redirect_stdout(output), redirect_stderr(output):
            profiler.enable()
            pyinstrument_profiler.start()
            try:
                exec(compiled, globals_dict)
            except BaseException as exc:
                error_message = f"{type(exc).__name__}: {exc}"
            finally:
                pyinstrument_profiler.stop()
                profiler.disable()
        duration_ms = (perf_counter() - start) * 1000
        _, peak_bytes = tracemalloc.get_traced_memory()
        snapshot = tracemalloc.take_snapshot()
        profile_rows = _profile_rows(profiler, path)
        memory_rows = _memory_rows(snapshot, peak_bytes, path)
        if pyinstrument_profiler.last_session is not None:
            session = pyinstrument_profiler.last_session
            if session.sample_count > pyinstrument_max_samples and session.duration:
                target_interval = max(
                    pyinstrument_interval,
                    session.duration / pyinstrument_max_samples,
                )
                session = session.resample(target_interval)
            pyinstrument_sample_count = session.sample_count
            pyinstrument_html = HTMLRenderer().render(
                session
            )
    except BaseException as exc:
        error_message = f"{type(exc).__name__}: {exc}"
    finally:
        if tracemalloc.is_tracing():
            tracemalloc.stop()
        if sys.path and sys.path[0] == parent_text:
            sys.path.pop(0)
        os.chdir(cwd)

    return {
        "duration_ms": duration_ms,
        "peak_mb": peak_bytes / (1024 * 1024) if peak_bytes else 0.0,
        "profile_rows": profile_rows,
        "memory_rows": memory_rows,
        "pyinstrument_html": pyinstrument_html,
        "pyinstrument_sample_count": pyinstrument_sample_count,
        "stdout": output.getvalue(),
        "error": error_message,
    }


def _profile_rows(profiler: cProfile.Profile, path: Path) -> list[dict]:
    stats = pstats.Stats(profiler)
    rows = []
    for (filename, lineno, name), values in stats.stats.items():
        if not filename:
            continue
        try:
            same_file = Path(filename).resolve() == path.resolve()
        except OSError:
            same_file = False
        if not same_file:
            continue
        cc, nc, tt, ct, _ = values
        rows.append(
            {
                "label": name,
                "line": lineno,
                "calls": nc or cc,
                "total_ms": ct * 1000,
                "self_ms": tt * 1000,
            }
        )
    rows.sort(key=lambda item: item["total_ms"], reverse=True)
    return rows[:5]


def _memory_rows(
    snapshot: tracemalloc.Snapshot,
    peak_bytes: float,
    path: Path,
) -> list[dict]:
    rows = []
    for stat in snapshot.statistics("lineno")[:6]:
        frame = stat.traceback[0]
        try:
            same_file = Path(frame.filename).resolve() == path.resolve()
        except OSError:
            same_file = False
        if not same_file:
            continue
        rows.append(
            {
                "label": f"第 {frame.lineno} 行",
                "value": round(
                    (stat.size / peak_bytes * 100) if peak_bytes else 0.0,
                    1,
                ),
                "size_kb": round(stat.size / 1024, 1),
            }
        )
    return rows[:4]


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: execution_worker.py <python-file>")
    result = profile_script(Path(sys.argv[1]).resolve())
    sys.__stdout__.write(json.dumps(result, ensure_ascii=False))
    sys.__stdout__.flush()


if __name__ == "__main__":
    main()
