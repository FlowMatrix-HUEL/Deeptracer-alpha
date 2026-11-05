from __future__ import annotations

import json
import math
import sys
import traceback
import types
from dataclasses import dataclass, field
from typing import Any


_FILENAME = "<turtle-student>"


@dataclass
class TurtleState:
    x: float = 0.0
    y: float = 0.0
    heading: float = 0.0
    pen_down: bool = True
    color: str = "#3370ff"
    size: float = 2.0
    fill_color: str = "#3370ff"
    filling: bool = False
    speed_value: float = 3.0
    commands: list[dict[str, Any]] = field(default_factory=list)

    def forward(self, distance: float) -> None:
        self._move(float(distance), source_line=_source_line())

    def backward(self, distance: float) -> None:
        self._move(-float(distance), source_line=_source_line())

    def left(self, angle: float) -> None:
        old = self.heading
        self.heading = (self.heading + float(angle)) % 360
        self.commands.append(
            {
                "type": "turn",
                "fromHeading": old,
                "toHeading": self.heading,
                "line": _source_line(),
            }
        )

    def right(self, angle: float) -> None:
        old = self.heading
        self.heading = (self.heading - float(angle)) % 360
        self.commands.append(
            {
                "type": "turn",
                "fromHeading": old,
                "toHeading": self.heading,
                "line": _source_line(),
            }
        )

    def penup(self) -> None:
        self.pen_down = False

    def pendown(self) -> None:
        self.pen_down = True

    def pencolor(self, color: str) -> None:
        self.color = str(color)
        self.commands.append(
            {
                "type": "style",
                "color": self.color,
                "line": _source_line(),
            }
        )

    def pensize(self, size: float) -> None:
        self.size = float(size)
        self.commands.append(
            {
                "type": "style",
                "size": self.size,
                "line": _source_line(),
            }
        )

    def fillcolor(self, color: str) -> None:
        self.fill_color = str(color)
        self.commands.append(
            {
                "type": "style",
                "fillColor": self.fill_color,
                "line": _source_line(),
            }
        )

    def speed(self, value: float) -> None:
        self.speed_value = float(value)

    def begin_fill(self) -> None:
        if self.filling:
            return
        self.filling = True
        self.commands.append(
            {
                "type": "fill_start",
                "at": {"x": self.x, "y": self.y},
                "color": self.fill_color or self.color,
                "line": _source_line(),
            }
        )

    def end_fill(self) -> None:
        if not self.filling:
            return
        start_index = next(
            (
                index
                for index in range(len(self.commands) - 1, -1, -1)
                if self.commands[index].get("type") == "fill_start"
            ),
            None,
        )
        start_command = (
            self.commands[start_index]
            if start_index is not None
            else {"at": {"x": self.x, "y": self.y}, "color": self.fill_color}
        )
        points = [start_command["at"]]
        if start_index is not None:
            for command in self.commands[start_index + 1:]:
                if command.get("type") == "move":
                    points.append(command["to"])
        self.commands.append(
            {
                "type": "fill",
                "points": points,
                "color": start_command.get("color") or self.fill_color or self.color,
                "line": _source_line(),
            }
        )
        self.filling = False

    def circle(self, radius: float, extent: float = 360, steps: int | None = None) -> None:
        radius = float(radius)
        extent = float(extent)
        step_count = int(steps) if steps else max(12, int(abs(extent) / 10))
        for _ in range(step_count):
            angle = extent / step_count
            arc = math.radians(angle) * radius
            self._move(arc, source_line=_source_line())
            old = self.heading
            self.heading = (self.heading + angle) % 360
            self.commands.append(
                {
                    "type": "turn",
                    "fromHeading": old,
                    "toHeading": self.heading,
                    "line": _source_line(),
                }
            )

    def goto(self, x: float, y: float) -> None:
        self._move_to(float(x), float(y), source_line=_source_line())

    def setheading(self, angle: float) -> None:
        old = self.heading
        self.heading = float(angle) % 360
        self.commands.append(
            {
                "type": "turn",
                "fromHeading": old,
                "toHeading": self.heading,
                "line": _source_line(),
            }
        )

    def dot(self, size: float = 5) -> None:
        self.commands.append(
            {
                "type": "dot",
                "x": self.x,
                "y": self.y,
                "size": float(size),
                "color": self.color,
                "line": _source_line(),
            }
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "x": round(self.x, 3),
            "y": round(self.y, 3),
            "heading": round(self.heading, 3),
            "penDown": self.pen_down,
            "color": self.color,
            "size": self.size,
            "fillColor": self.fill_color,
            "filling": self.filling,
            "speed": self.speed_value,
        }

    def _move(self, distance: float, *, source_line: int) -> None:
        radians = math.radians(self.heading)
        self._move_to(
            self.x + math.cos(radians) * distance,
            self.y + math.sin(radians) * distance,
            source_line=source_line,
        )

    def _move_to(self, x: float, y: float, *, source_line: int) -> None:
        command = {
            "type": "move",
            "from": {"x": self.x, "y": self.y},
            "to": {"x": x, "y": y},
            "penDown": self.pen_down,
            "color": self.color,
            "size": self.size,
            "line": source_line,
        }
        self.x = x
        self.y = y
        self.commands.append(command)


