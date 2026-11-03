"""Generate NetBrick's static PyTorch 2.6 model registry.

Run with a PyTorch 2.6 environment. The generated JSON is committed and is the
only artifact required by the deeptracer application at runtime.
"""

from __future__ import annotations

import inspect
import json
import types
from pathlib import Path
from typing import Any

import torch
import torch.nn as nn


EXCLUDED = {
    "AdaptiveLogSoftmaxWithLoss",
    "BCELoss",
    "BCEWithLogitsLoss",
    "CTCLoss",
    "CosineEmbeddingLoss",
    "CrossEntropyLoss",
    "GaussianNLLLoss",
    "HingeEmbeddingLoss",
    "HuberLoss",
    "KLDivLoss",
    "L1Loss",
    "MSELoss",
    "MarginRankingLoss",
    "MultiLabelMarginLoss",
    "MultiLabelSoftMarginLoss",
    "MultiMarginLoss",
    "NLLLoss",
    "NLLLoss2d",
    "PoissonNLLLoss",
    "SmoothL1Loss",
    "SoftMarginLoss",
    "TripletMarginLoss",
    "TripletMarginWithDistanceLoss",
    "Module",
    "Container",
    "Sequential",
    "ModuleList",
    "ModuleDict",
    "ParameterList",
    "ParameterDict",
    "Buffer",
    "Parameter",
    "UninitializedBuffer",
    "UninitializedParameter",
    "DataParallel",
    "RNNBase",
    "RNNCellBase",
}

SKIP_PARAMS = {
    "device",
    "dtype",
    "factory_kwargs",
    "weight_attr",
    "bias_attr",
}

EXISTING = {
    "Linear",
    "Identity",
    "Flatten",
    "Unflatten",
    "Dropout",
    "Dropout2d",
    "Conv1d",
    "Conv2d",
    "ConvTranspose2d",
    "MaxPool1d",
    "MaxPool2d",
    "AvgPool1d",
    "AvgPool2d",
    "AdaptiveAvgPool1d",
    "AdaptiveAvgPool2d",
    "Upsample",
    "BatchNorm1d",
    "BatchNorm2d",
    "LayerNorm",
    "GroupNorm",
    "InstanceNorm2d",
    "ReLU",
    "ReLU6",
    "LeakyReLU",
    "ELU",
    "GELU",
    "SiLU",
    "Sigmoid",
    "Tanh",
    "Softmax",
    "LogSoftmax",
    "Embedding",
    "PixelShuffle",
    "PixelUnshuffle",
    "Mish",
}

PORTS: dict[str, list[dict[str, Any]]] = {
    "Bilinear": [
        {"name": "input1", "required": True, "call_arg": None},
        {"name": "input2", "required": True, "call_arg": None},
    ],
    "MultiheadAttention": [
        {"name": "query", "required": True, "call_arg": None},
        {"name": "key", "required": True, "call_arg": None},
        {"name": "value", "required": True, "call_arg": None},
        {"name": "key_padding_mask", "required": False, "call_arg": "key_padding_mask"},
        {
            "name": "need_weights",
            "required": False,
            "call_arg": "need_weights",
            "data_type": "ScalarBool",
        },
        {"name": "attn_mask", "required": False, "call_arg": "attn_mask"},
    ],
    "RNN": [
        {"name": "input", "required": True, "call_arg": None},
        {"name": "hx", "required": False, "call_arg": "hx"},
    ],
    "LSTM": [
        {"name": "input", "required": True, "call_arg": None},
        {"name": "hx", "required": False, "call_arg": "hx"},
    ],
    "GRU": [
        {"name": "input", "required": True, "call_arg": None},
        {"name": "hx", "required": False, "call_arg": "hx"},
    ],
    "RNNCell": [
        {"name": "input", "required": True, "call_arg": None},
        {"name": "hx", "required": False, "call_arg": "hx"},
    ],
    "LSTMCell": [
        {"name": "input", "required": True, "call_arg": None},
        {"name": "hx", "required": False, "call_arg": "hx"},
    ],
    "GRUCell": [
        {"name": "input", "required": True, "call_arg": None},
        {"name": "hx", "required": False, "call_arg": "hx"},
    ],
    "Transformer": [
        {"name": "src", "required": True, "call_arg": None},
        {"name": "tgt", "required": True, "call_arg": None},
        {"name": "src_mask", "required": False, "call_arg": "src_mask"},
        {"name": "tgt_mask", "required": False, "call_arg": "tgt_mask"},
        {"name": "memory_mask", "required": False, "call_arg": "memory_mask"},
    ],
    "TransformerEncoder": [
        {"name": "src", "required": True, "call_arg": None},
        {"name": "mask", "required": False, "call_arg": "mask"},
        {"name": "src_key_padding_mask", "required": False, "call_arg": "src_key_padding_mask"},
    ],
    "TransformerEncoderLayer": [
        {"name": "src", "required": True, "call_arg": None},
        {"name": "src_mask", "required": False, "call_arg": "src_mask"},
        {"name": "src_key_padding_mask", "required": False, "call_arg": "src_key_padding_mask"},
    ],
    "TransformerDecoder": [
        {"name": "tgt", "required": True, "call_arg": None},
        {"name": "memory", "required": True, "call_arg": None},
        {"name": "tgt_mask", "required": False, "call_arg": "tgt_mask"},
        {"name": "memory_mask", "required": False, "call_arg": "memory_mask"},
    ],
    "TransformerDecoderLayer": [
        {"name": "tgt", "required": True, "call_arg": None},
        {"name": "memory", "required": True, "call_arg": None},
        {"name": "tgt_mask", "required": False, "call_arg": "tgt_mask"},
        {"name": "memory_mask", "required": False, "call_arg": "memory_mask"},
    ],
    "EmbeddingBag": [
        {"name": "input", "required": True, "call_arg": None},
        {"name": "offsets", "required": False, "call_arg": "offsets"},
        {"name": "per_sample_weights", "required": False, "call_arg": "per_sample_weights"},
    ],
    "CosineSimilarity": [
        {"name": "x1", "required": True, "call_arg": None},
        {"name": "x2", "required": True, "call_arg": None},
    ],
    "PairwiseDistance": [
        {"name": "x1", "required": True, "call_arg": None},
        {"name": "x2", "required": True, "call_arg": None},
    ],
}

