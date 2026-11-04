from __future__ import annotations

import os
import shutil
import sys
import time
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urlparse

from deeptracer.clip import _check_path, _print_report
from deeptracer.server.analysis_service import analyze_python_file
from deeptracer.workflow.env_utils import build_env_local

try:
    from rich.console import Console, Group
    from rich.prompt import Prompt
    from rich.table import Table
    from rich.text import Text

    HAVE_RICH = True
except ImportError:
    HAVE_RICH = False


WEB_URL = "http://127.0.0.1:8000"
LOGO = r"""
 ____                  _____
|  _ \  ___  ___ _ __ |_   _| __ __ _  ___ ___ _ __
| | | |/ _ \/ _ \ '_ \  | | '__/ _` |/ __/ _ \ '__|
| |_| |  __/  __/ |_) | | | | | (_| | (_|  __/ |
|____/ \___|\___| .__/  |_|_|  \__,_|\___\___|_|
                |_|
""".strip("\n")
LOGO_WIDTH = max(len(line) for line in LOGO.splitlines())


@dataclass(frozen=True)
class MenuItem:
    number: str
    group: str
    label: str
    action: str
    description: str = ""


class MenuModel:
    def __init__(self, items: list[MenuItem] | None = None) -> None:
        self.items = items or MENU_ITEMS
        self.index = self.option_indexes()[0]

    def option_indexes(self) -> list[int]:
        return [index for index, item in enumerate(self.items) if item.action]

    def move(self, delta: int) -> None:
        indexes = self.option_indexes()
        current = indexes.index(self.index) if self.index in indexes else 0
        self.index = indexes[(current + delta) % len(indexes)]

    def selected(self) -> MenuItem:
        return self.items[self.index]


@dataclass(frozen=True)
class MenuLayout:
    safe_height: int
    show_full_logo: bool = False
    show_compact_logo: bool = False
    show_group_headings: bool = False
    show_status: bool = False
    show_help: bool = False
    too_small: bool = False


def calculate_menu_layout(width: int, height: int) -> MenuLayout:
    """Choose a layout that never uses the terminal's last physical row."""
    safe_height = max(1, height - 1)
    full_logo_fits = width >= LOGO_WIDTH + 2
    return MenuLayout(
        safe_height=safe_height,
        show_full_logo=full_logo_fits and safe_height >= 22,
        show_compact_logo=(
            not (full_logo_fits and safe_height >= 22)
            and safe_height >= 10
        ),
        show_group_headings=safe_height >= 17,
        show_status=safe_height >= 12,
        show_help=safe_height >= 11,
        too_small=safe_height < 9,
    )


MENU_ITEMS = [
    MenuItem("1", "工作台", "启动 DeepTracer Web", "web", "同时提供 NetBrick、分析工作台和 API 文档"),
    MenuItem("2", "配置", "配置模型", "configure_model", "API Key、Base URL、模型和温度"),
    MenuItem("3", "配置", "启用 Agent", "enable_agents"),
    MenuItem("4", "配置", "关闭 Agent", "disable_agents", "仅使用本地分析，不发送模型请求"),
    MenuItem("5", "配置", "查看当前配置", "show_config"),
    MenuItem("6", "工具", "快速分析 Python 文件", "analyze"),
    MenuItem("7", "工具", "打开 API 文档", "api_docs"),
    MenuItem("8", "帮助", "关于 DeepTracer", "about"),
    MenuItem("0", "退出", "退出菜单", "exit"),
]


