# PyTorch 2.6 API

NetBrick 使用 PyTorch 2.6.0 作为模型层 API 基线。

静态注册表位于：

```text
backend/data/pytorch_2_6_registry.json
```

应用运行时不导入 PyTorch，该 JSON 已包含类名、参数表单、输入输出端口和可选端口信息。

## 覆盖范围

注册表覆盖 `torch.nn` 中的公开模型构建类，包括：

- Conv、Pool、Adaptive Pool、Unpool、Fractional Pool
- BatchNorm、InstanceNorm、LayerNorm、GroupNorm、RMSNorm
- Dropout 和 AlphaDropout 系列
- Activation 与 Shrink 系列
- Padding 系列
- Embedding、EmbeddingBag
- RNN、GRU、LSTM 及 Cell
- MultiheadAttention
- Transformer、Encoder、Decoder 和 Layer
- Fold、Unfold、Upsample、Pixel 重排
- Bilinear、CosineSimilarity、PairwiseDistance 等

现有基础 35 个官方 PyTorch/Paddle 双框架模块与新增 94 个 PyTorch 模型层共同组成 129 个模型 API。

## 排除项

以下内容不作为可放置模型节点：

- 所有 Loss 类
- `Module`、`Sequential`、`ModuleList`、`ModuleDict`
- Parameter/Buffer 容器
- `RNNBase`、`RNNCellBase` 等内部基类
- `DataParallel` 等训练/部署包装器

网络组合使用 CompositeResource 表达，Loss 和 Optimizer 仍保留在训练阶段入口。

## 可选端口

RNN 隐藏状态、Attention mask、Transformer mask 等可选项会作为可选端口显示：

- 不要求必须连接。
- 未连接时生成代码省略该关键字。
- 辅助输出即使未连接，也会出现在节点分析和代码变量中。

例如：

- MultiheadAttention：query/key/value 必填，key_padding_mask、need_weights、attn_mask 可选。
- LSTM：input 必填，hx 可选；输出 output、h_n、c_n。

## Paddle

新扩展的 94 个 PyTorch API 默认标记为 `PyTorch Only`。

- Paddle 模式下仍可在模块库查看。
- 不能新增 PyTorch Only 节点。
- 如果已有图切换到 Paddle 且包含不支持的模块，会返回 `FRAMEWORK_UNSUPPORTED`。
- 原有具有明确 Paddle 等价的 35 个模块继续支持双框架生成。

## 注册表更新

升级 PyTorch 基线时：

1. 在对应 PyTorch 环境运行 `scripts/generate_pytorch_registry.py`。
2. 审查新增/删除的类和参数。
3. 补充新增类的 Shape 规则。
4. 更新注册表版本和测试。

旧工程继续使用自身保存的 IR 和复合资源，不随注册表升级自动改写。
