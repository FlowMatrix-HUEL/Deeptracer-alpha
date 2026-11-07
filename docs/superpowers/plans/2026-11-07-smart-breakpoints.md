# 智能断点（Smart Breakpoints）实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Python、Turtle、NetBrick 三条已有时间线上自动标注 3–7 个关键瞬间，用户点击即可跳转查看；规则检测同步完成，LLM 只做异步文案增强。

**Architecture:** 新增 `deeptracer/breakpoints/` 包：Pydantic `Moment` 协议、三个世界的纯规则检测器、排序器、可选 LLM 增强器。检测器挂到现有 trace/compile 服务返回体；前端复用现有步进/Trace 面板渲染标记，不新建调试器。

**Tech Stack:** Python 3.10+、FastAPI、Pydantic v2、pytest、原生 JS（主工作台/Turtle）、React + Zustand（NetBrick）。

**Spec:** `docs/superpowers/specs/2026-11-07-smart-breakpoints-design.md`

## Global Constraints

- 检测器单次遍历、O(n)、硬预算 25ms；超过预算返回已找到候选。
- 输入上限 `MAX_MOMENT_STEPS = 5000`；超过则采样首末/错误/转向。
- 默认最多返回 7 个 moments；无证据不返回。
- Agent 关闭/模型未配置/LLM 超时：规则 moments 仍完整可用。
- LLM 只改 `label / why / question / importance`，不得修改 `step_index / line / node_id / evidence`。
- 不修改 `vendor/pathrise-python-tutor/`。
- 不修改 `NetBrick/backend/` 的既有协议。
- 所有新代码使用 `from __future__ import annotations`，遵循现有文件风格。

## Review Focus

- Python Tutor trace 在循环零次执行时没有循环体行：检测器不能崩溃，也不能把"没有迭代"误判为"最后一次迭代"。
- Turtle 在快速连续画图时，旧 compile 的 moments 不能覆盖新画布：前端必须用 `compileRequest` 序号丢弃过期结果。
- Turtle 闭合检测在起点附近来回移动时不能误报：要求至少 3 次移动且距离容差 ≤ 1e-6。
- NetBrick 的 `input_shape` 可能为 `None` 或空列表：shape 变化检测必须跳过无效 shape。
- LLM 返回的 moment id 不在候选集合时必须丢弃，不能污染 UI。

---

### Task 1: Moment 协议与模型

**Files:**
- Create: `deeptracer/breakpoints/__init__.py`
- Create: `deeptracer/breakpoints/models.py`
- Test: `tests/test_breakpoints.py`

**Interfaces:**
- Produces: `Moment`, `MomentEvidence`, `MomentList`（Pydantic v2 模型），字段与设计文档一致；`MomentList(moments=[...])` 可直接 `.model_dump()`。

- [ ] **Step 1: 写失败测试**

```python
from deeptracer.breakpoints.models import Moment, MomentEvidence


def test_moment_round_trip():
    moment = Moment(
        id="py-loop-last",
        world="python",
        kind="boundary",
        concepts=["repetition", "boundary"],
        severity="info",
        importance=0.9,
        step_index=42,
        line=7,
        source_ref={"fileId": "editor", "sourceHash": "abc", "startLine": 7, "endLine": 7},
        label="最后一次迭代",
        why="循环体最后一次执行",
        evidence=[MomentEvidence(type="trace_step", step_index=42, line=7)],
    )
    payload = moment.model_dump()
    assert payload["id"] == "py-loop-last"
    assert payload["evidence"][0]["step_index"] == 42
    assert Moment.model_validate(payload).world == "python"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_breakpoints.py::test_moment_round_trip -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'deeptracer.breakpoints'`

- [ ] **Step 3: 实现模型**

在 `deeptracer/breakpoints/models.py` 定义 `MomentEvidence`、`Moment`、`MomentList`。`Moment.id` 必填，`world`/`kind`/`severity` 用 `Literal`，`concepts`/`evidence`/`tags` 默认空列表，`importance`/`confidence` 为 `float`。

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_breakpoints.py::test_moment_round_trip -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add deeptracer/breakpoints/__init__.py deeptracer/breakpoints/models.py tests/test_breakpoints.py
git commit -m "feat(breakpoints): add moment protocol"
```

---

### Task 2: Python 检测器

**Files:**
- Create: `deeptracer/breakpoints/python.py`
- Modify: `tests/test_breakpoints.py`

**Interfaces:**
- Produces: `detect_python_moments(trace: list[dict], code: str, *, analysis: dict | None = None) -> list[Moment]`
- Consumes: Task 1 的 `Moment` / `MomentEvidence`。

- [ ] **Step 1: 写失败测试（循环边界 + off-by-one）**

```python
from deeptracer.breakpoints.python import detect_python_moments

