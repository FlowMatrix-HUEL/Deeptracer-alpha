from __future__ import annotations

import ast
import re
from copy import deepcopy
from typing import Any

from .catalog import BLOCK_BY_OP
from .inference import analyze
from .composites import flatten_graph_parameters
from .models import (
    Diagnostic,
    CompositeRef,
    CompositeResource,
    Edge,
    EdgeEndpoint,
    Graph,
    GraphMeta,
    ImportRequest,
    ImportResponse,
    IRDocument,
    Node,
    PortContract,
    Position,
    GraphRegion,
    StateContract,
    UiState,
)


class UnsupportedImport(ValueError):
    def __init__(self, message: str, node: ast.AST, tip: str = "") -> None:
        super().__init__(message)
        self.node = node
        self.tip = tip


def _diag(message: str, node: ast.AST, tip: str = "") -> Diagnostic:
    return Diagnostic(
        code="IMPORT_UNSUPPORTED",
        severity="error",
        message=message,
        teaching_tip=tip,
        field=f"line {getattr(node, 'lineno', '?')}:{getattr(node, 'col_offset', 0) + 1}",
    )


def _torch_call_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name):
        if call.func.value.id in {"nn", "torch"}:
            return f"nn.{call.func.attr}"
    if isinstance(call.func, ast.Name):
        return f"nn.{call.func.id}"
    return None


def _constant(value: ast.AST) -> Any:
    try:
        return ast.literal_eval(value)
    except (ValueError, TypeError) as exc:
        raise UnsupportedImport("模块参数必须是字面量", value, "只支持整数、浮点数、布尔值和固定列表。") from exc


def _params_from_call(op: str, call: ast.Call) -> dict[str, Any]:
    spec = BLOCK_BY_OP.get(op)
    if spec is None:
        raise UnsupportedImport(f"暂不支持 {op}", call, "请改用目录中的 35 个受支持模块。")
    params: dict[str, Any] = {}
    positional_fields = [item for item in spec.fields if item.key not in {"name", "sample_shape", "dtype"}]
    for field_spec, value in zip(positional_fields, call.args):
        params[field_spec.key] = _constant(value)
    for keyword_node in call.keywords:
        if keyword_node.arg is None:
            raise UnsupportedImport("不支持 **kwargs 展开", keyword_node.value)
        if keyword_node.arg not in {item.key for item in spec.fields}:
            raise UnsupportedImport(
                f"{op} 不支持参数 {keyword_node.arg}",
                keyword_node.value,
                "导入器坚持白名单，不会猜测未知参数。",
            )
        params[keyword_node.arg] = _constant(keyword_node.value)
    return params


def _find_module_class(tree: ast.Module) -> ast.ClassDef:
    candidates: list[ast.ClassDef] = []
    for item in tree.body:
        if not isinstance(item, ast.ClassDef):
            continue
        for base in item.bases:
            if (isinstance(base, ast.Attribute) and base.attr == "Module") or (
                isinstance(base, ast.Name) and base.id == "Module"
            ):
                candidates.append(item)
    if len(candidates) != 1:
        raise UnsupportedImport(
            "文件必须恰好包含一个 nn.Module 子类",
            tree,
            "请只上传一个简单模型类，不要包含训练循环或多个候选模型。",
        )
    return candidates[0]


def _find_module_classes(tree: ast.Module) -> list[ast.ClassDef]:
    candidates: list[ast.ClassDef] = []
    for item in tree.body:
        if not isinstance(item, ast.ClassDef):
            continue
        if any(
            (isinstance(base, ast.Attribute) and base.attr == "Module")
            or (isinstance(base, ast.Name) and base.id == "Module")
            for base in item.bases
        ):
            candidates.append(item)
    if not candidates:
        raise UnsupportedImport("文件没有 nn.Module 子类", tree)
    return candidates


def _find_function(class_node: ast.ClassDef, name: str) -> ast.FunctionDef:
    for item in class_node.body:
        if isinstance(item, ast.FunctionDef) and item.name == name:
            return item
    raise UnsupportedImport(f"模型类缺少 {name} 方法", class_node)


