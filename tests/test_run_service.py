from __future__ import annotations

from deeptracer.server.run_service import execute_python_code


def test_run_service_returns_stdout_and_stderr():
    result = execute_python_code(
        "import sys\nprint('hello')\nprint('warning', file=sys.stderr)\n"
    )

    assert result["stdout"].strip() == "hello"
    assert result["stderr"].strip() == "warning"
    assert result["runtimeError"] is None
    assert result["exitCode"] == 0


def test_run_service_returns_runtime_error_and_traceback():
    result = execute_python_code("raise ValueError('broken')\n")

    assert result["runtimeError"] == "ValueError: broken"
    assert "Traceback" in result["traceback"]
    assert result["exitCode"] == 1


def test_run_service_terminates_infinite_loop(monkeypatch):
    monkeypatch.setenv("DEEPTRACER_RUN_TIMEOUT_SECONDS", "0.2")

    try:
        execute_python_code("while True:\n    pass\n")
    except TimeoutError as exc:
        assert "已终止执行" in str(exc)
    else:
        raise AssertionError("infinite loop should time out")
