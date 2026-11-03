# TraceError.py
from __future__ import annotations

import json
import os
import textwrap
import traceback
from dataclasses import dataclass, field
from typing import Any

from tracer.core.Color import set_color

DEFAULT_MAX_REPR = 200


def _safe_str(value: Any, max_len: int) -> str:
    """Best-effort stringify that never raises and never explodes in size."""
    try:
        text = str(value)
    except BaseException as err:  # pragma: no cover - exotic __str__
        text = f"<unprintable {type(value).__name__}: {err}>"
    if max_len > 0 and len(text) > max_len:
        text = text[:max_len] + f"...<+{len(text) - max_len} chars>"
    return text


def _safe_repr(value: Any, max_len: int) -> str:
    try:
        text = repr(value)
    except BaseException as err:  # pragma: no cover - exotic __repr__
        text = f"<unrepresentable {type(value).__name__}: {err}>"
    if max_len > 0 and len(text) > max_len:
        text = text[:max_len] + f"...<+{len(text) - max_len} chars>"
    return text


def _collapse(names: list[str]) -> list[str]:
    """Run-length fold consecutive duplicates: [mid, mid, outer] -> ['mid x2', 'outer']."""
    folded: list[str] = []
    prev: str | None = None
    run = 0
    for name in list(names) + [None]:  # type: ignore[list-item]
        if name == prev:
            run += 1
            continue
        if prev is not None:
            folded.append(prev if run == 1 else f"{prev} x{run}")
        prev = name
        run = 1
    return folded


@dataclass
class FrameInfo:
    """One frame extracted from a traceback object."""

    func_name: str
    filename: str
    lineno: int
    code_line: str

    def to_dict(self) -> dict:
        return {
            "func_name": self.func_name,
            "filename": self.filename,
            "lineno": self.lineno,
            "code_line": self.code_line,
        }

    def format_text(self) -> str:
        head = f'File "{self.filename}", line {self.lineno}, in {self.func_name}'
        if self.code_line:
            return f"{head}\n    {self.code_line.strip()}"
        return head


@dataclass
class ExcRecord:
    """A single exception observed inside the traced scope."""

    seq: int
    exc_type: str
    message: str
    origin: FrameInfo | None = None
    stack: list[FrameInfo] = field(default_factory=list)
    path: list[str] = field(default_factory=list)
    handled_by: str | None = None
    escaped: bool = False
    locals_snapshot: dict[str, str] | None = None

    @property
    def header(self) -> str:
        return f"{self.exc_type}: {self.message}" if self.message else self.exc_type

    @property
    def status(self) -> str:
        if self.handled_by is not None:
            return f"handled by {self.handled_by}()"
        if self.escaped:
            return "escaped (unhandled within traced scope)"
        return "observed"

    def to_dict(self) -> dict:
        return {
            "seq": self.seq,
            "exc_type": self.exc_type,
            "message": self.message,
            "status": self.status,
            "raised_at": self.origin.to_dict() if self.origin else None,
            "handled_by": self.handled_by,
            "escaped": self.escaped,
            "propagation_path": _collapse(self.path),
            "stack": [f.to_dict() for f in self.stack],
            "locals": self.locals_snapshot,
        }

    def format_text(self, setcolor: bool = False) -> str:
        head = f"#{self.seq}  {self.header}"
        head = set_color(s=head, color="red") if setcolor else head
        status = self.status
        status = set_color(s=status, color="yellow") if setcolor else status

        lines = [head, f"    status      : {status}"]
        if self.origin:
            lines.append(
                f"    raised at   : {self.origin.func_name}() "
                f"-> {os.path.basename(self.origin.filename)}:{self.origin.lineno}"
            )
        if self.path:
            lines.append(f"    propagated  : {' -> '.join(_collapse(self.path))}")
        lines.append("    stack (outermost -> raise point):")
        for f in self.stack:
            lines.append(textwrap.indent(f.format_text(), "      "))
        if self.locals_snapshot:
            lines.append("    locals at observation point:")
            for k, v in self.locals_snapshot.items():
                lines.append(f"      {k} = {v}")
        return "\n".join(lines)