CODE = """\
total = 0
for i in range(5):
    total += i
print(total)
"""

TRACE = [
    {"line": 1, "event": "step_line", "ordered_globals": []},
    {"line": 2, "event": "step_line", "ordered_globals": [{"name": "total", "value": "0"}]},
    {"line": 3, "event": "step_line", "ordered_globals": [{"name": "i", "value": "0"}]},
    {"line": 2, "event": "step_line", "ordered_globals": [{"name": "i", "value": "1"}]},
    {"line": 3, "event": "step_line", "ordered_globals": [{"name": "i", "value": "4"}]},
    {"line": 4, "event": "step_line", "ordered_globals": [{"name": "i", "value": "5"}]},
]
```

断言返回的 moments：
- 存在 `kind == "boundary"` 且 `step_index == 2`（第一次迭代）；
- 存在 `kind == "boundary"` 且 `step_index == 4`（最后一次迭代）；
- 存在 moments 中 `line == 4` 且 `actual["i"] == 5`（循环退出值）。

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_breakpoints.py -k python_loop -v`
Expected: FAIL with `ModuleNotFoundError` / `ImportError`

- [ ] **Step 3: 实现最小检测器**

`detect_python_moments`：
- 遍历 trace，按 `line` 分组；同一行出现 ≥2 次视为循环体候选。
- 对每个重复行组取第一次和最后一次出现，生成 `first_iteration` / `last_iteration` moments。
- 若循环体行之后出现"不同行 + 变量值是最后一轮值 + 1"（或全局变量变化），生成 `loop_exit` moment。
- 变量 diff：相邻步 `ordered_globals` 变化，生成 `state_change` moment（去重，最多 3 个）。
- 异常：`event` 含 `exception` 生成 `exception` moment。
- 所有 moment 附 `evidence`，`importance` 按类型赋值。

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_breakpoints.py -k python_loop -v`
Expected: PASS

- [ ] **Step 5: 补零次循环与异常测试并实现**

新增测试：
```python
def test_python_zero_iteration_does_not_crash():
    code = "for i in range(0):\n    print(i)\nprint('done')\n"
    trace = [{"line": 3, "event": "step_line", "ordered_globals": []}]
    moments = detect_python_moments(trace, code)
    assert all(m.kind != "exception" for m in moments)


def test_python_exception_is_marked():
    code = "x = 1 / 0\n"
    trace = [{"line": 1, "event": "exception", "ordered_globals": []}]
    moments = detect_python_moments(trace, code)
    assert any(m.kind == "exception" for m in moments)
```
运行并补齐实现。

- [ ] **Step 6: 提交**

```bash
git add deeptracer/breakpoints/python.py tests/test_breakpoints.py
git commit -m "feat(breakpoints): detect python loop and exception moments"
```

---

### Task 3: Turtle 检测器

**Files:**
- Create: `deeptracer/breakpoints/turtle.py`
- Modify: `tests/test_breakpoints.py`

**Interfaces:**
- Produces: `detect_turtle_moments(result: dict) -> list[Moment]`
- Consumes: `compile_turtle_source` 的返回 dict（`steps`、`commands`、`programFeatures`、`error`）。

- [ ] **Step 1: 写失败测试（闭合点 + 错误）**

```python
from deeptracer.breakpoints.turtle import detect_turtle_moments


def test_turtle_closure_is_marked():
    result = {
        "steps": [
            {"index": 0, "line": 1, "turtle": {"x": 0, "y": 0, "heading": 0}, "callStack": []},
            {"index": 1, "line": 2, "turtle": {"x": 100, "y": 0, "heading": 0}, "callStack": []},
            {"index": 2, "line": 3, "turtle": {"x": 100, "y": 100, "heading": 90}, "callStack": []},
            {"index": 3, "line": 4, "turtle": {"x": 0, "y": 100, "heading": 180}, "callStack": []},
            {"index": 4, "line": 5, "turtle": {"x": 0, "y": 0, "heading": 270}, "callStack": []},
        ],
        "commands": [],
        "programFeatures": {"loopIterations": [], "loops": 0},
        "error": None,
    }
    moments = detect_turtle_moments(result)
    assert any(m.kind == "closure" for m in moments)
    assert any(m.step_index == 4 for m in moments)


