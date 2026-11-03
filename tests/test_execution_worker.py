from __future__ import annotations

import os

from deeptracer.server.analysis_service import analyze_python_input


def test_user_code_runs_in_an_isolated_process():
    payload = analyze_python_input(
        source_code="import os\nprint(os.getpid())\n",
        display_name="pid.py",
    )

    child_pid = int(payload["meta"]["stdout"].strip())
    assert child_pid != os.getpid()
    assert payload["meta"]["runtimeError"] is None
    assert payload["meta"]["pyinstrumentSamples"] > 0
    assert "pyinstrument" in payload["visualizations"]["performance"].lower()


def test_infinite_loop_is_terminated_by_execution_timeout(monkeypatch):
    monkeypatch.setenv("DEEPTRACER_EXECUTION_TIMEOUT_SECONDS", "0.2")

    payload = analyze_python_input(
        source_code="while True:\n    pass\n",
        display_name="loop.py",
    )

    assert "执行超时" in payload["meta"]["runtimeError"]
