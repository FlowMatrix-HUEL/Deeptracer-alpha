from __future__ import annotations

from .models import (
    Edge,
    EdgeEndpoint,
    Graph,
    GraphMeta,
    IRDocument,
    Node,
    Position,
    UiState,
)


def _chain_document(
    name: str,
    nodes: list[Node],
    positions: dict[str, tuple[float, float]],
    note: str = "",
) -> IRDocument:
    edges: list[Edge] = []
    for index in range(len(nodes) - 1):
        edges.append(
            Edge(
                id=f"e_{index + 1}",
                source=EdgeEndpoint(node_id=nodes[index].id, port="out"),
                target=EdgeEndpoint(node_id=nodes[index + 1].id, port="x"),
            )
        )
    return IRDocument(
        graph_meta=GraphMeta(name=name, author="NetBrick", note=note),
        graph=Graph(nodes=nodes, edges=edges),
        ui=UiState(
            positions={
                node_id: Position(x=point[0], y=point[1])
                for node_id, point in positions.items()
            }
        ),
    )


def mnist_mlp() -> IRDocument:
    nodes = [
        Node(
            id="input_x",
            op="Input",
            params={"name": "x", "sample_shape": [1, 784], "dtype": "float32"},
            teaching_note="MNIST 的 28×28 图像已展平为 784。",
        ),
        Node(
            id="linear_1",
            op="nn.Linear",
            params={"in_features": 784, "out_features": 128, "bias": True},
            teaching_note="第一层把 784 个像素压缩到 128 个隐藏特征。",
        ),
        Node(id="relu_1", op="nn.ReLU", params={"inplace": False}),
        Node(id="linear_2", op="nn.Linear", params={"in_features": 128, "out_features": 10, "bias": True}),
        Node(
            id="output_logits",
            op="Output",
            params={"name": "logits"},
            teaching_note="10 个数值分别对应数字 0–9 的类别分数。",
        ),
    ]
    return _chain_document(
        "MNIST MLP",
        nodes,
        {
            "input_x": (60, 190),
            "linear_1": (340, 190),
            "relu_1": (620, 190),
            "linear_2": (900, 190),
            "output_logits": (1180, 190),
        },
        note="一个最小、完整的多层感知机课堂示例。",
    )


def simple_cnn() -> IRDocument:
    nodes = [
        Node(
            id="input_image",
            op="Input",
            params={"name": "image", "sample_shape": [1, 1, 28, 28], "dtype": "float32"},
            teaching_note="单通道 28×28 的 MNIST 图像。",
        ),
        Node(
            id="conv_1",
            op="nn.Conv2d",
            params={
                "in_channels": 1,
                "out_channels": 8,
                "kernel_size": 3,
                "stride": 1,
                "padding": 1,
                "dilation": 1,
                "groups": 1,
                "bias": True,
            },
            teaching_note="八个 3×3 卷积核从图像中提取局部边缘和纹理。",
        ),
        Node(id="relu_1", op="nn.ReLU", params={"inplace": False}),
        Node(
            id="pool_1",
            op="nn.MaxPool2d",
            params={
                "kernel_size": 2,
                "stride": 2,
                "padding": 0,
                "dilation": 1,
                "ceil_mode": False,
            },
        ),
        Node(id="flatten_1", op="nn.Flatten", params={"start_dim": 1, "end_dim": -1}),
        Node(
            id="linear_1",
            op="nn.Linear",
            params={"in_features": 1568, "out_features": 10, "bias": True},
            teaching_note="8×14×14 = 1568，卷积特征被映射到 10 个类别。",
        ),
        Node(id="output_logits", op="Output", params={"name": "logits"}),
    ]
    return _chain_document(
        "Simple CNN",
        nodes,
        {
            "input_image": (50, 160),
            "conv_1": (330, 160),
            "relu_1": (610, 160),
            "pool_1": (890, 160),
            "flatten_1": (1170, 160),
            "linear_1": (1450, 160),
            "output_logits": (1730, 160),
        },
        note="观察卷积、池化、展平和全连接之间的 shape 变化。",
    )