def _collect_modules(init_function: ast.FunctionDef) -> dict[str, list[tuple[str, dict[str, Any]]]]:
    modules: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for statement in init_function.body:
        if not isinstance(statement, ast.Assign):
            if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
                continue
            if isinstance(statement, ast.Pass):
                continue
            raise UnsupportedImport("__init__ 只能包含 super() 和 self.<模块> = nn.<层>(...)", statement)
        if len(statement.targets) != 1:
            raise UnsupportedImport("导入器只接受单个模块赋值", statement)
        target = statement.targets[0]
        if not (isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "self"):
            raise UnsupportedImport("模块必须赋值给 self.<名称>", target)
        if not isinstance(statement.value, ast.Call):
            raise UnsupportedImport("模块初始化必须是 nn 层调用", statement.value)
        call_name = _torch_call_name(statement.value)
        if call_name == "nn.Sequential":
            sequence: list[tuple[str, dict[str, Any]]] = []
            for item in statement.value.args:
                if not isinstance(item, ast.Call):
                    raise UnsupportedImport("Sequential 中只允许 nn 模块调用", item)
                item_name = _torch_call_name(item)
                if item_name is None:
                    raise UnsupportedImport("Sequential 中只允许 nn 模块调用", item)
                sequence.append((item_name, _params_from_call(item_name, item)))
            modules[target.attr] = sequence
        elif call_name and (call_name == "nn.Module" or call_name.startswith("nn.")):
            modules[target.attr] = [(call_name, _params_from_call(call_name, statement.value))]
        else:
            raise UnsupportedImport("只允许实例化 PyTorch nn 白名单模块", statement.value)
    return modules


def _collect_modules_with_custom(
    init_function: ast.FunctionDef,
    custom_classes: set[str],
) -> dict[str, list[tuple[str, dict[str, Any]]]]:
    modules: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for statement in init_function.body:
        if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
            continue
        if isinstance(statement, ast.Pass):
            continue
        if not isinstance(statement, ast.Assign):
            raise UnsupportedImport(
                "__init__ 只能包含 super() 和 self.<模块> = <Module>(...)",
                statement,
            )
        if len(statement.targets) != 1:
            raise UnsupportedImport("导入器只接受单个模块赋值", statement)
        target = statement.targets[0]
        if not (
            isinstance(target, ast.Attribute)
            and isinstance(target.value, ast.Name)
            and target.value.id == "self"
        ):
            raise UnsupportedImport("模块必须赋值给 self.<名称>", target)
        value = statement.value
        if not isinstance(value, ast.Call):
            raise UnsupportedImport("模块初始化必须是类调用", value)
        nn_name = _torch_call_name(value)
        if nn_name == "nn.Sequential":
            sequence: list[tuple[str, dict[str, Any]]] = []
            for item in value.args:
                if not isinstance(item, ast.Call):
                    raise UnsupportedImport("Sequential 只允许模块调用", item)
                item_name = _torch_call_name(item)
                if item_name is None:
                    raise UnsupportedImport("Sequential 中不支持该表达式", item)
                sequence.append((item_name, _params_from_call(item_name, item)))
            modules[target.attr] = sequence
            continue
        custom_name = None
        if isinstance(value.func, ast.Name) and value.func.id in custom_classes:
            custom_name = value.func.id
        elif (
            isinstance(value.func, ast.Attribute)
            and isinstance(value.func.value, ast.Name)
            and value.func.attr in custom_classes
        ):
            custom_name = value.func.attr
        if custom_name:
            modules[target.attr] = [(f"custom.{custom_name}", {})]
            continue
        if nn_name and nn_name.startswith("nn."):
            modules[target.attr] = [
                (nn_name, _params_from_call(nn_name, value))
            ]
            continue
        raise UnsupportedImport("只允许官方 nn API 或文件内 nn.Module 类", value)
    return modules


def _collect_forward_calls(
    forward: ast.FunctionDef, modules: dict[str, list[tuple[str, dict[str, Any]]]]
) -> list[tuple[str, dict[str, Any]]]:
    if len(forward.args.args) != 2:
        raise UnsupportedImport(
            "forward 必须且只能接收一个张量参数",
            forward,
            "多输入模型请先在画布中搭建，再导出代码。",
        )
    input_name = forward.args.args[1].arg
    variable = input_name
    result: list[tuple[str, dict[str, Any]]] = []
    returned = False
    for statement in forward.body:
        if returned:
            raise UnsupportedImport("return 之后不能有语句", statement)
        if isinstance(statement, ast.Assign):
            if len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name):
                raise UnsupportedImport("forward 中只支持 y = self.layer(x) 形式", statement)
            call = statement.value
            if not isinstance(call, ast.Call) or len(call.args) != 1:
                raise UnsupportedImport("forward 必须是顺序模块调用链", statement)
            if not (
                isinstance(call.func, ast.Attribute)
                and isinstance(call.func.value, ast.Name)
                and call.func.value.id == "self"
            ):
                raise UnsupportedImport("只支持调用 self.<模块>", call.func)
            if not (isinstance(call.args[0], ast.Name) and call.args[0].id == variable):
                raise UnsupportedImport("每个模块只能消费上一个模块的输出", call.args[0])
            module_name = call.func.attr
            if module_name not in modules:
                raise UnsupportedImport(f"forward 调用了未声明的模块 {module_name}", call.func)
            result.extend(modules[module_name])
            variable = statement.targets[0].id
        elif isinstance(statement, ast.Return) and statement.value is not None:
            if isinstance(statement.value, ast.Call):
                call = statement.value
                if not (
                    isinstance(call.func, ast.Attribute)
                    and isinstance(call.func.value, ast.Name)
                    and call.func.value.id == "self"
                    and len(call.args) == 1
                    and isinstance(call.args[0], ast.Name)
                    and call.args[0].id == variable
                ):
                    raise UnsupportedImport("return 中只支持一个顺序模块调用", call)
                if call.func.attr not in modules:
                    raise UnsupportedImport(f"forward 调用了未声明的模块 {call.func.attr}", call.func)
                result.extend(modules[call.func.attr])
            elif not (isinstance(statement.value, ast.Name) and statement.value.id == variable):
                raise UnsupportedImport(
                    "return 只能返回顺序链的最终变量",
                    statement.value,
                    "不支持张量运算、分支或元组输出。",
                )
            returned = True
        else:
            raise UnsupportedImport("forward 中只允许顺序赋值和 return", statement)
    if not returned:
        raise UnsupportedImport("forward 缺少 return", forward)
    return result


