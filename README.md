# DeepTracer

[中文](./README_zh.md) · [Documentation](./docs/README_zh.md)

DeepTracer is a local Python analysis workbench for learning, teaching, and lightweight code diagnosis. It combines AST structure, performance profiling, execution flow, function-call tracing, terminal execution, and optional agent explanations in one interface.

## Features

- **AST structure**: function signatures, parameter types, defaults, nesting, and syntax-node visualization.
- **Performance**: PyInstrument flame graphs, function timing, and memory summaries.
- **Python Tutor**: step-by-step execution, call stack, and variable state.
- **Run terminal**: execute code and inspect stdout, stderr, exceptions, and timing.
- **Tracer call tracing**: select functions and inspect call trees, arguments, return values, recursion, and timing.
- **Collapsible workbench**: collapse function signatures, analysis details, suggestions, and trace nodes.
- **Verified edits**: structured patches, unified/split diffs, before/after behavior comparison, and one-click rollback.
- **Linked source navigation**: suggestions, AST nodes, performance hotspots, Tracer nodes, and Python Tutor steps can focus the same source line.
- **AI Q&A and agents**: OpenAI-compatible integration with a complete local-only mode.
- **Turtle**: keyboard drawing, step execution, variable inspection, task feedback, linked code views, and local exports.
- **NetBrick**: drag-and-drop deep-learning model learning, shape inference, and PyTorch/Paddle code generation.

## Quick Start

```bash
conda create -n deeptracer python=3.11 -y
conda activate deeptracer
python -m pip install --upgrade pip
pip install -e .
deeptracer
```

Choose **Start DeepTracer Web** from the Rich terminal menu, then open:

```text
http://127.0.0.1:8000
```

Use **Turtle** for keyboard drawing and guided step-by-step learning, **NetBrick** for deep-learning model learning, or load Python code for analysis, Tracer, and terminal execution. The built-in sample is editable as a temporary copy and resets when reloaded. Native and library APIs are available from the `API 文档 ↗` navigation link.

## Documentation

- [Feature details](./docs/features.md)
- [Terminal menu](./docs/tui.md)
- [Configuration](./docs/configuration.md)
- [API documentation](./docs/api.md)
- [System design](./docs/design.md)
