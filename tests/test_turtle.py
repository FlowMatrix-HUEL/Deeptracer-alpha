from __future__ import annotations

import asyncio
from pathlib import Path

import httpx

from deeptracer.server.app import create_app


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = (ROOT / "deeptracer" / "templates" / "turtle.html").read_text(
    encoding="utf-8"
)
SCRIPT = (ROOT / "deeptracer" / "static" / "turtle.js").read_text(encoding="utf-8")
STYLES = (ROOT / "deeptracer" / "static" / "turtle.css").read_text(encoding="utf-8")


def _request(method: str, path: str, **kwargs):
    async def request():
        transport = httpx.ASGITransport(app=create_app())
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(request())


def test_home_page_exposes_turtle_entry():
    home = (ROOT / "deeptracer" / "templates" / "index.html").read_text(
        encoding="utf-8"
    )

    assert 'href="/turtle/"' in home
    assert "🐢" in home
    assert ">Turtle<" in home


def test_turtle_page_has_keyboard_guide_and_generated_code_panel():
    assert 'class="shortcut-guide"' in TEMPLATE
    assert "<kbd>↑</kbd><kbd>↓</kbd>" in TEMPLATE
    assert "<kbd>←</kbd><kbd>→</kbd>" in TEMPLATE
    assert 'id="turtleCanvas"' in TEMPLATE
    assert 'id="generatedTurtleCode"' in TEMPLATE
    assert 'id="patternResult"' in TEMPLATE
    assert 'id="togglePen"' not in TEMPLATE
    assert 'id="stepLength"' not in TEMPLATE
    assert 'id="turnAngle"' not in TEMPLATE
    assert 'id="drawingCharacter"' not in TEMPLATE
    assert "绘图角色" not in TEMPLATE
    assert 'id="controlResizeHandle"' in TEMPLATE
    assert 'id="codeResizeHandle"' in TEMPLATE
    assert 'id="collapseControlPanel"' in TEMPLATE
    assert 'id="openControlPanel"' in TEMPLATE
    assert 'id="toggleCodePanel"' in TEMPLATE
    assert 'id="studentSource"' in TEMPLATE
    assert 'id="studentLineNumbers"' in TEMPLATE
    assert 'id="stepExecution"' in TEMPLATE
    assert 'id="playExecution"' in TEMPLATE
    assert 'id="resetExecution"' in TEMPLATE
    assert 'id="playbackSpeed"' in TEMPLATE
    assert 'id="fullSpeedExecution"' in TEMPLATE
    assert 'id="variableList"' in TEMPLATE
    assert 'id="turtleStateList"' in TEMPLATE
    assert 'id="variableResizeHandle"' in TEMPLATE
    assert "path='turtle.css'" in TEMPLATE
    assert "path='turtle.js'" in TEMPLATE
    assert "?v={{ asset_version }}" in TEMPLATE


def test_turtle_uses_only_original_canvas_artwork():
    combined = f"{TEMPLATE}\n{SCRIPT}\n{STYLES}".lower()

    assert "<img" not in combined
    assert "raw.githubusercontent" not in combined
    assert "src=\"http" not in TEMPLATE.lower()
    assert "url(http" not in STYLES.lower()
    assert 'canvas.todataurl("image/png")' in SCRIPT.lower()
    assert "github.com/pythonturtle" not in combined
    assert "function drawarrow(" in SCRIPT.lower()
    assert "drawCatMarker" not in SCRIPT
    assert "drawTurtleMarker" not in SCRIPT
    assert "不需要先写代码" not in combined


def test_turtle_generator_matches_repeated_commands_and_controls_pen():
    assert "import turtle" in SCRIPT
    assert "function findRepeatedPattern" in SCRIPT
    assert "for _ in range(${pattern.repeats})" in SCRIPT
    assert "artist.penup()" in SCRIPT
    assert "artist.pendown()" in SCRIPT
    assert "def ${helper.name}(${helper.signature}):" in SCRIPT
    assert "def draw_scene(artist):" in SCRIPT
    assert "def main():" in SCRIPT
    assert 'if __name__ == "__main__":' in SCRIPT
    assert "function renderGeneratedCode" in SCRIPT
    assert "code-line__number" in SCRIPT
    assert "function setStepLength" in SCRIPT
    assert "function setTurnAngle" in SCRIPT
    assert "function setPenState" in SCRIPT
    assert "function renderExecutionStep" in SCRIPT
    assert "function renderVariables" in SCRIPT
    assert "function compileStudentSource" in SCRIPT
    assert "ArrowUp" in SCRIPT
    assert "ArrowDown" in SCRIPT
    assert "ArrowLeft" in SCRIPT
    assert "ArrowRight" in SCRIPT


def test_turtle_routes_and_assets_are_available():
    page = _request("GET", "/turtle/")
    redirect = _request("GET", "/turtle")

    assert page.status_code == 200
    assert "<title>Turtle</title>" in page.text
    assert redirect.status_code == 307
    assert redirect.headers["location"] == "/turtle/"
    assert (ROOT / "deeptracer" / "static" / "turtle.js").is_file()
    assert (ROOT / "deeptracer" / "static" / "turtle.css").is_file()
    assert ".turtle-workspace" in STYLES