def _module_class_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", name)
    return cleaned or "ImportedModule"


def _root_module_class(classes: list[ast.ClassDef]) -> ast.ClassDef:
    names = {item.name for item in classes}
    referenced: set[str] = set()
    for class_node in classes:
        init = next(
            (
                item
                for item in class_node.body
                if isinstance(item, ast.FunctionDef) and item.name == "__init__"
            ),
            None,
        )
        if init is None:
            continue
        for node in ast.walk(init):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in names:
                    referenced.add(node.func.id)
    roots = [item for item in classes if item.name not in referenced]
    if len(roots) != 1:
        raise UnsupportedImport(
            "无法确定唯一的入口模型类",
            classes[0],
            "文件中的其他模型类必须由入口类实例化。",
        )
    return roots[0]


def _build_class_resource(
    class_node: ast.ClassDef,
    class_map: dict[str, ast.ClassDef],
    cache: dict[str, CompositeResource],
    building: set[str],
) -> CompositeResource:
    if class_node.name in cache:
        return cache[class_node.name]
    if class_node.name in building:
        raise UnsupportedImport(
            "用户模型类存在循环实例化依赖",
            class_node,
        )
    building.add(class_node.name)
    init_function = _find_function(class_node, "__init__")
    forward_function = _find_function(class_node, "forward")
    modules = _collect_modules_with_custom(init_function, set(class_map))
    operations = _collect_forward_calls(forward_function, modules)
    input_name = forward_function.args.args[1].arg
    nodes = [
        Node(
            id="input_x",
            op="Input",
            params={
                "name": input_name,
                "sample_shape": [1, 10],
                "dtype": "float32",
                "data_type": "Tensor",
            },
            teaching_note="嵌套类形状由实际调用上下文决定。",
        )
    ]
    edges: list[Edge] = []
    dependencies: list[CompositeResource] = []
    previous_id = "input_x"
    previous_port = "out"
    for index, (op, params) in enumerate(operations, start=1):
        node_id = f"imported_{index}_{op.split('.')[-1].lower()}"
        if op.startswith("custom."):
            child_name = op.split(".", 1)[1]
            child = _build_class_resource(
                class_map[child_name],
                class_map,
                cache,
                building,
            )
            dependencies.append(child)
            contract = StateContract(
                inputs=child.inputs,
                outputs=child.outputs,
            )
            nodes.append(
                Node(
                    id=node_id,
                    op="composite.instance",
                    params={"name": child.name},
                    composite_ref=CompositeRef(
                        resource_id=child.resource_id,
                        revision=child.revision,
                    ),
                    state_contract=contract,
                )
            )
            target_port = child.inputs[0].name if child.inputs else "x"
            output_port = child.outputs[0].name if child.outputs else "out"
        else:
            spec = BLOCK_BY_OP[op]
            nodes.append(Node(id=node_id, op=op, params=params))
            target_port = (
                spec.input_ports[0].name
                if spec.input_ports
                else "x"
            )
            output_port = (
                spec.output_ports[0].name
                if spec.output_ports
                else "out"
            )
        edges.append(
            Edge(
                id=f"e_{index}",
                source=EdgeEndpoint(node_id=previous_id, port=previous_port),
                target=EdgeEndpoint(node_id=node_id, port=target_port),
            )
        )
        previous_id = node_id
        previous_port = output_port
    output_id = "output_y"
    nodes.append(
        Node(id=output_id, op="Output", params={"name": "output"})
    )
    edges.append(
        Edge(
            id=f"e_{len(operations) + 1}",
            source=EdgeEndpoint(node_id=previous_id, port=previous_port),
            target=EdgeEndpoint(node_id=output_id, port="x"),
        )
    )
    resource = CompositeResource(
        resource_id=f"import_{_module_class_name(class_node.name).lower()}",
        name=class_node.name,
        revision=1,
        description="由 Python 导入生成",
        graph=Graph(nodes=nodes, edges=edges),
        inputs=[
            PortContract(
                name=input_name,
                shape=[1, 10],
                dtype="float32",
            )
        ],
        outputs=[PortContract(name="output")],
        dependencies=dependencies,
        parameter_defaults=flatten_graph_parameters(
            Graph(nodes=nodes, edges=edges),
            dependencies,
        ),
    )
    building.remove(class_node.name)
    cache[class_node.name] = resource
    return resource