class DeepTracerTUI:
    def __init__(self) -> None:
        self.console = Console() if HAVE_RICH else None
        self.config = build_env_local()
        self._actions: dict[str, Callable[[], None]] = {
            "web": self.open_web,
            "configure_model": self.configure_model,
            "enable_agents": lambda: self.set_agents(True),
            "disable_agents": lambda: self.set_agents(False),
            "show_config": self.show_config,
            "analyze": self.analyze_file,
            "api_docs": self.open_api_docs,
            "about": self.about,
            "exit": lambda: None,
        }

    def menu_items(self) -> list[MenuItem]:
        return MENU_ITEMS

    def choice_map(self) -> dict[str, MenuItem]:
        return {item.number: item for item in MENU_ITEMS}

    def status_line(self) -> str:
        entries = self.config._read_entries()
        agent_value = entries.get("DEEPTRACER_AGENTS_ENABLED", "true").lower()
        agents = "关闭" if agent_value in {"0", "false", "no", "off", "disabled"} else "启用"
        model = (
            entries.get("DEEPTRACER_MODEL_NAME")
            or entries.get("OPENAI_MODEL")
            or "未配置"
        )
        return f"Web: {WEB_URL} | Agent: {agents} | 模型: {model}"

    def render(self) -> None:
        if self.console is not None:
            self.console.print(self._rich_menu(MenuModel()))
            self.console.print(
                Text("输入编号并回车 · 0 退出", style="dim"),
                justify="center",
            )
        else:
            print(self._ansi_menu(MenuModel()))

    def _rich_menu(self, model: MenuModel):
        width, height = self.console.size
        layout = calculate_menu_layout(width, height)

        if layout.too_small:
            return Text(
                "终端窗口过小，请放大窗口。按 Q 退出。",
                style="bold blue",
                no_wrap=True,
                overflow="ellipsis",
            )

        renderables = []
        if layout.show_full_logo:
            logo_indent = max(0, (width - LOGO_WIDTH) // 2)
            centered_logo = "\n".join(
                f"{' ' * logo_indent}{line}" for line in LOGO.splitlines()
            )
            renderables.append(
                Text(centered_logo, style="bold blue", no_wrap=True)
            )
        elif layout.show_compact_logo:
            compact_indent = max(0, (width - len("DeepTracer")) // 2)
            renderables.append(
                Text(f"{' ' * compact_indent}DeepTracer", style="bold blue", no_wrap=True)
            )

        if layout.show_status:
            renderables.append(
                Text(
                    self.status_line(),
                    style="dim",
                    no_wrap=True,
                    overflow="ellipsis",
                )
            )

        current_group = None
        grouped: list[tuple[str, list[MenuItem]]] = []
        for item in MENU_ITEMS:
            if item.group != current_group:
                current_group = item.group
                grouped.append((current_group, []))
            grouped[-1][1].append(item)

        for group, items in grouped:
            if layout.show_group_headings:
                renderables.append(Text(group, style="bold blue"))

            for item in items:
                selected = MENU_ITEMS.index(item) == model.index
                marker = ">" if selected else " "
                row_style = "bold white on blue" if selected else ""
                marker_style = "bold cyan" if selected else "bold blue"
                number_style = "bold white" if selected else "dim"
                label_style = "bold white" if selected else "bold"
                row = Text(style=row_style, no_wrap=True, overflow="ellipsis")
                row.append(f" {marker}  ", style=marker_style)
                row.append(f"{item.number:>2}   ", style=number_style)
                row.append(item.label, style=label_style)
                renderables.append(row)

        if layout.show_help:
            help_text = (
                "Up/Down 选择    Enter 执行    Esc/Q 退出"
                if width >= 44
                else "Up/Down  Enter  Q"
            )
            renderables.append(
                Text(help_text, style="dim", no_wrap=True, overflow="ellipsis")
            )
        return Group(*renderables)

    def _ansi_menu(self, model: MenuModel) -> str:
        blue = "\033[34m"
        reset = "\033[0m"
        dim = "\033[90m"
        selected = "\033[1;37;44m"
        width, height = shutil.get_terminal_size(fallback=(80, 24))
        layout = calculate_menu_layout(width, height)
        if layout.too_small:
            return f"{blue}终端窗口过小，请放大窗口。按 Q 退出。{reset}"

        lines = []
        if layout.show_full_logo:
            logo_indent = max(0, (width - LOGO_WIDTH) // 2)
            centered_logo = "\n".join(
                f"{' ' * logo_indent}{line}" for line in LOGO.splitlines()
            )
            lines.append(f"{blue}{centered_logo}{reset}")
        elif layout.show_compact_logo:
            compact_indent = max(0, (width - len("DeepTracer")) // 2)
            lines.append(f"{blue}{' ' * compact_indent}DeepTracer{reset}")
        if layout.show_status:
            lines.append(f"{dim}{self.status_line()}{reset}")
        current_group = None
        for index, item in enumerate(MENU_ITEMS):
            if layout.show_group_headings and item.group != current_group:
                current_group = item.group
                lines.append(f"{blue}{current_group}{reset}")
            row_style = selected if index == model.index else ""
            row_reset = reset if row_style else ""
            marker = ">" if index == model.index else " "
            lines.append(
                f"{row_style} {marker}  {item.number}   {item.label}{row_reset}"
            )
        if layout.show_help:
            help_text = (
                "Up/Down 选择    Enter 执行    Esc/Q 退出"
                if width >= 44
                else "Up/Down  Enter  Q"
            )
            lines.append(f"{dim}{help_text}{reset}")
        return "\n".join(lines)

    def ask_choice(self) -> str:
        choices = list(self.choice_map())
        if self.console is not None:
            return Prompt.ask("请选择", choices=choices, default="1")
        while True:
            value = input("请选择: ").strip()
            if value in choices:
                return value
            print("无效选项，请输入菜单编号。")

    @staticmethod
    def _read_key(timeout: float | None = None) -> str:
        if os.name == "nt":
            import msvcrt

            deadline = time.monotonic() + timeout if timeout is not None else None
            while not msvcrt.kbhit():
                if deadline is not None and time.monotonic() >= deadline:
                    return ""
                time.sleep(0.02)
            char = msvcrt.getwch()
            if char in ("\x00", "\xe0"):
                code = msvcrt.getwch()
                return {
                    "H": "up",
                    "P": "down",
                    "K": "left",
                    "M": "right",
                }.get(code, "")
            return {
                "\r": "enter",
                "\x1b": "exit",
                "q": "exit",
                "Q": "exit",
                "\x03": "exit",
            }.get(char, "")

        import select
        import termios
        import tty

        fd = sys.stdin.fileno()
        previous = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            if timeout is not None and not select.select([fd], [], [], timeout)[0]:
                return ""
            char = os.read(fd, 1)
            if char == b"\x1b":
                sequence = b""
                while select.select([fd], [], [], 0.02)[0]:
                    sequence += os.read(fd, 1)
                if sequence in (b"[A", b"OA", b"k"):
                    return "up"
                if sequence in (b"[B", b"OB", b"j"):
                    return "down"
                if sequence in (b"[H", b"OH", b"g"):
                    return "home"
                if sequence in (b"[F", b"OF", b"G"):
                    return "end"
                return "exit"
            if char in (b"\r", b"\n"):
                return "enter"
            if char in (b"q", b"Q", b"\x03"):
                return "exit"
            if char in (b"k", b"j", b"g", b"G"):
                return {b"k": "up", b"j": "down", b"g": "home", b"G": "end"}[char]
            return ""
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, previous)

    def navigate_interactive(self) -> MenuItem:
        model = MenuModel()
        if self.console is not None and not self.console.is_dumb_terminal:
            from rich.live import Live

            with Live(
                self._rich_menu(model),
                console=self.console,
                screen=False,
                transient=True,
                auto_refresh=False,
                get_renderable=lambda: self._rich_menu(model),
            ) as live:
                last_size = self.console.size
                while True:
                    key = self._read_key(timeout=0.2)
                    current_size = self.console.size
                    changed = current_size != last_size
                    last_size = current_size
                    if key == "up":
                        model.move(-1)
                        changed = True
                    elif key == "down":
                        model.move(1)
                        changed = True
                    elif key == "home":
                        model.index = model.option_indexes()[0]
                        changed = True
                    elif key == "end":
                        model.index = model.option_indexes()[-1]
                        changed = True
                    elif key == "enter":
                        return model.selected()
                    elif key == "exit":
                        return next(item for item in MENU_ITEMS if item.action == "exit")
                    if changed:
                        live.refresh()
        last_size = None
        while True:
            current_size = shutil.get_terminal_size(fallback=(80, 24))
            if current_size != last_size:
                sys.stdout.write("\x1b[2J\x1b[H")
                print(self._ansi_menu(model))
                sys.stdout.flush()
                last_size = current_size

            key = self._read_key(timeout=0.2)
            changed = False
            if key == "up":
                model.move(-1)
                changed = True
            elif key == "down":
                model.move(1)
                changed = True
            elif key == "home":
                model.index = model.option_indexes()[0]
                changed = True
            elif key == "end":
                model.index = model.option_indexes()[-1]
                changed = True
            elif key == "enter":
                return model.selected()
            elif key == "exit":
                return next(item for item in MENU_ITEMS if item.action == "exit")
            if changed:
                sys.stdout.write("\x1b[2J\x1b[H")
                print(self._ansi_menu(model))
                sys.stdout.flush()

    def pause(self) -> None:
        if self.console is not None:
            self.console.print()
            Prompt.ask("按 Enter 返回菜单", default="")
        else:
            try:
                input("按 Enter 返回菜单…")
            except (EOFError, KeyboardInterrupt):
                pass

    def run(self) -> None:
        while True:
            rich_interactive = (
                self.console is not None and not self.console.is_dumb_terminal
            )
            if sys.stdin.isatty() and sys.stdout.isatty() and (
                rich_interactive or not HAVE_RICH
            ):
                item = self.navigate_interactive()
            else:
                self.render()
                item = self.choice_map()[self.ask_choice()]
            if item.action == "exit":
                self.notice("已退出 DeepTracer。")
                return
            try:
                self._actions[item.action]()
            except KeyboardInterrupt:
                self.notice("操作已停止。")
            except Exception as exc:
                self.notice(f"操作失败：{type(exc).__name__}: {exc}", error=True)
            self.pause()

    def notice(self, message: str, *, error: bool = False) -> None:
        style = "red" if error else "blue"
        if self.console is not None:
            self.console.print(Text(message, style=style))
        else:
            color = "\033[31m" if error else "\033[34m"
            print(f"{color}{message}\033[0m")

    def open_web(self) -> None:
        from deeptracer.server.app import main as serve_web

        self.notice(
            "正在启动 Web 服务。\n"
            f"请在浏览器中手动打开：{WEB_URL}/\n"
            f"NetBrick：{WEB_URL}/netbrick/  |  API 文档：{WEB_URL}/api-docs\n"
            "按 Ctrl+C 可停止服务并返回菜单。"
        )
        serve_web()

    def configure_model(self) -> None:
        entries = self.config._read_entries()
        api_key = self._ask("API Key（回车保留）", secret=True)
        if not api_key:
            api_key = entries.get("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError("API Key 不能为空")

        base_url = self._ask(
            "Base URL（官方接口可留空）",
            default=entries.get("OPENAI_BASE_URL", ""),
            allow_empty=True,
        )
        if base_url:
            parsed = urlparse(base_url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("Base URL 必须是有效的 http:// 或 https:// 地址")

        model = self._ask(
            "模型名称",
            default=(
                entries.get("DEEPTRACER_MODEL_NAME")
                or entries.get("OPENAI_MODEL")
                or "gpt-4.1-mini"
            ),
        )
        temperature_text = self._ask(
            "Temperature",
            default=entries.get("DEEPTRACER_MODEL_TEMPERATURE", "0.2"),
        )
        temperature = float(temperature_text)
        if not 0 <= temperature <= 2:
            raise ValueError("Temperature 必须在 0 到 2 之间")

        path = self.config.save_model_config(
            api_key=api_key,
            base_url=base_url,
            model_name=model,
            provider="openai",
            temperature=str(temperature),
        )
        self.notice(f"模型配置已保存：{path}")

    def set_agents(self, enabled: bool) -> None:
        if not self._confirm(f"确定{'启用' if enabled else '关闭'} Agent 吗"):
            return
        path = self.config.set_agents_enabled(enabled)
        self.notice(f"Agent 已{'启用' if enabled else '关闭'}：{path}")

    def show_config(self) -> None:
        entries = self.config._read_entries()
        if self.console is None:
            print(f"配置文件：{self.config.get_config_path()}")
            for key in (
                "OPENAI_BASE_URL",
                "DEEPTRACER_MODEL_NAME",
                "DEEPTRACER_MODEL_PROVIDER",
                "DEEPTRACER_MODEL_TEMPERATURE",
                "DEEPTRACER_AGENTS_ENABLED",
            ):
                print(f"{key}={entries.get(key, '')}")
            print(f"OPENAI_API_KEY={self._mask(entries.get('OPENAI_API_KEY', ''))}")
            return

        table = Table.grid(padding=(0, 2))
        table.add_column("配置项", style="blue")
        table.add_column("值")
        rows = {
            "配置文件": str(self.config.get_config_path()),
            "API Key": self._mask(entries.get("OPENAI_API_KEY", "")),
            "Base URL": entries.get("OPENAI_BASE_URL") or "OpenAI 官方接口",
            "模型": entries.get("DEEPTRACER_MODEL_NAME")
            or entries.get("OPENAI_MODEL")
            or "未配置",
            "Provider": entries.get("DEEPTRACER_MODEL_PROVIDER", "openai"),
            "Temperature": entries.get("DEEPTRACER_MODEL_TEMPERATURE", "0.2"),
            "Agent": entries.get("DEEPTRACER_AGENTS_ENABLED", "true"),
        }
        for key, value in rows.items():
            table.add_row(key, value)
        self.console.print(Text("当前配置", style="bold blue"))
        self.console.print(table)

    def analyze_file(self) -> None:
        path_text = self._ask("Python 文件路径")
        resolved = _check_path(path_text)
        report = analyze_python_file(resolved)
        _print_report(report, resolved, False)

    def open_api_docs(self) -> None:
        url = f"{WEB_URL}/api-docs"
        self.notice(
            "API 文档需要 Web 服务。请先选择“启动 DeepTracer Web”，"
            f"再在浏览器中手动打开：\n{url}"
        )

    def about(self) -> None:
        self.notice(
            "DeepTracer\n"
            "Python 分析、Tracer、运行终端、NetBrick 与 API 文档。\n"
            f"配置文件：{self.config.get_config_path()}"
        )

    def _ask(
        self,
        label: str,
        *,
        default: str = "",
        secret: bool = False,
        allow_empty: bool = False,
    ) -> str:
        if self.console is not None:
            value = Prompt.ask(label, default=default, password=secret).strip()
        else:
            prompt = f"{label}" + (f" [{default}]" if default and not secret else "") + ": "
            value = input(prompt).strip() or default
        if not value and not allow_empty and not secret:
            raise ValueError(f"{label} 不能为空")
        return value

    def _confirm(self, label: str) -> bool:
        if self.console is not None:
            return Prompt.ask(label, choices=["y", "n"], default="n") == "y"
        return input(f"{label} [y/N] ").strip().lower() in {"y", "yes"}

    @staticmethod
    def _mask(value: str) -> str:
        if not value:
            return "未配置"
        if len(value) <= 8:
            return "********"
        return f"{value[:4]}...{value[-4:]}"


def main() -> None:
    DeepTracerTUI().run()


if __name__ == "__main__":
    main()
