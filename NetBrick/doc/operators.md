# 算子与官方 API

NetBrick 的基础双框架目录包含 35 个常用网络层、3 个合并算子和条件/控制节点；此外 PyTorch 2.6 注册表扩展了 94 个公开模型层。完整覆盖范围见 [PyTorch API](pytorch-api.md)。

## 模型边界

| 名称 | 作用 |
| --- | --- |
| Input | 定义模型输入变量、样本 Shape 和 dtype |
| Output | 定义模型输出变量 |

Input/Output 不是 PyTorch/Paddle 官方网络层，因此不套用 `torch.nn` 或 `paddle.nn` 路径。

## 基础层

| 功能 | PyTorch API | Paddle API | 主要参数 |
| --- | --- | --- | --- |
| 全连接 | `torch.nn.Linear` | `paddle.nn.Linear` | `in_features`、`out_features`、`bias`/`bias_attr` |
| 恒等映射 | `torch.nn.Identity` | `paddle.nn.Identity` | 无 |
| 展平 | `torch.nn.Flatten` | `paddle.nn.Flatten` | `start_dim`/`start_axis`、`end_dim`/`stop_axis` |
| 还原形状 | `torch.nn.Unflatten` | `paddle.nn.Unflatten` | `dim`/`axis`、`sizes`/`shape` |
| Dropout | `torch.nn.Dropout` | `paddle.nn.Dropout` | `p`、`inplace`（Paddle 不显示） |
| 二维 Dropout | `torch.nn.Dropout2d` | `paddle.nn.Dropout2D` | `p`、`inplace`（Paddle 不显示） |

## 卷积与池化

| 功能 | PyTorch API | Paddle API |
| --- | --- | --- |
| 一维卷积 | `torch.nn.Conv1d` | `paddle.nn.Conv1D` |
| 二维卷积 | `torch.nn.Conv2d` | `paddle.nn.Conv2D` |
| 二维转置卷积 | `torch.nn.ConvTranspose2d` | `paddle.nn.Conv2DTranspose` |
| 一维最大池化 | `torch.nn.MaxPool1d` | `paddle.nn.MaxPool1D` |
| 二维最大池化 | `torch.nn.MaxPool2d` | `paddle.nn.MaxPool2D` |
| 一维平均池化 | `torch.nn.AvgPool1d` | `paddle.nn.AvgPool1D` |
| 二维平均池化 | `torch.nn.AvgPool2d` | `paddle.nn.AvgPool2D` |
| 一维自适应池化 | `torch.nn.AdaptiveAvgPool1d` | `paddle.nn.AdaptiveAvgPool1D` |
| 二维自适应池化 | `torch.nn.AdaptiveAvgPool2d` | `paddle.nn.AdaptiveAvgPool2D` |
| 上采样 | `torch.nn.Upsample` | `paddle.nn.Upsample` |

卷积参数包括通道数、卷积核、步幅、填充、膨胀、分组和偏置。Paddle 的偏置参数显示为 `bias_attr`。Paddle 最大池化不显示 PyTorch 专属的 `dilation`。

## 归一化

| 功能 | PyTorch API | Paddle API |
| --- | --- | --- |
| 一维批归一化 | `torch.nn.BatchNorm1d` | `paddle.nn.BatchNorm1D` |
| 二维批归一化 | `torch.nn.BatchNorm2d` | `paddle.nn.BatchNorm2D` |
| 层归一化 | `torch.nn.LayerNorm` | `paddle.nn.LayerNorm` |
| 组归一化 | `torch.nn.GroupNorm` | `paddle.nn.GroupNorm` |
| 二维实例归一化 | `torch.nn.InstanceNorm2d` | `paddle.nn.InstanceNorm2D` |

Paddle 模式下 `eps` 显示为 `epsilon`。当前框架不支持的归一化参数不会出现在 Inspector 中。

## 激活函数

| 功能 | PyTorch API | Paddle API |
| --- | --- | --- |
| ReLU | `torch.nn.ReLU` | `paddle.nn.ReLU` |
| ReLU6 | `torch.nn.ReLU6` | `paddle.nn.ReLU6` |
| LeakyReLU | `torch.nn.LeakyReLU` | `paddle.nn.LeakyReLU` |
| ELU | `torch.nn.ELU` | `paddle.nn.ELU` |
| GELU | `torch.nn.GELU` | `paddle.nn.GELU` |
| SiLU | `torch.nn.SiLU` | `paddle.nn.Silu` |
| Sigmoid | `torch.nn.Sigmoid` | `paddle.nn.Sigmoid` |
| Tanh | `torch.nn.Tanh` | `paddle.nn.Tanh` |
| Softmax | `torch.nn.Softmax` | `paddle.nn.Softmax` |
| LogSoftmax | `torch.nn.LogSoftmax` | `paddle.nn.LogSoftmax` |
| Mish | `torch.nn.Mish` | `paddle.nn.Mish` |

Softmax/LogSoftmax 在 PyTorch 中使用 `dim`，Paddle 中使用 `axis`。

## 张量重排

| 功能 | PyTorch API | Paddle API | 主要参数 |
| --- | --- | --- | --- |
| 词嵌入 | `torch.nn.Embedding` | `paddle.nn.Embedding` | `num_embeddings`、`embedding_dim` |
| 像素重排 | `torch.nn.PixelShuffle` | `paddle.nn.PixelShuffle` | `upscale_factor` |
| 像素反重排 | `torch.nn.PixelUnshuffle` | `paddle.nn.PixelUnshuffle` | `downscale_factor` |

## 合并运算

合并算子使用一个可连接多条入线的 `x` 端口。

| 功能 | PyTorch API | Paddle API | 规则 |
| --- | --- | --- | --- |
| 多路相加 | `torch.add` | `paddle.add` | 所有输入 Shape 完全一致 |
| 多路相乘 | `torch.multiply` | `paddle.multiply` | 所有输入 Shape 完全一致 |
| 多路拼接 | `torch.cat` | `paddle.concat` | rank 一致，非拼接维一致 |

两个以上输入时：

- Add/Multiply 按输入顺序生成嵌套官方调用。
- Concat 将所有 Tensor 放入同一个列表后调用。

## 训练阶段入口

模块库还展示：

- 损失函数：CrossEntropyLoss、MSELoss
- 优化器：SGD、Adam

这些入口仅表示训练阶段能力，不进入当前前向推理图，也不会执行训练。
