from __future__ import annotations

from math import floor
from typing import Any

from .catalog import BLOCK_BY_OP
from .errors import ShapeError
from .models import (
    AnalysisResult,
    Diagnostic,
    GraphRegion,
    IRDocument,
    Node,
    NodeAnalysis,
    PortContract,
    PortInfo,
    StateContract,
    TraceResponse,
    TraceStep,
)
from .resources import apply_flat_overrides, find_resource
from .module_shapes import infer_registered_outputs
from .validation import (
    diagnostic,
    incoming_edges_by_node,
    input_port_names,
    normalize_and_validate,
    parameter_values,
    port_roles,
    topological_order,
)


def _named_dim(shape: list[int], dimension: int, label: str) -> int:
    try:
        return shape[dimension]
    except IndexError as exc:
        raise ShapeError(f"{label} 至少需要 {abs(dimension)} 维，当前形状为 {shape}") from exc


def _window_size(size: int, kernel: int, stride: int, padding: int, dilation: int) -> int:
    result = floor((size + 2 * padding - dilation * (kernel - 1) - 1) / stride + 1)
    if result <= 0:
        raise ShapeError(
            "池化/卷积窗口大于输入尺寸",
            "检查 kernel_size、stride 和 padding，或先使用更大的输入/更小的卷积核。",
        )
    return result


def _pool_spatial(
    shape: list[int],
    dimensions: int,
    params: dict[str, Any],
    *,
    transpose: bool = False,
) -> list[int]:
    expected = dimensions + 2
    if len(shape) != expected:
        raise ShapeError(f"{dimensions}D 卷积/池化期望 {expected} 维输入，当前为 {shape}")
    output = shape[:2]
    for size in shape[2:]:
        if transpose:
            output.append(
                (size - 1) * int(params["stride"])
                - 2 * int(params["padding"])
                + int(params["dilation"]) * (int(params["kernel_size"]) - 1)
                + int(params.get("output_padding", 0))
                + 1
            )
        else:
            output.append(
                _window_size(
                    size,
                    int(params["kernel_size"]),
                    int(params["stride"]),
                    int(params["padding"]),
                    int(params.get("dilation", 1)),
                )
            )
    if output[1] == 0:
        raise ShapeError("输出通道数必须大于 0")
    return output


def _normalize_dim(dimension: int, rank: int) -> int:
    return dimension if dimension >= 0 else rank + dimension


