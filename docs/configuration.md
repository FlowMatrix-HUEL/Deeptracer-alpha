# 配置指南

## 配置文件

DeepTracer 固定读取：

```text
~/.deeptracer/.env.local
```

推荐使用：

```bash
deeptracer-config
```

API Key 输入不会回显。配置写入后需要重启 `deeptracer-web`。

## 查看配置

```bash
deeptracer-config --show
```

API Key 会脱敏显示。

## 非交互式配置

```bash
deeptracer-config \
  --api-key "你的 API Key" \
  --base-url "https://兼容接口地址/v1" \
  --model "模型名称" \
  --temperature 0.2
```

## 关闭与启用 Agent

```bash
deeptracer-config --disable-agents
deeptracer-config --enable-agents
```

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
| `DEEPTRACER_PYINSTRUMENT_INTERVAL_SECONDS` | `0.00001` | PyInstrument 采样间隔；短代码可降低该值获得更多样本 |
| `DEEPTRACER_TUTOR_TIMEOUT_SECONDS` | `8` | Python Tutor |
| `DEEPTRACER_TRACER_TIMEOUT_SECONDS` | `8` | Tracer 调用追踪 |
| `DEEPTRACER_RUN_TIMEOUT_SECONDS` | `5` | 运行终端 |

## Tracer 路径

如果 `Tracer/` 不在项目根目录，可以设置：

```text
DEEPTRACER_TRACER_ROOT=/path/to/Tracer
```
