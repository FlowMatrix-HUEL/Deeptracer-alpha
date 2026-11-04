# 配置指南

## 配置文件

DeepTracer 固定读取：

```text
~/.deeptracer/.env.local
```

从唯一入口进入配置菜单：

```bash
deeptracer
```

选择“配置模型”或“查看当前配置”。API Key 输入不会回显。配置写入后需要在主菜单中重新启动 Web。

## 查看配置

```bash
deeptracer
```

选择“查看当前配置”，API Key 会脱敏显示。

## 非交互式配置

也可以从主菜单依次选择“配置模型”，然后按提示填写 API Key、Base URL、模型名称和 Temperature。

## 关闭与启用 Agent

在主菜单选择“关闭 Agent”或“启用 Agent”。

关闭后：

- 不创建 OpenAI 或兼容模型客户端。
- 不发送 Agent 网络请求。
- 使用本地结构、性能、内存、规则建议和本地答疑。

对应配置：

```text
DEEPTRACER_AGENTS_ENABLED=false
```

## 模型配置项

| 配置项 | 说明 |
| --- | --- |
| `OPENAI_API_KEY` | API Key |
| `OPENAI_BASE_URL` | OpenAI 兼容接口地址 |
| `OPENAI_MODEL` | 兼容模型名称 |
| `DEEPTRACER_MODEL_NAME` | DeepTracer 模型名称，优先级更高 |
| `DEEPTRACER_MODEL_PROVIDER` | 当前仅支持 `openai` |
| `DEEPTRACER_MODEL_TEMPERATURE` | 温度，默认 `0.2` |
| `DEEPTRACER_AGENTS_ENABLED` | Agent 总开关 |

## 超时配置

| 环境变量 | 默认值 | 用途 |
| --- | --- | --- |
| `DEEPTRACER_EXECUTION_TIMEOUT_SECONDS` | `5` | 分析与 PyInstrument 执行 |
| `DEEPTRACER_PYINSTRUMENT_INTERVAL_SECONDS` | 自动（200µs/500µs） | PyInstrument 采样间隔；无导入代码 200µs，有导入代码 500µs |
| `DEEPTRACER_PYINSTRUMENT_MAX_SAMPLES` | `2000` | 火焰图渲染前的最大样本数 |
| `DEEPTRACER_TUTOR_TIMEOUT_SECONDS` | `8` | Python Tutor |
| `DEEPTRACER_TRACER_TIMEOUT_SECONDS` | `8` | Tracer 调用追踪 |
| `DEEPTRACER_RUN_TIMEOUT_SECONDS` | `5` | 运行终端 |

## Tracer 路径

如果 `Tracer/` 不在项目根目录，可以设置：

```text
DEEPTRACER_TRACER_ROOT=/path/to/Tracer
```