def infer_op(op: str, shape: list[int], params: dict[str, Any]) -> list[int]:
    if op == "logic.CompareScalar":
        return list(shape)
    if op == "logic.All":
        if not shape:
            raise ShapeError("All 需要布尔张量输入")
        if params.get("input_dtype") not in {None, "bool"}:
            raise ShapeError("All 的输入 dtype 必须为 bool")
        return []
    if op == "nn.Linear":
        if not shape:
            raise ShapeError("Linear 至少需要一维输入")
        if shape[-1] != int(params["in_features"]):
            raise ShapeError(
                f"Linear 期望最后一维为 {params['in_features']}，实际为 {shape[-1]}",
                "784 通常来自 28×28 图像展平：先 Flatten 再 Linear。",
            )
        return [*shape[:-1], int(params["out_features"])]

    if op in {"nn.Identity", "nn.Dropout", "nn.Dropout2d"}:
        return shape

    if op == "nn.Flatten":
        rank = len(shape)
        start = _normalize_dim(int(params["start_dim"]), rank)
        end = _normalize_dim(int(params["end_dim"]), rank)
        if not 0 <= start <= end < rank:
            raise ShapeError("Flatten 的 start_dim/end_dim 超出输入维度")
        flattened = 1
        for dim in shape[start : end + 1]:
            flattened *= dim
        return [*shape[:start], flattened, *shape[end + 1 :]]

    if op == "nn.Unflatten":
        rank = len(shape)
        dim = _normalize_dim(int(params["dim"]), rank)
        if not 0 <= dim < rank:
            raise ShapeError("Unflatten 的 dim 超出输入维度")
        sizes = [int(value) for value in params["sizes"]]
        if sizes.count(-1) > 1 or any(value == 0 for value in sizes):
            raise ShapeError("Unflatten 的新形状最多一个 -1，且不能包含 0")
        known = 1
        for value in sizes:
            if value > 0:
                known *= value
        if sizes.count(-1):
            if shape[dim] % known:
                raise ShapeError("Unflatten 的新形状无法整除原维度")
            sizes[sizes.index(-1)] = shape[dim] // known
        elif known != shape[dim]:
            raise ShapeError(f"Unflatten 新形状乘积 {known} 与原维度 {shape[dim]} 不相等")
        return [*shape[:dim], *sizes, *shape[dim + 1 :]]

    if op in {"nn.Conv1d", "nn.Conv2d", "nn.ConvTranspose2d"}:
        dimensions = 1 if op == "nn.Conv1d" else 2
        if len(shape) != dimensions + 2:
            raise ShapeError(f"{op} 需要 {dimensions + 2} 维输入，当前为 {shape}")
        if shape[1] != int(params["in_channels"]):
            raise ShapeError(
                f"{op} 期望输入通道 {params['in_channels']}，实际为 {shape[1]}",
                "卷积的 in_channels 必须与上一层的输出通道数一致。",
            )
        if int(params["in_channels"]) % int(params["groups"]) or int(params["out_channels"]) % int(
            params["groups"]
        ):
            raise ShapeError("输入/输出通道数必须能被 groups 整除")
        result = _pool_spatial(shape, dimensions, params, transpose=op == "nn.ConvTranspose2d")
        result[1] = int(params["out_channels"])
        return result

    if op in {"nn.MaxPool1d", "nn.MaxPool2d", "nn.AvgPool1d", "nn.AvgPool2d"}:
        dimensions = 1 if op.endswith("1d") else 2
        result = _pool_spatial(shape, dimensions, params)
        return result

    if op == "nn.AdaptiveAvgPool1d":
        if len(shape) < 3:
            raise ShapeError("AdaptiveAvgPool1d 需要至少三维输入")
        return [*shape[:-1], int(params["output_size"])]

    if op == "nn.AdaptiveAvgPool2d":
        if len(shape) < 4:
            raise ShapeError("AdaptiveAvgPool2d 需要至少四维输入")
        output_size = [int(value) for value in params["output_size"]]
        if len(output_size) == 1:
            output_size *= 2
        if len(output_size) != 2:
            raise ShapeError("AdaptiveAvgPool2d 输出尺寸需要 1 或 2 个整数")
        return [*shape[:-2], *output_size]

    if op == "nn.Upsample":
        size = [int(value) for value in params["size"]]
        if len(shape) < 3:
            raise ShapeError("Upsample 需要带空间维的输入")
        if len(size) != len(shape) - 2:
            raise ShapeError(f"Upsample 目标尺寸需要 {len(shape) - 2} 个空间值")
        return [*shape[:2], *size]

    if op in {"nn.BatchNorm1d", "nn.BatchNorm2d", "nn.InstanceNorm2d"}:
        if len(shape) < 2 or shape[1] != int(params["num_features"]):
            actual = shape[1] if len(shape) > 1 else "未知"
            raise ShapeError(
                f"{op} 期望 {params['num_features']} 个通道，实际为 {actual}",
                "归一化的 num_features 必须匹配上一层的输出通道数。",
            )
        return shape

    if op == "nn.LayerNorm":
        normalized = [int(value) for value in params["normalized_shape"]]
        if shape[-len(normalized) :] != normalized:
            raise ShapeError(
                f"LayerNorm 的 normalized_shape={normalized} 与输入尾部 {shape[-len(normalized):]} 不匹配"
            )
        return shape

    if op == "nn.GroupNorm":
        if len(shape) < 2 or shape[1] != int(params["num_channels"]):
            raise ShapeError("GroupNorm 的 num_channels 必须匹配输入通道")
        if int(params["num_channels"]) % int(params["num_groups"]):
            raise ShapeError("GroupNorm 通道数必须能被分组数整除")
        return shape

    if op in {
        "nn.ReLU",
        "nn.ReLU6",
        "nn.LeakyReLU",
        "nn.ELU",
        "nn.GELU",
        "nn.SiLU",
        "nn.Sigmoid",
        "nn.Tanh",
        "nn.Mish",
    }:
        return shape

    if op in {"nn.Softmax", "nn.LogSoftmax"}:
        dim = _normalize_dim(int(params["dim"]), len(shape))
        if not 0 <= dim < len(shape):
            raise ShapeError("Softmax 的 dim 超出输入维度")
        return shape

    if op == "nn.Embedding":
        if params.get("input_dtype") not in {None, "int64"} and shape:
            raise ShapeError("Embedding 的输入 dtype 应为 int64")
        return [*shape, int(params["embedding_dim"])]

    if op == "nn.PixelShuffle":
        if len(shape) != 4:
            raise ShapeError("PixelShuffle 需要 [B,C,H,W] 四维输入")
        factor = int(params["upscale_factor"])
        if shape[1] % (factor * factor):
            raise ShapeError(f"PixelShuffle 通道数 {shape[1]} 不能被 {factor}² 整除")
        return [shape[0], shape[1] // (factor * factor), shape[2] * factor, shape[3] * factor]

    if op == "nn.PixelUnshuffle":
        if len(shape) != 4:
            raise ShapeError("PixelUnshuffle 需要 [B,C,H,W] 四维输入")
        factor = int(params["downscale_factor"])
        if shape[2] % factor or shape[3] % factor:
            raise ShapeError(f"PixelUnshuffle 的高宽必须能被 {factor} 整除")
        return [shape[0], shape[1] * factor * factor, shape[2] // factor, shape[3] // factor]

    raise ShapeError(f"暂不支持 {op} 的结构推断")


def infer_merge_op(op: str, shapes: list[list[int]], params: dict[str, Any]) -> list[int]:
    if len(shapes) < 2:
        raise ShapeError(f"{op} 至少需要两个输入张量")
    if any(not shape for shape in shapes):
        raise ShapeError(f"{op} 的输入 shape 尚未确定")
    if op in {"merge.Add", "merge.Multiply"}:
        first = shapes[0]
        mismatch = next((shape for shape in shapes[1:] if shape != first), None)
        if mismatch is not None:
            raise ShapeError(
                f"{op} 要求所有输入 shape 完全一致，实际为 {first} 与 {mismatch}",
                "先调整分支参数，或使用 Concat 按维度拼接不同 shape 的特征。",
            )
        return list(first)
    if op == "logic.Compare":
        if len(shapes) != 2:
            raise ShapeError("Compare 必须连接两个输入张量")
        if shapes[0] != shapes[1]:
            raise ShapeError(
                f"Compare 要求两个输入 Shape 完全一致，实际为 {shapes[0]} 与 {shapes[1]}"
            )
        return list(shapes[0])
    if op == "merge.Concat":
        first = shapes[0]
        if any(len(shape) != len(first) for shape in shapes[1:]):
            raise ShapeError(
                "Concat 要求所有输入维数一致",
                "例如两个二维特征可以沿最后一维拼接。",
            )
        if not first:
            raise ShapeError("Concat 输入不能是标量")
        dim = int(params["dim"])
        normalized_dim = _normalize_dim(dim, len(first))
        if not 0 <= normalized_dim < len(first):
            raise ShapeError(f"Concat 的维度 {dim} 超出输入 rank {len(first)}")
        for shape in shapes[1:]:
            for index, (a, b) in enumerate(zip(first, shape)):
                if index != normalized_dim and a != b:
                    raise ShapeError(
                        f"Concat 在 dim={normalized_dim} 拼接时，第 {index} 维必须一致，实际为 {a} 与 {b}",
                        "只有拼接维度可以不同，其余维度必须相同。",
                    )
        result = list(first)
        result[normalized_dim] = sum(shape[normalized_dim] for shape in shapes)
        return result
    raise ShapeError(f"暂不支持合并算子 {op}")


def _shape_diagnostic(node_id: str, exc: ShapeError) -> Diagnostic:
    return diagnostic(
        "SHAPE_MISMATCH",
        str(exc),
        tip=exc.tip or "检查上一层的输出形状与本节点的参数是否一致。",
        node_id=node_id,
    )


def _ordered_input_edges(node: Node, edges: list[Any]) -> list[Any]:
    if node.state_contract is not None:
        by_port: dict[str, list[Any]] = {}
        for edge in edges:
            by_port.setdefault(edge.target.port, []).append(edge)
        ordered = []
        for port in node.state_contract.inputs:
            ordered.extend(
                sorted(by_port.pop(port.name, []), key=lambda edge: edge.id)
            )
        for remaining in by_port.values():
            ordered.extend(sorted(remaining, key=lambda edge: edge.id))
        return ordered
    spec = BLOCK_BY_OP.get(node.op)
    if spec is not None and spec.input_ports:
        by_port = {}
        for edge in edges:
            by_port.setdefault(edge.target.port, []).append(edge)
        ordered = []
        for port in spec.input_ports:
            ordered.extend(
                sorted(by_port.pop(port.name, []), key=lambda edge: edge.id)
            )
        return ordered
    return sorted(edges, key=lambda edge: edge.id)


def _apply_overrides(
    graph: Any,
    overrides: dict[str, Any],
) -> None:
    for path, value in overrides.items():
        head, separator, remainder = path.partition("/")
        node_id, dot, key = head.partition(".")
        if not dot:
            continue
        node = next((item for item in graph.nodes if item.id == node_id), None)
        if node is None:
            continue
        if separator:
            node.param_overrides[remainder] = value
        else:
            node.params[key] = value


def _bind_region_inputs(
    graph: Any,
    contracts: list[PortContract],
    shapes: list[list[int]],
    dtypes: list[str],
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    inputs = [node for node in graph.nodes if node.op == "Input"]
    contract_by_name = {port.name: port for port in contracts}
    for index, node in enumerate(inputs):
        name = str(node.params.get("name", ""))
        contract = contract_by_name.get(name)
        if contract is None and index < len(contracts):
            contract = contracts[index]
        if contract is None:
            diagnostics.append(
                diagnostic(
                    "REGION_INPUT_MISMATCH",
                    f"区域输入节点 {node.id} 不在接口契约中",
                    node_id=node.id,
                )
            )
            continue
        value_index = next(
            (i for i, port in enumerate(contracts) if port.name == contract.name),
            index,
        )
        node.params["name"] = contract.name
        node.params["data_type"] = contract.data_type
        node.params["sample_shape"] = (
            list(shapes[value_index])
            if value_index < len(shapes)
            else list(contract.shape or [])
        )
        node.params["dtype"] = (
            dtypes[value_index]
            if value_index < len(dtypes)
            else contract.dtype or "float32"
        )
    return diagnostics


def _resource_document(
    resource: Any,
    overrides: dict[str, Any],
    framework: str,
) -> IRDocument:
    graph = resource.graph.model_copy(deep=True)
    regions = {
        key: value.model_copy(deep=True)
        for key, value in resource.regions.items()
    }
    apply_flat_overrides(graph, regions, overrides)
    return IRDocument(
        target_framework=framework,
        graph=graph,
        regions=regions,
        resources=resource.dependencies,
        ui=resource.ui,
    )


def _contracts_from_result(
    graph: Any,
    templates: list[PortContract],
    result: AnalysisResult,
) -> list[PortContract]:
    analyzed = {node.node_id: node for node in result.nodes}
    outputs = [node for node in graph.nodes if node.op == "Output"]
    contracts: list[PortContract] = []
    for index, output_node in enumerate(outputs):
        template = (
            templates[index]
            if index < len(templates)
            else PortContract(name=str(output_node.params.get("name", output_node.id)))
        )
        port = next(
            (
                item
                for item in analyzed.get(output_node.id, NodeAnalysis(
                    node_id=output_node.id,
                    label="",
                )).ports
                if item.io == "in"
            ),
            None,
        )
        contracts.append(
            template.model_copy(
                update={
                    "shape": port.shape if port else template.shape,
                    "dtype": port.dtype if port else template.dtype,
                }
            )
        )
    return contracts


def _state_ports(
    contract: StateContract | None,
    input_shapes: list[list[int]],
    input_dtypes: list[str],
    outputs: list[PortContract],
) -> list[PortInfo]:
    ports: list[PortInfo] = []
    if contract is not None:
        for index, port in enumerate(contract.inputs):
            ports.append(
                PortInfo(
                    name=port.name,
                    io="in",
                    data_type=port.data_type,
                    role=port.role,
                    shape=input_shapes[index] if index < len(input_shapes) else port.shape,
                    dtype=input_dtypes[index] if index < len(input_dtypes) else port.dtype,
                )
            )
    for port in outputs:
        ports.append(
            PortInfo(
                name=port.name,
                io="out",
                data_type=port.data_type,
                role=port.role,
                shape=port.shape,
                dtype=port.dtype,
            )
        )
    return ports


def _analyze_region(
    ir: IRDocument,
    region: GraphRegion,
    input_shapes: list[list[int]],
    input_dtypes: list[str],
    depth: int,
) -> tuple[AnalysisResult, list[Diagnostic]]:
    graph = region.graph.model_copy(deep=True)
    diagnostics = _bind_region_inputs(
        graph,
        region.inputs,
        input_shapes,
        input_dtypes,
    )
    child = IRDocument(
        target_framework=ir.target_framework,
        graph=graph,
        regions=ir.regions,
        resources=ir.resources,
        ui=region.ui,
    )
    result = _analyze_with_depth(child, depth + 1)
    diagnostics.extend(result.diagnostics)
    contracts = _contracts_from_result(graph, region.outputs, result)
    result.nodes = result.nodes
    return result, diagnostics


def _analyze_control_node(
    ir: IRDocument,
    node: Node,
    input_shapes: list[list[int]],
    input_dtypes: list[str],
    depth: int,
    diagnostics: list[Diagnostic],
) -> list[PortContract]:
    if depth >= 3:
        diagnostics.append(
            diagnostic(
                "CONTROL_DEPTH_EXCEEDED",
                "控制流嵌套超过 3 层",
                node_id=node.id,
            )
        )
        return []
    contract = node.state_contract
    if contract is None:
        diagnostics.append(
            diagnostic(
                "CONTROL_STATE_CONTRACT",
                "控制容器缺少状态契约",
                node_id=node.id,
            )
        )
        return []

    def region(name: str) -> GraphRegion | None:
        region_id = node.region_refs.get(name)
        if region_id is None:
            diagnostics.append(
                diagnostic(
                    "CONTROL_REGION_MISSING",
                    f"{node.op} 缺少 {name} 区域",
                    node_id=node.id,
                )
            )
            return None
        found = ir.regions.get(region_id)
        if found is None:
            diagnostics.append(
                diagnostic(
                    "CONTROL_REGION_NOT_FOUND",
                    f"区域 {region_id} 不存在",
                    node_id=node.id,
                )
            )
        return found

    def analyze_region(
        name: str,
        include_index: bool,
    ) -> tuple[GraphRegion | None, AnalysisResult | None, list[PortContract]]:
        found = region(name)
        if found is None:
            return None, None, []
        region_shapes = list(input_shapes)
        region_dtypes = list(input_dtypes)
        if include_index and any(port.name == "index" for port in found.inputs):
            region_shapes.append([])
            region_dtypes.append("int64")
        result, region_diagnostics = _analyze_region(
            ir,
            found,
            region_shapes,
            region_dtypes,
            depth,
        )
        diagnostics.extend(region_diagnostics)
        graph = found.graph
        contracts = _contracts_from_result(graph, found.outputs, result)
        return found, result, contracts

    if node.op == "control.If":
        _, _, predicate_outputs = analyze_region("predicate", False)
        if (
            len(predicate_outputs) != 1
            or predicate_outputs[0].data_type != "ScalarBool"
        ):
            diagnostics.append(
                diagnostic(
                    "IF_PREDICATE_OUTPUT",
                    "If 谓词子图必须输出一个 ScalarBool",
                    node_id=node.id,
                )
            )
        _, _, then_outputs = analyze_region("then", False)
        _, _, else_outputs = analyze_region("else", False)
        if _signature(then_outputs) != _signature(else_outputs):
            diagnostics.append(
                diagnostic(
                    "IF_BRANCH_SIGNATURE",
                    "If 的 then/else 分支输出签名必须完全一致",
                    node_id=node.id,
                )
            )
        return then_outputs

    _, _, body_outputs = analyze_region("body", True)
    expected = [
        PortContract(
            name=port.name,
            data_type=port.data_type,
            shape=input_shapes[index] if index < len(input_shapes) else port.shape,
            dtype=input_dtypes[index] if index < len(input_dtypes) else port.dtype,
            required=port.required,
            role=port.role,
        )
        for index, port in enumerate(contract.outputs)
    ]
    if _signature(body_outputs) != _signature(expected):
        diagnostics.append(
            diagnostic(
                "LOOP_SIGNATURE_MISMATCH",
                f"{node.op} 循环体输出必须保持状态签名不变",
                node_id=node.id,
            )
        )
    if node.op == "control.While":
        _, _, predicate_outputs = analyze_region("predicate", True)
        if (
            len(predicate_outputs) != 1
            or predicate_outputs[0].data_type != "ScalarBool"
        ):
            diagnostics.append(
                diagnostic(
                    "WHILE_PREDICATE_OUTPUT",
                    "While 谓词子图必须输出一个 ScalarBool",
                    node_id=node.id,
                )
            )
    return expected


def _signature(contracts: list[PortContract]) -> list[tuple[str, str, str | None, tuple[int, ...] | None]]:
    return [
        (
            port.name,
            port.data_type,
            port.dtype,
            tuple(port.shape) if port.shape is not None else None,
        )
        for port in contracts
    ]


def analyze(ir: IRDocument) -> AnalysisResult:
    return _analyze_with_depth(ir, 0)


def _analyze_with_depth(ir: IRDocument, depth: int) -> AnalysisResult:
    normalized, diagnostics = normalize_and_validate(ir)
    if diagnostics:
        return AnalysisResult(
            valid=False,
            normalized_ir=normalized,
            nodes=[],
            diagnostics=diagnostics,
            chain_count=sum(node.op == "Output" for node in normalized.graph.nodes),
        )
    node_analyses, trace_steps, diagnostics = _analyze_graph(normalized, depth)

    if not any(item.severity == "error" for item in diagnostics):
        normalized.check_info = None
    return AnalysisResult(
        valid=not any(item.severity == "error" for item in diagnostics),
        normalized_ir=normalized,
        nodes=list(node_analyses.values()),
        diagnostics=diagnostics,
        chain_count=sum(node.op == "Output" for node in normalized.graph.nodes),
    )


def _analyze_graph(
    ir: IRDocument,
    depth: int = 0,
) -> tuple[dict[str, NodeAnalysis], list[TraceStep], list[Diagnostic]]:
    incoming = incoming_edges_by_node(ir)
    node_by_id = {node.id: node for node in ir.graph.nodes}
    shapes: dict[tuple[str, str], list[int]] = {}
    dtypes: dict[tuple[str, str], str] = {}
    node_analyses: dict[str, NodeAnalysis] = {}
    trace_steps: list[TraceStep] = []
    diagnostics: list[Diagnostic] = []

    for node in topological_order(ir):
        if node.op == "Input":
            params = parameter_values(node)
            shape = [int(value) for value in params["sample_shape"]]
            dtype = str(params["dtype"])
            data_type = str(params.get("data_type", "Tensor"))
            _, output_role = port_roles(node)
            shapes[(node.id, "out")] = shape
            dtypes[(node.id, "out")] = dtype
            node_analyses[node.id] = NodeAnalysis(
                node_id=node.id,
                label=str(params["name"]),
                ports=[
                    PortInfo(
                        name="out",
                        io="out",
                        data_type=data_type,
                        role=output_role,
                        shape=shape,
                        dtype=dtype,
                    )
                ],
            )
            trace_steps.append(
                TraceStep(
                    index=len(trace_steps),
                    node_id=node.id,
                    label=f"Input · {params['name']}",
                    output_shape=shape,
                    dtype=dtype,
                    note="由画布中的示例形状提供。",
                )
            )
            continue

        if node.op == "Output":
            edge = incoming[node.id][0]
            source = node_by_id[edge.source.node_id]
            shape = shapes.get((source.id, edge.source.port), [])
            dtype = dtypes.get((source.id, edge.source.port), "float32")
            input_role, _ = port_roles(node)
            output_data_type = str(
                parameter_values(node).get("data_type", "Tensor")
            )
            output_name = str(parameter_values(node)["name"])
            node_analyses[node.id] = NodeAnalysis(
                node_id=node.id,
                label=output_name,
                ports=[
                    PortInfo(
                        name="x",
                        io="in",
                        data_type=output_data_type,
                        role=input_role,
                        shape=shape or None,
                        dtype=dtype,
                    )
                ],
            )
            trace_steps.append(
                TraceStep(
                    index=len(trace_steps),
                    node_id=node.id,
                    label=f"Output · {output_name}",
                    input_shape=shape or None,
                    input_shapes=[shape] if shape else None,
                    output_shape=shape or None,
                    dtype=dtype,
                    note="结构模拟完成。",
                )
            )
            continue

        if node.op == "composite.instance":
            edges = _ordered_input_edges(node, incoming[node.id])
            input_shapes = [
                shapes.get((edge.source.node_id, edge.source.port), [])
                for edge in edges
            ]
            input_dtypes = [
                dtypes.get((edge.source.node_id, edge.source.port), "float32")
                for edge in edges
            ]
            resource = find_resource(ir, node.composite_ref)
            if resource is None:
                diagnostics.append(
                    diagnostic(
                        "MISSING_COMPOSITE_RESOURCE",
                        "复合实例找不到对应资源版本",
                        node_id=node.id,
                    )
                )
                output_contracts: list[PortContract] = []
            elif depth >= 3:
                diagnostics.append(
                    diagnostic(
                        "COMPOSITE_DEPTH_EXCEEDED",
                        "复合模块嵌套超过 3 层",
                        node_id=node.id,
                    )
                )
                output_contracts = resource.outputs
            else:
                child = _resource_document(
                    resource,
                    node.param_overrides,
                    ir.target_framework,
                )
                diagnostics.extend(
                    _bind_region_inputs(
                        child.graph,
                        resource.inputs,
                        input_shapes,
                        input_dtypes,
                    )
                )
                child_result = _analyze_with_depth(child, depth + 1)
                diagnostics.extend(child_result.diagnostics)
                output_contracts = _contracts_from_result(
                    child.graph,
                    resource.outputs,
                    child_result,
                )
            ports = _state_ports(
                node.state_contract,
                input_shapes,
                input_dtypes,
                output_contracts,
            )
            node_analyses[node.id] = NodeAnalysis(
                node_id=node.id,
                label=resource.name if resource else node.op,
                ports=ports,
            )
            trace_steps.append(
                TraceStep(
                    index=len(trace_steps),
                    node_id=node.id,
                    label=resource.name if resource else node.op,
                    input_shape=input_shapes[0] if input_shapes else None,
                    input_shapes=input_shapes or None,
                    output_shape=(
                        output_contracts[0].shape if output_contracts else None
                    ),
                    dtype=output_contracts[0].dtype if output_contracts else None,
                    note="复合资源结构推演",
                )
            )
            for port in output_contracts:
                shapes[(node.id, port.name)] = port.shape or []
                dtypes[(node.id, port.name)] = port.dtype or "float32"
            continue

        if node.op.startswith("control."):
            edges = _ordered_input_edges(node, incoming[node.id])
            input_shapes = [
                shapes.get((edge.source.node_id, edge.source.port), [])
                for edge in edges
            ]
            input_dtypes = [
                dtypes.get((edge.source.node_id, edge.source.port), "float32")
                for edge in edges
            ]
            output_contracts = _analyze_control_node(
                ir,
                node,
                input_shapes,
                input_dtypes,
                depth,
                diagnostics,
            )
            ports = _state_ports(
                node.state_contract,
                input_shapes,
                input_dtypes,
                output_contracts,
            )
            node_analyses[node.id] = NodeAnalysis(
                node_id=node.id,
                label=node.op,
                ports=ports,
            )
            trace_steps.append(
                TraceStep(
                    index=len(trace_steps),
                    node_id=node.id,
                    label=node.op,
                    input_shape=input_shapes[0] if input_shapes else None,
                    input_shapes=input_shapes or None,
                    output_shape=(
                        output_contracts[0].shape if output_contracts else None
                    ),
                    dtype=output_contracts[0].dtype if output_contracts else None,
                    note="结构化控制流推演",
                )
            )
            for port in output_contracts:
                shapes[(node.id, port.name)] = port.shape or []
                dtypes[(node.id, port.name)] = port.dtype or "float32"
            continue

        edges = _ordered_input_edges(node, incoming[node.id])
        input_shapes = [
            shapes.get((edge.source.node_id, edge.source.port), [])
            for edge in edges
        ]
        input_dtypes = [
            dtypes.get((edge.source.node_id, edge.source.port), "float32")
            for edge in edges
        ]
        params = parameter_values(node)
        params["input_dtype"] = input_dtypes[0] if input_dtypes else "float32"
        try:
            spec = BLOCK_BY_OP[node.op]
            if spec.input_mode == "merge" and len(edges) < 2:
                raise ShapeError(f"{node.op} 至少需要连接两个输入分支")
            if spec.input_mode == "merge" and len(set(input_dtypes)) > 1:
                raise ShapeError(
                    f"{node.op} 的输入 dtype 不一致：{', '.join(input_dtypes)}"
                )
            if node.op.startswith("merge.") or node.op == "logic.Compare":
                output_shape = infer_merge_op(node.op, input_shapes, params)
                output_values = [("out", output_shape, "bool" if node.op == "logic.Compare" else input_dtypes[0])]
            elif spec.input_ports:
                primary, auxiliary = infer_registered_outputs(
                    spec,
                    input_shapes,
                    input_dtypes,
                    params,
                )
                inferred = primary + auxiliary
                inferred_by_name = {name: (shape, dtype) for name, shape, dtype in inferred}
                output_values = []
                for port in spec.output_ports:
                    shape, output_dtype = inferred_by_name.get(
                        port.name,
                        (primary[0][1], primary[0][2]),
                    )
                    output_values.append((port.name, shape, output_dtype))
            else:
                output_shape = infer_op(node.op, input_shapes[0], params)
                output_values = [
                    (
                        "out",
                        output_shape,
                        "bool"
                        if node.op in {"logic.All", "logic.CompareScalar"}
                        else "float32"
                        if node.op == "nn.Embedding"
                        else input_dtypes[0],
                    )
                ]
        except ShapeError as exc:
            diagnostics.append(_shape_diagnostic(node.id, exc))
            output_values = [
                (
                    (spec.output_ports[0].name if spec and spec.output_ports else "out"),
                    [],
                    input_dtypes[0] if input_dtypes else "float32",
                )
            ]
        for port_name, shape_value, dtype_value in output_values:
            shapes[(node.id, port_name)] = shape_value
            dtypes[(node.id, port_name)] = dtype_value
        _, output_role = port_roles(node)
        spec = BLOCK_BY_OP.get(node.op)
        ports = [
            PortInfo(
                name=edge.target.port,
                io="in",
                shape=input_shapes[index] or None,
                dtype=input_dtypes[index],
            )
            for index, edge in enumerate(edges)
        ]
        for port_name, shape_value, dtype_value in output_values:
            port_spec = next(
                (item for item in (spec.output_ports if spec else []) if item.name == port_name),
                None,
            )
            ports.append(
                PortInfo(
                    name=port_name,
                    io="out",
                    data_type=(
                        port_spec.data_type
                        if port_spec is not None
                        else spec.output_data_type
                        if spec is not None
                        else "Tensor"
                    ),
                    role=port_spec.role if port_spec is not None else output_role,
                    shape=shape_value or None,
                    dtype=dtype_value,
                )
            )
        first_port_name, first_shape, first_dtype = output_values[0]
        node_analyses[node.id] = NodeAnalysis(
            node_id=node.id,
            label=node.op,
            ports=ports,
        )
        trace_steps.append(
            TraceStep(
                index=len(trace_steps),
                node_id=node.id,
                label=node.op,
                input_shape=input_shapes[0] if input_shapes else None,
                input_shapes=input_shapes or None,
                output_shape=first_shape or None,
                dtype=first_dtype,
                note=node.teaching_note,
            )
        )
    return node_analyses, trace_steps, diagnostics


def trace_preview(ir: IRDocument) -> TraceResponse:
    normalized, diagnostics = normalize_and_validate(ir)
    if diagnostics:
        return TraceResponse(steps=[], diagnostics=diagnostics)
    _, trace_steps, diagnostics = _analyze_graph(normalized)
    return TraceResponse(steps=trace_steps, diagnostics=diagnostics)
