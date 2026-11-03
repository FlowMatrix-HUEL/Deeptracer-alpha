# HTTP API

服务默认地址为 `http://127.0.0.1:8000`，同时托管生产前端。

## 健康检查

### `GET /api/v1/health`

返回服务版本、Python 版本和运行时能力。当前 `framework_runtime` 固定为 `disabled`。

## 算子目录

### `GET /api/v1/catalog`

返回所有模块元数据：

- 算子 ID 和分类。
- 当前框架官方 API 名称。
- 参数字段、类型、默认值和范围。
- 输入模式：`single` 或 `merge`。

## 示例

### `GET /api/v1/samples`

返回示例列表。

### `GET /api/v1/samples/{sample_id}`

返回完整 IR，例如：

- `mnist-mlp`
- `simple-cnn`
- `simple-unet`
- `multi-chain`
- `parallel-add`

## 图校验

### `POST /api/v1/graphs/validate`

请求体为完整 `IRDocument`，返回：

- 是否有效。
- 规范化后的 IR。
- 节点端口和 Shape。
- 诊断列表。
- Output 数据流数量。

### `POST /api/v1/graphs/infer/static`

当前与 `/validate` 使用同一套结构 Shape 推演。

## 结构追踪

### `POST /api/v1/graphs/trace-preview`

请求：

```json
{
  "ir": {},
  "seed": 42
}
```

返回拓扑顺序步骤，每步包含节点、输入 Shape、输出 Shape 和 dtype。该接口不执行真实张量。

## 代码生成

### `POST /api/v1/graphs/codegen`

请求：

```json
{
  "ir": {},
  "framework": "pytorch",
  "include_demo": true
}
```

`framework` 支持 `pytorch` 或 `paddle`。返回文件名、源码、语法状态和警告。

## 复合资源

### `POST /api/v1/composites/validate`

### `POST /api/v1/composites/publish`

两个路由都接收：

```json
{
  "resource_id": "teacher-mlp-block",
  "name": "MLP Block",
  "revision": 1,
  "description": "",
  "author": "",
  "ir": {}
}
```

发布接口会校验当前网络、自动生成接口、递归收集参数和内嵌依赖。资源文件与 IndexedDB 管理由前端完成，服务端不持久化资源。

## Python 导入

### `POST /api/v1/graphs/import/pytorch`

请求包含 Python 源码、文件名、输入 Shape 和 dtype。解析过程只做 AST 分析，不执行源码。

## 课件

### `POST /api/v1/course-packages/validate`

接收 Base64 编码的 `.netbrick` 内容，返回验证结果和解析后的课件。

### `POST /api/v1/course-packages/export`

接收课件对象，返回 ZIP 文件。

## 本地部署

- 默认只绑定 `127.0.0.1`。
- 不需要账号或数据库。
- 不提供公共云服务。
- 前端生产构建由 FastAPI 的 `/` 静态路由提供。
