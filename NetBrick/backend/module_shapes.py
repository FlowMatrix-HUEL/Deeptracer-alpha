from __future__ import annotations

from math import floor
from typing import Any

from .catalog import BlockSpec
from .errors import ShapeError


def _value(params: dict[str, Any], key: str, default: Any) -> Any:
    return params.get(key, default)


def _single(value: Any, default: int = 1) -> int:
    if isinstance(value, (list, tuple)):
        return int(value[0]) if value else default
    return int(value)


def _output_size(
    size: int,
    kernel: int,
    stride: int,
    padding: int,
    dilation: int,
) -> int:
    result = floor(
        (size + 2 * padding - dilation * (kernel - 1) - 1) / stride + 1
    )
    if result <= 0:
        raise ShapeError("卷积或池化窗口大于输入尺寸")
    return result


def _transpose_size(
    size: int,
    kernel: int,
    stride: int,
    padding: int,
    output_padding: int,
    dilation: int,
) -> int:
    return (
        (size - 1) * stride
        - 2 * padding
        + dilation * (kernel - 1)
        + output_padding
        + 1
    )


def _dimensions(name: str) -> int:
    if name.endswith("3d") or name.endswith("3D"):
        return 3
    if name.endswith("2d") or name.endswith("2D"):
        return 2
    return 1


