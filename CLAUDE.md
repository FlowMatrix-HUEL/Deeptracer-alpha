# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install the package in editable mode (for development)
pip install -e .

# Install with dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest tests/

# Run a single test file
pytest tests/test_clip.py -v

# Run a single test
pytest tests/test_clip.py::test_clip_function_prints_current_analysis_summary -v

# Lint
flake8 deeptracer/

# Format
black deeptracer/ tests/

# Run the web server
deeptracer-web

# CLI analysis entrypoint
deeptracer path/to/file.py
```

## Project Architecture

Deeptracer is an AI-powered Python code analysis platform with a FastAPI web server and a LangGraph-based multi-agent pipeline.

### System Entrypoints

- **`deeptracer clip main`** (`deeptracer/clip.py`): CLI entrypoint. Parses args, validates path, calls `analyze_python_file`, prints a summary report.
- **`deeptracer-web`** (`deeptracer/server/app.py`): FastAPI web server on `127.0.0.1:8000`. Serves a Jinja2 frontend (`templates/index.html`, `static/app.js`, `static/app.css`) and REST endpoints.

### Analysis Pipeline (`deeptracer/graph/`)

A LangGraph `StateGraph` orchestrates these sequential stages:

1. **local_tools** → `deeptracer/server/analysis_service.py`: Runs static AST analysis (`deeptracer/astAnalyer/`), cProfile performance profiling (`deeptracer/speedAnalyer/`), and tracemalloc memory analysis on the submitted Python file.
2. **core_agents** → `deeptracer/agents/`: Three LangChain agents run in parallel via ThreadPoolExecutor:
   - `structure_agent.py` — explains code structure
   - `performance_agent.py` — explains performance findings
   - `memory_agent.py` — explains memory findings
   - Each agent falls back to local analysis data if the LLM is unavailable.
3. **refactor** → `refactor_agent.py`: Generates code improvement suggestions combining all prior analysis.
4. **teaching** → `teaching_agent.py`: Generates beginner-friendly guidance.
5. **response** → `response_builder.py`: Merges all agent outputs into the frontend response payload.

State is typed via `AnalysisState` in `deeptracer/graph/state.py`.

### Agents System

All agents in `deeptracer/agents/` follow the same pattern:
- Define a Pydantic `BaseModel` schema in `schemas.py`
- Build a `ChatPromptTemplate`, chain it with `llm.with_structured_output(Schema)`
- Use `invoke_structured_or_fallback()` from `utils.py` to catch LLM failures and fall back to local analysis data

### LLM Configuration

- `deeptracer/modeling/llm.py`: `get_chat_model()` reads `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `DEEPTRACER_MODEL_NAME`, etc. from environment or `.deeptracer/.env.local`.
- `deeptracer/workflow/env_utils.py`: `build_env_local` manages the `.env.local` config file at `~/.deeptracer/.env.local`.
- Configure via CLI: `deeptracer -k <coze_token>` or edit `~/.deeptracer/.env.local` directly.
- Without API key, the system runs in local-only fallback mode (no LLM agents).

### Web Server API

- `POST /api/analyze` — submit a Python file path or inline source code for analysis
- `POST /api/chat/stream` — SSE-streamed grounded conversation about analyzed code
- `POST /api/tutor/trace` — execute code and return a Python Tutor execution trace
- `GET /api/tutor/status` — check if local Python Tutor is available

### Analysis Context & Chat

- `deeptracer/server/analysis_context.py`: Manages an LRU analysis result cache (up to 24 entries), builds "grounding bundles" (code anchors + analysis summary) for the chat service.
- `deeptracer/server/chat_service.py`: SSE-streamed chat. If LLM is configured, streams LangChain responses grounded in analysis context. Otherwise falls back to a template reply.

### Frontend

Vanilla JavaScript + CSS (no framework). Three-page layout: home (file selection), code (editor + execution flow), analysis results (AST, performance, suggestions). Features Git-style diff display, draggable panels, and a Python Tutor iframe for execution visualization.

### Local Analyzers

- `deeptracer/astAnalyer/viztracer.py` (`AstAnalyer`): Parses Python into AST, builds a pyvis/networkx visualization graph of code structure.
- `deeptracer/speedAnalyer/viztracer.py` (`SpeedAnalyzer`): Runs `cProfile` on the target code, parses `pstats` output for performance data.

### Key Dependencies

Python 3.10+, FastAPI, Uvicorn, LangChain, LangGraph, langchain-openai, Pyinstrument, PyVis, NetworkX.
