from __future__ import annotations

from deeptracer.server.turtle_service import (
    build_standard_code,
    compile_turtle_source,
)


def test_turtle_service_records_loop_variables_and_turtle_state():
    result = compile_turtle_source(
        "length = 60\n"
        "angle = 90\n"
        "for i in range(3):\n"
        "    forward(length)\n"
        "    right(angle)\n"
    )

    assert result["ok"] is True
    assert result["error"] is None
    assert len(result["commands"]) == 6
    assert result["finalState"]["x"] == 0
    assert result["steps"]
    loop_values = [
        next(
            variable["value"]
            for variable in step["variables"]
            if variable["name"] == "i"
        )
        for step in result["steps"]
        if any(variable["name"] == "i" for variable in step["variables"])
    ]
    assert list(dict.fromkeys(loop_values)) == [0, 1, 2]
    assert all(step["standardLine"] for step in result["steps"] if step["line"])


def test_standard_turtle_code_keeps_source_line_mapping():
    source = "length = 80\nforward(length)\n"
    generated, start_line = build_standard_code(source)

    assert "def draw_scene(artist, screen):" in generated
    assert "def main():" in generated
    assert "draw_scene(artist, screen)" in generated
    assert "forward = artist.forward" in generated
    assert "    length = 80\n    forward(length)" in generated
    assert start_line > 1
    compile(generated, "<generated-turtle>", "exec")


def test_turtle_syntax_error_is_translated_with_line():
    result = compile_turtle_source("for i in range(4)\n    forward(20)\n")

    assert result["ok"] is False
    assert result["error"]["category"] == "syntax"
    assert "冒号" in result["error"]["title"]
    assert result["error"]["line"] == 1


def test_turtle_runtime_error_has_user_line_and_hint():
    result = compile_turtle_source("value = 1 / 0\nforward(value)\n")

    assert result["ok"] is False
    assert result["error"]["category"] == "runtime"
    assert result["error"]["line"] == 1
    assert "除数" in result["error"]["title"]


def test_turtle_timeout_is_reported(monkeypatch):
    monkeypatch.setenv("DEEPTRACER_TURTLE_TIMEOUT_SECONDS", "0.2")

    result = compile_turtle_source("while True:\n    pass\n")

    assert result["ok"] is False
    assert "超时" in result["error"]["message"]


def test_turtle_service_tracks_styles_fill_and_program_features():
    result = compile_turtle_source(
        'pencolor("red")\n'
        "pensize(4)\n"
        'fillcolor("yellow")\n'
        "begin_fill()\n"
        "for i in range(4):\n"
        "    forward(40)\n"
        "    right(90)\n"
        "end_fill()\n"
    )

    assert result["ok"] is True
    assert result["finalState"]["color"] == "red"
    assert result["finalState"]["size"] == 4
    assert result["finalState"]["fillColor"] == "yellow"
    assert any(command["type"] == "style" for command in result["commands"])
    fill = next(command for command in result["commands"] if command["type"] == "fill")
    assert fill["color"] == "yellow"
    assert len(fill["points"]) == 5
    assert result["programFeatures"]["loops"] == 1
    assert result["programFeatures"]["loopIterations"] == [4]


def test_turtle_function_scope_and_event_bindings_are_visible():
    result = compile_turtle_source(
        "length = 40\n"
        "def move_once(size):\n"
        "    local_step = size / 2\n"
        "    forward(local_step)\n"
        "move_once(length)\n"
        "def on_up():\n"
        "    forward(10)\n"
        'screen.onkeypress(on_up, "Up")\n'
        "screen.onscreenclick(lambda x, y: forward(1))\n"
        "screen.listen()\n"
    )

    assert result["ok"] is True
    function_step = next(
        step for step in result["steps"] if step["scope"] == "move_once"
    )
    local_names = {
        variable["name"]
        for variable in function_step["variables"]
        if variable["scopeKind"] == "local"
    }
    assert "size" in local_names
    assert "local_step" in local_names
    assert any(
        variable["name"] == "length" and variable["scopeKind"] == "global"
        for variable in function_step["variables"]
    )
    assert len(function_step["callStack"]) >= 2
    assert result["screen"]["listening"] is True
    assert result["programFeatures"]["functions"] == ["move_once", "on_up"]
    assert "onkeypress" in result["programFeatures"]["eventBindings"]
    assert "onscreenclick" in result["programFeatures"]["eventBindings"]
