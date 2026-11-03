# Tracer API

本页专门说明 Tracer 库。DeepTracer 原生接口和未来新增接口统一记录在 [API 文档](./api.md)，运行服务后可从顶部“API 文档 ↗”跳转到 `/api-docs`。

## 导入

```python
from deeptracer import Tracer, tracer

# 或
from deeptracer.tracing import Tracer, tracer
```

被 DeepTracer 执行的代码：

```python
from tracer import Tracer, tracer
```

DeepTracer 只负责把本地 `Tracer/` 加入导入路径，不修改 Tracer 源码。

## tracer 装饰器

```python
@tracer(
    trace_fn=[func_a, func_b],
    trace_entity=True,
    time_trace=True,
    use_color=True,
)
def entrypoint():
    ...
```

参数：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `trace_fn` | `None` | 额外追踪的函数列表 |
| `trace_entity` | `False` | 是否追踪被装饰函数本身 |
| `logging_path` | `None` | 日志文件 |
| `time_trace` | `False` | 调用次数和耗时 |
| `interactive` | `False` | 追踪前进入交互 Shell |
| `interactive_on_event` | `False` | 每个事件进入交互 Shell |
| `interactive_filter` | `None` | 指定交互事件函数 |
| `use_color` | `False` | ANSI 彩色终端输出 |
| `exception_trace` | `False` | 异常传播追踪 |
| `show_locals` | `False` | 异常时记录局部变量 |
| `exception_json_path` | `None` | 异常 JSON 导出 |

## Tracer 上下文管理器

```python
with Tracer(
    trace_fn=[add, recursive_count],
    time_trace=True,
) as trace_context:
    main()

statistics = trace_context.stats.data
errors = trace_context.errors.to_list()
```

## Web 支持范围

| 功能 | Web 支持 |
| --- | --- |
| `time_trace` | 是 |
| `use_color` | 是 |
| `exception_trace` | 是 |
| `show_locals` | 是，需开启异常追踪 |
| `interactive` | 否 |
| `interactive_on_event` | 否 |
| `logging_path` | 否，仅作为 Tracer 库能力说明 |

## 匹配规则

Tracer 当前按函数名匹配。不同类或作用域中的同名函数会一起被追踪。

## 安全限制

- 调用追踪会重新执行用户代码。
- 独立子进程和超时用于隔离服务进程，不是完整文件/网络沙箱。
- 交互式 Shell 不开放给 Web 请求。