REQUIRED_DEFAULTS = {
    "embed_dim": 8,
    "num_heads": 2,
    "num_features": 8,
    "num_channels": 8,
    "in_channels": 1,
    "out_channels": 8,
    "in1_features": 1,
    "in2_features": 1,
    "out_features": 10,
    "num_embeddings": 10,
    "embedding_dim": 8,
    "input_size": 8,
    "hidden_size": 8,
    "d_model": 512,
    "nhead": 8,
}

MANUAL_FIELDS: dict[str, list[dict[str, Any]]] = {}
for class_name, hidden_name in [
    ("RNN", "hidden_size"),
    ("GRU", "hidden_size"),
    ("LSTM", "hidden_size"),
]:
    MANUAL_FIELDS[class_name] = [
        {"key": "input_size", "label": "input_size", "type": "int", "default": 8, "help": "", "options": None},
        {"key": "hidden_size", "label": "hidden_size", "type": "int", "default": 8, "help": "", "options": None},
        {"key": "num_layers", "label": "num_layers", "type": "int", "default": 1, "help": "", "options": None},
        {"key": "bias", "label": "bias", "type": "bool", "default": True, "help": "", "options": None},
        {"key": "batch_first", "label": "batch_first", "type": "bool", "default": False, "help": "", "options": None},
        {"key": "dropout", "label": "dropout", "type": "float", "default": 0.0, "help": "", "options": None},
        {"key": "bidirectional", "label": "bidirectional", "type": "bool", "default": False, "help": "", "options": None},
    ]
for class_name, hidden_name in [
    ("RNNCell", "hidden_size"),
    ("GRUCell", "hidden_size"),
    ("LSTMCell", "hidden_size"),
]:
    MANUAL_FIELDS[class_name] = [
        {"key": "input_size", "label": "input_size", "type": "int", "default": 8, "help": "", "options": None},
        {"key": "hidden_size", "label": "hidden_size", "type": "int", "default": 8, "help": "", "options": None},
        {"key": "bias", "label": "bias", "type": "bool", "default": True, "help": "", "options": None},
    ]

OUTPUTS: dict[str, list[dict[str, Any]]] = {
    "MultiheadAttention": [
        {"name": "attn_output", "output_index": 0},
        {"name": "attn_weights", "output_index": 1, "required": False},
    ],
    "RNN": [
        {"name": "output", "output_index": 0},
        {"name": "h_n", "output_index": 1, "required": False},
    ],
    "LSTM": [
        {"name": "output", "output_index": 0},
        {"name": "h_n", "output_index": 1, "required": False},
        {"name": "c_n", "output_index": 2, "required": False},
    ],
    "GRU": [
        {"name": "output", "output_index": 0},
        {"name": "h_n", "output_index": 1, "required": False},
    ],
    "RNNCell": [{"name": "h", "output_index": 0}],
    "GRUCell": [{"name": "h", "output_index": 0}],
    "LSTMCell": [
        {"name": "h", "output_index": 0},
        {"name": "c", "output_index": 1},
    ],
    "EmbeddingBag": [
        {"name": "out", "output_index": 0},
        {"name": "offset2bag", "output_index": 1, "required": False},
        {"name": "bag_size", "output_index": 2, "required": False},
        {"name": "max_indices", "output_index": 3, "required": False},
    ],
}