class ScreenState:
    """A small, non-blocking screen facade used by the teaching runner."""

    def __init__(self) -> None:
        self.name = "我的 Turtle 图形"
        self.key_bindings: list[dict[str, Any]] = []
        self.click_bindings: list[dict[str, Any]] = []
        self.listening = False

    def title(self, value: str) -> None:
        self.name = str(value)

    def setup(self, *args: Any, **kwargs: Any) -> None:
        return None

    def bgcolor(self, *args: Any, **kwargs: Any) -> None:
        return None

    def onkeypress(self, function: Any, key: Any = None) -> None:
        self.key_bindings.append(
            {"key": str(key) if key is not None else "", "handler": getattr(function, "__name__", "")}
        )

    onkey = onkeypress

    def onscreenclick(self, function: Any, button: Any = 1, add: Any = None) -> None:
        self.click_bindings.append(
            {"button": button, "handler": getattr(function, "__name__", "")}
        )

    onclick = onscreenclick

    def listen(self) -> None:
        self.listening = True

    def mainloop(self) -> None:
        return None

    done = mainloop
    exitonclick = mainloop

    def bye(self) -> None:
        return None

    def snapshot(self) -> dict[str, Any]:
        return {
            "title": self.name,
            "keyBindings": self.key_bindings,
            "clickBindings": self.click_bindings,
            "listening": self.listening,
        }


def _source_line() -> int:
    frame = sys._getframe(2)
    while frame and frame.f_code.co_filename != _FILENAME:
        frame = frame.f_back
    return frame.f_lineno if frame else 0


def _serialize_variable(value: Any) -> tuple[Any, str]:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value, type(value).__name__
    if isinstance(value, (list, tuple)):
        items = []
        for item in value[:20]:
            serialized, _ = _serialize_variable(item)
            items.append(serialized)
        return items, type(value).__name__
    if isinstance(value, dict):
        result = {}
        for key, item in list(value.items())[:20]:
            serialized, _ = _serialize_variable(item)
            result[str(key)] = serialized
        return result, "dict"
    return repr(value)[:200], type(value).__name__


_SCAFFOLD_NAMES = {
    "artist",
    "screen",
    "forward",
    "backward",
    "back",
    "left",
    "right",
    "penup",
    "pendown",
    "pencolor",
    "pensize",
    "fillcolor",
    "begin_fill",
    "end_fill",
    "circle",
    "goto",
    "setheading",
    "dot",
    "speed",
    "done",
}


def _is_user_variable(name: str, value: Any) -> bool:
    if name.startswith("__") or name in _SCAFFOLD_NAMES:
        return False
    if isinstance(value, types.ModuleType):
        return False
    if callable(value) or hasattr(value, "write"):
        return False
    return True


def _variable_record(
    name: str,
    value: Any,
    *,
    scope: str,
    scope_kind: str,
) -> dict[str, Any]:
    serialized, type_name = _serialize_variable(value)
    return {
        "name": name,
        "value": serialized,
        "type": type_name,
        "scope": scope,
        "scopeKind": scope_kind,
    }