def _import_multiple_classes(
    tree: ast.Module,
    request: ImportRequest,
) -> ImportResponse:
    try:
        classes = _find_module_classes(tree)
        class_map = {item.name: item for item in classes}
        root = _root_module_class(classes)
        init_function = _find_function(root, "__init__")
        forward_function = _find_function(root, "forward")
        modules = _collect_modules_with_custom(init_function, set(class_map))
        operations = _collect_forward_calls(forward_function, modules)
    except UnsupportedImport as exc:
        return ImportResponse(diagnostics=[_diag(str(exc), exc.node, exc.tip)])

    input_shape = [int(value) for value in request.shape]
    if not input_shape or any(value <= 0 for value in input_shape):
        return ImportResponse(
            diagnostics=[
                Diagnostic(
                    code="IMPORT_INPUT_SHAPE",
                    message="示例输入形状必须全部为正整数",
                )
            ]
        )
    input_name = forward_function.args.args[1].arg
    nodes = [
        Node(
            id="input_x",
            op="Input",
            params={
                "name": input_name,
                "sample_shape": input_shape,
                "dtype": request.dtype,
                "data_type": "Tensor",
            },
        )
    ]
    edges: list[Edge] = []
    cache: dict[str, CompositeResource] = {}
    embedded: dict[tuple[str, int], CompositeResource] = {}
    previous_id = "input_x"
    previous_port = "out"
    for index, (op, params) in enumerate(operations, start=1):
        node_id = f"imported_{index}_{op.split('.')[-1].lower()}"
        if op.startswith("custom."):
            child_name = op.split(".", 1)[1]
            child = _build_class_resource(
                class_map[child_name],
                class_map,
                cache,
                set(),
            )
            for resource in [*child.dependencies, child]:
                embedded[(resource.resource_id, resource.revision)] = resource
            nodes.append(
                Node(
                    id=node_id,
                    op="composite.instance",
                    params={"name": child.name},
                    composite_ref=CompositeRef(
                        resource_id=child.resource_id,
                        revision=child.revision,
                    ),
                    state_contract=StateContract(
                        inputs=child.inputs,
                        outputs=child.outputs,
                    ),
                )
            )
            target_port = child.inputs[0].name
            output_port = child.outputs[0].name
        else:
            spec = BLOCK_BY_OP[op]
            if len(spec.input_ports) > 1:
                raise UnsupportedImport(
                    f"{op} 需要多个输入，当前多类顺序导入无法推导",
                    forward_function,
                )
            nodes.append(Node(id=node_id, op=op, params=params))
            target_port = spec.input_ports[0].name if spec.input_ports else "x"
            output_port = spec.output_ports[0].name if spec.output_ports else "out"
        edges.append(
            Edge(
                id=f"e_{index}",
                source=EdgeEndpoint(node_id=previous_id, port=previous_port),
                target=EdgeEndpoint(node_id=node_id, port=target_port),
            )
        )
        previous_id = node_id
        previous_port = output_port
    nodes.append(Node(id="output_y", op="Output", params={"name": "output"}))
    edges.append(
        Edge(
            id=f"e_{len(operations) + 1}",
            source=EdgeEndpoint(node_id=previous_id, port=previous_port),
            target=EdgeEndpoint(node_id="output_y", port="x"),
        )
    )
    ir = IRDocument(
        graph_meta=GraphMeta(
            name=root.name,
            author="Python 导入",
            note="入口类与用户复合类依赖由 AST 白名单导入。",
        ),
        graph=Graph(nodes=nodes, edges=edges),
        resources=list(embedded.values()),
        ui=UiState(
            positions={
                node.id: Position(x=70 + index * 280, y=180)
                for index, node in enumerate(nodes)
            }
        ),
    )
    analysis = analyze(ir)
    if not analysis.valid:
        return ImportResponse(ir=ir, diagnostics=analysis.diagnostics)
    node_analysis = {item.node_id: item for item in analysis.nodes}
    resource_by_key = {
        (resource.resource_id, resource.revision): resource
        for resource in ir.resources
    }
    for node in ir.graph.nodes:
        if node.op != "composite.instance" or node.composite_ref is None:
            continue
        resource = resource_by_key.get(
            (
                node.composite_ref.resource_id,
                node.composite_ref.revision,
            )
        )
        analyzed = node_analysis.get(node.id)
        if resource is None or analyzed is None:
            continue
        input_ports = [
            port for port in analyzed.ports if port.io == "in"
        ]
        output_ports = [
            port for port in analyzed.ports if port.io == "out"
        ]
        for index, port in enumerate(resource.inputs):
            if index < len(input_ports):
                port.shape = input_ports[index].shape
                port.dtype = input_ports[index].dtype
        for index, port in enumerate(resource.outputs):
            if index < len(output_ports):
                port.shape = output_ports[index].shape
                port.dtype = output_ports[index].dtype
        input_nodes = [
            item for item in resource.graph.nodes if item.op == "Input"
        ]
        for index, input_node in enumerate(input_nodes):
            if index < len(resource.inputs):
                input_node.params["sample_shape"] = resource.inputs[index].shape
                input_node.params["dtype"] = resource.inputs[index].dtype
        if node.state_contract:
            node.state_contract.inputs = [
                port.model_copy() for port in resource.inputs
            ]
            node.state_contract.outputs = [
                port.model_copy() for port in resource.outputs
            ]
    analysis = analyze(ir)
    return ImportResponse(
        ir=analysis.normalized_ir or ir,
        diagnostics=analysis.diagnostics,
    )