def test_turtle_error_is_marked():
    result = {
        "steps": [{"index": 0, "line": 1, "turtle": {"x": 0, "y": 0, "heading": 0}, "callStack": []}],
        "commands": [],
        "programFeatures": {},
        "error": {"line": 1, "category": "runtime", "title": "boom"},
    }
    moments = detect_turtle_moments(result)
    assert any(m.kind == "exception" and m.line == 1 for m in moments)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_breakpoints.py -k turtle -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: 实现检测器**

实现：
- 首步/末步。
- 闭合：从起点 (0,0) 出发，至少 3 次移动后，位置距离起点 ≤ 1e-6。
- 转向：相邻步 `turtle.heading` 变化 ≥ 1°，取首次/最大转向。
- 重复行：同一 `line` 出现 ≥2 次，取首末。
- 画笔变化：`penDown/color/size` 变化。
- 错误：`error.line` 对应步。
- `programFeatures.loopIterations` 与实际重复次数不一致时生成 `boundary` moment。

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_breakpoints.py -k turtle -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add deeptracer/breakpoints/turtle.py tests/test_breakpoints.py
git commit -m "feat(breakpoints): detect turtle closure and error moments"
```

---

### Task 4: 排序器与上限

**Files:**
- Create: `deeptracer/breakpoints/ranking.py`
- Modify: `tests/test_breakpoints.py`

**Interfaces:**
- Produces: `rank_moments(moments: list[Moment], limit: int = 7) -> list[Moment]`
- 规则：severity 权重（error=3, warning=2, info=1）+ importance；同 `kind + line` 去重；按分数降序；截断 `limit`。

- [ ] **Step 1: 写失败测试**

```python
from deeptracer.breakpoints.models import Moment
from deeptracer.breakpoints.ranking import rank_moments


def test_rank_moments_limits_and_prioritizes_errors():
    moments = [
        Moment(id=f"m{i}", world="python", kind="state_change", concepts=[], severity="info", importance=0.1, label="x", why="x")
        for i in range(10)
    ]
    moments.append(
        Moment(id="err", world="python", kind="exception", concepts=[], severity="error", importance=0.1, label="e", why="e")
    )
    ranked = rank_moments(moments, limit=3)
    assert len(ranked) == 3
    assert ranked[0].id == "err"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_breakpoints.py -k rank -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: 实现排序器并运行测试**

Run: `pytest tests/test_breakpoints.py -k rank -v`
Expected: PASS

- [ ] **Step 4: 提交**

```bash
git add deeptracer/breakpoints/ranking.py tests/test_breakpoints.py
git commit -m "feat(breakpoints): rank and cap moments"
```

---

### Task 5: 接入 Python/Turtle/Tracer 响应

**Files:**
- Modify: `deeptracer/server/pytutor_service.py`
- Modify: `deeptracer/server/turtle_service.py`
- Modify: `deeptracer/server/tracer_service.py`
- Modify: `tests/test_breakpoints.py`

**Interfaces:**
- Consumes: Task 2/3/4 的 `detect_python_moments`、`detect_turtle_moments`、`rank_moments`。
- Produces: 三个服务的返回 dict 增加 `"moments": list[dict]`；字段为 `Moment.model_dump()`。

- [ ] **Step 1: 写 API 级测试**

```python
from deeptracer.server.turtle_service import compile_turtle_source


def test_turtle_compile_returns_moments():
    result = compile_turtle_source("forward(100)\nright(90)\nforward(100)\n")
    assert "moments" in result
    assert isinstance(result["moments"], list)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_breakpoints.py::test_turtle_compile_returns_moments -v`
Expected: FAIL with `KeyError: 'moments'`

- [ ] **Step 3: 接入三个服务**