def _global_variables(globals_dict: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _variable_record(
            name,
            value,
            scope="<module>",
            scope_kind="global",
        )
        for name, value in sorted(globals_dict.items())
        if _is_user_variable(name, value)
    ]


def _variables(frame, globals_dict: dict[str, Any]) -> list[dict[str, Any]]:
    variables = _global_variables(globals_dict)
    local_names = set(frame.f_locals)
    if frame.f_code.co_name == "<module>":
        return variables

    for name, value in sorted(frame.f_locals.items()):
        if not _is_user_variable(name, value):
            continue
        if name in globals_dict and globals_dict[name] is value:
            continue
        variables.append(
            _variable_record(
                name,
                value,
                scope=frame.f_code.co_name,
                scope_kind="local" if name in local_names else "global",
            )
        )
    return variables


def _call_stack(frame) -> list[dict[str, Any]]:
    stack = []
    current = frame
    while current:
        if current.f_code.co_filename == _FILENAME:
            stack.append(
                {
                    "name": current.f_code.co_name,
                    "line": current.f_lineno,
                }
            )
        current = current.f_back
    return list(reversed(stack))


def execute(source: str) -> dict[str, Any]:
    turtle = TurtleState()
    screen = ScreenState()
    steps: list[dict[str, Any]] = []
    globals_dict = {
        "__name__": "__main__",
        "__file__": _FILENAME,
        "__builtins__": __builtins__,
        "screen": screen,
        "artist": turtle,
        "forward": turtle.forward,
        "backward": turtle.backward,
        "back": turtle.backward,
        "left": turtle.left,
        "right": turtle.right,
        "penup": turtle.penup,
        "pendown": turtle.pendown,
        "pencolor": turtle.pencolor,
        "pensize": turtle.pensize,
        "fillcolor": turtle.fillcolor,
        "begin_fill": turtle.begin_fill,
        "end_fill": turtle.end_fill,
        "circle": turtle.circle,
        "goto": turtle.goto,
        "setheading": turtle.setheading,
        "dot": turtle.dot,
        "speed": turtle.speed,
        "done": screen.done,
    }
    error = None
    traceback_text = ""
    pending: tuple[Any, int] | None = None

    def append_pending(*, finished: bool = False) -> None:
        nonlocal pending
        if pending is None:
            return
        frame, line = pending
        steps.append(
            {
                "index": len(steps),
                "line": line,
                "scope": frame.f_code.co_name,
                "variables": _variables(frame, globals_dict),
                "turtle": turtle.snapshot(),
                "commandCount": len(turtle.commands),
                "callStack": _call_stack(frame),
                "finished": finished,
            }
        )
        pending = None

    def trace(frame, event, arg):
        nonlocal pending
        if frame.f_code.co_filename != _FILENAME:
            return None
        if event == "line":
            append_pending()
            pending = (frame, frame.f_lineno)
        elif event == "return" and pending and pending[0] is frame:
            append_pending(finished=frame.f_code.co_name == "<module>")
        return trace

    try:
        compiled = compile(source, _FILENAME, "exec")
        sys.settrace(trace)
        exec(compiled, globals_dict)
    except BaseException as exc:
        error_line = getattr(exc, "lineno", None)
        if error_line is None:
            trace_frames = traceback.extract_tb(exc.__traceback__)
            user_frames = [
                item for item in trace_frames if item.filename == _FILENAME
            ]
            if user_frames:
                error_line = user_frames[-1].lineno
        error = {
            "type": type(exc).__name__,
            "message": str(exc),
            "line": error_line,
            "offset": getattr(exc, "offset", None),
        }
        traceback_text = traceback.format_exc(limit=8)
    finally:
        sys.settrace(None)
        append_pending(finished=error is None)

    final_state = turtle.snapshot()
    final_variables = _global_variables(globals_dict)
    return {
        "ok": error is None,
        "steps": steps,
        "commands": turtle.commands,
        "finalState": final_state,
        "variables": final_variables,
        "screen": screen.snapshot(),
        "error": error,
        "traceback": traceback_text,
    }


def main() -> None:
    payload = json.load(sys.stdin)
    result = execute(str(payload.get("source") or ""))
    sys.__stdout__.write(json.dumps(result, ensure_ascii=False))
    sys.__stdout__.flush()


if __name__ == "__main__":
    main()
