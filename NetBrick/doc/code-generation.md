# 代码生成

## 生成流程

1. 校验 IR 的结构、端口、参数和 Shape。
2. 对 DAG 进行拓扑排序。
3. 创建 `nn.Module` / `paddle.nn.Layer` 子类。
4. 为普通网络层创建模块属性。
5. 按拓扑顺序生成 `forward`。
6. 为合并节点生成官方函数调用。
7. 根据 Output 节点生成返回张量或元组。
8. 使用 `ast.unparse()` 输出源码。
9. 使用 `compile()` 检查 Python 语法。

复合资源会先生成独立模块类；控制流的谓词、分支和循环体在父类 `forward` 中生成实际 Python 控制语句。

## 框架导入

PyTorch：

```python
import torch
import torch.nn as nn
```

Paddle：

```python
import paddle
import paddle.nn as nn
```

## 并行变量复用

同一节点有多个下游时，只计算一次，变量会被多个下游复用。

```python
out_input = x
out_left = self.layer_left(out_input)
out_right = self.layer_right(out_input)
out_merge = torch.add(out_left, out_right)
```

## 多路合并

### PyTorch

```python
out_merge = torch.add(torch.add(out_a, out_b), out_c)
out_cat = torch.cat([out_a, out_b, out_c], dim=-1)
```

### Paddle

```python
out_merge = paddle.add(paddle.add(out_a, out_b), out_c)
out_cat = paddle.concat([out_a, out_b, out_c], axis=-1)
```

## forward 返回值

- 一个 Output：返回单个 Tensor。
- 多个 Output：返回 Tuple。
- 多个 Input：`forward` 接收多个参数。

## 复合资源

- 每个实际使用的复合实例生成独立命名模块类。
- 内部参数覆盖会写入生成模块的构造值。
- 资源依赖类按依赖顺序写在同一个 Python 文件中。
- 复合模块保留多输入、多输出端口。

## 控制流

- If 生成 `if ...: ... else: ...`。
- For 生成 `for index in range(iterations): ...`。
- While 生成带 `max_iterations` 保护的 `while`。
- 谓词结果通过 `.item()` 转换为 Python bool。

## 演示代码

默认导出会包含：

- 固定随机种子。
- 根据 Input 样本 Shape 创建示例输入。
- 调用一次 `forward`。
- 打印输出 Shape。

演示代码不包含训练步骤。

## 官方 API 一致性

用户界面和生成代码使用当前框架的官方 API：

- 不会创建名为 `NetBrickLinear` 的自定义替代层。
- 不会添加翻译后的中间包装类。
- Paddle 专属参数直接使用官网名称，例如 `bias_attr`、`axis`。
- 只对内部框架中立 IR 做等价映射。

## Python 导入

当前支持可精确映射的 PyTorch 静态导入：

- 单个 `nn.Module` 子类。
- 支持顺序 `forward`、常量 `range` For、简单标量比较 If/While。
- 多个用户 `nn.Module` 类会生成有依赖的复合资源。
- 支持 `nn.Sequential` 展开。
- 不支持任意分支表达式、自定义函数和副作用。
- 导入过程不执行原始 Python。
- 源码不包含样本 Shape 时，由用户手动提供。

## 已知限制

- 生成代码只做语法校验，不导入框架运行。
- 不生成训练循环、数据加载器或优化器执行代码。
- 某些框架 API 差异会通过参数名和类名映射体现。
