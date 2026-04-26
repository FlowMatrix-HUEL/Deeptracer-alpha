from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from deeptracer.agents import (
    run_memory_agent,
    run_performance_agent,
    run_refactor_agent,
    run_structure_agent,
    run_teaching_agent,
)
from deeptracer.graph.response_builder import build_frontend_response
from deeptracer.graph.state import AnalysisState
from deeptracer.server.analysis_service import analyze_python_input


def _merge_timings(state: AnalysisState, **entries: float) -> dict[str, float]:
    timings = dict(state.get("timings", {}))
    timings.update(entries)
    return timings


def local_tools_node(state: AnalysisState) -> dict:
    started_at = perf_counter()
    local_analysis = analyze_python_input(
        path_text=state.get("path_text"),
        source_code=state["code"],
        display_name=state.get("display_name"),
    )
    return {
        "local_analysis": local_analysis,
        "timings": _merge_timings(
            state,
            local_analysis_ms=(perf_counter() - started_at) * 1000,
        ),
    }


def core_agents_node(state: AnalysisState) -> dict:
    started_at = perf_counter()
    with ThreadPoolExecutor(max_workers=3) as executor:
        structure_future = executor.submit(
            run_structure_agent, state["code"], state["local_analysis"]
        )
        performance_future = executor.submit(
            run_performance_agent, state["code"], state["local_analysis"]
        )
        memory_future = executor.submit(
            run_memory_agent, state["code"], state["local_analysis"]
        )

        structure_result = structure_future.result()
        performance_result = performance_future.result()
        memory_result = memory_future.result()

    return {
        "structure_result": structure_result,
        "performance_result": performance_result,
        "memory_result": memory_result,
        "timings": _merge_timings(
            state,
            core_agents_ms=(perf_counter() - started_at) * 1000,
        ),
    }


def refactor_node(state: AnalysisState) -> dict:
    started_at = perf_counter()
    return {
        "refactor_result": run_refactor_agent(
            state["code"],
            state["local_analysis"],
            state["structure_result"],
            state["performance_result"],
            state["memory_result"],
        ),
        "timings": _merge_timings(
            state,
            refactor_ms=(perf_counter() - started_at) * 1000,
        ),
    }


def teaching_node(state: AnalysisState) -> dict:
    started_at = perf_counter()
    return {
        "teaching_result": run_teaching_agent(
            state["code"],
            state["structure_result"],
            state["performance_result"],
            state["memory_result"],
            state["refactor_result"],
        ),
        "timings": _merge_timings(
            state,
            teaching_ms=(perf_counter() - started_at) * 1000,
        ),
    }


def response_node(state: AnalysisState) -> dict:
    timings = _merge_timings(
        state,
        total_ms=(perf_counter() - state["started_at"]) * 1000,
    )
    next_state = dict(state)
    next_state["timings"] = timings
    return {"final_response": build_frontend_response(next_state)}


def build_analysis_graph():
    graph = StateGraph(AnalysisState)
    graph.add_node("local_tools", local_tools_node)
    graph.add_node("core_agents", core_agents_node)
    graph.add_node("refactor", refactor_node)
    graph.add_node("teaching", teaching_node)
    graph.add_node("response", response_node)

    graph.add_edge(START, "local_tools")
    graph.add_edge("local_tools", "core_agents")
    graph.add_edge("core_agents", "refactor")
    graph.add_edge("refactor", "teaching")
    graph.add_edge("teaching", "response")
    graph.add_edge("response", END)
    return graph.compile()


@lru_cache(maxsize=1)
def get_analysis_graph():
    return build_analysis_graph()


def run_analysis_graph(
    code: str, path_text: str | None = None, display_name: str | None = None
) -> dict:
    state: AnalysisState = {
        "code": code,
        "task_id": str(uuid4()),
        "started_at": perf_counter(),
        "local_analysis": {},
        "timings": {},
    }
    if path_text:
        state["path_text"] = path_text
    if display_name:
        state["display_name"] = display_name
    result = get_analysis_graph().invoke(state)
    return result["final_response"]


def run_analysis_graph_for_input(
    path_text: str | None = None,
    source_code: str | None = None,
    display_name: str | None = None,
) -> dict:
    if source_code and source_code.strip():
        return run_analysis_graph(
            code=source_code,
            path_text=path_text,
            display_name=display_name,
        )
    if path_text:
        target = Path(path_text).expanduser()
        code = target.read_text(encoding="utf-8")
        return run_analysis_graph(
            code=code,
            path_text=path_text,
            display_name=display_name or target.name,
        )
    raise ValueError("Missing required field: code or path")
