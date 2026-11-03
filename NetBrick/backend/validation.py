from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from collections import deque
from typing import Any

from .catalog import BLOCK_BY_OP
from .models import Diagnostic, Edge, IRDocument, Node, StateContract
from .resources import find_resource, resolve_resource_dependencies


def diagnostic(
    code: str,
    message: str,
    *,
    tip: str = "",
    node_id: str | None = None,
    edge_id: str | None = None,
    field: str | None = None,
    severity: str = "error",
) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=severity,  # type: ignore[arg-type]
        node_id=node_id,
        edge_id=edge_id,
        field=field,
        message=message,
        teaching_tip=tip,
    )


def _validate_params(node: Node) -> list[Diagnostic]:
    if node.op == "composite.instance":
        return []
    result: list[Diagnostic] = []
    spec = BLOCK_BY_OP.get(node.op)
    if spec is None:
        return [
            diagnostic(
                "UNKNOWN_OP",
                f"未知算子：{node.op}",
                tip="请从左侧块库重新拖入一个受支持的算子。",
                node_id=node.id,
            )
        ]

    known_keys = {item.key for item in spec.fields}
    for key in node.params:
        if key not in known_keys:
            result.append(
                diagnostic(
                    "UNKNOWN_PARAM",
                    f"{node.op} 不支持参数 {key}",
                    node_id=node.id,
                    field=key,
                )
            )

    for item in spec.fields:
        value = node.params.get(item.key, item.default)
        if item.type == "int":
            if isinstance(value, bool) or not isinstance(value, int):
                result.append(
                    diagnostic(
                        "PARAM_TYPE",
                        f"{item.label} 必须是整数",
                        node_id=node.id,
                        field=item.key,
                    )
                )
                continue
            if item.minimum is not None and value < item.minimum:
                result.append(
                    diagnostic(
                        "PARAM_RANGE",
                        f"{item.label} 不能小于 {item.minimum:g}",
                        node_id=node.id,
                        field=item.key,
                    )
                )
            if item.maximum is not None and value > item.maximum:
                result.append(
                    diagnostic(
                        "PARAM_RANGE",
                        f"{item.label} 不能大于 {item.maximum:g}",
                        node_id=node.id,
                        field=item.key,
                    )
                )
        elif item.type == "float":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                result.append(
                    diagnostic(
                        "PARAM_TYPE",
                        f"{item.label} 必须是数字",
                        node_id=node.id,
                        field=item.key,
                    )
                )
                continue
            if item.minimum is not None and value < item.minimum:
                result.append(
                    diagnostic("PARAM_RANGE", f"{item.label} 超出允许范围", node_id=node.id, field=item.key)
                )
            if item.maximum is not None and value > item.maximum:
                result.append(
                    diagnostic("PARAM_RANGE", f"{item.label} 超出允许范围", node_id=node.id, field=item.key)
                )
        elif item.type == "bool" and not isinstance(value, bool):
            result.append(
                diagnostic("PARAM_TYPE", f"{item.label} 必须是布尔值", node_id=node.id, field=item.key)
            )
        elif item.type == "enum" and item.options and value not in item.options:
            result.append(
                diagnostic(
                    "PARAM_OPTION",
                    f"{item.label} 只支持 {', '.join(item.options)}",
                    node_id=node.id,
                    field=item.key,
                )
            )
        elif item.type == "int_list":
            if not isinstance(value, list) or not value or any(
                isinstance(part, bool) or not isinstance(part, int) for part in value
            ):
                result.append(
                    diagnostic(
                        "PARAM_TYPE",
                        f"{item.label} 必须是非空整数列表",
                        node_id=node.id,
                        field=item.key,
                    )
                )
        elif item.type == "text":
            if not isinstance(value, str) or not value.strip():
                result.append(
                    diagnostic("PARAM_TYPE", f"{item.label} 不能为空", node_id=node.id, field=item.key)
                )
    return result


