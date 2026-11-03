# DeepTracer 文档

本目录保存 DeepTracer 的功能、配置、设计与接口说明。根目录的 `README_zh.md` 只保留功能介绍和快速使用。

## 文档索引

- [功能说明](./features.md)
- [配置指南](./configuration.md)
- [API 文档](./api.md)
- [Tracer 库 API](./tracer-api.md)
- [系统设计](./design.md)

## 项目定位

DeepTracer 是面向 Python 学习、教学和轻量代码诊断的本地分析工作台。它将 AST 结构、PyInstrument 性能火焰图、Python Tutor 执行步骤、Tracer 函数调用追踪、终端输出和可选 Agent 解释统一在一个界面中。

DeepTracer 默认在本地执行代码，并将用户代码分析放入独立子进程。Agent 为可选增强，可以完全关闭。
