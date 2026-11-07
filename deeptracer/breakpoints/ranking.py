from __future__ import annotations

from .models import Moment


_SEVERITY_SCORE = {"error": 3.0, "warning": 2.0, "info": 1.0}
_KIND_SCORE = {
    "exception": 1.0,
    "closure": 0.6,
    "boundary": 0.4,
    "shape_change": 0.4,
    "merge": 0.3,
    "diagnostic": 0.5,
    "control_flow": 0.3,
    "call": 0.15,
}


def rank_moments(moments: list[Moment], limit: int = 7) -> list[Moment]:
    """Deduplicate, score, and cap moments for the UI.

    Rules are intentionally simple: an error always outranks an interesting
    moment, and a high-importance boundary outranks a routine variable change.
    The detector ids are stable, so deduplication by id is enough.
    """

    if limit <= 0:
        return []

    seen: set[str] = set()
    scored: list[tuple[float, Moment]] = []
    for moment in moments:
        if moment.id in seen:
            continue
        seen.add(moment.id)
        score = (
            _SEVERITY_SCORE.get(moment.severity, 1.0)
            + moment.importance
            + _KIND_SCORE.get(moment.kind, 0.0)
        )
        scored.append((score, moment))

    scored.sort(
        key=lambda item: (
            -item[0],
            item[1].step_index if item[1].step_index is not None else 10**9,
            item[1].id,
        )
    )
    return [moment for _, moment in scored[:limit]]