def _condition_from_test(test: ast.AST) -> tuple[str, float] | None:
    def number(value: ast.AST) -> float | None:
        if isinstance(value, ast.Constant) and isinstance(value.value, (int, float)):
            return float(value.value)
        if (
            isinstance(value, ast.UnaryOp)
            and isinstance(value.op, ast.USub)
            and isinstance(value.operand, ast.Constant)
            and isinstance(value.operand.value, (int, float))
        ):
            return -float(value.operand.value)
        return None

    if (
        isinstance(test, ast.Call)
        and isinstance(test.func, ast.Attribute)
        and isinstance(test.func.value, ast.Name)
        and test.func.value.id == "torch"
        and test.func.attr == "all"
        and len(test.args) == 1
    ):
        return _condition_from_test(test.args[0])
    if isinstance(test, ast.Compare) and len(test.ops) == 1:
        left, right = test.left, test.comparators[0]
        if isinstance(left, ast.Name):
            op = {
                ast.Gt: "gt",
                ast.Lt: "lt",
                ast.GtE: "ge",
                ast.LtE: "le",
                ast.Eq: "eq",
                ast.NotEq: "ne",
            }.get(type(test.ops[0]))
            right_number = number(right)
            if op and right_number is not None:
                return op, right_number
    return None


def _region_from_operations(
    region_id: str,
    kind: str,
    operations: list[tuple[str, dict[str, Any]]],
) -> GraphRegion:
    input_node = Node(
        id=f"in_{region_id}",
        op="Input",
        params={
            "name": "state",
            "sample_shape": [1, 10],
            "dtype": "float32",
            "data_type": "Tensor",
        },
    )
    output_node = Node(
        id=f"out_{region_id}",
        op="Output",
        params={"name": "state", "data_type": "Tensor"},
    )
    nodes = [input_node]
    edges: list[Edge] = []
    previous = input_node
    for index, (op, params) in enumerate(operations, start=1):
        node = Node(
            id=f"op_{region_id}_{index}_{op.split('.')[-1].lower()}",
            op=op,
            params=params,
        )
        spec = BLOCK_BY_OP[op]
        nodes.append(node)
        edges.append(
            Edge(
                id=f"e_{region_id}_{index}",
                source=EdgeEndpoint(node_id=previous.id, port="out"),
                target=EdgeEndpoint(
                    node_id=node.id,
                    port=spec.input_ports[0].name if spec.input_ports else "x",
                ),
            )
        )
        previous = node
    nodes.append(output_node)
    edges.append(
        Edge(
            id=f"e_{region_id}_out",
            source=EdgeEndpoint(node_id=previous.id, port="out"),
            target=EdgeEndpoint(node_id=output_node.id, port="x"),
        )
    )
    return GraphRegion(
        id=region_id,
        kind=kind,  # type: ignore[arg-type]
        graph=Graph(nodes=nodes, edges=edges),
        inputs=[
            PortContract(
                name="state",
                shape=[1, 10],
                dtype="float32",
            )
        ],
        outputs=[
            PortContract(
                name="state",
                shape=[1, 10],
                dtype="float32",
            )
        ],
    )


