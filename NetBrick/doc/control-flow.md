# 控制流

NetBrick 支持三种结构化控制容器。它们只描述模型前向结构，不执行真实 Tensor。

## 状态契约

控制容器使用命名多端口状态包：

- 输入和输出端口均有名称、dtype、Shape。
- Then/Else 分支必须具有一致的输出端口签名。
- For/While 循环体输出必须与状态输入签名一致。
- 控制容器可以修改状态 Shape，但循环体必须保持签名稳定。
- 控制区域可以继续嵌套复合模块和其他控制容器。

默认创建一个 Tensor 状态端口 `state`。

## If

If 容器包含三个区域：

1. `predicate`：读取状态，输出一个 `ScalarBool`。
2. `then`：状态输入和输出。
3. `else`：必须与 then 输出签名完全一致。

生成代码包含真实 Python `if/else`：

```python
if bool(condition.item()):
    state = then_branch(state)
else:
    state = else_branch(state)
```

## For

For 使用有界整数参数 `iterations`：

```python
for index in range(iterations):
    state = body(state, index)
```

- 迭代次数不会从 Tensor Shape 推断。
- 谓词不是必需区域。
- 循环体可声明可选的 `index: ScalarInt` 输入。
- 循环体输出必须匹配容器状态签名。

## While

While 包含：

- `predicate` 子图。
- `body` 子图。
- `max_iterations` 保护参数。

```python
index = 0
while index < max_iterations:
    if not predicate(state, index):
        break
    state = body(state, index)
    index += 1
```

## 条件运算

谓词可以使用：

- `logic.Compare`：`gt`、`lt`、`ge`、`le`、`eq`、`ne`
- `logic.All`：将布尔张量归约为 ScalarBool

条件表达式必须能从状态端口推导，不能从控制区域外直接传入未声明布尔边。

## 编辑

双击控制容器进入第一个逻辑区域：

- If：默认为谓词区域，可通过面包屑切换谓词、Then、Else。
- For：进入循环体。
- While：可在谓词和循环体之间切换。

控制容器的 Inspector 可以增加输入/输出状态端口；对应区域会同步增加边界节点。新增边界仍需手工连接到区域中的数据流。

## 限制

- 控制流只生成结构代码，不运行 Tensor 或训练。
- While 必须设置最大次数。
- 累计嵌套复合资源和控制区域最多 3 层。
- Python 导入只接受可转换为这些结构的有限 AST 子集。