class TraceErrors:
    """
    Collector for exceptions raised inside the traced scope.

    One exception object propagating through several traced frames is stored as a
    single record enriched with:
      - full traceback stack (including frames that were NOT traced)
      - the propagation path across traced functions
      - whether it was swallowed by a traced function or escaped the scope
    """

    def __init__(self, show_locals: bool = False, max_repr: int = DEFAULT_MAX_REPR):
        self.records: list[ExcRecord] = []
        self.show_locals = show_locals
        self.max_repr = max_repr
        self._by_id: dict[int, ExcRecord] = {}
        self._keepalive: dict[int, Any] = {}

    def observe(self, func_name:str, arg, frame) -> ExcRecord:
        """Called from the 'exception' trace event. arg = (type, value, tb)."""
        exc_type, exc_value, tb = arg
        stack = [
            FrameInfo(
                func_name=fs.name,
                filename=fs.filename,
                lineno=fs.lineno,
                code_line=fs.line or "",
            )
            for fs in traceback.extract_tb(tb)
        ]

        key = id(exc_value)
        rec = self._by_id.get(key)
        if rec is None:
            rec = ExcRecord(
                seq=len(self.records) + 1,
                exc_type=getattr(exc_type, "__name__", str(exc_type)),
                message=_safe_str(exc_value, self.max_repr),
                origin=stack[-1] if stack else None,
                stack=stack,
            )
            if self.show_locals:
                rec.locals_snapshot = {
                    k: _safe_repr(v, self.max_repr) for k, v in frame.f_locals.items()
                }
            self._by_id[key] = rec
            # keep a strong ref so `id()` can not be recycled while tracing
            self._keepalive[key] = exc_value
            self.records.append(rec)
        elif len(stack) > len(rec.stack):
            # deeper observation -> strictly richer stack, keep the longest one
            rec.stack = stack

        rec.path.append(func_name)
        return rec

    def mark_handled(self, rec: ExcRecord, func_name: str) -> None:
        if rec.handled_by is None:
            rec.handled_by = func_name

    def finalize(self) -> None:
        """Called once the traced scope ends: classify every record."""
        for rec in self.records:
            if rec.handled_by is None:
                rec.escaped = True
        self.pending_clear()

    def pending_clear(self) -> None:
        self._keepalive.clear()
        self._by_id.clear()

    @property
    def unhandled(self) -> list[ExcRecord]:
        return [r for r in self.records if r.handled_by is None]

    @property
    def handled(self) -> list[ExcRecord]:
        return [r for r in self.records if r.handled_by is not None]

    def to_list(self) -> list[dict]:
        return [r.to_dict() for r in self.records]

    def export_json(self, path: str) -> None:
        payload = {
            "summary": {
                "total": len(self.records),
                "unhandled": len(self.unhandled),
                "handled": len(self.handled),
                "by_type": self._count_by_type(),
            },
            "exceptions": self.to_list(),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def _count_by_type(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for r in self.records:
            counts[r.exc_type] = counts.get(r.exc_type, 0) + 1
        return counts

    def print_report(self, setcolor: bool = False) -> None:
        title = "===== Exception Trace Report ====="
        print(f"\n{title}")
        if not self.records:
            print("No exception observed inside traced scope.")
            print("=" * len(title) + "\n")
            return

        summary = (
            f"total={len(self.records)}  "
            f"unhandled={len(self.unhandled)}  "
            f"handled={len(self.handled)}  "
            f"by_type={self._count_by_type()}"
        )
        print(set_color(s=summary, color="blue") if setcolor else summary)
        print("-" * len(title))
        for rec in self.records:
            print(rec.format_text(setcolor=setcolor))
            print("-" * len(title))
        print("=" * len(title) + "\n")
