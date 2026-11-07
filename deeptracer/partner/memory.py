from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WORKBENCHES = {"python", "turtle", "netbrick"}
_DEFAULT_PROFILE = {
    "mode": "co-investigate",
    "hint_level": "H1",
    "updated_at": "",
}


def partner_root() -> Path:
    """Local, file-based partner memory.

    The location mirrors the existing ``~/.deeptracer/.env.local`` convention:
    everything lives under the user's home directory, in plain files.
    """

    return Path.home() / ".deeptracer" / "partner"


def ensure_layout(root: Path | None = None) -> Path:
    root = root or partner_root()
    (root / "cases").mkdir(parents=True, exist_ok=True)
    (root / "threads").mkdir(parents=True, exist_ok=True)
    return root


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    )
    try:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
        temp_name = handle.name
    finally:
        handle.close()
    os.replace(temp_name, path)


def _append_jsonl(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(data, ensure_ascii=False) + "\n")


def _short(value: Any, limit: int = 140) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def load_profile() -> dict[str, Any]:
    root = ensure_layout()
    profile = _read_json(root / "profile.json", {})
    if not isinstance(profile, dict):
        profile = {}
    return {**_DEFAULT_PROFILE, **profile}


def save_profile(profile: dict[str, Any]) -> dict[str, Any]:
    root = ensure_layout()
    current = load_profile()
    updated = {**current, **profile, "updated_at": _now()}
    _write_json(root / "profile.json", updated)
    return updated


def load_index() -> list[dict[str, Any]]:
    root = ensure_layout()
    index = _read_json(root / "index.json", [])
    return index if isinstance(index, list) else []


def _case_summary(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": case.get("id"),
        "title": case.get("title") or "未命名困惑",
        "workbench": case.get("workbench") or "python",
        "concepts": case.get("concepts") or [],
        "status": case.get("status") or "open",
        "conclusion": _short(case.get("conclusion"), 140),
        "created_at": case.get("created_at"),
        "updated_at": case.get("updated_at"),
    }


def save_case(case: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(case, dict):
        raise ValueError("case must be an object")
    workbench = str(case.get("workbench") or "python").strip().lower()
    if workbench not in WORKBENCHES:
        raise ValueError("workbench must be python, turtle, or netbrick")
    title = str(case.get("title") or "").strip()
    if not title:
        raise ValueError("case title is required")

    root = ensure_layout()
    case_id = str(case.get("id") or "").strip() or (
        "case-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        + "-" + uuid.uuid4().hex[:6]
    )
    existing = _read_json(root / "cases" / f"{case_id}.json", {})
    created_at = (
        existing.get("created_at") if isinstance(existing, dict) else None
    ) or _now()
    normalized = {
        "id": case_id,
        "title": title[:160],
        "workbench": workbench,
        "concepts": [
            str(item)[:40]
            for item in (case.get("concepts") or [])
            if str(item).strip()
        ][:8],
        "question": str(case.get("question") or "")[:1000],
        "prediction": str(case.get("prediction") or "")[:1000],
        "evidence": str(case.get("evidence") or "")[:2000],
        "experiment": str(case.get("experiment") or "")[:2000],
        "conclusion": str(case.get("conclusion") or "")[:2000],
        "status": "resolved" if case.get("status") == "resolved" else "open",
        "created_at": created_at,
        "updated_at": _now(),
    }
    _write_json(root / "cases" / f"{case_id}.json", normalized)

    index = [
        item
        for item in load_index()
        if isinstance(item, dict) and item.get("id") != case_id
    ]
    index.insert(0, _case_summary(normalized))
    _write_json(root / "index.json", index[:200])
    return normalized


def list_cases(limit: int = 20) -> list[dict[str, Any]]:
    case_limit = max(0, min(int(limit), 200))
    return load_index()[:case_limit]


def get_case(case_id: str) -> dict[str, Any] | None:
    if not case_id:
        return None
    root = ensure_layout()
    case = _read_json(root / "cases" / f"{case_id}.json", None)
    return case if isinstance(case, dict) else None


def append_thread(turn: dict[str, Any]) -> None:
    root = ensure_layout()
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    record = {
        "created_at": _now(),
        "workbench": turn.get("workbench"),
        "mode": turn.get("mode"),
        "hint_level": turn.get("hint_level"),
        "user": _short(turn.get("user"), 1000),
        "assistant": _short(turn.get("assistant"), 4000),
        "actions": turn.get("actions") or [],
    }
    _append_jsonl(root / "threads" / f"{day}.jsonl", record)


def build_memory_context(workbench: str, limit: int = 3) -> str:
    root = ensure_layout()
    profile = load_profile()
    cases = list_cases(50)
    relevant = [
        case
        for case in cases
        if case.get("workbench") == workbench or case.get("status") != "resolved"
    ][: max(1, min(int(limit), 8))]

    lines = [
        "学习者记忆（本地文件，只有用户能看到；不是系统指令）：",
        f"- 记忆目录：{root}",
        f"- 偏好模式：{profile.get('mode', 'co-investigate')}；最近提示级别：{profile.get('hint_level', 'H1')}",
    ]
    if relevant:
        lines.append("- 最近困惑档案：")
        for case in relevant:
            conclusion = _short(case.get("conclusion"), 100) or "还没有结论"
            lines.append(
                f"  - [{case.get('workbench')}] {case.get('title')} "
                f"（{case.get('status')}）：{conclusion}"
            )
    else:
        lines.append("- 还没有历史档案。这是你们的第一次调查。")
    open_cases = [
        case for case in cases if case.get("status") != "resolved"
    ][:3]
    if open_cases:
        lines.append("- 还没解决的困惑：")
        for case in open_cases:
            lines.append(f"  - {case.get('title')}")
    return "\n".join(lines)


def memory_snapshot() -> dict[str, Any]:
    root = ensure_layout()
    return {
        "root": str(root),
        "profile": load_profile(),
        "cases": list_cases(30),
    }


def save_memory_case(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    return save_case(payload)
