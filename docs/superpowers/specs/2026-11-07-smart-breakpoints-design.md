# 智能断点（Smart Breakpoints）设计

## 意图与为什么

DeepTracer 已经有三个可执行工作台：Turtle（行为可视）、Python（执行可视）、NetBrick（结构可视）。每个工作台都有自己的时间线，但用户必须自己知道"在哪里停"——这对初学者是最大的门槛。

智能断点要做的不是"更强的调试器"，而是把专家的"知道哪里值得停"产品化：

> Agent 在三条时间线上自动标注 3–7 个关键瞬间；用户点击标注就能跳到对应状态，看到证据、解释和可选预测问题。

它连接三个工作台的方式不是导航或课程包，而是同一套 **moment（关键瞬间）语言**：边界、状态变化、偏离、失败、结构变化。同一个概念可以在三个世界里以不同形态出现。

## 目标

- 三个工作台都能在已有执行/Trace 结果上自动产出 moments，无需用户手动设断点。
- 每个 moment 可解释（证据）、可跳转（stepIndex / line / nodeId）、可验证（规则检测，不靠模型猜）。
- 第一帧只用规则检测，额外开销 <5ms/1000 步；LLM 只做异步文案增强，不阻塞任何交互。
- Agent 关闭、模型未配置、LLM 超时，规则 moments 仍然完整可用。
- 现有手动断点、步进、Trace、结构追踪行为不变。

## 非目标

- 不替换现有手动断点。
- 不自动修代码。
- v1 不做跨世界自动生成实验；只做同概念跳转/提示。
- 不做学习画像、课堂管理、账号系统。
- 不把 Python Tutor trace 全量传给 LLM。

## 约束

- 本地优先；检测在本地完成，只有用户配置了模型才可能发生网络请求。
- 检测必须 O(n)、单次遍历、硬预算 25ms；超过预算返回已找到的候选。
- LLM 永远不在第一帧关键路径上。
- 不修改 Python Tutor vendor 源码。
- 不修改 NetBrick backend 的既有协议；NetBrick 前端通过主应用接口获取 moments。

## 方案选择

考虑过三种：

1. **纯 LLM 检测**：直接把 trace 交给模型判断哪里重要。问题是慢、贵、不可验证，且会把"哪里值得停"变成幻觉。
2. **纯规则检测**：快、可验证，但文案生硬，难以解释"为什么值得停"。
3. **规则检测 + LLM 增强（选中）**：规则负责事实与位置，LLM 负责文案、排序和预测问题。检测可离线，增强可关闭。满足"不卡顿"和"Agent 驱动"两个目标。

## 数据模型

```python
class MomentEvidence(BaseModel):
    type: Literal["trace_step", "source_line", "variable", "shape",
                  "diagnostic", "command", "call", "profile"]
    step_index: int | None = None
    node_id: str | None = None
    line: int | None = None
    field: str | None = None
    value: Any | None = None
    source_ref: dict | None = None

class Moment(BaseModel):
    id: str
    world: Literal["python", "turtle", "netbrick"]
    kind: Literal["boundary", "state_change", "call", "exception",
                  "branch", "hotspot", "shape_change", "merge",
                  "control_flow", "closure", "style", "diagnostic"]
    concepts: list[str]
    severity: Literal["info", "warning", "error"]
    importance: float
    step_index: int | None = None
    node_id: str | None = None
    line: int | None = None
    source_ref: dict | None = None
    label: str
    why: str
    question: str | None = None
    evidence: list[MomentEvidence] = []
    expected: Any | None = None
    actual: Any | None = None
    tags: list[str] = []
    confidence: float = 1.0
    enriched: bool = False
```

## 检测器

### Python（Python Tutor trace + Tracer traceTree）

- 循环首次/最后一次迭代：同一行重复出现，取首末步。
- 循环退出后的变量值：最后一次迭代值 vs 退出值（off-by-one）。
- 零次迭代：AST 有循环，但循环体行从未出现。
- 变量首次出现 / 值变化：相邻步 `ordered_globals` diff。
- 函数进入/返回/递归加深：`stack_to_render` 深度变化。
- 异常点：`event` 含 exception 或 traceback。
- 分支首次进入：AST `If` + trace 行首次出现。
- 热点行：analysis performance / suggestions 的 sourceRef。
- Tracer 错误节点 / 高耗时节点。

