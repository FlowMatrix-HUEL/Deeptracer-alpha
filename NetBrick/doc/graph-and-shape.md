# 图结构与 Shape

## 图模型

NetBrick 使用有向无环图描述张量流动：

- 多条分支可以从同一输出 fan-out。
- 多个分支可以在合并节点重新汇合。
- 允许多个 Input、多个 Output。
- 禁止自环、循环连接和悬空输入端口。
- 每个节点都必须能从某个 Input 到达。
- 每个节点都必须能到达某个 Output。

## 端口规则

| 节点类型 | 输入端口 | 输出端口 |
| --- | --- | --- |
| Input | 无 | `out`，可连接多个下游 |
| 普通网络层 | `x`，最多一条入线 | `out`，可连接多个下游 |
| Output | `x`，恰好一条入线 | 无 |
| Add / Multiply / Concat | `x`，两条或更多入线 | `out`，可连接多个下游 |
| 条件运算 | `x`，Compare 需要两条同形入线 | `out`，布尔 Tensor 或 ScalarBool |
| 复合/控制容器 | 按状态契约生成多个命名端口 | 按状态契约生成多个命名端口 |

合并节点只有一个输入锚点。用户在画布上把多条连线接到这同一个锚点，后端将其视为该端口上的多个 Tensor 输入。

## 拓扑顺序

后端使用 Kahn 拓扑排序：

1. 从所有 Input 开始。
2. 父节点计算完成后再计算当前节点。
3. 同一父输出变量可以被多个下游直接复用。
4. 合并节点按入线稳定顺序组合所有输入。

## Shape 推演

普通网络层使用纯 Python 规则计算输出 Shape，不创建真实 Tensor。

### Add

- 至少两个输入。
- 所有输入 Shape 必须完全一致。
- 输出 Shape 等于任一输入 Shape。
- 对应代码：`torch.add` / `paddle.add`。

### Multiply

- 至少两个输入。
- 所有输入 Shape 必须完全一致。
- 输出 Shape 等于任一输入 Shape。
- 对应代码：`torch.multiply` / `paddle.multiply`。

### Concat

- 至少两个输入。
- 所有输入 rank 必须一致。
- 除拼接维度外，所有维度必须一致。
- 输出在拼接维度上的大小等于所有输入该维度大小之和。
- PyTorch 参数：`dim`
- Paddle 参数：`axis`

例如：

```text
[1, 16] + [1, 32] --Concat(dim=-1)--> [1, 48]
```

## dtype

- 所有合并输入 dtype 必须一致。
- Embedding 输出为 `float32`。
- Input 目前支持 `float32`、`float64`、`int64` 和 `uint8`。
- 控制谓词使用 `ScalarBool`，循环索引使用 `ScalarInt`。

## 子图与控制流

- 控制区域是独立的局部 DAG。
- Then/Else 必须具有完全相同的输出签名。
- For/While 循环体输出必须匹配状态输入签名。
- 复合资源以固定版本嵌入父图，递归参与校验与 Shape 推演。

## 结构追踪

结构追踪不是运行时 Hook：

- 不创建 Tensor。
- 不调用 PyTorch/Paddle。
- 仅按拓扑顺序复用 Shape 推演结果。
- 合并节点会展示全部输入 Shape。

## 常见错误

| 错误码 | 含义 |
| --- | --- |
| `MISSING_INPUT_PORT` | 普通输入未连接，或合并端口少于两个输入 |
| `DUPLICATE_TARGET_PORT` | 普通节点输入端口接收了多条线 |
| `INVALID_PORT` | 使用了当前 API 不存在的端口 |
| `CYCLE` | 图中存在环 |
| `UNREACHABLE_FROM_INPUT` | 节点无法从 Input 到达 |
| `UNREACHABLE_OUTPUT` | 节点无法到达 Output |
| `SHAPE_MISMATCH` | 当前参数或合并规则不接受输入 Shape |
| `PARAM_TYPE` / `PARAM_RANGE` | 参数类型或范围错误 |
