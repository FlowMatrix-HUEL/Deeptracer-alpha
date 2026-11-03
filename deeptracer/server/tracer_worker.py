from __future__ import annotations

import io
import importlib
import json
import os
import sys
import time
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any

from deeptracer.tracer_support import ensure_tracer_importable


_OUTPUT_LIMIT = 512_000


class LimitedBuffer(io.StringIO):
    def write(self, value: str) -> int:
        remaining = _OUTPUT_LIMIT - self.tell()
        if remaining <= 0:
            return 0
        return super().write(value[:remaining])


def _stub(name: str):
    def target():
        return None

    target.__name__ = name
    return target


class _CodeView:
    def __init__(self, code):
        self._code = code
        self.co_name = code.co_name
        self.co_varnames = code.co_varnames[: _argument_count(code)]

    def __getattr__(self, name):
        return getattr(self._code, name)


class _FrameView:
    """Expose only initialized arguments to Tracer at function call time."""

    def __init__(self, frame):
        self._frame = frame
        self.f_code = _CodeView(frame.f_code)
        self.f_locals = {
            name: frame.f_locals.get(name, "<unassigned>")
            for name in self.f_code.co_varnames
        }

    def __getattr__(self, name):
        return getattr(self._frame, name)


def _argument_count(code) -> int:
    count = code.co_argcount + code.co_kwonlyargcount
    count += 1 if code.co_flags & 0x04 else 0  # CO_VARARGS
    count += 1 if code.co_flags & 0x08 else 0  # CO_VARKEYWORDS
    return count


def _install_call_event_compatibility():
    parser_module = importlib.import_module("tracer.core.Parser")
    tracer_module = importlib.import_module("tracer.core.Tracer")
    original = parser_module.frame_callback
    previous_tracer_callback = tracer_module.frame_callback
    frames = {}

    def safe_frame_callback(
        ctx,
        target_set,
        interactive_on_event,
        interactive_filter,
        frame,
        event,
        arg,
    ):
        is_target = (
            frame is not None
            and target_set is not None
            and frame.f_code.co_name in target_set
        )
        if not is_target:
            return original(
                ctx,
                target_set,
                interactive_on_event,
                interactive_filter,
                frame,
                event,
                arg,
            )

        frame_id = id(frame)
        if event == "call":
            safe_frame = frames.setdefault(frame_id, _FrameView(frame))
        else:
            safe_frame = frames.get(frame_id, _FrameView(frame))

        result = original(
            ctx,
            target_set,
            interactive_on_event,
            interactive_filter,
            safe_frame,
            event,
            arg,
        )
        if event == "return":
            frames.pop(frame_id, None)
        return result

    parser_module.frame_callback = safe_frame_callback
    tracer_module.frame_callback = safe_frame_callback

    def restore() -> None:
        parser_module.frame_callback = original
        tracer_module.frame_callback = previous_tracer_callback

    return restore


def trace_script(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    ensure_tracer_importable()
    from tracer import Tracer

    target_names = [str(name) for name in payload.get("targetNames", []) if name]
    if not target_names:
        raise ValueError("至少选择一个需要追踪的函数。")

    options = payload.get("options") or {}
    use_color = bool(options.get("useColor", False))
    if use_color:
        from tracer.core import Color as tracer_color

        tracer_color.COLOR_SUPPORT = True

    code = path.read_text(encoding="utf-8")
    output = LimitedBuffer()
    trace_lines: list[str] = []
    runtime_error = None

    namespace = {
        "__file__": str(path),
        "__name__": "__main__",
        "__package__": None,
        "__cached__": None,
    }
    previous_cwd = os.getcwd()
    sys.path.insert(0, str(path.parent))
    started_at = time.perf_counter()
    tracer_context = Tracer(
        trace_fn=[_stub(name) for name in target_names],
        logging_path=None,
        time_trace=bool(options.get("timeTrace", False)),
        use_color=use_color,
        exception_trace=bool(options.get("exceptionTrace", False)),
        show_locals=bool(options.get("showLocals", False)),
    )
    original_add = tracer_context.ctx.add

    def capture_trace_line(line: str) -> None:
        trace_lines.append(line)
        original_add(line)

    tracer_context.ctx.add = capture_trace_line
    restore_tracer_parser = _install_call_event_compatibility()

    try:
        os.chdir(path.parent)
        compiled = compile(code, str(path), "exec")
        with redirect_stdout(output), redirect_stderr(output):
            try:
                with tracer_context:
                    exec(compiled, namespace)
            except BaseException as exc:
                runtime_error = f"{type(exc).__name__}: {exc}"
    finally:
        restore_tracer_parser()
        os.chdir(previous_cwd)
        if sys.path and sys.path[0] == str(path.parent):
            sys.path.pop(0)

    stats = {}
    if tracer_context.stats is not None:
        for name, stat in tracer_context.stats.data.items():
            stats[name] = {
                "calls": stat.call_count,
                "totalSeconds": stat.total_cost,
                "averageSeconds": stat.avg_cost,
                "minSeconds": 0.0 if stat.min_cost == float("inf") else stat.min_cost,
                "maxSeconds": stat.max_cost,
            }
    errors = []
    if tracer_context.errors is not None:
        errors = tracer_context.errors.to_list()

    return {
        "targetNames": target_names,
        "durationMs": (time.perf_counter() - started_at) * 1000,
        "terminalOutput": output.getvalue(),
        "traceLines": trace_lines,
        "statistics": stats,
        "errors": errors,
        "runtimeError": runtime_error,
    }


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: tracer_worker.py <python-file>")
    payload = json.load(sys.stdin)
    result = trace_script(Path(sys.argv[1]).resolve(), payload)
    sys.__stdout__.write(json.dumps(result, ensure_ascii=False))
    sys.__stdout__.flush()


if __name__ == "__main__":
    main()