def input_port_names(node: Node) -> list[str]:
    if node.op == "Input":
        return []
    if node.op == "Output":
        return ["x"]
    if node.op in {"composite.instance", "control.If", "control.For", "control.While"}:
        return [port.name for port in (node.state_contract.inputs if node.state_contract else [])]
    spec = BLOCK_BY_OP.get(node.op)
    if spec is not None and spec.input_ports:
        return [port.name for port in spec.input_ports]
    if spec is not None and spec.input_mode == "merge":
        return ["x"]
    return ["x"]


def required_input_port_names(node: Node) -> list[str]:
    if node.op in {"composite.instance", "control.If", "control.For", "control.While"}:
        return [
            port.name
            for port in (node.state_contract.inputs if node.state_contract else [])
            if port.required
        ]
    spec = BLOCK_BY_OP.get(node.op)
    if spec is not None and spec.input_ports:
        return [port.name for port in spec.input_ports if port.required]
    return input_port_names(node)


def output_port_names(node: Node) -> list[str]:
    if node.op == "Output":
        return []
    if node.op in {"composite.instance", "control.If", "control.For", "control.While"}:
        return [port.name for port in (node.state_contract.outputs if node.state_contract else [])]
    spec = BLOCK_BY_OP.get(node.op)
    if spec is not None and spec.output_ports:
        return [port.name for port in spec.output_ports]
    return ["out"]


def port_data_type(node: Node, port_name: str, io: str) -> str:
    if node.state_contract is not None:
        contracts = (
            node.state_contract.inputs
            if io == "in"
            else node.state_contract.outputs
        )
        port = next((item for item in contracts if item.name == port_name), None)
        return port.data_type if port is not None else "Tensor"
    if node.op == "Input" and io == "out":
        return str(node.params.get("data_type", "Tensor"))
    if node.op == "Output" and io == "in":
        return str(node.params.get("data_type", "Tensor"))
    spec = BLOCK_BY_OP.get(node.op)
    if spec is not None:
        if io == "in":
            port = next(
                (item for item in spec.input_ports if item.name == port_name),
                None,
            )
            return port.data_type if port is not None else "Tensor"
        port = next(
            (item for item in spec.output_ports if item.name == port_name),
            None,
        )
        return port.data_type if port is not None else spec.output_data_type
    return "Tensor"


def _port_index(port: str) -> int:
    if port == "x":
        return 0
    suffix = port.removeprefix("x")
    return int(suffix) if suffix.isdigit() else 0


def incoming_edges_by_node(ir: IRDocument) -> dict[str, list[Edge]]:
    incoming: dict[str, list[Edge]] = defaultdict(list)
    for edge in ir.graph.edges:
        incoming[edge.target.node_id].append(edge)
    for items in incoming.values():
        items.sort(key=lambda edge: (_port_index(edge.target.port), edge.id))
    return incoming


def topological_order(ir: IRDocument) -> list[Node]:
    node_by_id = {node.id: node for node in ir.graph.nodes}
    indegree = {node.id: 0 for node in ir.graph.nodes}
    outgoing: dict[str, list[str]] = defaultdict(list)
    for edge in ir.graph.edges:
        if edge.source.node_id not in node_by_id or edge.target.node_id not in node_by_id:
            continue
        indegree[edge.target.node_id] += 1
        outgoing[edge.source.node_id].append(edge.target.node_id)

    ready = deque(sorted(node_id for node_id, count in indegree.items() if count == 0))
    ordered: list[Node] = []
    while ready:
        node_id = ready.popleft()
        ordered.append(node_by_id[node_id])
        for target_id in sorted(outgoing[node_id]):
            indegree[target_id] -= 1
            if indegree[target_id] == 0:
                ready.append(target_id)
    if len(ordered) != len(ir.graph.nodes):
        raise ValueError("图包含环，无法进行拓扑排序")
    return ordered