def _predicate_from_condition(
    region_id: str,
    operator: str,
    threshold: float,
) -> GraphRegion:
    nodes = [
        Node(
            id=f"in_{region_id}",
            op="Input",
            params={
                "name": "state",
                "sample_shape": [1, 10],
                "dtype": "float32",
                "data_type": "Tensor",
            },
        ),
        Node(
            id=f"cmp_{region_id}",
            op="logic.CompareScalar",
            params={"operator": operator, "threshold": threshold},
        ),
        Node(id=f"all_{region_id}", op="logic.All", params={}),
        Node(
            id=f"out_{region_id}",
            op="Output",
            params={"name": "condition", "data_type": "ScalarBool"},
        ),
    ]
    return GraphRegion(
        id=region_id,
        kind="predicate",
        graph=Graph(
            nodes=nodes,
            edges=[
                Edge(
                    id=f"p1_{region_id}",
                    source=EdgeEndpoint(node_id=nodes[0].id, port="out"),
                    target=EdgeEndpoint(node_id=nodes[1].id, port="x"),
                ),
                Edge(
                    id=f"p2_{region_id}",
                    source=EdgeEndpoint(node_id=nodes[1].id, port="out"),
                    target=EdgeEndpoint(node_id=nodes[2].id, port="x"),
                ),
                Edge(
                    id=f"p3_{region_id}",
                    source=EdgeEndpoint(node_id=nodes[2].id, port="out"),
                    target=EdgeEndpoint(node_id=nodes[3].id, port="x"),
                ),
            ],
        ),
        inputs=[PortContract(name="state", shape=[1, 10], dtype="float32")],
        outputs=[
            PortContract(
                name="condition",
                data_type="ScalarBool",
                shape=[],
                dtype="bool",
            )
        ],
    )


def _sequential_operations(
    statements: list[ast.stmt],
    modules: dict[str, list[tuple[str, dict[str, Any]]]],
    variable: str,
) -> tuple[list[tuple[str, dict[str, Any]]], str]:
    result: list[tuple[str, dict[str, Any]]] = []
    for statement in statements:
        if isinstance(statement, ast.Return) and isinstance(statement.value, ast.Name):
            variable = statement.value.id
            continue
        if not isinstance(statement, ast.Assign):
            raise UnsupportedImport(
                "控制流区域目前只支持顺序模块赋值",
                statement,
            )
        if len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name):
            raise UnsupportedImport("控制流区域只支持单个变量赋值", statement)
        call = statement.value
        if not (
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and isinstance(call.func.value, ast.Name)
            and call.func.value.id == "self"
            and len(call.args) == 1
            and isinstance(call.args[0], ast.Name)
            and call.args[0].id == variable
        ):
            raise UnsupportedImport(
                "控制流区域只支持 y = self.layer(x) 顺序调用",
                statement,
            )
        module_name = call.func.attr
        if module_name not in modules:
            raise UnsupportedImport(
                f"forward 调用了未声明模块 {module_name}",
                call.func,
            )
        result.extend(modules[module_name])
        variable = statement.targets[0].id
    return result, variable


