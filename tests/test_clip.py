from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest


@logtitle
def test_clip_import():
    """测试能否正常导入 clip 文件"""
    from deeptracer import clip

    assert clip is not None


@logtitle
def test_clip_structure():
    """测试 clip 的基本结构"""
    file_path = Path("deeptracer") / "clip.py"
    assert file_path.exists(), f"clip 文件不存在: {file_path}"


def _make_temp_python_file(source: str) -> str:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".py", delete=False) as handle:
        handle.write(source)
        return handle.name


@logtitle
def test_clip_function_prints_current_analysis_summary(capsys, monkeypatch):
    from deeptracer.clip import main

    sample_file = _make_temp_python_file(
        "def add(a, b):\n"
        "    return a + b\n\n"
        "print(add(1, 2))\n"
    )

    try:
        monkeypatch.setattr(sys, "argv", ["DeepTracer", sample_file])
        main()

        captured = capsys.readouterr()
        assert "Analysis target:" in captured.out
        assert "Code lines:" in captured.out
        assert "Key function:" in captured.out
        assert "Duration:" in captured.out
    finally:
        Path(sample_file).unlink(missing_ok=True)


@logtitle
def test_clip_all_flag_is_kept_as_compatibility_notice(capsys, monkeypatch):
    from deeptracer.clip import main

    sample_file = _make_temp_python_file("print('hello')\n")

    try:
        monkeypatch.setattr(sys, "argv", ["DeepTracer", sample_file, "--all"])
        main()

        captured = capsys.readouterr()
        assert "Compatibility note:" in captured.out
    finally:
        Path(sample_file).unlink(missing_ok=True)


@logtitle
def test_clip_rejects_non_python_input(monkeypatch):
    from deeptracer.clip import main

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as handle:
        handle.write("hello\n")
        sample_file = handle.name

    try:
        monkeypatch.setattr(sys, "argv", ["DeepTracer", sample_file])
        with pytest.raises(SystemExit):
            main()
    finally:
        Path(sample_file).unlink(missing_ok=True)