def normalize_and_validate(ir: IRDocument) -> tuple[IRDocument, list[Diagnostic]]:
    normalized = deepcopy(ir)
    if normalized.ir_version == "0.2":
        normalized.ir_version = "0.3"
    diagnostics: list[Diagnostic] = []

    nodes = normalized.graph.nodes
    edges = normalized.graph.edges
    id_counts = Counter(node.id for node in nodes)
    edge_counts = Counter(edge.id for edge in edges)
    node_by_id = {node.id: node for node in nodes}

    try:
        resolve_resource_dependencies(normalized.resources)
    except ValueError as exc:
        diagnostics.append(diagnostic("RESOURCE_DEPENDENCY_CYCLE", str(exc)))

    for node in nodes:
        if node.op == "composite.instance":
            resource = find_resource(normalized, node.composite_ref)
            if resource is None:
                diagnostics.append(
                    diagnostic(
                        "MISSING_COMPOSITE_RESOURCE",
                        "复合模块引用的资源版本不在当前工程中",
                        node_id=node.id,
                    )
                )
            elif node.state_contract is None:
                node.state_contract = StateContract(
                    inputs=resource.inputs,
                    outputs=resource.outputs,
                )
            elif resource is not None:
                if (
                    [port.name for port in node.state_contract.inputs]
                    != [port.name for port in resource.inputs]
                    or [port.name for port in node.state_contract.outputs]
                    != [port.name for port in resource.outputs]
                ):
                    diagnostics.append(
                        diagnostic(
                            "COMPOSITE_INTERFACE_MISMATCH",
                            "复合节点端口与资源版本接口不一致",
                            node_id=node.id,
                        )
                    )
        elif node.op.startswith("control."):
            if node.state_contract is None or not node.state_contract.inputs:
                diagnostics.append(
                    diagnostic(
                        "CONTROL_STATE_CONTRACT",
                        "控制容器必须定义状态输入端口",
                        node_id=node.id,
                    )
                )
            required_regions = {
                "control.If": {"predicate", "then", "else"},
                "control.For": {"body"},
                "control.While": {"predicate", "body"},
            }.get(node.op, set())
            missing_regions = required_regions - set(node.region_refs)
            if missing_regions:
                diagnostics.append(
                    diagnostic(
                        "CONTROL_REGION_MISSING",
                        f"控制容器缺少区域：{', '.join(sorted(missing_regions))}",
                        node_id=node.id,
                    )
                )
            for region_id in node.region_refs.values():
                if region_id not in normalized.regions:
                    diagnostics.append(
                        diagnostic(
                            "CONTROL_REGION_NOT_FOUND",
                            f"控制容器引用的区域 {region_id} 不存在",
                            node_id=node.id,
                        )
                    )

    for node_id, count in id_counts.items():
        if count > 1:
            diagnostics.append(
                diagnostic("DUPLICATE_NODE_ID", f"节点 ID {node_id} 重复", node_id=node_id)
            )
    for edge_id, count in edge_counts.items():
        if count > 1:
            diagnostics.append(
                diagnostic("DUPLICATE_EDGE_ID", f"连线 ID {edge_id} 重复", edge_id=edge_id)
            )

    for node in nodes:
        spec = BLOCK_BY_OP.get(node.op)
        if spec is None:
            diagnostics.extend(_validate_params(node))
            continue
        for item in spec.fields:
            node.params.setdefault(item.key, deepcopy(item.default))
        diagnostics.extend(_validate_params(node))
        if normalized.target_framework == "paddle" and spec.pytorch_only:
            diagnostics.append(
                diagnostic(
                    "FRAMEWORK_UNSUPPORTED",
                    f"{spec.torch_api or spec.op} 当前仅在 PyTorch 模式下可用",
                    node_id=node.id,
                )
            )

    if not any(node.op == "Input" for node in nodes):
        diagnostics.append(diagnostic("MISSING_INPUT", "模型缺少 Input 节点", tip="从“输入输出”分类拖入输入块。"))
    if not any(node.op == "Output" for node in nodes):
        diagnostics.append(diagnostic("MISSING_OUTPUT", "模型缺少 Output 节点", tip="一个模型至少需要一条完整输出链。"))

    incoming: dict[tuple[str, str], list[Edge]] = defaultdict(list)
    outgoing: dict[str, list[Edge]] = defaultdict(list)
    for edge in edges:
        source = node_by_id.get(edge.source.node_id)
        target = node_by_id.get(edge.target.node_id)
        if source is None:
            diagnostics.append(
                diagnostic("MISSING_SOURCE", f"连线 {edge.id} 的起点节点不存在", edge_id=edge.id)
            )
            continue
        if target is None:
            diagnostics.append(
                diagnostic("MISSING_TARGET", f"连线 {edge.id} 的终点节点不存在", edge_id=edge.id)
            )
            continue
        if source.id == target.id:
            diagnostics.append(
                diagnostic("SELF_LOOP", "节点不能连接到自身", edge_id=edge.id, node_id=source.id)
            )
        if source.op == "Output":
            diagnostics.append(
                diagnostic("OUTPUT_HAS_EDGE", "Output 节点不能再向后连接", edge_id=edge.id, node_id=source.id)
            )
        if target.op == "Input":
            diagnostics.append(
                diagnostic("INPUT_HAS_INBOUND", "Input 节点不能接收连线", edge_id=edge.id, node_id=target.id)
            )
        valid_source_ports = output_port_names(source)
        valid_target_ports = input_port_names(target)
        source_port_valid = edge.source.port in valid_source_ports
        target_port_valid = edge.target.port in valid_target_ports
        if not source_port_valid or not target_port_valid:
            diagnostics.append(
                diagnostic(
                    "INVALID_PORT",
                    "连线端口与节点 API 的输入输出定义不匹配",
                    tip=(
                        f"{source.op} 的输出端口应为 out；"
                        f"{target.op} 可接收的端口为 {', '.join(valid_target_ports) or '无'}"
                    ),
                    edge_id=edge.id,
                    node_id=target.id,
                )
            )
        elif source_port_valid and target_port_valid:
            source_data_type = port_data_type(
                source,
                edge.source.port,
                "out",
            )
            target_data_type = port_data_type(
                target,
                edge.target.port,
                "in",
            )
            if source_data_type != target_data_type:
                diagnostics.append(
                    diagnostic(
                        "PORT_TYPE_MISMATCH",
                        f"端口类型不一致：{source_data_type} → {target_data_type}",
                        edge_id=edge.id,
                        node_id=target.id,
                    )
                )
        incoming[(target.id, edge.target.port)].append(edge)
        outgoing[source.id].append(edge)

    input_names: list[str] = []
    output_names: list[str] = []
    for node in nodes:
        out_count = len(outgoing[node.id])
        if node.op == "Input":
            if any(
                edge.target.node_id == node.id
                for edge in edges
            ):
                diagnostics.append(
                    diagnostic("INPUT_DEGREE", "Input 必须没有输入连线", node_id=node.id)
                )
            if out_count < 1:
                diagnostics.append(
                    diagnostic(
                        "INPUT_UNCONNECTED",
                        "Input 至少需要连接一个下游节点",
                        node_id=node.id,
                    )
                )
            input_names.append(str(node.params.get("name", "")).strip())
        elif node.op == "Output":
            if len(incoming[(node.id, "x")]) != 1:
                diagnostics.append(
                    diagnostic(
                        "OUTPUT_DEGREE",
                        "每个 Output 必须接收一条输入",
                        node_id=node.id,
                    )
                )
            if out_count != 0:
                diagnostics.append(
                    diagnostic("OUTPUT_DEGREE", "Output 不能继续连接", node_id=node.id)
                )
            output_names.append(str(node.params.get("name", "")).strip())
        elif node.op in BLOCK_BY_OP or node.op == "composite.instance":
            spec = BLOCK_BY_OP.get(node.op)
            for port in input_port_names(node):
                count = len(incoming[(node.id, port)])
                if spec is not None and spec.input_mode == "merge":
                    if count < 2:
                        diagnostics.append(
                            diagnostic(
                                "MISSING_INPUT_PORT",
                                f"{node.op} 的输入端口 {port} 至少需要连接两个分支",
                                tip="合并节点的同一个输入端口可以连接多条数据流。",
                                node_id=node.id,
                            )
                        )
                elif count == 0 and port in required_input_port_names(node):
                    diagnostics.append(
                        diagnostic(
                            "MISSING_INPUT_PORT",
                            f"{node.op} 的输入端口 {port} 尚未连接",
                            node_id=node.id,
                        )
                    )
                elif count > 1:
                    diagnostics.append(
                        diagnostic(
                            "DUPLICATE_TARGET_PORT",
                            f"{node.op} 的输入端口 {port} 只能接收一条连线",
                            node_id=node.id,
                        )
                    )
            if out_count < 1:
                diagnostics.append(
                    diagnostic(
                        "NODE_UNCONNECTED",
                        f"{node.op} 还没有连接下游节点",
                        node_id=node.id,
                    )
                )

    if len(set(input_names)) != len(input_names):
        diagnostics.append(
            diagnostic("DUPLICATE_INPUT_NAME", "Input 变量名必须唯一", tip="例如 x、aux_input。")
        )
    if len(set(output_names)) != len(output_names):
        diagnostics.append(diagnostic("DUPLICATE_OUTPUT_NAME", "Output 名称必须唯一"))

    if not any(item.code == "DUPLICATE_NODE_ID" for item in diagnostics):
        try:
            topological_order(normalized)
        except ValueError:
            diagnostics.append(
                diagnostic(
                    "CYCLE",
                    "检测到循环连接，数据流必须是有向无环图",
                    tip="删除形成回路的连线；并行分支可以分叉，但最终必须汇合或连接 Output。",
                )
            )

    valid_edges = [
        edge
        for edge in edges
        if edge.source.node_id in node_by_id and edge.target.node_id in node_by_id
    ]
    reachable_from_input: set[str] = set()
    queue = deque(node.id for node in nodes if node.op == "Input")
    forward: dict[str, list[str]] = defaultdict(list)
    reverse: dict[str, list[str]] = defaultdict(list)
    for edge in valid_edges:
        forward[edge.source.node_id].append(edge.target.node_id)
        reverse[edge.target.node_id].append(edge.source.node_id)
    while queue:
        node_id = queue.popleft()
        if node_id in reachable_from_input:
            continue
        reachable_from_input.add(node_id)
        queue.extend(forward[node_id])

    can_reach_output: set[str] = set()
    queue = deque(node.id for node in nodes if node.op == "Output")
    while queue:
        node_id = queue.popleft()
        if node_id in can_reach_output:
            continue
        can_reach_output.add(node_id)
        queue.extend(reverse[node_id])

    for node in nodes:
        if node.id not in reachable_from_input:
            diagnostics.append(
                diagnostic(
                    "UNREACHABLE_FROM_INPUT",
                    f"节点 {node.id} 无法从任何 Input 到达",
                    node_id=node.id,
                )
            )
        if node.id not in can_reach_output:
            diagnostics.append(
                diagnostic(
                    "UNREACHABLE_OUTPUT",
                    f"节点 {node.id} 无法到达任何 Output",
                    tip="并行分支最终需要汇合，或分别连接到 Output。",
                    node_id=node.id,
                )
            )

    normalized.check_info = None
    return normalized, _deduplicate(diagnostics)


def _deduplicate(diagnostics: list[Diagnostic]) -> list[Diagnostic]:
    seen: set[tuple[str, str | None, str | None, str]] = set()
    result: list[Diagnostic] = []
    for item in diagnostics:
        key = (item.code, item.node_id, item.edge_id, item.message)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def port_roles(node: Node) -> tuple[str | None, str | None]:
    if node.op == "Input":
        return None, "input_img"
    if node.op == "Output":
        return ("logits" if str(node.params.get("name", "")).lower() == "logits" else "pred"), None
    return None, None


def parameter_values(node: Node) -> dict[str, Any]:
    spec = BLOCK_BY_OP[node.op]
    return {item.key: deepcopy(node.params.get(item.key, item.default)) for item in spec.fields}