def test_turtle_uses_flat_netbrick_neutral_layout():
    assert "#f7f8fa" in STYLES
    assert "#ffffff" in STYLES
    assert "#eef0f3" in STYLES
    assert "#3370ff" in STYLES
    assert ".turtle-panel" in STYLES
    assert "background:" in STYLES
    assert "background: #f7f8fa;" in STYLES
    assert "background: #101820;" in STYLES
    assert "border: 0;" in STYLES
    assert "box-shadow: none;" in STYLES
    assert "min-height: 64px;" in STYLES


def test_generated_code_is_below_canvas_and_panels_are_resizable():
    canvas_position = TEMPLATE.index('class="turtle-panel canvas-panel"')
    code_position = TEMPLATE.index('class="turtle-panel code-dock"')

    assert canvas_position < code_position
    assert "function initPanelResizing" in SCRIPT
    assert '"col-resize"' in SCRIPT
    assert '"row-resize"' in SCRIPT
    assert ".code-line__number" in STYLES
    assert ".code-dock-content" in STYLES


def test_left_and_bottom_panels_can_be_fully_collapsed():
    assert "is-control-collapsed" in STYLES
    assert "is-code-collapsed" in STYLES
    assert "function setControlCollapsed" in SCRIPT
    assert "function toggleCodePanel" in SCRIPT
    assert "function setVariableCollapsed" in SCRIPT


def test_keyboard_shortcuts_adjust_pen_angle_and_distance():
    assert 'event.key.toLowerCase() === "p"' in SCRIPT
    assert 'event.key.toLowerCase() === "u"' in SCRIPT
    assert 'event.key.toLowerCase() === "d"' in SCRIPT
    assert 'event.key === "[" || event.key === "]"' in SCRIPT
    assert 'event.key === "-" || event.key === "="' in SCRIPT
    assert "event.shiftKey" in SCRIPT
    assert 'event.key.toLowerCase() === "c"' in SCRIPT
    assert 'event.key.toLowerCase() === "s"' in SCRIPT
    assert "event.repeat" in SCRIPT
    assert 'event.key === "Escape"' in SCRIPT
    assert 'canvas.addEventListener("pointerdown"' in SCRIPT
    assert 'tabindex="0"' in TEMPLATE
    assert "function moveInDirection" in SCRIPT
    assert "face_move" in SCRIPT
    assert "ArrowDown: 270" in SCRIPT
    assert "setheading(${formatNumber(command.heading)})" in SCRIPT
    assert 'event.key.toLowerCase() === "q"' in SCRIPT
    assert "def draw_scene(artist, screen):" in (
        ROOT / "deeptracer" / "server" / "turtle_service.py"
    ).read_text(encoding="utf-8")


def test_turtle_page_has_dual_code_view_and_breakpoints_without_coordinate_axes():
    assert 'class="student-code-pane"' in TEMPLATE
    assert 'class="standard-code-pane"' in TEMPLATE
    assert "has-breakpoint" in STYLES
    assert "student-line-highlight" in STYLES
    assert "drawRulers" not in SCRIPT
    assert "canvasCoordinate" not in SCRIPT
    assert "网格与坐标轴" not in TEMPLATE
    assert "lineMap" in SCRIPT


def test_turtle_teaching_loop_has_tasks_hints_and_logic_feedback():
    assert 'id="checkTask"' in TEMPLATE
    assert 'id="taskFeedback"' in TEMPLATE
    assert 'id="conceptNarration"' in TEMPLATE
    assert 'id="narrationEnabled"' in TEMPLATE
    assert "evaluateActiveTask" in SCRIPT
    assert "renderTaskFeedback" in SCRIPT
    assert "renderNarration" in SCRIPT
    assert "logic" in SCRIPT
    assert "主要转向角度" in SCRIPT
    assert "图形终点回到起点" in SCRIPT
    assert "taskPassed" in SCRIPT


def test_turtle_page_tracks_numeric_length_heading_styles_and_canvas_options():
    assert 'id="currentLengthValue"' in TEMPLATE
    assert 'id="currentAngleValue"' in TEMPLATE
    assert 'id="currentHeadingValue"' in TEMPLATE
    assert 'id="penColorInput"' in TEMPLATE
    assert 'id="penSizeInput"' in TEMPLATE
    assert 'id="beginFill"' in TEMPLATE
    assert 'id="trailEnabled"' in TEMPLATE
    assert "setTurtleReadouts" in SCRIPT
    assert "headingLabel" in SCRIPT
    assert "fitSceneViewport" in SCRIPT
    assert "Math.max(0.00001" in SCRIPT
    assert "originY: height / 2 +" in SCRIPT
    assert "begin_fill" in SCRIPT
    assert "end_fill" in SCRIPT


def test_turtle_secondary_features_are_collapsible_and_use_line_separators():
    assert '<details class="side-section"' in TEMPLATE
    assert '<details class="command-strip"' in TEMPLATE
    assert '<details class="shortcut-more"' in TEMPLATE
    assert "border-bottom: 1px solid var(--line)" in STYLES
    assert "border: 1px solid var(--line-strong)" not in STYLES


def test_turtle_works_and_interaction_code_are_available():
    assert 'id="saveWork"' in TEMPLATE
    assert 'id="workList"' in TEMPLATE
    assert 'id="exportPng"' in TEMPLATE
    assert 'id="exportPython"' in TEMPLATE
    assert 'id="interactiveCodeToggle"' in TEMPLATE
    assert "localStorage" in SCRIPT
    assert "saveCurrentWork" in SCRIPT
    assert "loadSelectedWork" in SCRIPT
    assert "screen.onkeypress" in SCRIPT
    assert "screen.onscreenclick" in SCRIPT
    assert "toDataURL" in SCRIPT
