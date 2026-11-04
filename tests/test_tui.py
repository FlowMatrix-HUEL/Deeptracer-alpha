from __future__ import annotations

import io
import re
from pathlib import Path

from rich.console import Console

from deeptracer.tui import (
    LOGO,
    LOGO_WIDTH,
    DeepTracerTUI,
    MENU_ITEMS,
    MenuModel,
    calculate_menu_layout,
)


ROOT = Path(__file__).resolve().parents[1]


def test_only_deeptracer_console_command_is_registered():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    scripts_section = pyproject.split("[project.scripts]", 1)[1].split("\n[", 1)[0]
    commands = re.findall(r"^([A-Za-z0-9_-]+)\s*=", scripts_section, flags=re.MULTILINE)

    assert commands == ["deeptracer"]
    assert "deeptracer = \"deeptracer.tui:main\"" in scripts_section
    setup_text = (ROOT / "setup.py").read_text(encoding="utf-8")
    assert '"deeptracer-config=' not in setup_text
    assert '"deeptracer-web=' not in setup_text


def test_rich_menu_contains_web_configuration_and_tools():
    actions = {item.action for item in MENU_ITEMS}

    assert "web" in actions
    assert "configure_model" in actions
    assert "enable_agents" in actions
    assert "disable_agents" in actions
    assert "show_config" in actions
    assert "analyze" in actions
    assert "api_docs" in actions


def test_tui_choice_map_exposes_numeric_menu_shortcuts():
    menu = DeepTracerTUI()

    choices = menu.choice_map()

    assert choices["1"].action == "web"
    assert choices["2"].action == "configure_model"
    assert choices["0"].action == "exit"


def test_arrow_navigation_moves_between_menu_actions():
    model = MenuModel()

    assert model.selected().action == "web"
    model.move(1)
    assert model.selected().action == "configure_model"
    model.move(-1)
    assert model.selected().action == "web"


def test_tui_has_ascii_logo():
    assert "____" in LOGO
    assert "|____/" in LOGO
    assert LOGO_WIDTH >= 50


def test_tui_never_opens_a_browser_automatically():
    source = (ROOT / "deeptracer" / "tui.py").read_text(encoding="utf-8")

    assert "webbrowser" not in source
    assert "threading.Timer" not in source
    assert "请在浏览器中手动打开" in source


def _render_rich_menu(width: int, height: int) -> str:
    output = io.StringIO()
    menu = DeepTracerTUI()
    menu.console = Console(
        file=output,
        force_terminal=True,
        color_system=None,
        width=width,
        height=height,
    )
    menu.console.print(menu._rich_menu(MenuModel()))
    return output.getvalue()


def test_rich_menu_has_no_horizontal_separator_lines():
    rendered = _render_rich_menu(width=120, height=35)

    assert "─" not in rendered
    assert "╭" not in rendered
    assert "╰" not in rendered
    assert "│" not in rendered
    assert "›" not in rendered
    assert "↑" not in rendered
    assert "↓" not in rendered
    assert "·" not in rendered


def test_rich_menu_uses_compact_layout_after_resize():
    full = _render_rich_menu(width=120, height=35)
    standard = _render_rich_menu(width=80, height=24)
    compact = _render_rich_menu(width=44, height=18)

    assert LOGO.splitlines()[1] in full
    assert LOGO.splitlines()[1] in standard
    assert LOGO.splitlines()[1] not in compact
    assert "DeepTracer" in compact
    for item in MENU_ITEMS:
        assert item.label in compact


def test_rich_menu_never_uses_the_last_terminal_row():
    for width, height in ((120, 35), (80, 24), (60, 18), (44, 14), (36, 10)):
        rendered = _render_rich_menu(width=width, height=height)
        assert len(rendered.splitlines()) <= max(1, height - 1)


def test_tiny_terminal_shows_resize_instruction_instead_of_clipped_menu():
    layout = calculate_menu_layout(width=36, height=8)
    rendered = _render_rich_menu(width=36, height=8)

    assert layout.too_small is True
    assert "请放大窗口" in rendered
    for item in MENU_ITEMS:
        assert item.label not in rendered


def test_interactive_menu_does_not_refresh_while_idle():
    source = (ROOT / "deeptracer" / "tui.py").read_text(encoding="utf-8")

    assert "auto_refresh=False" in source
    assert "refresh_per_second" not in source


def test_notice_uses_plain_text_without_a_border():
    output = io.StringIO()
    menu = DeepTracerTUI()
    menu.console = Console(
        file=output,
        force_terminal=True,
        color_system=None,
        width=80,
        height=24,
    )

    menu.notice("测试提示")
    rendered = output.getvalue()

    assert "测试提示" in rendered
    assert "╭" not in rendered
    assert "╰" not in rendered
