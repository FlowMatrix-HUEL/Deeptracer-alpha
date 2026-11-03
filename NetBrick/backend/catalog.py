from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class CatalogModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FieldSpec(CatalogModel):
    key: str
    label: str
    type: Literal["int", "float", "bool", "int_list", "enum", "text"]
    default: Any
    help: str = ""
    minimum: float | None = None
    maximum: float | None = None
    step: float | None = None
    options: list[str] | None = None


class CatalogPort(CatalogModel):
    name: str
    required: bool = True
    data_type: Literal["Tensor", "ScalarBool", "ScalarInt"] = "Tensor"
    role: str | None = None
    call_arg: str | None = None
    output_index: int = 0


class BlockSpec(CatalogModel):
    op: str
    label: str
    category: str
    description: str
    color: str
    torch_name: str | None = None
    paddle_name: str | None = None
    torch_api: str | None = None
    paddle_api: str | None = None
    input_mode: Literal["single", "merge"] = "single"
    control_type: Literal["if", "for", "while"] | None = None
    output_data_type: Literal["Tensor", "ScalarBool", "ScalarInt"] = "Tensor"
    input_ports: list[CatalogPort] = Field(default_factory=list)
    output_ports: list[CatalogPort] = Field(default_factory=list)
    pytorch_only: bool = False
    fields: list[FieldSpec] = Field(default_factory=list)
    input_role: str | None = None
    output_role: str | None = None
    system: bool = False


class CatalogResponse(CatalogModel):
    version: str = "0.2"
    blocks: list[BlockSpec]


def field(
    key: str,
    label: str,
    kind: Literal["int", "float", "bool", "int_list", "enum", "text"],
    default: Any,
    help_text: str = "",
    minimum: float | None = None,
    maximum: float | None = None,
    step: float | None = None,
    options: list[str] | None = None,
) -> FieldSpec:
    return FieldSpec(
        key=key,
        label=label,
        type=kind,
        default=default,
        help=help_text,
        minimum=minimum,
        maximum=maximum,
        step=step,
        options=options,
    )


def int_field(key: str, label: str, default: int, *, low: int = 1, help_text: str = "") -> FieldSpec:
    return field(key, label, "int", default, help_text, maximum=1_000_000, minimum=low)


def bool_field(key: str, label: str, default: bool, help_text: str = "") -> FieldSpec:
    return field(key, label, "bool", default, help_text)


def add_spec(
    items: list[BlockSpec],
    op: str,
    label: str,
    category: str,
    description: str,
    color: str,
    fields: list[FieldSpec],
    *,
    paddle_name: str | None = None,
    torch_api: str | None = None,
    paddle_api: str | None = None,
    input_mode: Literal["single", "merge"] = "single",
    control_type: Literal["if", "for", "while"] | None = None,
    output_data_type: Literal["Tensor", "ScalarBool", "ScalarInt"] = "Tensor",
    input_ports: list[CatalogPort] | None = None,
    output_ports: list[CatalogPort] | None = None,
    pytorch_only: bool = False,
    system: bool = False,
) -> None:
    items.append(
        BlockSpec(
            op=op,
            label=label,
            category=category,
            description=description,
            color=color,
            torch_name=op.removeprefix("nn.") if op.startswith("nn.") else None,
            paddle_name=(
                paddle_name
                or (op.removeprefix("nn.") if op.startswith("nn.") else None)
            ),
            torch_api=torch_api,
            paddle_api=paddle_api,
            input_mode=input_mode,
            control_type=control_type,
            output_data_type=output_data_type,
            input_ports=input_ports or [],
            output_ports=output_ports or [],
            pytorch_only=pytorch_only,
            fields=fields,
            system=system,
        )
    )


