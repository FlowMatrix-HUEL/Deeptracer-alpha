from __future__ import annotations

import json
import queue
import re
import threading
from itertools import islice
from typing import Any, Iterable

from deeptracer.modeling.llm import describe_model_runtime, get_chat_model

from .memory import (
    append_thread,
    build_memory_context,
    list_cases,
    partner_root,
)
from .prompts import build_partner_system_prompt


_ACTION_RE = re.compile(r"\[ACTION\](.*?)\[/ACTION\]", re.S)
_HINT_RE = re.compile(r"\[HINT\]\s*(H[0-4])\s*\[/HINT\]", re.I)
_TAG_TOKENS = ("[ACTION]", "[HINT]")
_ALLOWED_KINDS = {
    "evidence",
    "highlight",
    "jump",
    "run",
    "propose_code",
    "save_case",
}


def _event(name: str, payload: dict[str, Any]) -> str:
    return f"event: {name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _chunk_text(text: str, *, chunk_size: int = 28) -> Iterable[str]:
    for start in range(0, len(text), chunk_size):
        yield text[start : start + chunk_size]


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text") or ""))
        return "".join(parts)
    return str(content or "")


def _normalize_messages(messages: Any) -> list[dict[str, str]]:
    if not isinstance(messages, list):
        return []
    normalized: list[dict[str, str]] = []
    for item in messages:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").strip().lower()
        content = str(item.get("content") or "").strip()
        if role not in {"user", "assistant"} or not content:
            continue
        normalized.append({"role": role, "content": content})
    return list(islice(normalized, max(0, len(normalized) - 10), None))