def category_for(name: str) -> str:
    if any(token in name for token in ("Conv", "Pool", "Unpool", "Adaptive", "LPPool", "Fractional")):
        return "卷积与池化"
    if any(token in name for token in ("Norm", "Norm1d", "Norm2d", "Norm3d")):
        return "归一化"
    if any(
        token in name
        for token in (
            "ReLU",
            "Sigmoid",
            "Tanh",
            "ELU",
            "GELU",
            "SiLU",
            "Mish",
            "Soft",
            "Shrink",
            "Hard",
            "CELU",
            "SELU",
            "PReLU",
            "Threshold",
            "GLU",
            "Hardshrink",
        )
    ):
        return "激活函数"
    if "Pad" in name:
        return "Padding"
    if any(token in name for token in ("RNN", "LSTM", "GRU", "Transformer", "Attention")):
        return "序列与注意力"
    return "其他模型层"


def field_from_param(name: str, parameter: inspect.Parameter):
    default = parameter.default
    if name in SKIP_PARAMS:
        return None
    annotation = parameter.annotation
    annotation_text = str(annotation)
    required = default is inspect.Parameter.empty
    if required:
        if name in REQUIRED_DEFAULTS:
            default = REQUIRED_DEFAULTS[name]
        elif any(token in annotation_text for token in ("Sequence", "List", "Tuple")):
            return {
                "key": name,
                "label": name,
                "type": "int_list",
                "default": [1],
                "help": "",
                "options": None,
            }
        elif annotation is int or "int" in annotation_text and "Optional" not in annotation_text:
            default = 1
        elif annotation is float or "float" in annotation_text and "Optional" not in annotation_text:
            default = 0.0
        elif annotation is bool:
            default = False
        elif annotation is str:
            default = ""
        else:
            return None
    if not isinstance(default, (int, float, bool, str, type(None))):
        return None
    if default is None:
        return None
    if isinstance(default, bool):
        kind = "bool"
    elif isinstance(default, int):
        kind = "int"
    elif isinstance(default, float):
        kind = "float"
    elif isinstance(default, str):
        kind = "enum" if name in {"mode", "approximate"} else "text"
    else:
        return None
    return {
        "key": name,
        "label": name,
        "type": kind,
        "default": default,
        "help": "",
        "options": (
            ["nearest", "linear", "bilinear", "bicubic", "trilinear", "area"]
            if name == "mode"
            else ["none", "tanh"]
            if name == "approximate"
            else None
        ),
    }


def main() -> None:
    result: list[dict[str, Any]] = []
    classes = []
    for name in dir(nn):
        value = getattr(nn, name, None)
        if (
            inspect.isclass(value)
            and issubclass(value, nn.Module)
            and name not in EXCLUDED
        ):
            classes.append((name, value))
    for name, value in sorted(classes):
        if name in EXISTING:
            continue
        try:
            signature = inspect.signature(value.__init__)
        except (TypeError, ValueError):
            signature = None
        fields = MANUAL_FIELDS.get(name, [])
        if signature is not None and not fields:
            for parameter_name, parameter in signature.parameters.items():
                if parameter_name in {"self", "args", "kwargs"}:
                    continue
                field = field_from_param(parameter_name, parameter)
                if field is not None:
                    fields.append(field)
        result.append(
            {
                "class_name": name,
                "category": category_for(name),
                "inputs": PORTS.get(
                    name,
                    [{"name": "x", "required": True, "call_arg": None}],
                ),
                "outputs": OUTPUTS.get(
                    name,
                    [{"name": "out", "output_index": 0, "required": True}],
                ),
                "fields": fields,
            }
        )
    target = (
        Path(__file__).resolve().parent.parent
        / "backend"
        / "data"
        / "pytorch_2_6_registry.json"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "torch_version": torch.__version__.split("+")[0],
                "source": "torch.nn.__all__",
                "classes": result,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {len(result)} classes to {target}")


if __name__ == "__main__":
    main()