- `compile_turtle_source`：在返回 payload 前 `payload["moments"] = [m.model_dump() for m in rank_moments(detect_turtle_moments(payload))]`。
- `execute_python_tutor_trace`：在返回 result 前用 `user_script` + `result.get("trace", [])` 检测并追加 `moments`。
- `execute_tracer_trace`：在返回前基于 `traceTree` 检测错误/热点节点并追加 `moments`（Tracer 专用小检测器可先内联在 `tracer_service.py` 或新增 `python.py` 的 `detect_tracer_moments`）。

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_breakpoints.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add deeptracer/server/pytutor_service.py deeptracer/server/turtle_service.py deeptracer/server/tracer_service.py tests/test_breakpoints.py
git commit -m "feat(breakpoints): attach moments to python and turtle traces"
```

---

### Task 6: NetBrick 检测器与 `/api/breakpoints`

**Files:**
- Create: `deeptracer/breakpoints/netbrick.py`
- Modify: `deeptracer/server/app.py`
- Modify: `tests/test_breakpoints.py`

**Interfaces:**
- Produces: `detect_netbrick_moments(trace: dict) -> list[Moment]`；`POST /api/breakpoints` 接受 `{"world": "netbrick", "trace": {...}}`，返回 `{"moments": [...]}`。
- Consumes: NetBrick `TraceResponse`（`steps: list[TraceStep]`, `diagnostics`）。

- [ ] **Step 1: 写失败测试**

```python
def test_netbrick_shape_change_is_marked():
    trace = {
        "steps": [
            {"index": 0, "node_id": "input", "label": "Input", "output_shape": [1, 784]},
            {"index": 1, "node_id": "linear", "label": "nn.Linear", "input_shape": [1, 784], "output_shape": [1, 128]},
        ],
        "diagnostics": [],
    }
    from deeptracer.breakpoints.netbrick import detect_netbrick_moments
    moments = detect_netbrick_moments(trace)
    assert any(m.kind == "shape_change" and m.node_id == "linear" for m in moments)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_breakpoints.py -k netbrick -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: 实现检测器与路由**

- shape 变化：input_shape 与 output_shape 均有效且不相等。
- merge：`input_shapes` 长度 ≥2。
- control：label 以 `control.` 开头。
- composite：label 含复合模块 / node op `composite.instance`。
- diagnostic：`diagnostics` 中带 `node_id`。
- 路由 `POST /api/breakpoints`：校验 `world == "netbrick"`，调用检测器，返回 `{"moments": [...]}`。

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_breakpoints.py -k netbrick -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add deeptracer/breakpoints/netbrick.py deeptracer/server/app.py tests/test_breakpoints.py
git commit -m "feat(breakpoints): detect netbrick shape moments"
```

---

### Task 7: LLM 增强端点

**Files:**
- Create: `deeptracer/breakpoints/enrich.py`
- Modify: `deeptracer/server/app.py`
- Modify: `tests/test_breakpoints.py`

**Interfaces:**
- Produces: `enrich_moments(moments: list[dict], *, code: str, world: str) -> list[dict]`
- Endpoint: `POST /api/breakpoints/enrich`，入参 `{"world", "code", "moments"}`，出参 `{"moments": [...], "enriched": true|false}`。
- 约束：只允许改 `label / why / question / importance`；id 必须匹配；失败回退原列表。

- [ ] **Step 1: 写回退测试（不依赖真实模型）**

```python
def test_enrich_falls_back_when_model_missing(monkeypatch):
    from deeptracer.breakpoints import enrich
    monkeypatch.setattr(enrich, "get_chat_model", lambda optional=False: None)
    moments = [{"id": "m1", "label": "old", "why": "old", "question": None}]
    result = enrich.enrich_moments(moments, code="x = 1", world="python")
    assert result[0]["label"] == "old"
    assert result[0]["enriched"] is False
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_breakpoints.py -k enrich -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: 实现增强器与路由**