def _short(value: Any, limit: int) -> str:
    text = str(value or "")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _validate_action(raw: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    kind = str(raw.get("kind") or "").strip()
    if kind not in _ALLOWED_KINDS:
        return None
    action: dict[str, Any] = {"kind": kind}

    if kind == "evidence":
        refs = raw.get("refs")
        if not isinstance(refs, list) or not refs:
            return None
        clean_refs = []
        for ref in refs[:6]:
            if not isinstance(ref, dict):
                continue
            item = {
                "type": str(ref.get("type") or "evidence")[:30],
                "label": _short(ref.get("label"), 120),
            }
            for key in ("stepIndex", "line", "nodeId"):
                if ref.get(key) not in (None, ""):
                    item[key] = ref.get(key)
            clean_refs.append(item)
        if not clean_refs:
            return None
        action["refs"] = clean_refs
        return action

    if kind in {"highlight", "jump"}:
        target = raw.get("target")
        if not isinstance(target, dict):
            return None
        clean_target = {
            "type": str(target.get("type") or "line")[:20],
        }
        for key in ("line", "stepIndex", "nodeId", "x", "y"):
            if target.get(key) not in (None, ""):
                clean_target[key] = target.get(key)
        if not any(key in clean_target for key in ("line", "stepIndex", "nodeId", "x", "y")):
            return None
        action["target"] = clean_target
        action["label"] = _short(raw.get("label") or "看这里", 80)
        return action

    if kind == "run":
        target = raw.get("target")
        if not isinstance(target, dict):
            return None
        code = _short(target.get("code"), 4000)
        action["target"] = {
            "type": str(target.get("type") or "variant")[:20],
            "code": code,
        }
        action["label"] = _short(raw.get("label") or "运行验证", 80)
        return action

    if kind == "propose_code":
        code = _short(raw.get("code"), 4000)
        if not code.strip():
            return None
        target = raw.get("target")
        if not isinstance(target, dict):
            target = {}
        action["target"] = {
            "workbench": str(target.get("workbench") or "python")[:20],
            "mode": str(target.get("mode") or "insert")[:20],
            "line": target.get("line"),
        }
        action["code"] = code
        action["why"] = _short(raw.get("why"), 400)
        action["hintLevel"] = str(raw.get("hintLevel") or "H3")[:2]
        return action

    if kind == "save_case":
        case = raw.get("case")
        if not isinstance(case, dict):
            return None
        action["case"] = {
            "title": _short(case.get("title"), 160),
            "workbench": str(case.get("workbench") or "")[:20],
            "concepts": [
                _short(item, 40)
                for item in (case.get("concepts") or [])
                if str(item).strip()
            ][:8],
            "question": _short(case.get("question"), 1000),
            "conclusion": _short(case.get("conclusion"), 2000),
            "status": "resolved" if case.get("status") == "resolved" else "open",
        }
        return action

    return None


def _parse_action_blocks(text: str) -> tuple[str, list[dict[str, Any]], str | None]:
    hint = None
    hint_match = _HINT_RE.search(text or "")
    if hint_match:
        hint = hint_match.group(1).upper()

    actions: list[dict[str, Any]] = []
    for match in _ACTION_RE.finditer(text or ""):
        try:
            raw = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        action = _validate_action(raw)
        if action:
            actions.append(action)

    cleaned = _ACTION_RE.sub("", text or "")
    cleaned = _HINT_RE.sub("", cleaned).strip()
    return cleaned, actions[:8], hint


def _first_tag_index(text: str) -> int:
    indexes = [text.find(token) for token in _TAG_TOKENS if text.find(token) >= 0]
    return min(indexes) if indexes else -1


def _fallback_text(workbench: str, context: dict[str, Any]) -> str:
    if workbench == "turtle":
        steps = context.get("steps") or []
        last = steps[-1] if steps else {}
        line = last.get("line")
        if line:
            return (
                f"我现在没有连接模型，但我们可以先用证据。先看第 {line} 行的执行步："
                "你原本预期画布会变成什么样？"
            )
        return "我现在没有连接模型，但我们可以先用证据。先说说你原本预期画布会变成什么样？"
    if workbench == "netbrick":
        return (
            "我现在没有连接模型，但我们可以先用证据。先选中一个节点，"
            "说说你预期它的输出 Shape 是多少？"
        )
    trace = context.get("trace") or {}
    line = trace.get("line") or (context.get("selection") or {}).get("line")
    if line:
        return (
            f"我现在没有连接模型，但我们可以先用证据。先看第 {line} 行："
            "你原本预期这里会发生什么？"
        )
    return "我现在没有连接模型，但我们可以先用证据。先说说你原本预期这段代码会发生什么？"


def _fallback_actions(workbench: str, context: dict[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    if workbench == "turtle":
        steps = context.get("steps") or []
        last = steps[-1] if steps else {}
        if last.get("index") is not None:
            actions.append(
                {
                    "kind": "jump",
                    "target": {"type": "step", "stepIndex": last.get("index")},
                    "label": "跳到最近一步",
                }
            )
        return actions
    if workbench == "netbrick":
        trace = context.get("trace") or {}
        steps = trace.get("steps") if isinstance(trace, dict) else None
        last = steps[-1] if isinstance(steps, list) and steps else {}
        if last.get("node_id"):
            actions.append(
                {
                    "kind": "highlight",
                    "target": {"type": "node", "nodeId": last.get("node_id")},
                    "label": "看这个节点",
                }
            )
        return actions
    trace = context.get("trace") or {}
    line = trace.get("line") or (context.get("selection") or {}).get("line")
    if line:
        actions.append(
            {
                "kind": "highlight",
                "target": {"type": "line", "line": line},
                "label": "看这一行",
            }
        )
    return actions


def _emit_fallback(
    *,
    workbench: str,
    context: dict[str, Any],
    latest_user: str,
    mode: str,
) -> Iterable[str]:
    for chunk in _chunk_text(_fallback_text(workbench, context)):
        yield _event("token", {"delta": chunk})
    for action in _fallback_actions(workbench, context):
        yield _event("action", action)
    yield _event("hint", {"level": "H1"})
    yield _event(
        "done",
        {
            "mode": "fallback",
            "hintLevel": "H1",
            "actions": 0,
            "note": "模型不可用，当前只使用本地证据。",
        },
    )
    append_thread(
        {
            "workbench": workbench,
            "mode": mode,
            "hint_level": "H1",
            "user": latest_user,
            "assistant": _fallback_text(workbench, context),
            "actions": _fallback_actions(workbench, context),
        }
    )


def _iter_model_chunks(llm: Any, messages: list[Any]) -> Iterable[Any]:
    """Consume the model stream in a worker thread with a hard deadline.

    Some OpenAI-compatible proxies accept the request and then never send a
    chunk. Without this guard the SSE response would hang forever.
    """

    chunks: queue.Queue = queue.Queue()
    stop = threading.Event()

    def worker() -> None:
        try:
            for chunk in llm.stream(messages):
                if stop.is_set():
                    break
                chunks.put(("chunk", chunk))
        except Exception as exc:  # noqa: BLE001 - forwarded to the caller
            chunks.put(("error", exc))
        finally:
            chunks.put(("done", None))

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    timeout = 50.0
    try:
        while True:
            try:
                kind, value = chunks.get(timeout=timeout)
            except queue.Empty as exc:
                raise TimeoutError("模型在限定时间内没有返回内容。") from exc
            if kind == "done":
                return
            if kind == "error":
                raise value
            yield value
            timeout = 30.0
    finally:
        stop.set()


def stream_partner_events(payload: dict[str, Any]) -> Iterable[str]:
    if not isinstance(payload, dict):
        yield _event("error", {"message": "payload must be an object"})
        return

    workbench = str(payload.get("workbench") or "python").strip().lower()
    if workbench not in {"python", "turtle", "netbrick"}:
        yield _event("error", {"message": "workbench must be python, turtle, or netbrick"})
        return

    mode = str(payload.get("mode") or "co-investigate").strip().lower()
    if mode not in {"ask", "co-investigate", "challenge", "reflect"}:
        mode = "co-investigate"

    context = payload.get("context")
    if not isinstance(context, dict):
        context = {}

    history = _normalize_messages(payload.get("messages"))
    latest_user = next(
        (item["content"] for item in reversed(history) if item["role"] == "user"),
        "",
    )
    if not latest_user:
        yield _event("error", {"message": "缺少用户输入，无法发起调查。"})
        return

    llm = get_chat_model(optional=True)
    runtime = describe_model_runtime()
    runtime["modelReady"] = llm is not None
    memory_context = build_memory_context(workbench)
    yield _event(
        "meta",
        {
            "workbench": workbench,
            "mode": mode,
            "runtime": runtime,
            "memoryRoot": str(partner_root()),
            "cases": list_cases(5),
        },
    )

    if llm is None:
        yield from _emit_fallback(
            workbench=workbench,
            context=context,
            latest_user=latest_user,
            mode=mode,
        )
        return

    try:
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        system_prompt = build_partner_system_prompt(
            workbench=workbench,
            context=context,
            memory_context=memory_context,
            mode=mode,
        )
        lc_messages = [SystemMessage(content=system_prompt)]
        for item in history:
            if item["role"] == "assistant":
                lc_messages.append(AIMessage(content=item["content"]))
            else:
                lc_messages.append(HumanMessage(content=item["content"]))

        buffer = ""
        emitted = ""
        text_finished = False
        full_text = ""

        for chunk in _iter_model_chunks(llm, lc_messages):
            piece = _content_to_text(getattr(chunk, "content", ""))
            if not piece:
                continue
            full_text += piece
            buffer += piece
            if text_finished:
                continue
            marker = _first_tag_index(buffer)
            if marker >= 0:
                if marker > 0:
                    text = buffer[:marker]
                    emitted += text
                    yield _event("token", {"delta": text})
                buffer = buffer[marker:]
                text_finished = True
            elif len(buffer) > 24:
                text = buffer[:-24]
                emitted += text
                buffer = buffer[-24:]
                yield _event("token", {"delta": text})

        if not text_finished:
            if buffer:
                emitted += buffer
                yield _event("token", {"delta": buffer})
            buffer = ""

        cleaned, actions, hint = _parse_action_blocks(buffer)
        if cleaned:
            remainder = cleaned
            if emitted and remainder.startswith(emitted):
                remainder = remainder[len(emitted) :]
            if remainder:
                emitted += remainder
                yield _event("token", {"delta": remainder})

        for action in actions:
            yield _event("action", action)

        hint = hint or "H1"
        yield _event("hint", {"level": hint})
        yield _event(
            "done",
            {
                "mode": "model",
                "hintLevel": hint,
                "actions": len(actions),
            },
        )
        append_thread(
            {
                "workbench": workbench,
                "mode": mode,
                "hint_level": hint,
                "user": latest_user,
                "assistant": emitted or full_text,
                "actions": actions,
            }
        )
    except Exception as exc:
        yield _event("error", {"message": f"思辨伙伴生成失败：{exc}"})
