# API 文档

本页统一记录 DeepTracer 原生 API 和内置库 API。运行服务后，也可以通过顶部“API 文档 ↗”跳转到独立页面 `/api-docs`。

`/api-docs` 使用文档树导航：

- “DeepTracer 主库”下列出所有原生接口。
- “Tracer 内置库”下列出装饰器和上下文管理器。
- 点击条目只在当前页面右侧更新内容，不滚到锚点，也不创建新的路由。
- 主库分组、Tracer 分组以及每个 API 页内的“请求”“响应”等子标题均支持折叠。
- 每个原生 API 页包含只读示范代码和“运行示范”按钮，只有用户点击后才发送请求并显示结果。

## DeepTracer 原生 API

所有接口默认监听 `127.0.0.1:8000`。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/api/run` | 运行代码并返回 stdout、stderr、异常和耗时 |
| `POST` | `/api/analyze` | 执行 AST、性能、内存和可选 Agent 分析 |
| `POST` | `/api/tracer/trace` | 追踪选中函数 |
| `POST` | `/api/tutor/trace` | 生成 Python Tutor 执行轨迹 |
| `GET` | `/api/tutor/status` | 检查 Python Tutor 是否可用 |
| `POST` | `/api/chat/stream` | 基于当前代码进行流式答疑 |

### 运行代码

```http
POST /api/run
Content-Type: application/json

{
  "code": "print('hello')"
}
```

返回：

```json
{
  "durationMs": 1.2,
  "stdout": "hello\n",
  "stderr": "",
  "runtimeError": null,
  "traceback": "",
  "exitCode": 0
}
```

### 函数调用追踪

```http
POST /api/tracer/trace
Content-Type: application/json

{
  "code": "def f(x): ...",
  "functions": ["f"],
  "options": {
    "timeTrace": true,
    "useColor": true,
    "exceptionTrace": false,
    "showLocals": false
  }
}
```

## Tracer 库 API

```python
from deeptracer import Tracer, tracer

# 或
from deeptracer.tracing import Tracer, tracer
```

完整参数说明见 [Tracer API](./tracer-api.md)。

## 扩展约定

- 原生接口统一使用 `/api/*`。
- 文档页面使用独立 URL 跳转，不使用工作台内部滑动面板。
- 新增 API 必须登记到本页和 `/api-docs`。
- 执行用户代码的接口必须使用独立子进程并进行超时控制。
