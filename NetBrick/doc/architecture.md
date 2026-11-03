# 系统架构

## 总体结构

NetBrick 由 React 前端、FastAPI 后端和本地代码生成器组成：

```text
React Flow 编辑器
  │
  ├─ IR JSON ──> FastAPI 校验 ──> DAG / 端口 / Shape 检查
  │                              │
  │                              ├─> 结构追踪结果
  │                              └─> PyTorch/Paddle AST 代码
  │
  ├─ 浏览器本地 JSON 文件
  ├─ 浏览器 localStorage 中的 Mojo
  └─ .netbrick 课件 ZIP
```

前端不执行张量运算，后端也不导入 PyTorch/Paddle。框架仅作为代码生成目标存在。

## 前端

- React + TypeScript + Vite。
- React Flow 负责节点、端口、连线、多选、缩放和平移。
- Zustand 维护 IR、撤销重做、校验结果、代码和临时追踪结果。
- 当前框架切换只改变官方 API 展示和代码目标，不破坏图结构。

## 后端

| 模块 | 职责 |
| --- | --- |
| `catalog.py` | 算子、参数、PyTorch/Paddle API 名称 |
| `validation.py` | IR 规范化、DAG、端口和连通性检查 |
| `inference.py` | 纯 Python Shape 推演和结构追踪 |
| `codegen.py` | 使用 Python `ast` 生成模型 Python 文件 |
| `importer.py` | 受限 PyTorch AST 导入 |
| `course.py` | `.netbrick` 课件包校验和生成 |
| `app.py` | HTTP 路由和静态前端托管 |

## 框架中立 IR 0.3

IR 0.3 使用统一算子 ID 描述图结构，并增加 `GraphRegion`、控制流契约和复合资源快照。用户界面、Inspector 和生成代码会根据当前框架显示对应官方名称：

- PyTorch：`torch.nn.Linear`、`torch.add`
- Paddle：`paddle.nn.Linear`、`paddle.add`

0.2 工程在加载时迁移到 0.3。复合资源版本固定嵌入父 IR，旧资源不会随模块库升级而变化。

## 核心处理顺序

1. 前端编辑 IR 并调用图校验接口。
2. 后端补全默认参数、检查端口和构建拓扑顺序。
3. Shape 服务按拓扑顺序计算每个节点的输入、输出 Shape。
4. 结构追踪返回路径事件。
5. 代码生成按同一拓扑顺序构造 Python AST。
6. 后端使用 `compile()` 验证生成源码语法。

## 项目结构

```text
backend/           FastAPI、IR、校验、推演、代码生成
frontend/src/      React 页面、React Flow、状态和样式
frontend/dist/     生产构建产物
tests/             后端单元与回归测试
doc/               详细能力文档
promot.md          原始项目设计说明
```
