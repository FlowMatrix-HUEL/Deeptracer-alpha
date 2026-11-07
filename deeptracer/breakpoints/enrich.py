from __future__ import annotations

import copy
import hashlib
import json
import os
from collections import OrderedDict
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from deeptracer.agents.utils import JSON_OUTPUT_INSTRUCTION
from deeptracer.modeling.llm import get_chat_model


class MomentEnrichment(BaseModel):
    id: str = Field(description="Exact moment id from the input.")
    label: str | None = Field(default=None, description="Short label, at most 24 Chinese characters.")
    why: str | None = Field(default=None, description="One sentence explaining why this moment matters.")
    question: str | None = Field(default=None, description="Optional concrete prediction question.")
    concepts: list[str] | None = Field(default=None, description="Optional concept tags.")
    importance: float | None = Field(default=None, ge=0, le=1)


class MomentEnrichmentList(BaseModel):
    moments: list[MomentEnrichment] = Field(default_factory=list)


_CACHE: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
_CACHE_MAX = 64
_MAX_CODE_CHARS = 4000
_MAX_MOMENT_JSON_CHARS = 6000


def _cache_key(
    world: str,
    code: str,
    moments: list[dict[str, Any]],
    model_name: str,
) -> str:
    payload = json.dumps(
        {
            "world": world,
            "code": code,
            "ids": [moment.get("id") for moment in moments],
            "model": model_name,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _fallback(moments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for moment in moments:
        item = dict(moment)
        item["enriched"] = False
        result.append(item)
    return result


def _compact_moments(moments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for moment in moments:
        compact.append(
            {
                "id": moment.get("id"),
                "kind": moment.get("kind"),
                "line": moment.get("line"),
                "step_index": moment.get("step_index"),
                "node_id": moment.get("node_id"),
                "label": moment.get("label"),
                "why": moment.get("why"),
                "question": moment.get("question"),
                "evidence": moment.get("evidence"),
            }
        )
    return compact


def enrich_moments(
    moments: list[dict[str, Any]],
    *,
    code: str,
    world: str,
) -> list[dict[str, Any]]:
    """Optionally rewrite moment copy with the configured model.

    Only `label`, `why`, `question`, `concepts`, and `importance` can change.
    Locations and evidence are copied from the detector output verbatim. Any
    failure returns the original moments with ``enriched=False``.
    """

    if not moments:
        return []

    llm = get_chat_model(optional=True)
    if llm is None:
        return _fallback(moments)

    model_name = str(
        getattr(llm, "model_name", "")
        or os.getenv("DEEPTRACER_MODEL_NAME", "")
        or ""
    )
    cache_key = _cache_key(world, code, moments, model_name)
    cached = _CACHE.get(cache_key)
    if cached is not None:
        _CACHE.move_to_end(cache_key)
        return copy.deepcopy(cached)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You improve teaching copy for debugging moments. "
                "You must not change ids, locations, or evidence, and you must not "
                "invent facts that are not present in the supplied moment. "
                "Keep labels short, write one plain-language sentence for why, and "
                "only add a question when a concrete prediction helps. "
                f"{JSON_OUTPUT_INSTRUCTION}",
            ),
            (
                "human",
                "World: {world}\n\nCode:\n{code}\n\nMoments:\n{moments}\n\n"
                "Rewrite only label/why/question/concepts/importance. "
                "Return every input id exactly once.",
            ),
        ]
    )

    try:
        chain = prompt | llm.with_structured_output(MomentEnrichmentList)
        response = chain.invoke(
            {
                "world": world,
                "code": code[:_MAX_CODE_CHARS],
                "moments": json.dumps(
                    _compact_moments(moments), ensure_ascii=False
                )[:_MAX_MOMENT_JSON_CHARS],
            }
        )
        items = getattr(response, "moments", None) or []
    except Exception:
        return _fallback(moments)

    by_id = {
        item.id: item
        for item in items
        if isinstance(item, MomentEnrichment) and item.id
    }
    result: list[dict[str, Any]] = []
    updated_any = False
    for original in moments:
        updated = dict(original)
        item = by_id.get(str(original.get("id") or ""))
        if item is None:
            updated["enriched"] = False
            result.append(updated)
            continue
        if item.label:
            updated["label"] = item.label[:80]
        if item.why:
            updated["why"] = item.why[:300]
        if item.question is not None:
            updated["question"] = item.question[:200] if item.question else None
        if item.concepts:
            updated["concepts"] = [str(concept)[:40] for concept in item.concepts][:5]
        if item.importance is not None:
            updated["importance"] = max(0.0, min(1.0, float(item.importance)))
        updated["enriched"] = True
        updated_any = True
        result.append(updated)

    if not updated_any:
        return _fallback(moments)

    _CACHE[cache_key] = copy.deepcopy(result)
    while len(_CACHE) > _CACHE_MAX:
        _CACHE.popitem(last=False)
    return result