def multi_chain() -> IRDocument:
    nodes = [
        Node(id="input_image", op="Input", params={"name": "image", "sample_shape": [1, 8, 8], "dtype": "float32"}),
        Node(id="flatten_image", op="nn.Flatten", params={"start_dim": 1, "end_dim": -1}),
        Node(id="image_fc", op="nn.Linear", params={"in_features": 64, "out_features": 16, "bias": True}),
        Node(id="output_visual", op="Output", params={"name": "visual_feature"}),
        Node(id="input_table", op="Input", params={"name": "table", "sample_shape": [1, 4], "dtype": "float32"}),
        Node(id="table_fc", op="nn.Linear", params={"in_features": 4, "out_features": 8, "bias": True}),
        Node(id="table_relu", op="nn.ReLU", params={"inplace": False}),
        Node(id="output_table", op="Output", params={"name": "table_logit"}),
    ]
    edges = [
        Edge(
            id="e_image_1",
            source=EdgeEndpoint(node_id="input_image", port="out"),
            target=EdgeEndpoint(node_id="flatten_image", port="x"),
        ),
        Edge(
            id="e_image_2",
            source=EdgeEndpoint(node_id="flatten_image", port="out"),
            target=EdgeEndpoint(node_id="image_fc", port="x"),
        ),
        Edge(
            id="e_image_3",
            source=EdgeEndpoint(node_id="image_fc", port="out"),
            target=EdgeEndpoint(node_id="output_visual", port="x"),
        ),
        Edge(
            id="e_table_1",
            source=EdgeEndpoint(node_id="input_table", port="out"),
            target=EdgeEndpoint(node_id="table_fc", port="x"),
        ),
        Edge(
            id="e_table_2",
            source=EdgeEndpoint(node_id="table_fc", port="out"),
            target=EdgeEndpoint(node_id="table_relu", port="x"),
        ),
        Edge(
            id="e_table_3",
            source=EdgeEndpoint(node_id="table_relu", port="out"),
            target=EdgeEndpoint(node_id="output_table", port="x"),
        ),
    ]
    return IRDocument(
        graph_meta=GraphMeta(
            name="Dual Branch Model",
            author="NetBrick",
            note="两条完全独立的数据链，演示一个文件中的多输入、多输出模型。",
        ),
        graph=Graph(nodes=nodes, edges=edges),
        ui=UiState(
            positions={
                "input_image": Position(x=60, y=80),
                "flatten_image": Position(x=340, y=80),
                "image_fc": Position(x=620, y=80),
                "output_visual": Position(x=900, y=80),
                "input_table": Position(x=60, y=330),
                "table_fc": Position(x=340, y=330),
                "table_relu": Position(x=620, y=330),
                "output_table": Position(x=900, y=330),
            }
        ),
    )


def simple_unet() -> IRDocument:
    nodes = [
        Node(
            id="input_image",
            op="Input",
            params={"name": "image", "sample_shape": [1, 1, 32, 32], "dtype": "float32"},
            teaching_note="教学版 U-Net 使用 32×32 单通道图像。",
        ),
        Node(
            id="encoder_conv",
            op="nn.Conv2d",
            params={
                "in_channels": 1,
                "out_channels": 8,
                "kernel_size": 3,
                "stride": 1,
                "padding": 1,
                "dilation": 1,
                "groups": 1,
                "bias": True,
            },
            teaching_note="编码器提取局部纹理，同时保持空间尺寸。",
        ),
        Node(id="encoder_relu", op="nn.ReLU", params={"inplace": False}),
        Node(
            id="downsample",
            op="nn.MaxPool2d",
            params={
                "kernel_size": 2,
                "stride": 2,
                "padding": 0,
                "dilation": 1,
                "ceil_mode": False,
            },
            teaching_note="下采样把空间尺寸减半。",
        ),
        Node(
            id="bottleneck",
            op="nn.Conv2d",
            params={
                "in_channels": 8,
                "out_channels": 16,
                "kernel_size": 3,
                "stride": 1,
                "padding": 1,
                "dilation": 1,
                "groups": 1,
                "bias": True,
            },
        ),
        Node(id="bottleneck_relu", op="nn.ReLU", params={"inplace": False}),
        Node(
            id="upsample",
            op="nn.Upsample",
            params={"size": [32, 32], "mode": "nearest", "align_corners": False},
            teaching_note="解码器恢复到原图分辨率。",
        ),
        Node(
            id="decoder_conv",
            op="nn.Conv2d",
            params={
                "in_channels": 16,
                "out_channels": 1,
                "kernel_size": 3,
                "stride": 1,
                "padding": 1,
                "dilation": 1,
                "groups": 1,
                "bias": True,
            },
        ),
        Node(id="mask_sigmoid", op="nn.Sigmoid", params={}),
        Node(
            id="output_mask",
            op="Output",
            params={"name": "mask_logits"},
            teaching_note="输出与输入同尺寸的掩码张量。",
        ),
    ]
    return _chain_document(
        "Simple U-Net",
        nodes,
        {
            "input_image": (50, 150),
            "encoder_conv": (330, 150),
            "encoder_relu": (610, 150),
            "downsample": (890, 150),
            "bottleneck": (1170, 150),
            "bottleneck_relu": (1450, 150),
            "upsample": (1730, 150),
            "decoder_conv": (2010, 150),
            "mask_sigmoid": (2290, 150),
            "output_mask": (2570, 150),
        },
        note="简化的编码器-解码器结构，用于演示下采样与恢复分辨率；不执行训练。",
    )


