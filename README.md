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
- **AI Q&A and agents**: OpenAI-compatible integration with a complete local-only mode.

## Quick Start

```bash
conda create -n deeptracer python=3.11 -y
conda activate deeptracer
python -m pip install --upgrade pip
pip install -e .
deeptracer-web
```

Open:

```text
http://127.0.0.1:8000
```

Use the built-in sample, analyze it, then switch the right-hand runtime panel between Python Tutor, Tracer, and the run terminal. Native and library APIs are available from the `API 文档 ↗` navigation link.

## Documentation

- [Feature details](./docs/features.md)
- [Configuration](./docs/configuration.md)
- [API documentation](./docs/api.md)
- [System design](./docs/design.md)
