from __future__ import annotations

import argparse
import sys
from pathlib import Path

from deeptracer.server.analysis_service import analyze_python_file
from deeptracer.workflow.env_utils import build_env_local


def _check_path(path: str, allowed_suffixes: tuple[str, ...] = (".py",)) -> str:
    """Validate the CLI target path before passing it to the analysis service."""
    target = Path(path).resolve()
    if not target.exists():
        raise FileNotFoundError(f"python file not found: {path}")
    if target.suffix.lower() not in allowed_suffixes:
        raise ValueError(f"Invalid file type (only .py files are supported) {path}")
    return str(target)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="DeepTracer",
        description="Deeptracer command-line analysis entrypoint.",
        epilog="Version 1.0.0",
    )
    parser.add_argument("-k", "--key", help="Deployment configuration key")
    parser.add_argument("pypath", nargs="?", help="Target Python file path")
    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        dest="full_ast",
        help="Compatibility flag retained for the historical CLI surface.",
    )
    return parser


def _print_report(report: dict, path_text: str, full_ast: bool) -> None:
    hero_metrics = {item["label"]: item["value"] for item in report.get("heroMetrics", [])}
    suggestions = report.get("suggestions", [])
    print(f"Analysis target: {hero_metrics.get('分析对象', Path(path_text).name)}")
    print(f"Code lines: {hero_metrics.get('代码行数', '未知')}")
    print(f"Key function: {hero_metrics.get('重点函数', '未知')}")
    print(f"Duration: {hero_metrics.get('执行耗时', '未知')}")

    runtime_error = report.get("meta", {}).get("runtimeError")
    if runtime_error:
        print(f"Runtime error: {runtime_error}")

    if suggestions:
        print("Top suggestions:")
        for item in suggestions[:3]:
            print(f"- {item.get('title', 'Untitled suggestion')}")

    if full_ast:
        print("Compatibility note: --all is retained, and the current analysis already includes AST output.")


def main() -> None:
    """
    Keep the historical `deeptracer` console script alive by routing it to the
    current analysis service instead of the removed legacy analyzers.
    """
    parser = _build_parser()
    args = parser.parse_args()

    try:
        if args.key:
            if args.pypath:
                parser.error("the following arguments are required: pypath (unless --key/-k is provided)")
            builder = build_env_local()
            builder.creator(args.key)
            return

        if not args.pypath:
            parser.error("the following arguments are required: pypath (since --key/-k is not provided)")

        path_text = _check_path(args.pypath)
        report = analyze_python_file(path_text)
        _print_report(report, path_text, args.full_ast)
    except FileNotFoundError as exc:
        parser.error(f"File error: {exc}")
        sys.exit(1)
    except ValueError as exc:
        parser.error(f"Parameter error: {exc}")
        sys.exit(1)
    except Exception as exc:
        parser.error(f"Conversion failed: {exc} (Please check file paths and dependencies)")
        sys.exit(1)