def infer_registered_outputs(
    block: BlockSpec,
    input_shapes: list[list[int]],
    input_dtypes: list[str],
    params: dict[str, Any],
) -> tuple[list[tuple[str, list[int], str]], list[tuple[str, list[int], str]]]:
    if not input_shapes:
        raise ShapeError(f"{block.op} 缺少输入")
    name = block.torch_name or block.op.removeprefix("nn.")
    primary = list(input_shapes[0])
    dtype = input_dtypes[0]
    auxiliary: list[tuple[str, list[int], str]] = []

    if name in {
        "Identity",
        "Dropout1d",
        "Dropout3d",
        "AlphaDropout",
        "FeatureAlphaDropout",
        "ReLU",
        "ReLU6",
        "LeakyReLU",
        "ELU",
        "GELU",
        "SiLU",
        "Sigmoid",
        "Tanh",
        "Softmax",
        "Softmax2d",
        "LogSoftmax",
        "Softmin",
        "Softplus",
        "Softsign",
        "Tanhshrink",
        "LogSigmoid",
        "Mish",
        "Hardsigmoid",
        "Hardshrink",
        "Hardswish",
        "Hardtanh",
        "Threshold",
        "CELU",
        "SELU",
        "PReLU",
        "RReLU",
        "PretrainedReLU",
        "SyncBatchNorm",
        "LocalResponseNorm",
        "CrossMapLRN2d",
        "LayerNorm",
        "GroupNorm",
        "RMSNorm",
        "ChannelShuffle",
        "ParameterList",
        "ParameterDict",
    }:
        return [(block.output_ports[0].name if block.output_ports else "out", primary, dtype)], auxiliary

    if name.endswith("Norm1d") or name.endswith("Norm2d") or name.endswith("Norm3d"):
        return [(block.output_ports[0].name if block.output_ports else "out", primary, dtype)], auxiliary

    if name.startswith(("ConvTranspose1d", "ConvTranspose2d", "ConvTranspose3d", "LazyConvTranspose")):
        dimensions = _dimensions(name)
        if len(primary) < dimensions + 2:
            raise ShapeError(f"{name} 需要至少 {dimensions + 2} 维输入")
        kernel = _single(_value(params, "kernel_size", 1))
        stride = _single(_value(params, "stride", 1))
        padding = _single(_value(params, "padding", 0), 0)
        output_padding = _single(_value(params, "output_padding", 0), 0)
        dilation = _single(_value(params, "dilation", 1))
        output = primary[:2] + [
            _transpose_size(
                size,
                kernel,
                stride,
                padding,
                output_padding,
                dilation,
            )
            for size in primary[2 : dimensions + 2]
        ]
        output[1] = int(_value(params, "out_channels", primary[1]))
        return [(block.output_ports[0].name if block.output_ports else "out", output, dtype)], auxiliary

    if name.startswith(("Conv1d", "Conv2d", "Conv3d", "LazyConv")):
        dimensions = _dimensions(name)
        if len(primary) < dimensions + 2:
            raise ShapeError(f"{name} 需要至少 {dimensions + 2} 维输入")
        kernel = _single(_value(params, "kernel_size", 1))
        stride = _single(_value(params, "stride", 1))
        padding = _single(_value(params, "padding", 0), 0)
        dilation = _single(_value(params, "dilation", 1))
        output = primary[:2] + [
            _output_size(size, kernel, stride, padding, dilation)
            for size in primary[2 : dimensions + 2]
        ]
        output[1] = int(_value(params, "out_channels", output[1]))
        return [(block.output_ports[0].name if block.output_ports else "out", output, dtype)], auxiliary

    if name.startswith(("MaxPool", "AvgPool", "LPPool")):
        dimensions = _dimensions(name)
        kernel = _single(_value(params, "kernel_size", 2), 2)
        stride = _single(_value(params, "stride", kernel), kernel)
        padding = _single(_value(params, "padding", 0), 0)
        dilation = _single(_value(params, "dilation", 1))
        output = primary[:2] + [
            _output_size(size, kernel, stride, padding, dilation)
            for size in primary[2 : dimensions + 2]
        ]
        return [(block.output_ports[0].name if block.output_ports else "out", output, dtype)], auxiliary

    if name.startswith(("FractionalMaxPool")):
        ratio = float(_value(params, "output_ratio", 0.5))
        output = primary[:2] + [max(1, floor(size * ratio)) for size in primary[2:]]
        return [(block.output_ports[0].name if block.output_ports else "out", output, dtype)], auxiliary

    if name.startswith(("AdaptiveMaxPool", "AdaptiveAvgPool")):
        output_size = _value(params, "output_size", 1)
        target = list(output_size) if isinstance(output_size, (list, tuple)) else [int(output_size)]
        return [(block.output_ports[0].name if block.output_ports else "out", primary[:2] + target, dtype)], auxiliary

    if name.startswith(("MaxUnpool",)):
        dimensions = _dimensions(name)
        stride = _single(_value(params, "stride", 2), 2)
        output = primary[:2] + [size * stride for size in primary[2 : dimensions + 2]]
        return [(block.output_ports[0].name if block.output_ports else "out", output, dtype)], auxiliary

    if "Pad" in name:
        padding = _value(params, "padding", 0)
        amounts = list(padding) if isinstance(padding, (list, tuple)) else [int(padding)]
        output = list(primary)
        for index, amount in enumerate(reversed(amounts)):
            dimension = len(output) - 1 - index // 2
            if dimension >= 2:
                output[dimension] += int(amount)
        return [(block.output_ports[0].name if block.output_ports else "out", output, dtype)], auxiliary

    if name in {"Upsample", "UpsamplingNearest2d", "UpsamplingBilinear2d"}:
        size = _value(params, "size", None)
        if isinstance(size, (list, tuple)):
            output = primary[:2] + [int(item) for item in size]
        else:
            factor = float(_value(params, "scale_factor", 2))
            output = primary[:-2] + [round(item * factor) for item in primary[-2:]]
        return [(block.output_ports[0].name if block.output_ports else "out", output, dtype)], auxiliary

    if name in {"GLU"}:
        output = list(primary)
        dim = int(_value(params, "dim", -1))
        dim = dim if dim >= 0 else len(output) + dim
        output[dim] //= 2
        return [(block.output_ports[0].name if block.output_ports else "out", output, dtype)], auxiliary

    if name in {"CosineSimilarity", "PairwiseDistance"}:
        output = primary[:-1] if len(primary) > 1 else primary
        if bool(_value(params, "keepdim", False)) and output:
            output = output + [1]
        return [(block.output_ports[0].name if block.output_ports else "out", output, dtype)], auxiliary

    if name == "Bilinear":
        first = input_shapes[0]
        output = [first[0] if first else 1, int(_value(params, "out_features", 1))]
        return [(block.output_ports[0].name if block.output_ports else "out", output, dtype)], auxiliary

    if name == "EmbeddingBag":
        embedding_dim = int(_value(params, "embedding_dim", 1))
        batch = primary[0] if primary else 1
        output = [batch, embedding_dim]
        token_count = 1
        for dim in primary:
            token_count *= max(1, dim)
        return [(block.output_ports[0].name if block.output_ports else "out", output, dtype)], [
            ("offset2bag", [token_count], "int64"),
            ("bag_size", [batch], "int64"),
            ("max_indices", [token_count], "int64"),
        ]

    if name in {"RNN", "LSTM", "GRU", "RNNCell", "LSTMCell", "GRUCell"}:
        hidden = int(_value(params, "hidden_size", 1))
        layers = int(_value(params, "num_layers", 1))
        directions = 2 if bool(_value(params, "bidirectional", False)) else 1
        if name.endswith("Cell"):
            output = [primary[0] if primary else 1, hidden]
        else:
            batch_first = bool(_value(params, "batch_first", False))
            if len(primary) < 3:
                raise ShapeError(f"{name} 需要 [sequence,batch,feature] 三维输入")
            output = list(primary)
            output[-1] = hidden * directions
            if not batch_first:
                output = primary
        batch = output[0] if name.endswith("Cell") else (
            output[0] if bool(_value(params, "batch_first", False)) else output[1]
        )
        hidden_shape = [layers * directions, batch, hidden]
        aux_name = "h" if name.endswith("Cell") else "h_n"
        auxiliary.append((aux_name, hidden_shape, dtype))
        if name in {"LSTM", "LSTMCell"}:
            auxiliary.append(("c" if name.endswith("Cell") else "c_n", hidden_shape, dtype))
        return [(block.output_ports[0].name if block.output_ports else "out", output, dtype)], auxiliary

    if name in {"TransformerEncoder", "TransformerEncoderLayer"}:
        return [(block.output_ports[0].name if block.output_ports else "out", primary, dtype)], auxiliary

    if name in {"Transformer", "TransformerDecoder", "TransformerDecoderLayer"}:
        return [(block.output_ports[0].name if block.output_ports else "out", primary, dtype)], auxiliary

    if name == "MultiheadAttention":
        query = input_shapes[0]
        output = list(query)
        return [(block.output_ports[0].name if block.output_ports else "out", output, dtype)], [
            ("attn_weights", [1], dtype)
        ]

    if name == "Unfold":
        kernel = _single(_value(params, "kernel_size", 1))
        dilation = _single(_value(params, "dilation", 1))
        padding = _single(_value(params, "padding", 0), 0)
        stride = _single(_value(params, "stride", 1))
        if not primary:
            raise ShapeError("Unfold 缺少输入维度")
        length = primary[-1]
        blocks = _output_size(length, kernel, stride, padding, dilation)
        return [(block.output_ports[0].name if block.output_ports else "out", primary[:-1] + [blocks, kernel * kernel], dtype)], auxiliary

    if name == "Fold":
        kernel = _single(_value(params, "kernel_size", 1))
        if len(primary) < 2:
            raise ShapeError("Fold 缺少输入维度")
        blocks = primary[-2]
        stride = _single(_value(params, "stride", 1))
        dilation = _single(_value(params, "dilation", 1))
        padding = _single(_value(params, "padding", 0), 0)
        length = (blocks - 1) * stride - 2 * padding + dilation * (kernel - 1) + 1
        return [(block.output_ports[0].name if block.output_ports else "out", primary[:-2] + [length], dtype)], auxiliary

    # Remaining public layers are shape-preserving or expose their primary
    # tensor with the same spatial signature. Explicit multi-output handlers
    # above remain authoritative.
    primary_ports = block.output_ports or []
    first_name = primary_ports[0].name if primary_ports else "out"
    return [(first_name, primary, dtype)], auxiliary
