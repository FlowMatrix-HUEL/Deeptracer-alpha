# DeepTracer

[English](./README.md) · [完整文档](./docs/README_zh.md)

DeepTracer 是一个本地 Python 代码分析工作台，面向代码学习、教学演示和轻量级代码诊断。它把 AST、性能、执行流程、函数调用追踪、终端运行和可选 Agent 解释整合在一个界面中。

## 功能

- **AST 结构**：函数签名、参数类型、默认值、嵌套调用关系与语法节点图。
- **性能分析**：PyInstrument 火焰图、函数耗时和内存摘要。
- **Python Tutor**：逐行执行、调用栈和变量变化。
- **运行终端**：独立执行代码，查看 stdout、stderr、异常和耗时。
- **Tracer 调用追踪**：选择函数，查看调用树、参数、返回值、递归层级和耗时。
- **折叠工作台**：函数签名、分析详情、优化建议和调用树支持折叠。
- **AI 答疑与 Agent**：支持 OpenAI 兼容接口；可以完全关闭，只使用本地分析。

## 快速开始

### 1. 创建环境

```bash
conda create -n deeptracer python=3.11 -y
conda activate deeptracer
python -m pip install --upgrade pip
pip install -e .
```

### 2. 启动

```bash
deeptracer-web
```

访问：

```text
http://127.0.0.1:8000
```

### 3. 基本使用

1. 选择或拖入 `.py` 文件，也可以载入内置示例。
2. 点击“分析代码”查看 AST、性能、建议和执行流程。
3. 在“运行观察”中切换 Python Tutor、Tracer 和运行终端。
4. 需要查看原生接口和 Tracer 库接口时，打开顶部 `API 文档 ↗` 页面。

## 文档

- [功能说明](./docs/features.md)
- [配置指南](./docs/configuration.md)
- [API 文档](./docs/api.md)
- [系统设计](./docs/design.md)