def _import_structured_single_class(
    class_node: ast.ClassDef,
    modules: dict[str, list[tuple[str, dict[str, Any]]]],
    forward: ast.FunctionDef,
    request: ImportRequest,
) -> ImportResponse:
    args = [item.arg for item in forward.args.args[1:]]
    if len(args) != 1:
        return ImportResponse(
            diagnostics=[
                _diag(
                    "结构化控制流导入目前要求一个 forward 张量参数",
                    forward,
                )
            ]
        )
    input_shape = [int(value) for value in request.shape]
    nodes = [
        Node(
            id="input_x",
            op="Input",
            params={
                "name": args[0],
                "sample_shape": input_shape,
                "dtype": request.dtype,
                "data_type": "Tensor",
            },
        )
    ]
    edges: list[Edge] = []
    regions: dict[str, GraphRegion] = {}
    previous_id = "input_x"
    previous_port = "out"
    variable_name = args[0]
    counter = 0

    def append_sequence(operations: list[tuple[str, dict[str, Any]]]) -> None:
        nonlocal previous_id, previous_port, counter
        for op, params in operations:
            counter += 1
            node_id = f"imported_{counter}_{op.split('.')[-1].lower()}"
            spec = BLOCK_BY_OP[op]
            nodes.append(Node(id=node_id, op=op, params=params))
            edges.append(
                Edge(
                    id=f"e_{counter}",
                    source=EdgeEndpoint(node_id=previous_id, port=previous_port),
                    target=EdgeEndpoint(
                        node_id=node_id,
                        port=spec.input_ports[0].name if spec.input_ports else "x",
                    ),
                )
            )
            previous_id = node_id
            previous_port = spec.output_ports[0].name if spec.output_ports else "out"

    try:
        for statement_index, statement in enumerate(forward.body):
            if isinstance(statement, ast.Return):
                if isinstance(statement.value, ast.Name):
                    variable_name = statement.value.id
                continue
            if isinstance(statement, ast.Assign):
                operations, variable_name = _sequential_operations(
                    [statement],
                    modules,
                    variable_name,
                )
                append_sequence(operations)
                continue
            if isinstance(statement, ast.If):
                condition = _condition_from_test(statement.test)
                if condition is None or not statement.orelse:
                    raise UnsupportedImport(
                        "If 导入需要可映射的条件比较和 else 分支",
                        statement,
                    )
                then_ops, _ = _sequential_operations(
                    statement.body,
                    modules,
                    variable_name,
                )
                else_ops, _ = _sequential_operations(
                    statement.orelse,
                    modules,
                    variable_name,
                )
                prefix = f"import_if_{statement_index}"
                predicate = _predicate_from_condition(
                    f"{prefix}_pred",
                    condition[0],
                    condition[1],
                )
                then_region = _region_from_operations(
                    f"{prefix}_then",
                    "then",
                    then_ops,
                )
                else_region = _region_from_operations(
                    f"{prefix}_else",
                    "else",
                    else_ops,
                )
                regions.update(
                    {
                        predicate.id: predicate,
                        then_region.id: then_region,
                        else_region.id: else_region,
                    }
                )
                counter += 1
                control_id = f"imported_{counter}_if"
                nodes.append(
                    Node(
                        id=control_id,
                        op="control.If",
                        params={},
                        state_contract=StateContract(
                            inputs=[PortContract(name="state", shape=input_shape, dtype=request.dtype)],
                            outputs=[PortContract(name="state", shape=input_shape, dtype=request.dtype)],
                        ),
                        region_refs={
                            "predicate": predicate.id,
                            "then": then_region.id,
                            "else": else_region.id,
                        },
                    )
                )
                edges.append(
                    Edge(
                        id=f"e_{counter}_in",
                        source=EdgeEndpoint(node_id=previous_id, port=previous_port),
                        target=EdgeEndpoint(node_id=control_id, port="state"),
                    )
                )
                previous_id, previous_port = control_id, "state"
                continue
            if isinstance(statement, (ast.For, ast.While)):
                if isinstance(statement, ast.For):
                    if not (
                        isinstance(statement.iter, ast.Call)
                        and isinstance(statement.iter.func, ast.Name)
                        and statement.iter.func.id == "range"
                        and len(statement.iter.args) >= 1
                        and isinstance(statement.iter.args[-1], ast.Constant)
                        and isinstance(statement.iter.args[-1].value, int)
                    ):
                        raise UnsupportedImport(
                            "For 导入只支持 range(<常量>)",
                            statement,
                        )
                    params = {"iterations": statement.iter.args[-1].value}
                    body_ops, _ = _sequential_operations(
                        statement.body,
                        modules,
                        variable_name,
                    )
                    prefix = f"import_for_{statement_index}"
                    body = _region_from_operations(
                        f"{prefix}_body",
                        "body",
                        body_ops,
                    )
                    regions[body.id] = body
                    counter += 1
                    control_id = f"imported_{counter}_for"
                    node = Node(
                        id=control_id,
                        op="control.For",
                        params=params,
                        state_contract=StateContract(
                            inputs=[PortContract(name="state", shape=input_shape, dtype=request.dtype)],
                            outputs=[PortContract(name="state", shape=input_shape, dtype=request.dtype)],
                        ),
                        region_refs={"body": body.id},
                    )
                else:
                    condition = _condition_from_test(statement.test)
                    if condition is None:
                        raise UnsupportedImport(
                            "While 导入需要可映射的条件比较",
                            statement,
                        )
                    body_ops, _ = _sequential_operations(
                        statement.body,
                        modules,
                        variable_name,
                    )
                    prefix = f"import_while_{statement_index}"
                    predicate = _predicate_from_condition(
                        f"{prefix}_pred",
                        condition[0],
                        condition[1],
                    )
                    body = _region_from_operations(
                        f"{prefix}_body",
                        "body",
                        body_ops,
                    )
                    regions.update({predicate.id: predicate, body.id: body})
                    counter += 1
                    control_id = f"imported_{counter}_while"
                    node = Node(
                        id=control_id,
                        op="control.While",
                        params={"max_iterations": 10},
                        state_contract=StateContract(
                            inputs=[PortContract(name="state", shape=input_shape, dtype=request.dtype)],
                            outputs=[PortContract(name="state", shape=input_shape, dtype=request.dtype)],
                        ),
                        region_refs={
                            "predicate": predicate.id,
                            "body": body.id,
                        },
                    )
                nodes.append(node)
                edges.append(
                    Edge(
                        id=f"e_{counter}_in",
                        source=EdgeEndpoint(node_id=previous_id, port=previous_port),
                        target=EdgeEndpoint(node_id=control_id, port="state"),
                    )
                )
                previous_id, previous_port = control_id, "state"
                continue
            raise UnsupportedImport(
                "forward 中只支持模块赋值、return、可映射 If/For/While",
                statement,
            )
    except UnsupportedImport as exc:
        return ImportResponse(
            diagnostics=[_diag(str(exc), exc.node, exc.tip)]
        )
    nodes.append(Node(id="output_y", op="Output", params={"name": "output"}))
    edges.append(
        Edge(
            id="e_output",
            source=EdgeEndpoint(node_id=previous_id, port=previous_port),
            target=EdgeEndpoint(node_id="output_y", port="x"),
        )
    )
    ir = IRDocument(
        graph_meta=GraphMeta(
            name=class_node.name,
            author="Python 导入",
            note="结构化控制流由 AST 白名单导入；请检查示例输入 Shape。",
        ),
        graph=Graph(nodes=nodes, edges=edges),
        regions=regions,
        ui=UiState(
            positions={
                node.id: Position(x=70 + index * 280, y=180)
                for index, node in enumerate(nodes)
            }
        ),
    )
    analysis = analyze(ir)
    return ImportResponse(
        ir=analysis.normalized_ir or ir,
        diagnostics=analysis.diagnostics,
    )


