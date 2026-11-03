from __future__ import annotations

import base64
import binascii
import hashlib
import io
import json
import zipfile
from pathlib import PurePosixPath

from .models import (
    CourseImportRequest,
    CoursePack,
    CourseValidateResponse,
    Diagnostic,
    IRDocument,
)


MAX_PACKAGE_BYTES = 20 * 1024 * 1024
PACKAGE_FILES = {"manifest.json", "graph.ir.json", "course.json"}


def create_package(pack: CoursePack) -> bytes:
    manifest = {
        "format": "netbrick.course",
        "version": "1.0",
        "title": pack.title,
        "author": pack.author,
    }
    ir_data = pack.ir.model_dump(mode="json")
    course = {
        "title": pack.title,
        "author": pack.author,
        "description": pack.description,
        "steps": [step.model_dump(mode="json") for step in pack.steps],
    }
    files = {
        "manifest.json": json.dumps(manifest, ensure_ascii=False, indent=2).encode(),
        "graph.ir.json": json.dumps(ir_data, ensure_ascii=False, indent=2).encode(),
        "course.json": json.dumps(course, ensure_ascii=False, indent=2).encode(),
    }
    manifest["sha256"] = {
        name: hashlib.sha256(content).hexdigest()
        for name, content in files.items()
        if name != "manifest.json"
    }
    files["manifest.json"] = json.dumps(manifest, ensure_ascii=False, indent=2).encode()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def validate_package(request: CourseImportRequest) -> CourseValidateResponse:
    try:
        raw = base64.b64decode(request.content_base64, validate=True)
    except (binascii.Error, ValueError):
        return _invalid("课件包不是有效的 Base64 数据")
    if len(raw) > MAX_PACKAGE_BYTES:
        return _invalid("课件包超过 20 MiB 限制")
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile:
        return _invalid("文件不是有效的 .netbrick ZIP 包")

    total = 0
    seen: set[str] = set()
    for info in archive.infolist():
        path = PurePosixPath(info.filename)
        if path.is_absolute() or ".." in path.parts or len(path.parts) != 1:
            return _invalid(f"课件包包含不安全路径：{info.filename}")
        if info.is_dir() or info.filename not in PACKAGE_FILES:
            return _invalid(f"课件包包含未知文件：{info.filename}")
        if info.filename in seen:
            return _invalid(f"课件包包含重复文件：{info.filename}")
        seen.add(info.filename)
        total += info.file_size
        if total > MAX_PACKAGE_BYTES:
            return _invalid("课件解压后超过 20 MiB 限制")
    if seen != PACKAGE_FILES:
        return _invalid("课件包缺少 manifest、IR 或课程步骤")

    try:
        manifest = json.loads(archive.read("manifest.json"))
        if manifest.get("format") != "netbrick.course" or manifest.get("version") != "1.0":
            return _invalid("不支持的课件包格式版本")
        hashes = manifest.get("sha256", {})
        for name in PACKAGE_FILES - {"manifest.json"}:
            content = archive.read(name)
            if hashlib.sha256(content).hexdigest() != hashes.get(name):
                return _invalid(f"{name} 校验失败")
        ir = IRDocument.model_validate_json(archive.read("graph.ir.json"))
        course = json.loads(archive.read("course.json"))
        pack = CoursePack(
            title=course["title"],
            author=course.get("author", ""),
            description=course.get("description", ""),
            ir=ir,
            steps=course.get("steps", []),
        )
    except (KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return _invalid(f"课件内容解析失败：{exc}")
    return CourseValidateResponse(valid=True, pack=pack)


def _invalid(message: str) -> CourseValidateResponse:
    return CourseValidateResponse(
        valid=False,
        diagnostics=[
            Diagnostic(
                code="COURSE_PACKAGE_INVALID",
                message=message,
                teaching_tip="只导入由 NetBrick 导出的 .netbrick 课件包。",
            )
        ],
    )
