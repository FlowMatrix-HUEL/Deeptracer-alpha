# NetBrick 文档索引

NetBrick 是教学用的神经网络结构编辑器。当前版本专注于网络结构表达、Shape 推演、代码生成和课堂交互，不执行真实张量计算或训练。

## 文档目录

| 文档 | 内容 |
| --- | --- |
| [系统架构](architecture.md) | 前端、后端、IR、DAG 和代码生成的总体关系 |
| [编辑器与交互](editor.md) | 顶部导航、模块库、画布、Inspector、底部面板及快捷操作 |
| [图结构与 Shape](graph-and-shape.md) | 无环图、fan-out、多路汇合、Shape 规则和诊断 |
| [复合资源](composites.md) | 网络发布、版本、接口、参数覆盖和下钻编辑 |
| [控制流](control-flow.md) | If/For/While、谓词子图、状态契约和代码生成 |
| [PyTorch API](pytorch-api.md) | PyTorch 2.6 公开模型层注册表和 Paddle 可用性 |
| [算子与官方 API](operators.md) | 基础层、合并算子及官方 API 映射 |
| [代码生成](code-generation.md) | PyTorch/Paddle AST 生成、拓扑顺序和 Python 导入 |
| [文件与教学资产](files-and-examples.md) | JSON、Mojo、课件包和内置示例 |
| [HTTP API](api.md) | FastAPI 路由、请求和返回结构 |
| [开发与测试](development.md) | 环境、启动、测试、扩展方式和已知限制 |

## 当前能力

- 支持多个 Input/Output、分支 fan-out 和任意数量输入的合并端口。
- 支持 `Add`、`Multiply`、`Concat` 三种基础合并方式。
- 支持版本化复合资源，任何有效网络都可以发布为可复用模块。
- 支持 If、For、While 结构化运行控制流和条件运算。
- PyTorch 2.6 公开模型层进入模块库、Shape、代码生成和导入链路。
- 同一份框架中立 IR 可生成 PyTorch 或 Paddle 官方 API 代码。
- 支持结构错误、Shape 错误和 Python 语法错误的教学化提示。
- 支持本地工程、复合 Mojo、课件包和内置教学示例。

## 使用边界

- 不加载 PyTorch、Paddle 或 ONNX 运行时。
- Shape 结果由纯 Python 规则推演，不是真实 Tensor Trace。
- 不包含训练循环、GPU 运算、AutoML 或云端调度。
- 损失函数和优化器分组仅作为训练阶段入口展示。
- Python 导入只接受可精确映射的 PyTorch 结构子集，不执行源码。