### Turtle（steps + commands + programFeatures）

- 首步/末步。
- 转向点：相邻步 `turtle.heading` 变化。
- 闭合点：位置回到起点附近且移动 ≥3 次。
- 循环首/末次迭代：同一 `line` 重复出现。
- 画笔状态变化：penDown/color/size/filling。
- 错误步：`result.error.line`。
- 少一条边：`programFeatures.loopIterations` 与实际重复次数不一致。

### NetBrick（TraceResponse.steps + diagnostics）

- Shape 变化节点：input_shape != output_shape。
- rank / 空间维变化。
- 合并节点：多输入 Add/Multiply/Concat。
- 控制流进出：`control.*`。
- 复合模块边界：`composite.instance`。
- 输入/输出边界。
- 诊断错误/警告。

统一排序：severity + 概念相关度 + 证据强度 + 新颖度；默认最多 7 个，相邻同类合并。

## 延迟模型

| 阶段 | 触发 | 预算 | 阻塞 UI |
|---|---|---|---|
| 规则检测 | 现有编译/Trace 响应内 | <5ms/1000 步，硬上限 25ms | 否 |
| 第一帧渲染 | 响应到达 | <5ms | 否 |
| LLM 增强 | 用户停止操作 800ms 后 | 1–3s，超时 3s | 否，后台 |
| 文案替换 | 增强返回 | <10ms，原地替换 | 否 |

LLM 启动规则：已有规则 moments、用户停止操作 ≥800ms、`sourceHash + momentIds` 变化、模型已配置。一次批量调用；取消过期请求；缓存命中不调用；失败回退规则文案。

## 接入点

- `deeptracer/server/pytutor_service.py`：`execute_python_tutor_trace` 返回前追加 `moments`。
- `deeptracer/server/tracer_service.py`：`execute_tracer_trace` 返回前追加 `moments`。
- `deeptracer/server/turtle_service.py`：`compile_turtle_source` 返回前追加 `moments`。
- `deeptracer/server/app.py`：新增 `POST /api/breakpoints`（NetBrick 前端调用）和 `POST /api/breakpoints/enrich`（LLM 增强）。
- NetBrick backend 不改；NetBrick 前端在 `runTracePreview()` 后调用主应用接口。

## 前端

- 主工作台：Python Tutor 面板旁新增 moment rail；点击调用 `jumpToTutorStep(index)`；源码 gutter 标记；"为什么"展开证据；"下一个瞬间"。
- Turtle：复用 `state.breakpoints` 的 UI 位置，新增 `has-moment` 样式；点击调用 `renderExecutionStep(index)`。
- NetBrick：`BottomPanel` 的 trace step 加 badge；点击 `setSelectedNode(node_id)`。
- 统一视觉：红=失败/异常，黄=值得看，蓝=信息/结构；固定高度，稳定 key，避免布局抖动。
- 开关："智能断点" on/off；关闭后完全回到现有行为。

## 测试

- 单测检测器：Python 5 次循环/零次循环/异常/函数/递归；Turtle 正方形/五边形/少一条边/错误；NetBrick MNIST MLP/CNN/merge/diagnostic。
- 排序与上限：最多 7 个；无证据不返回。
- API：三个端点返回 `moments` 且 schema 合法。
- 回退：Agent 关闭时仅规则标签。
- 性能：1000 步 trace < 50ms（目标 <10ms）。

## 风险与对策

- 标记过多：先高精度、默认 7 个、可关闭。
- Trace 字段耦合：adapter + 只依赖稳定字段。
- LLM 乱说：只改文案不改证据；id 校验；冲突回退。
- LLM 延迟：异步、debounce、取消、缓存、超时。
- NetBrick 模块污染：不改 backend。
- 隐私：本地检测；只有配置模型才发请求。

## 留给实现者

- 具体检测阈值（闭合容差、热点阈值、最大步数）可在实现时按样例调优。
- LLM prompt 的具体措辞可在实现时迭代；但必须遵守"只改文案、不改证据"的约束。
- 跨世界同概念链接 v1 只做标签与跳转，不做自动生成。