- 用 `get_chat_model(optional=True)`；`None` 直接返回原列表。
- prompt：代码 + 候选 moments 的 `id/kind/line/step_index/evidence`；要求返回 JSON 列表。
- 解析后按 id 合并；未知 id 丢弃；异常/超时返回原列表。
- 缓存：进程内 `dict`，key `(world, code_hash, tuple(ids), model_name)`。

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_breakpoints.py -k enrich -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add deeptracer/breakpoints/enrich.py deeptracer/server/app.py tests/test_breakpoints.py
git commit -m "feat(breakpoints): add optional llm enrichment"
```

---

### Task 8: 主工作台 moment rail

**Files:**
- Modify: `deeptracer/static/app.js`
- Modify: `deeptracer/static/app.css`
- Modify: `deeptracer/templates/index.html`

**Interfaces:**
- Consumes: `/api/tutor/trace` 返回的 `moments`。
- Produces: `renderMomentRail(moments)`、`jumpToTutorStep(index)`、`enrichMoments(moments)`。

- [ ] **Step 1:** 在 Tutor 面板增加 `#momentRail` 容器和"智能断点"开关。
- [ ] **Step 2:** `loadTutorVisualization` 保存 `payload.moments`，渲染 rail；点击卡片调用 `currentTutorVisualizer.renderStep(index)` 或设置 `curInstr`。
- [ ] **Step 3:** "为什么"展开证据；"下一个瞬间"循环。
- [ ] **Step 4:** trace 渲染完成后 debounce 800ms 调用 `/api/breakpoints/enrich`，用请求 id 丢弃过期结果，仅替换文案。
- [ ] **Step 5:** 手动验证：跑一个循环，确认标记出现、跳转正确、关闭开关后恢复原状。

---

### Task 9: Turtle 标记

**Files:**
- Modify: `deeptracer/static/turtle.js`
- Modify: `deeptracer/static/turtle.css`

**Interfaces:**
- Consumes: `/api/turtle/compile` 返回的 `moments`。
- Produces: `renderMomentMarkers(moments)`、点击调用 `renderExecutionStep(index)`。

- [ ] **Step 1:** `applyCompileResult` 保存 `result.moments`，在步进条/行号上渲染 `has-moment` 标记。
- [ ] **Step 2:** 点击标记跳转到对应步；与现有 `state.breakpoints` 视觉区分。
- [ ] **Step 3:** debounce 800ms 调用 enrich；`compileRequest` 序号变化时取消。
- [ ] **Step 4:** 手动验证：画五边形，确认闭合点被标记；快速画图不闪烁。

---

### Task 10: NetBrick 标记

**Files:**
- Modify: `NetBrick/frontend/src/types.ts`
- Modify: `NetBrick/frontend/src/store.ts`
- Modify: `NetBrick/frontend/src/components/BottomPanel.tsx`

**Interfaces:**
- Consumes: `POST /api/breakpoints` 返回的 `moments`。
- Produces: `runMomentDetection()` store action；trace step badge。

- [ ] **Step 1:** `types.ts` 加 `Moment`；`store.ts` 加 `moments` 状态与 `runMomentDetection()`。
- [ ] **Step 2:** `runTracePreview()` 成功后调用 `/api/breakpoints`，保存 moments。
- [ ] **Step 3:** `BottomPanel` trace step 渲染 badge；点击沿用 `setSelectedNode`。
- [ ] **Step 4:** `npm run build` 通过；手动验证 MNIST MLP 的 shape 变化标记。

---

### Task 11: 导览与跨世界同概念

**Files:**
- Modify: `deeptracer/static/app.js`
- Modify: `deeptracer/static/turtle.js`
- Modify: `NetBrick/frontend/src/components/BottomPanel.tsx`

**Interfaces:**
- Consumes: moments 的 `concepts` 字段。
- Produces: "下一个瞬间"导览；同概念 chip（只跳转，不自动生成）。

- [ ] **Step 1:** 三个前端各自实现"下一个瞬间"按钮，循环当前 moments。
- [ ] **Step 2:** 当同一 session 中存在相同 `concepts` 时，显示"同一概念在 Turtle/Python/NetBrick"chip。
- [ ] **Step 3:** 手动验证 demo 脚本：Python 循环 → Turtle 闭合 → NetBrick shape。

---

### Task 12: 性能与回归验证

**Files:**
- Modify: `tests/test_breakpoints.py`

- [ ] **Step 1:** 生成 5000 步合成 trace，断言 `detect_python_moments` < 50ms。
- [ ] **Step 2:** 断言 `rank_moments` 最多 7 个。
- [ ] **Step 3:** 关闭 Agent（`DEEPTRACER_AGENTS_ENABLED=0`）跑 API 测试，确认 moments 仍返回。
- [ ] **Step 4:** 跑全量 `pytest tests/ -q`，确认无回归。
- [ ] **Step 5:** 提交。

```bash
git add tests/test_breakpoints.py
git commit -m "test(breakpoints): add performance and fallback coverage"
```
