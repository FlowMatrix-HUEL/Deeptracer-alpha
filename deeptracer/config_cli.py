from __future__ import annotations

import argparse
import getpass
from pathlib import Path
from urllib.parse import urlparse

from deeptracer.workflow.env_utils import build_env_local


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="deeptracer",
        description="配置 DeepTracer 的 OpenAI 兼容模型。",
    )
    parser.add_argument("--api-key", help="OpenAI 或兼容网关的 API Key")
    parser.add_argument("--base-url", help="OpenAI 兼容接口地址，例如 https://example.com/v1")
    parser.add_argument("--model", help="模型名称")
    parser.add_argument("--temperature", help="生成温度，默认 0.2")
    parser.add_argument(
        "--provider",
        help="模型提供方，目前仅支持 openai",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="显示当前配置，API Key 会脱敏",
    )
    agent_group = parser.add_mutually_exclusive_group()
    agent_group.add_argument(
        "--disable-agents",
        action="store_true",
        help="关闭全部 Agent，只运行本地分析",
    )
    agent_group.add_argument(
        "--enable-agents",
        action="store_true",
        help="重新启用 Agent",
    )
    return parser


def configure(argv: list[str] | None = None, builder: build_env_local | None = None) -> Path:
    parser = build_parser()
    args = parser.parse_args(argv)
    builder = builder or build_env_local()
    entries = builder._read_entries()

    if args.show:
        _show_config(builder, entries)
        return builder.get_config_path()

    if args.disable_agents or args.enable_agents:
        enabled = bool(args.enable_agents)
        config_path = builder.set_agents_enabled(enabled)
        print(f"配置已写入：{config_path}")
        print(f"Agent：{'已启用' if enabled else '已关闭（仅本地分析）'}")
        print("请在 deeptracer 菜单中重新启动 Web 使设置生效。")
        return config_path

    interactive = not any(
        [
            args.api_key,
            args.base_url is not None,
            args.model,
            args.temperature,
            args.provider,
        ]
    )
    api_key = args.api_key
    base_url = args.base_url
    model_name = args.model
    temperature = args.temperature
    provider = args.provider

    if interactive:
        print(f"配置文件：{builder.get_config_path()}")
        print("直接回车可保留当前值。\n")
        api_key = _prompt("API Key", entries.get("OPENAI_API_KEY", ""), secret=True)
        base_url = _prompt("Base URL（官方接口可留空）", entries.get("OPENAI_BASE_URL", ""))
        model_name = _prompt(
            "模型名称",
            entries.get("DEEPTRACER_MODEL_NAME")
            or entries.get("OPENAI_MODEL")
            or "gpt-4.1-mini",
        )
        temperature = _prompt(
            "Temperature",
            entries.get("DEEPTRACER_MODEL_TEMPERATURE", "0.2"),
        )
        provider = _prompt(
            "Provider",
            entries.get("DEEPTRACER_MODEL_PROVIDER", "openai"),
        )

    api_key = api_key or entries.get("OPENAI_API_KEY", "")
    if not api_key:
        parser.error("必须提供 --api-key，或从 deeptracer 主菜单配置模型")

    model_name = (
        model_name
        or entries.get("DEEPTRACER_MODEL_NAME")
        or entries.get("OPENAI_MODEL")
        or "gpt-4.1-mini"
    )
    temperature = (
        temperature
        or entries.get("DEEPTRACER_MODEL_TEMPERATURE")
        or "0.2"
    )
    provider = (
        provider
        or entries.get("DEEPTRACER_MODEL_PROVIDER")
        or "openai"
    ).strip().lower()

    if provider != "openai":
        parser.error("当前仅支持 DEEPTRACER_MODEL_PROVIDER=openai")
    if base_url:
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            parser.error("Base URL 必须是有效的 http:// 或 https:// 地址")
    try:
        numeric_temperature = float(temperature)
    except ValueError:
        parser.error("Temperature 必须是数字")
    if not 0 <= numeric_temperature <= 2:
        parser.error("Temperature 必须在 0 到 2 之间")

    config_path = builder.save_model_config(
        api_key=api_key,
        base_url=base_url if base_url is not None else entries.get("OPENAI_BASE_URL", ""),
        model_name=model_name,
        provider=provider,
        temperature=str(numeric_temperature),
    )
    print(f"\n配置已写入：{config_path}")
    print(f"模型：{model_name}")
    print("如果 Web 正在运行，请返回 deeptracer 菜单并重新启动服务。")
    return config_path


def _prompt(label: str, current: str = "", *, secret: bool = False) -> str:
    if secret:
        suffix = " [已配置，回车保留]" if current else " [必填]"
    else:
        suffix = f" [{current}]" if current else ""
    prompt = f"{label}{suffix}: "
    value = getpass.getpass(prompt) if secret else input(prompt)
    return value.strip() or current


def _show_config(builder: build_env_local, entries: dict[str, str]) -> None:
    print(f"配置文件：{builder.get_config_path()}")
    if not entries:
        print("状态：尚未配置")
        return
    print(f"API Key：{_mask_secret(entries.get('OPENAI_API_KEY', ''))}")
    print(f"Base URL：{entries.get('OPENAI_BASE_URL') or 'OpenAI 官方接口'}")
    print(
        "模型："
        + (
            entries.get("DEEPTRACER_MODEL_NAME")
            or entries.get("OPENAI_MODEL")
            or "gpt-4.1-mini"
        )
    )
    print(f"Provider：{entries.get('DEEPTRACER_MODEL_PROVIDER', 'openai')}")
    print(f"Temperature：{entries.get('DEEPTRACER_MODEL_TEMPERATURE', '0.2')}")
    agents_enabled = entries.get("DEEPTRACER_AGENTS_ENABLED", "true").lower()
    print(
        "Agent："
        + ("已启用" if agents_enabled not in {"0", "false", "no", "off", "disabled"} else "已关闭（仅本地分析）")
    )


def _mask_secret(value: str) -> str:
    if not value:
        return "未配置"
    if len(value) <= 8:
        return "********"
    return f"{value[:4]}...{value[-4:]}"


def main() -> None:
    configure()


if __name__ == "__main__":
    main()