def import_pytorch(request: ImportRequest) -> ImportResponse:
    try:
        tree = ast.parse(request.source, filename=request.source_name)
    except SyntaxError as exc:
        return ImportResponse(
            diagnostics=[
                Diagnostic(
                    code="IMPORT_SYNTAX_ERROR",
                    severity="error",
                    message=f"Python 语法错误：{exc.msg}",
                    field=f"line {exc.lineno}:{exc.offset}",
                )
            ]
        )

    try:
        module_classes = _find_module_classes(tree)
    except UnsupportedImport as exc:
        return ImportResponse(diagnostics=[_diag(str(exc), exc.node, exc.tip)])
    if len(module_classes) > 1:
        return _import_multiple_classes(tree, request)

    try:
        class_node = module_classes[0]
        init_function = _find_function(class_node, "__init__")
        forward_function = _find_function(class_node, "forward")
        modules = _collect_modules(init_function)
        if any(
            isinstance(statement, (ast.If, ast.For, ast.While))
            for statement in forward_function.body
        ):
            return _import_structured_single_class(
                class_node,
                modules,
                forward_function,
                request,
            )
        operations = _collect_forward_calls(forward_function, modules)
    except UnsupportedImport as exc:
        return ImportResponse(
            diagnostics=[_diag(str(exc), exc.node, exc.tip)],
        )

    input_shape = [int(value) for value in request.shape]
    if not input_shape or any(value <= 0 for value in input_shape):
        return ImportResponse(
            diagnostics=[
                Diagnostic(
                    code="IMPORT_INPUT_SHAPE",
                    message="示例输入形状必须全部为正整数",
                    teaching_tip="例如 [1, 784] 或 [1, 1, 28, 28]。",
                )
            ]
        )

    input_name = forward_function.args.args[1].arg
    nodes = [
        Node(
            id="input_x",
            op="Input",
            params={"name": input_name, "sample_shape": input_shape, "dtype": request.dtype},
        )
    ]
    for index, (op, params) in enumerate(operations, start=1):
        nodes.append(Node(id=f"imported_{index}_{op.split('.')[-1].lower()}", op=op, params=params))
    nodes.append(Node(id="output_y", op="Output", params={"name": "output"}))
    edges = [
        Edge(
            id=f"e_{index + 1}",
            source=EdgeEndpoint(node_id=nodes[index].id, port="out"),
            target=EdgeEndpoint(node_id=nodes[index + 1].id, port="x"),
        )
        for index in range(len(nodes) - 1)
    ]
    positions = {
        node.id: Position(x=70 + index * 280, y=180)
        for index, node in enumerate(nodes)
    }
    ir = IRDocument(
        graph_meta=GraphMeta(
            name=class_node.name,
            author="Python 导入",
            note="由受限 AST 白名单导入；请检查示例输入形状。",
        ),
        graph=Graph(nodes=nodes, edges=edges),
        ui=UiState(positions=positions),
    )
    analysis = analyze(ir)
    if not analysis.valid:
        return ImportResponse(ir=ir, diagnostics=analysis.diagnostics)
    return ImportResponse(ir=analysis.normalized_ir or ir, diagnostics=[])
