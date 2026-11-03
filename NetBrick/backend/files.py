from __future__ import annotations

import shutil
import subprocess
from pathlib import Path, PurePath

from pydantic import BaseModel, Field


class SavePythonRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=180)
    source: str = Field(min_length=1, max_length=5_000_000)


class SavePythonResponse(BaseModel):
    status: str
    path: str | None = None
    message: str = ""


def save_python_with_native_dialog(request: SavePythonRequest) -> SavePythonResponse:
    filename = PurePath(request.filename).name
    if not filename.endswith(".py"):
        filename += ".py"
    default_dir = Path.home() / "Downloads"
    if not default_dir.is_dir():
        default_dir = Path.home()
    suggested = default_dir / filename
    zenity = shutil.which("zenity")
    if zenity is None:
        return SavePythonResponse(
            status="unavailable",
            message="系统未安装 zenity，无法打开原生保存对话框",
        )
    try:
        result = subprocess.run(
            [
                zenity,
                "--file-selection",
                "--save",
                "--confirm-overwrite",
                "--title=保存 NetBrick Python 文件",
                "--file-filter=Python files | *.py",
                f"--filename={suggested}",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return SavePythonResponse(
            status="unavailable",
            message=f"无法打开系统保存对话框：{exc}",
        )
    if result.returncode == 1:
        return SavePythonResponse(status="cancelled", message="已取消保存")
    if result.returncode != 0:
        return SavePythonResponse(
            status="unavailable",
            message=result.stderr.strip() or "系统保存对话框启动失败",
        )
    selected = result.stdout.strip()
    if not selected:
        return SavePythonResponse(status="cancelled", message="未选择保存路径")
    target = Path(selected)
    if target.suffix.lower() != ".py":
        target = target.with_suffix(".py")
    if not target.parent.is_dir():
        return SavePythonResponse(
            status="error",
            message="所选目录不存在",
        )
    try:
        target.write_text(request.source, encoding="utf-8")
    except OSError as exc:
        return SavePythonResponse(
            status="error",
            message=f"文件写入失败：{exc}",
        )
    return SavePythonResponse(
        status="saved",
        path=str(target),
        message="文件已保存",
    )