def _build_blocks() -> list[BlockSpec]:
    items: list[BlockSpec] = []
    add_spec(
        items,
        "Input",
        "输入",
        "输入输出",
        "模型入口。示例形状只用于分析和生成演示代码。",
        "#0f9b8e",
        [
            field("name", "变量名", "text", "x", "将用于 forward 参数和示例代码"),
            field("sample_shape", "示例形状", "int_list", [1, 1, 28, 28], "包含 batch 维"),
            field(
                "data_type",
                "端口类型",
                "enum",
                "Tensor",
                options=["Tensor", "ScalarBool", "ScalarInt"],
                help_text="控制流谓词可使用标量类型",
            ),
            field(
                "dtype",
                "数据类型",
                "enum",
                "float32",
                options=["float32", "float64", "int64", "uint8", "bool"],
            ),
        ],
        system=True,
    )
    add_spec(
        items,
        "Output",
        "输出",
        "输入输出",
        "模型出口。一个入口和一个出口组成一条独立数据链。",
        "#e26952",
        [
            field("name", "输出名", "text", "logits"),
            field(
                "data_type",
                "端口类型",
                "enum",
                "Tensor",
                options=["Tensor", "ScalarBool", "ScalarInt"],
            ),
        ],
        system=True,
    )

    layers = "基础层"
    add_spec(items, "nn.Linear", "全连接", layers, "把最后一维映射到新的特征维度。", "#4569d4", [
        int_field("in_features", "输入特征", 784),
        int_field("out_features", "输出特征", 10),
        bool_field("bias", "使用偏置", True),
    ])
    add_spec(items, "nn.Identity", "恒等映射", layers, "原样传递张量，适合教学对照。", "#6f7684", [])
    add_spec(items, "nn.Flatten", "展平", layers, "合并连续维度，常见于 CNN 到全连接的过渡。", "#a05ac2", [
        int_field("start_dim", "起始维度", 1, low=-4),
        int_field("end_dim", "结束维度", -1, low=-4),
    ])
    add_spec(items, "nn.Unflatten", "还原形状", layers, "把一个维度展开为多个维度。", "#a05ac2", [
        field("dim", "维度", "int", 1, "允许负数维度", minimum=-4),
        field("sizes", "新形状", "int_list", [1, 28, 28]),
    ])
    add_spec(items, "nn.Dropout", "随机失活", layers, "训练时随机置零，推理时关闭。", "#c48c25", [
        field("p", "失活概率", "float", 0.5, minimum=0, maximum=1, step=0.05),
        bool_field("inplace", "原地操作", False),
    ])
    add_spec(items, "nn.Dropout2d", "二维随机失活", layers, "按通道随机置零，常用于 CNN。", "#c48c25", [
        field("p", "失活概率", "float", 0.5, minimum=0, maximum=1, step=0.05),
        bool_field("inplace", "原地操作", False),
    ], paddle_name="Dropout2D")

    conv = "卷积与池化"
    for name, label, desc in [
        ("nn.Conv1d", "一维卷积", "在序列或一维信号上提取局部特征。"),
        ("nn.Conv2d", "二维卷积", "提取图像局部特征，是 CNN 的核心算子。"),
    ]:
        add_spec(items, name, label, conv, desc, "#2f83b9", [
            int_field("in_channels", "输入通道", 1),
            int_field("out_channels", "输出通道", 8),
            int_field("kernel_size", "卷积核", 3),
            int_field("stride", "步幅", 1),
            int_field("padding", "填充", 1, low=0),
            int_field("dilation", "膨胀", 1),
            int_field("groups", "分组数", 1),
            bool_field("bias", "使用偏置", True),
        ], paddle_name="Conv1D" if name == "nn.Conv1d" else "Conv2D")
    add_spec(items, "nn.ConvTranspose2d", "二维转置卷积", conv, "上采样特征图，常用于图像生成。", "#2f83b9", [
        int_field("in_channels", "输入通道", 1),
        int_field("out_channels", "输出通道", 8),
        int_field("kernel_size", "卷积核", 3),
        int_field("stride", "步幅", 2),
        int_field("padding", "填充", 0, low=0),
        int_field("output_padding", "输出补边", 0, low=0),
        int_field("dilation", "膨胀", 1),
        int_field("groups", "分组数", 1),
        bool_field("bias", "使用偏置", True),
    ], paddle_name="Conv2DTranspose")
    for name, label in [("nn.MaxPool1d", "一维最大池化"), ("nn.MaxPool2d", "二维最大池化")]:
        add_spec(items, name, label, conv, "在每个窗口取最大值，缩小特征图。", "#3b9e83", [
            int_field("kernel_size", "池化窗口", 2),
            int_field("stride", "步幅", 2),
            int_field("padding", "填充", 0, low=0),
            int_field("dilation", "膨胀", 1),
            bool_field("ceil_mode", "向上取整", False),
        ], paddle_name="MaxPool1D" if name == "nn.MaxPool1d" else "MaxPool2D")
    for name, label in [("nn.AvgPool1d", "一维平均池化"), ("nn.AvgPool2d", "二维平均池化")]:
        add_spec(items, name, label, conv, "在每个窗口取平均值，缩小特征图。", "#3b9e83", [
            int_field("kernel_size", "池化窗口", 2),
            int_field("stride", "步幅", 2),
            int_field("padding", "填充", 0, low=0),
            bool_field("ceil_mode", "向上取整", False),
            bool_field("count_include_pad", "统计填充区域", False),
        ], paddle_name="AvgPool1D" if name == "nn.AvgPool1d" else "AvgPool2D")
    add_spec(items, "nn.AdaptiveAvgPool1d", "一维自适应平均池化", conv, "把特征维调整到指定大小。", "#3b9e83", [
        int_field("output_size", "输出大小", 1),
    ], paddle_name="AdaptiveAvgPool1D")
    add_spec(items, "nn.AdaptiveAvgPool2d", "二维自适应平均池化", conv, "把空间尺寸调整到指定大小。", "#3b9e83", [
        field("output_size", "输出大小", "int_list", [1, 1]),
    ], paddle_name="AdaptiveAvgPool2D")
    add_spec(items, "nn.Upsample", "上采样", conv, "按尺寸或倍率放大特征图。", "#3b9e83", [
        field("size", "目标尺寸", "int_list", [56, 56]),
        field("mode", "插值模式", "enum", "nearest", options=["nearest", "bilinear"]),
        bool_field("align_corners", "对齐角点", False),
    ])

    norm = "归一化"
    for name, label in [("nn.BatchNorm1d", "一维批归一化"), ("nn.BatchNorm2d", "二维批归一化")]:
        add_spec(items, name, label, norm, "稳定训练并加快收敛，常用于卷积层之后。", "#6a72c8", [
            int_field("num_features", "特征数/通道数", 8),
            field("eps", "数值稳定项 eps", "float", 1e-5, minimum=0, step=1e-6),
            field("momentum", "动量", "float", 0.1, minimum=0, maximum=1, step=0.01),
            bool_field("affine", "可学习缩放", True),
            bool_field("track_running_stats", "追踪运行统计", True),
        ], paddle_name="BatchNorm1D" if name == "nn.BatchNorm1d" else "BatchNorm2D")
    add_spec(items, "nn.LayerNorm", "层归一化", norm, "在最后一组特征维度上归一化。", "#6a72c8", [
        field("normalized_shape", "归一化形状", "int_list", [10]),
        field("eps", "数值稳定项 eps", "float", 1e-5, minimum=0, step=1e-6),
        bool_field("elementwise_affine", "逐元素缩放", True),
    ])
    add_spec(items, "nn.GroupNorm", "组归一化", norm, "将通道分组后在组内归一化。", "#6a72c8", [
        int_field("num_groups", "分组数", 1),
        int_field("num_channels", "通道数", 8),
        field("eps", "数值稳定项 eps", "float", 1e-5, minimum=0, step=1e-6),
        bool_field("affine", "可学习缩放", True),
    ])
    add_spec(items, "nn.InstanceNorm2d", "实例归一化", norm, "对每个样本、每个通道分别归一化。", "#6a72c8", [
        int_field("num_features", "通道数", 8),
        field("eps", "数值稳定项 eps", "float", 1e-5, minimum=0, step=1e-6),
        field("momentum", "动量", "float", 0.1, minimum=0, maximum=1, step=0.01),
        bool_field("affine", "可学习缩放", False),
        bool_field("track_running_stats", "追踪运行统计", False),
    ], paddle_name="InstanceNorm2D")

    activation = "激活函数"
    activation_color = "#cf6b42"
    for name, label, fields in [
        ("nn.ReLU", "ReLU", [bool_field("inplace", "原地操作", False)]),
        ("nn.ReLU6", "ReLU6", [bool_field("inplace", "原地操作", False)]),
        ("nn.LeakyReLU", "LeakyReLU", [
            field("negative_slope", "负半轴斜率", "float", 0.01, minimum=0, step=0.01),
            bool_field("inplace", "原地操作", False),
        ]),
        ("nn.ELU", "ELU", [
            field("alpha", "alpha", "float", 1.0, minimum=0, step=0.1),
            bool_field("inplace", "原地操作", False),
        ]),
        ("nn.GELU", "GELU", [field("approximate", "近似方式", "enum", "none", options=["none", "tanh"])]),
        ("nn.SiLU", "SiLU", [bool_field("inplace", "原地操作", False)]),
        ("nn.Sigmoid", "Sigmoid", []),
        ("nn.Tanh", "Tanh", []),
        ("nn.Softmax", "Softmax", [field("dim", "归一化维度", "int", -1, minimum=-4)]),
        ("nn.LogSoftmax", "LogSoftmax", [field("dim", "归一化维度", "int", -1, minimum=-4)]),
        ("nn.Mish", "Mish", [bool_field("inplace", "原地操作", False)]),
    ]:
        add_spec(
            items,
            name,
            label,
            activation,
            "逐元素非线性变换，让网络能够学习复杂函数。",
            activation_color,
            fields,
            paddle_name="Silu" if name == "nn.SiLU" else None,
        )

    shape = "张量与嵌入"
    add_spec(items, "nn.Embedding", "词嵌入", shape, "把离散索引映射为可学习向量。", "#9b6b45", [
        int_field("num_embeddings", "词表大小", 10),
        int_field("embedding_dim", "嵌入维度", 8),
    ])
    add_spec(items, "nn.PixelShuffle", "像素重排", shape, "把通道信息重排到空间维度。", "#9b6b45", [
        int_field("upscale_factor", "放大倍率", 2),
    ])
    add_spec(items, "nn.PixelUnshuffle", "像素反重排", shape, "把空间信息重排到通道维度。", "#9b6b45", [
        int_field("downscale_factor", "缩小倍率", 2),
    ])
    merge = "合并运算"
    add_spec(
        items,
        "merge.Add",
        "逐元素相加",
        merge,
        "将输入端口接收的多个同形张量逐元素相加。",
        "#8c98a5",
        [],
        torch_api="torch.add",
        paddle_api="paddle.add",
        input_mode="merge",
    )
    add_spec(
        items,
        "merge.Multiply",
        "逐元素相乘",
        merge,
        "将输入端口接收的多个同形张量逐元素相乘。",
        "#8c98a5",
        [],
        torch_api="torch.multiply",
        paddle_api="paddle.multiply",
        input_mode="merge",
    )
    add_spec(
        items,
        "merge.Concat",
        "张量拼接",
        merge,
        "沿指定维度拼接输入端口接收的多个张量，其余维度必须一致。",
        "#8c98a5",
        [
            field(
                "dim",
                "拼接维度",
                "int",
                -1,
                "PyTorch 使用 dim，Paddle 使用 axis",
                minimum=-4,
            )
        ],
        torch_api="torch.cat",
        paddle_api="paddle.concat",
        input_mode="merge",
    )
    condition = "条件运算"
    add_spec(
        items,
        "logic.Compare",
        "比较",
        condition,
        "比较两个同形张量，输出布尔张量。",
        "#8c98a5",
        [
            field(
                "operator",
                "比较运算",
                "enum",
                "gt",
                options=["gt", "lt", "ge", "le", "eq", "ne"],
            )
        ],
        input_mode="merge",
    )
    add_spec(
        items,
        "logic.All",
        "全部为真",
        condition,
        "将布尔张量归约为标量条件。",
        "#8c98a5",
        [],
        output_data_type="ScalarBool",
    )
    add_spec(
        items,
        "logic.CompareScalar",
        "与标量比较",
        condition,
        "把张量与固定标量比较，输出布尔张量，便于编写控制谓词。",
        "#8c98a5",
        [
            field(
                "operator",
                "比较运算",
                "enum",
                "gt",
                options=["gt", "lt", "ge", "le", "eq", "ne"],
            ),
            field(
                "threshold",
                "比较值",
                "float",
                0.0,
                "与输入逐元素比较的标量",
            ),
        ],
        torch_api="torch.gt",
        paddle_api="paddle.greater_than",
        output_data_type="Tensor",
    )
    control = "控制流"
    add_spec(
        items,
        "control.If",
        "If 分支",
        control,
        "按谓词子图选择 then 或 else 网络。",
        "#8c98a5",
        [],
        control_type="if",
    )
    add_spec(
        items,
        "control.For",
        "For 循环",
        control,
        "对同一状态签名执行固定次数的有界循环。",
        "#8c98a5",
        [int_field("iterations", "迭代次数", 2, low=0)],
        control_type="for",
    )
    add_spec(
        items,
        "control.While",
        "While 循环",
        control,
        "在谓词为真时重复循环体，并受最大次数限制。",
        "#8c98a5",
        [int_field("max_iterations", "最大迭代次数", 10, low=1)],
        control_type="while",
    )
    registry_path = (
        Path(__file__).resolve().parent / "data" / "pytorch_2_6_registry.json"
    )
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    for item in registry["classes"]:
        class_name = item["class_name"]
        items.append(
            BlockSpec(
                op=f"nn.{class_name}",
                label=class_name,
                category=item["category"],
                description=f"PyTorch 2.6 官方模块 {class_name}，仅在结构层建模。",
                color="#8c98a5",
                torch_name=class_name,
                torch_api=f"torch.nn.{class_name}",
                paddle_name=None,
                paddle_api=None,
                fields=[FieldSpec(**field) for field in item["fields"]],
                input_ports=[CatalogPort(**port) for port in item["inputs"]],
                output_ports=[CatalogPort(**port) for port in item["outputs"]],
                pytorch_only=True,
            )
        )
    return items


BLOCKS = _build_blocks()
BLOCK_BY_OP = {item.op: item for item in BLOCKS}


def catalog_response() -> CatalogResponse:
    return CatalogResponse(blocks=deepcopy(BLOCKS))


def defaults_for(op: str) -> dict[str, Any]:
    spec = BLOCK_BY_OP.get(op)
    if spec is None:
        return {}
    return {item.key: deepcopy(item.default) for item in spec.fields}