def parallel_add() -> IRDocument:
    nodes = [
        Node(
            id="input_x",
            op="Input",
            params={"name": "x", "sample_shape": [1, 784], "dtype": "float32"},
            teaching_note="同一个输入会被并行送入两条特征分支。",
        ),
        Node(
            id="left_linear",
            op="nn.Linear",
            params={"in_features": 784, "out_features": 32, "bias": True},
        ),
        Node(id="left_relu", op="nn.ReLU", params={"inplace": False}),
        Node(
            id="right_linear",
            op="nn.Linear",
            params={"in_features": 784, "out_features": 32, "bias": True},
        ),
        Node(
            id="merge_add",
            op="merge.Add",
            params={},
            teaching_note="两个分支的形状都是 [1,32]，可以逐元素相加。",
        ),
        Node(id="output_y", op="Output", params={"name": "y"}),
    ]
    edges = [
        Edge(
            id="e1",
            source=EdgeEndpoint(node_id="input_x", port="out"),
            target=EdgeEndpoint(node_id="left_linear", port="x"),
        ),
        Edge(
            id="e2",
            source=EdgeEndpoint(node_id="input_x", port="out"),
            target=EdgeEndpoint(node_id="right_linear", port="x"),
        ),
        Edge(
            id="e3",
            source=EdgeEndpoint(node_id="left_linear", port="out"),
            target=EdgeEndpoint(node_id="left_relu", port="x"),
        ),
        Edge(
            id="e4",
            source=EdgeEndpoint(node_id="left_relu", port="out"),
            target=EdgeEndpoint(node_id="merge_add", port="x"),
        ),
        Edge(
            id="e5",
            source=EdgeEndpoint(node_id="right_linear", port="out"),
            target=EdgeEndpoint(node_id="merge_add", port="x"),
        ),
        Edge(
            id="e6",
            source=EdgeEndpoint(node_id="merge_add", port="out"),
            target=EdgeEndpoint(node_id="output_y", port="x"),
        ),
    ]
    return IRDocument(
        graph_meta=GraphMeta(
            name="Parallel Add",
            author="NetBrick",
            note="单个输入并行经过两条分支，再用 Add 合并。",
        ),
        graph=Graph(nodes=nodes, edges=edges),
        ui=UiState(
            positions={
                "input_x": Position(x=60, y=210),
                "left_linear": Position(x=340, y=90),
                "left_relu": Position(x=620, y=90),
                "right_linear": Position(x=340, y=330),
                "merge_add": Position(x=900, y=210),
                "output_y": Position(x=1180, y=210),
            }
        ),
    )


SAMPLES = {
    "mnist-mlp": {
        "id": "mnist-mlp",
        "title": "MNIST MLP",
        "description": "784 → 128 → 10 的入门全连接网络",
        "ir": mnist_mlp,
    },
    "simple-cnn": {
        "id": "simple-cnn",
        "title": "CNN 图像分类",
        "description": "卷积、池化、展平与分类输出",
        "ir": simple_cnn,
    },
    "simple-unet": {
        "id": "simple-unet",
        "title": "简单 U-Net",
        "description": "编码、下采样、解码和掩码输出",
        "ir": simple_unet,
    },
    "multi-chain": {
        "id": "multi-chain",
        "title": "多输入多输出",
        "description": "两条独立的线性数据链",
        "ir": multi_chain,
    },
    "parallel-add": {
        "id": "parallel-add",
        "title": "并行分支 Add 汇合",
        "description": "单输入 fan-out 到两条分支后合并",
        "ir": parallel_add,
    },
}
