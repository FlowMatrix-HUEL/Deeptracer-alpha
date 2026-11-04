# 系统设计

## 分析流水线

```text
用户输入
  ↓
AST 与函数签名
  ↓
隔离子进程执行 + PyInstrument
  ↓
本地规则分析
  ↓
可选 Agent 解释
  ↓
工作台响应
```

Agent 关闭时，后半段直接使用本地回退结果。

## 运行观察

运行观察包含三个互斥视图：

1. Python Tutor：逐行执行和变量状态。
2. Tracer：函数级调用树、耗时和终端输出。
3. 运行终端：直接查看程序 stdout、stderr 和异常。

三种模式都可能重新执行代码，因此都必须由用户主动触发。

## 子进程隔离

- 分析、Python Tutor、Tracer 和运行终端分别使用独立子进程。
- 每个入口有独立超时。
- 超时后终止整个进程组。
- 用户代码不能通过无限循环直接阻塞 Web 主进程。
- 这不是完整的文件或网络沙箱。

## Agent 设计

- LangChain `ChatOpenAI`。
- OpenAI 兼容 Chat Completions。
- Structure、Performance、Memory、Refactor、Teaching 五个结构化 Agent。
- 模型失败或关闭时使用本地结果。
- Agent 状态写入响应元数据，页面不会把本地结果伪装成模型结果。

## 界面设计

- 使用连续内容布局，不用大量卡片背景。
- 只使用浅色分隔线、留白和字重区分层级。
- 分析详情、建议、Tracer 设置、函数签名和调用树支持折叠。
- 所有函数名称始终列出，不通过“加载更多”隐藏。
- 源代码区永久展开。
- 按钮统一为无边框、无阴影和小圆角；主操作使用浅色强调，而不是实色边框块。

## 内置 Tracer

- Tracer 源目录保持不变。
- DeepTracer 通过 `deeptracer.tracing` 提供内置导入。
- 分析子进程会加载本地 `Tracer/`。
- Web 端关闭交互式调试开关。
