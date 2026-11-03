from __future__ import annotations

import ast
import keyword
import re
from collections import OrderedDict
from copy import deepcopy
from typing import Any

from .catalog import BLOCK_BY_OP
from .inference import analyze
from .models import (
    CodegenResponse,
    CompositeResource,
    Diagnostic,
    Graph,
    GraphRegion,
    IRDocument,
    Node,
    PortContract,
    StateContract,
)
from .resources import (
    apply_flat_overrides,
    find_resource,
    resolve_resource_dependencies,
)
from .validation import (
    incoming_edges_by_node,
    input_port_names,
    parameter_values,
    topological_order,
)


class CodegenError(ValueError):
    def __init__(self, diagnostics: list[Diagnostic]) -> None:
        super().__init__("IR 未通过校验，无法生成代码")
        self.diagnostics = diagnostics


def _safe_identifier(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", value.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if not cleaned:
        cleaned = fallback
    if cleaned[0].isdigit():
        cleaned = f"{fallback}_{cleaned}"
    if keyword.iskeyword(cleaned):
        cleaned = f"{cleaned}_"
    return cleaned


def _class_identifier(value: str) -> str:
    words = [
        part
        for part in re.split(r"[^A-Za-z0-9]+", value)
        if part
    ]
    class_name = "".join(word[:1].upper() + word[1:] for word in words)
    if not class_name or class_name[0].isdigit():
        class_name = "NetBrick"
    if not class_name.endswith("Model"):
        class_name += "Model"
    return class_name


def _layer_name(op: str, index: int) -> str:
    raw = op.removeprefix("nn.").lower()
    raw = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", raw)
    return f"layer_{index:02d}_{_safe_identifier(raw, 'op').lower()}"


def _paddle_kwargs(op: str, values: dict[str, Any]) -> OrderedDict[str, Any]:
    values = deepcopy(values)
    bias = values.pop("bias", None)
    if op == "nn.Flatten":
        values["start_axis"] = values.pop("start_dim")
        values["stop_axis"] = values.pop("end_dim")
    elif op == "nn.Unflatten":
        values["axis"] = values.pop("dim")
        values["shape"] = tuple(values.pop("sizes"))
    elif op in {"nn.Softmax", "nn.LogSoftmax"}:
        values["axis"] = values.pop("dim")
    elif op == "nn.LayerNorm":
        values["epsilon"] = values.pop("eps")
        elementwise_affine = values.pop("elementwise_affine", True)
        if not elementwise_affine:
            values["weight_attr"] = False
            values["bias_attr"] = False
    elif op == "nn.GroupNorm":
        values["epsilon"] = values.pop("eps")
        affine = values.pop("affine", True)
        if not affine:
            values["weight_attr"] = False
            values["bias_attr"] = False
    elif op in {"nn.BatchNorm1d", "nn.BatchNorm2d"}:
        values["epsilon"] = values.pop("eps")
        values.pop("track_running_stats", None)
        affine = values.pop("affine", True)
        if not affine:
            values["weight_attr"] = False
            values["bias_attr"] = False
    elif op == "nn.InstanceNorm2d":
        values["epsilon"] = values.pop("eps")
        values.pop("track_running_stats", None)
        affine = values.pop("affine", False)
        if not affine:
            values["weight_attr"] = False
            values["bias_attr"] = False
    elif op in {"nn.AvgPool1d", "nn.AvgPool2d"}:
        include_pad = values.pop("count_include_pad", True)
        values["exclusive"] = not include_pad
    elif op == "nn.AdaptiveAvgPool2d":
        size = list(values["output_size"])
        values["output_size"] = tuple(size)
    elif op == "nn.Upsample":
        values["size"] = tuple(values["size"])
    elif op == "nn.GELU":
        approximation = values.pop("approximate", "none")
        values["approximate"] = approximation == "tanh"
    elif op == "nn.Embedding":
        values.pop("input_dtype", None)

    if op in {
        "nn.Dropout",
        "nn.Dropout2d",
        "nn.ReLU",
        "nn.ReLU6",
        "nn.LeakyReLU",
        "nn.ELU",
        "nn.Mish",
    }:
        values.pop("inplace", None)
    if op in {"nn.MaxPool1d", "nn.MaxPool2d"}:
        values.pop("dilation", None)

    values.pop("input_dtype", None)
    if bias is not None and op.startswith(("nn.Conv", "nn.Linear")):
        values["bias_attr"] = bool(bias)
    if op == "nn.PixelShuffle":
        values["upscale_factor"] = values.pop("upscale_factor")
    return OrderedDict(values)


def _torch_kwargs(op: str, values: dict[str, Any]) -> OrderedDict[str, Any]:
    values = deepcopy(values)
    values.pop("input_dtype", None)
    if op == "nn.AdaptiveAvgPool2d":
        values["output_size"] = tuple(values["output_size"])
    elif op == "nn.Upsample":
        values["size"] = tuple(values["size"])
    return OrderedDict(values)


def _module_kwargs(framework: str, op: str, node_params: dict[str, Any]) -> OrderedDict[str, Any]:
    if framework == "paddle":
        return _paddle_kwargs(op, node_params)
    return _torch_kwargs(op, node_params)


def _ast_value(value: Any) -> ast.expr:
    if isinstance(value, tuple):
        return ast.Tuple(elts=[_ast_value(item) for item in value], ctx=ast.Load())
    if isinstance(value, list):
        return ast.List(elts=[_ast_value(item) for item in value], ctx=ast.Load())
    if isinstance(value, dict):
        return ast.Dict(
            keys=[_ast_value(key) for key in value],
            values=[_ast_value(item) for item in value.values()],
        )
    return ast.Constant(value=value)


def _keyword(key: str, value: Any) -> ast.keyword:
    return ast.keyword(arg=key, value=_ast_value(value))


def _statement(source: str) -> ast.stmt:
    parsed = ast.parse(source).body
    if len(parsed) != 1:
        raise ValueError("Expected one AST statement")
    return parsed[0]


def _node_variable(node_id: str) -> str:
    return f"out_{_safe_identifier(node_id, 'node').lower()}"


def _merge_expression(
    framework: str,
    op: str,
    inputs: list[ast.expr],
    params: dict[str, Any],
) -> ast.expr:
    runtime = "paddle" if framework == "paddle" else "torch"
    if op in {"merge.Add", "merge.Multiply"}:
        method = "add" if op == "merge.Add" else "multiply"
        result = inputs[0]
        for item in inputs[1:]:
            result = ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id=runtime, ctx=ast.Load()),
                    attr=method,
                    ctx=ast.Load(),
                ),
                args=[result, item],
                keywords=[],
            )
        return result
    if op == "merge.Concat":
        return ast.Call(
            func=ast.Attribute(
                value=ast.Name(id=runtime, ctx=ast.Load()),
                attr="cat" if framework == "pytorch" else "concat",
                ctx=ast.Load(),
            ),
            args=[ast.List(elts=inputs, ctx=ast.Load())],
            keywords=[
                _keyword(
                    "dim" if framework == "pytorch" else "axis",
                    int(params["dim"]),
                )
            ],
        )
    if op == "logic.Compare":
        operator = str(params.get("operator", "gt"))
        method = (
            {
                "gt": "greater_than",
                "lt": "less_than",
                "ge": "greater_equal",
                "le": "less_equal",
                "eq": "equal",
                "ne": "not_equal",
            }[operator]
            if framework == "paddle"
            else operator
        )
        return ast.Call(
            func=ast.Attribute(
                value=ast.Name(id=runtime, ctx=ast.Load()),
                attr=method,
                ctx=ast.Load(),
            ),
            args=inputs,
            keywords=[],
        )
    if op == "logic.CompareScalar":
        operator = str(params.get("operator", "gt"))
        method = (
            {
                "gt": "greater_than",
                "lt": "less_than",
                "ge": "greater_equal",
                "le": "less_equal",
                "eq": "equal",
                "ne": "not_equal",
            }[operator]
            if framework == "paddle"
            else operator
        )
        return ast.Call(
            func=ast.Attribute(
                value=ast.Name(id=runtime, ctx=ast.Load()),
                attr=method,
                ctx=ast.Load(),
            ),
            args=[
                inputs[0],
                _ast_value(float(params.get("threshold", 0.0))),
            ],
            keywords=[],
        )
    raise ValueError(f"不支持的合并算子：{op}")


def _ordered_edge_map(
    node: Node,
    edges: list[Any],
    values: dict[tuple[str, str], ast.expr],
) -> dict[str, list[ast.expr]]:
    by_port: dict[str, list[ast.expr]] = {}
    for edge in edges:
        source_value = values.get((edge.source.node_id, edge.source.port))
        if source_value is not None:
            by_port.setdefault(edge.target.port, []).append(source_value)
    if node.state_contract is not None:
        ordered: dict[str, list[ast.expr]] = {}
        for port in node.state_contract.inputs:
            ordered[port.name] = by_port.pop(port.name, [])
        return ordered
    spec = BLOCK_BY_OP.get(node.op)
    if spec is not None and spec.input_ports:
        ordered = {}
        for port in spec.input_ports:
            ordered[port.name] = by_port.pop(port.name, [])
        return ordered
    return by_port


def _flatten_edge_map(edge_map: dict[str, list[ast.expr]]) -> list[ast.expr]:
    return [
        item
        for port_items in edge_map.values()
        for item in port_items
    ]


def _module_call(
    node: Node,
    spec: Any,
    input_map: dict[str, list[ast.expr]],
) -> ast.Call:
    if not spec.input_ports:
        return ast.Call(
            func=ast.Name(id="self", ctx=ast.Load()),
            args=_flatten_edge_map(input_map),
            keywords=[],
        )
    args: list[ast.expr] = []
    keywords: list[ast.keyword] = []
    for port in spec.input_ports:
        port_values = input_map.get(port.name)
        if not port_values:
            continue
        if port.call_arg:
            keywords.append(
                ast.keyword(arg=port.call_arg, value=port_values[0])
            )
        else:
            args.extend(port_values)
    return ast.Call(args=args, func=ast.Name(id="self", ctx=ast.Load()), keywords=keywords)


def _port_variable(prefix: str, node_id: str, port: str) -> str:
    return (
        f"out_{_safe_identifier(prefix + node_id, 'node').lower()}_"
        f"{_safe_identifier(port, 'port').lower()}"
    )


def _condition_expression(value: ast.expr) -> ast.expr:
    return ast.Call(
        func=ast.Name(id="bool", ctx=ast.Load()),
        args=[
            ast.Call(
                func=ast.Attribute(
                    value=value,
                    attr="item",
                    ctx=ast.Load(),
                ),
                args=[],
                keywords=[],
            )
        ],
        keywords=[],
    )


class _ClassCompiler:
    def __init__(
        self,
        framework: str,
        resources: list[CompositeResource],
        regions: dict[str, GraphRegion],
        *,
        depth: int = 0,
    ) -> None:
        self.framework = framework
        self.resources = resources
        self.regions = regions
        self.depth = depth
        self.init_body: list[ast.stmt] = [
            ast.Expr(
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Call(
                            func=ast.Name(id="super", ctx=ast.Load()),
                            args=[],
                            keywords=[],
                        ),
                        attr="__init__",
                        ctx=ast.Load(),
                    ),
                    args=[],
                    keywords=[],
                )
            )
        ]
        self.layer_index = 0
        self.helper_classes: list[ast.ClassDef] = []

    def _resource(
        self,
        ref: Any,
    ) -> CompositeResource | None:
        temporary = IRDocument(resources=self.resources)
        return find_resource(temporary, ref)

    def _compile_module_node(
        self,
        node: Node,
        input_map: dict[str, list[ast.expr]],
        prefix: str,
    ) -> tuple[list[ast.stmt], dict[str, str]]:
        spec = BLOCK_BY_OP[node.op]
        class_name = spec.paddle_name if self.framework == "paddle" else spec.torch_name
        if class_name is None:
            raise ValueError(
                f"{node.op} 在 {self.framework} 模式下没有官方 API"
            )
        layer_name = _layer_name(node.op, self.layer_index)
        self.layer_index += 1
        kwargs = _module_kwargs(self.framework, node.op, parameter_values(node))
        self.init_body.append(
            ast.Assign(
                targets=[
                    ast.Attribute(
                        value=ast.Name(id="self", ctx=ast.Load()),
                        attr=layer_name,
                        ctx=ast.Store(),
                    )
                ],
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id="nn", ctx=ast.Load()),
                        attr=class_name,
                        ctx=ast.Load(),
                    ),
                    args=[],
                    keywords=[
                        _keyword(key, value) for key, value in kwargs.items()
                    ],
                ),
            )
        )
        call = _module_call(node, spec, input_map)
        call.func = ast.Attribute(
            value=ast.Name(id="self", ctx=ast.Load()),
            attr=layer_name,
            ctx=ast.Load(),
        )
        output_ports = (
            [port.name for port in spec.output_ports]
            if spec.output_ports
            else ["out"]
        )
        output_vars = {
            port: _port_variable(prefix, node.id, port)
            for port in output_ports
        }
        if len(output_vars) == 1:
            target: ast.expr = ast.Name(
                id=next(iter(output_vars.values())),
                ctx=ast.Store(),
            )
        else:
            target = ast.Tuple(
                elts=[
                    ast.Name(id=value, ctx=ast.Store())
                    for value in output_vars.values()
                ],
                ctx=ast.Store(),
            )
        return [ast.Assign(targets=[target], value=call)], output_vars

    def _compile_composite_node(
        self,
        node: Node,
        inputs: list[ast.expr],
        prefix: str,
    ) -> tuple[list[ast.stmt], dict[str, str]]:
        resource = self._resource(node.composite_ref)
        if resource is None:
            raise ValueError(f"复合资源 {node.composite_ref} 不存在")
        if self.depth >= 3:
            raise ValueError("复合模块嵌套超过 3 层")
        helper_name = (
            _class_identifier(
                f"{resource.name}_{resource.revision}_{node.id}"
            )
        )
        helper = _build_class_ast(
            resource.graph,
            resource.regions,
            resource.dependencies,
            helper_name,
            self.framework,
            depth=self.depth + 1,
            graph_name=resource.graph,
            overrides=node.param_overrides,
        )
        self.helper_classes.extend(helper[0])
        self.helper_classes.append(helper[1])
        attr = _layer_name("composite.instance", self.layer_index)
        self.layer_index += 1
        self.init_body.append(
            ast.Assign(
                targets=[
                    ast.Attribute(
                        value=ast.Name(id="self", ctx=ast.Load()),
                        attr=attr,
                        ctx=ast.Store(),
                    )
                ],
                value=ast.Call(
                    func=ast.Name(id=helper_name, ctx=ast.Load()),
                    args=[],
                    keywords=[],
                ),
            )
        )
        outputs = (
            [port.name for port in node.state_contract.outputs]
            if node.state_contract
            else []
        )
        output_vars = {
            port: _port_variable(prefix, node.id, port) for port in outputs
        }
        call = ast.Call(
            func=ast.Attribute(
                value=ast.Name(id="self", ctx=ast.Load()),
                attr=attr,
                ctx=ast.Load(),
            ),
            args=inputs,
            keywords=[],
        )
        if len(output_vars) == 1:
            target = ast.Name(
                id=next(iter(output_vars.values())),
                ctx=ast.Store(),
            )
        else:
            target = ast.Tuple(
                elts=[
                    ast.Name(id=value, ctx=ast.Store())
                    for value in output_vars.values()
                ],
                ctx=ast.Store(),
            )
        return [ast.Assign(targets=[target], value=call)], output_vars

    def _compile_region(
        self,
        region: GraphRegion,
        input_values: list[ast.expr],
        prefix: str,
    ) -> tuple[list[ast.stmt], list[ast.expr]]:
        return self.compile_graph(
            region.graph,
            input_values,
            prefix,
        )

    def _compile_control_node(
        self,
        node: Node,
        inputs: list[ast.expr],
        prefix: str,
    ) -> tuple[list[ast.stmt], dict[str, str]]:
        contract = node.state_contract or StateContract()
        statements: list[ast.stmt] = []
        output_vars = {
            port.name: _port_variable(prefix, node.id, port.name)
            for port in contract.outputs
        }

        def get_region(name: str) -> GraphRegion:
            region_id = node.region_refs[name]
            return self.regions[region_id]

        index_name = f"index_{_safe_identifier(node.id, 'loop').lower()}"
        if node.op == "control.If":
            predicate_statements, predicate_outputs = self._compile_region(
                get_region("predicate"),
                inputs,
                f"{prefix}{node.id}_pred_",
            )
            then_statements, then_outputs = self._compile_region(
                get_region("then"),
                inputs,
                f"{prefix}{node.id}_then_",
            )
            else_statements, else_outputs = self._compile_region(
                get_region("else"),
                inputs,
                f"{prefix}{node.id}_else_",
            )
            then_body: list[ast.stmt] = list(then_statements)
            else_body: list[ast.stmt] = list(else_statements)
            for index, port in enumerate(contract.outputs):
                target_name = output_vars[port.name]
                then_body.append(
                    ast.Assign(
                        targets=[ast.Name(id=target_name, ctx=ast.Store())],
                        value=then_outputs[index],
                    )
                )
                else_body.append(
                    ast.Assign(
                        targets=[ast.Name(id=target_name, ctx=ast.Store())],
                        value=else_outputs[index],
                    )
                )
            statements.extend(predicate_statements)
            statements.append(
                ast.If(
                    test=_condition_expression(predicate_outputs[0]),
                    body=then_body,
                    orelse=else_body,
                )
            )
            return statements, output_vars

        state_vars = [
            f"state_{_safe_identifier(node.id, 'state').lower()}_{index}"
            for index in range(len(contract.inputs))
        ]
        for index, value in enumerate(inputs):
            statements.append(
                ast.Assign(
                    targets=[ast.Name(id=state_vars[index], ctx=ast.Store())],
                    value=value,
                )
            )

        if node.op == "control.For":
            body_region = get_region("body")
            body_inputs = [
                ast.Name(id=name, ctx=ast.Load()) for name in state_vars
            ]
            if any(port.name == "index" for port in body_region.inputs):
                body_inputs.append(ast.Name(id=index_name, ctx=ast.Load()))
            body_statements, body_outputs = self._compile_region(
                body_region,
                body_inputs,
                f"{prefix}{node.id}_body_",
            )
            for index, name in enumerate(state_vars):
                body_statements.append(
                    ast.Assign(
                        targets=[ast.Name(id=name, ctx=ast.Store())],
                        value=body_outputs[index],
                    )
                )
            statements.append(
                ast.For(
                    target=ast.Name(id=index_name, ctx=ast.Store()),
                    iter=ast.Call(
                        func=ast.Name(id="range", ctx=ast.Load()),
                        args=[_ast_value(parameter_values(node)["iterations"])],
                        keywords=[],
                    ),
                    body=body_statements or [ast.Pass()],
                    orelse=[],
                    type_comment=None,
                )
            )
        else:
            max_iterations = int(parameter_values(node)["max_iterations"])
            predicate_region = get_region("predicate")
            body_region = get_region("body")
            predicate_inputs = [
                ast.Name(id=name, ctx=ast.Load()) for name in state_vars
            ]
            body_inputs = list(predicate_inputs)
            if any(port.name == "index" for port in predicate_region.inputs):
                predicate_inputs.append(ast.Name(id=index_name, ctx=ast.Load()))
            if any(port.name == "index" for port in body_region.inputs):
                body_inputs.append(ast.Name(id=index_name, ctx=ast.Load()))
            predicate_statements, predicate_outputs = self._compile_region(
                predicate_region,
                predicate_inputs,
                f"{prefix}{node.id}_pred_",
            )
            body_statements, body_outputs = self._compile_region(
                body_region,
                body_inputs,
                f"{prefix}{node.id}_body_",
            )
            loop_body = list(predicate_statements)
            loop_body.append(
                ast.If(
                    test=ast.UnaryOp(
                        op=ast.Not(),
                        operand=_condition_expression(predicate_outputs[0]),
                    ),
                    body=[ast.Break()],
                    orelse=[],
                )
            )
            loop_body.extend(body_statements)
            for index, name in enumerate(state_vars):
                loop_body.append(
                    ast.Assign(
                        targets=[ast.Name(id=name, ctx=ast.Store())],
                        value=body_outputs[index],
                    )
                )
            loop_body.append(
                ast.AugAssign(
                    target=ast.Name(id=index_name, ctx=ast.Store()),
                    op=ast.Add(),
                    value=ast.Constant(value=1),
                )
            )
            statements.append(
                ast.Assign(
                    targets=[ast.Name(id=index_name, ctx=ast.Store())],
                    value=ast.Constant(value=0),
                )
            )
            statements.append(
                ast.While(
                    test=ast.Compare(
                        left=ast.Name(id=index_name, ctx=ast.Load()),
                        ops=[ast.Lt()],
                        comparators=[ast.Constant(value=max_iterations)],
                    ),
                    body=loop_body or [ast.Pass()],
                    orelse=[],
                )
            )

        for index, port in enumerate(contract.outputs):
            statements.append(
                ast.Assign(
                    targets=[
                        ast.Name(
                            id=output_vars[port.name],
                            ctx=ast.Store(),
                        )
                    ],
                    value=ast.Name(id=state_vars[index], ctx=ast.Load()),
                )
            )
        return statements, output_vars

    def compile_graph(
        self,
        graph: Graph,
        input_values: list[ast.expr],
        prefix: str = "",
    ) -> tuple[list[ast.stmt], list[ast.expr]]:
        incoming = incoming_edges_by_node(
            IRDocument(graph=graph)
        )
        values: dict[tuple[str, str], ast.expr] = {}
        statements: list[ast.stmt] = []
        input_nodes = [node for node in graph.nodes if node.op == "Input"]
        for index, node in enumerate(input_nodes):
            if index >= len(input_values):
                break
            values[(node.id, "out")] = input_values[index]
        for node in topological_order(IRDocument(graph=graph)):
            if node.op == "Input":
                continue
            if node.op == "Output":
                continue
            input_map = _ordered_edge_map(
                node,
                incoming[node.id],
                values,
            )
            node_inputs = _flatten_edge_map(input_map)
            if node.op == "composite.instance":
                node_statements, output_vars = self._compile_composite_node(
                    node,
                    node_inputs,
                    prefix,
                )
            elif node.op.startswith("control."):
                node_statements, output_vars = self._compile_control_node(
                    node,
                    node_inputs,
                    prefix,
                )
            elif node.op in {
                "merge.Add",
                "merge.Multiply",
                "merge.Concat",
                "logic.Compare",
                "logic.CompareScalar",
            }:
                expression = _merge_expression(
                    self.framework,
                    node.op,
                    node_inputs,
                    parameter_values(node),
                )
                variable = _port_variable(prefix, node.id, "out")
                node_statements = [
                    ast.Assign(
                        targets=[ast.Name(id=variable, ctx=ast.Store())],
                        value=expression,
                    )
                ]
                output_vars = {"out": variable}
            elif node.op == "logic.All":
                variable = _port_variable(prefix, node.id, "out")
                node_statements = [
                    ast.Assign(
                        targets=[ast.Name(id=variable, ctx=ast.Store())],
                        value=ast.Call(
                            func=ast.Attribute(
                                value=ast.Name(
                                    id="paddle"
                                    if self.framework == "paddle"
                                    else "torch",
                                    ctx=ast.Load(),
                                ),
                                attr="all",
                                ctx=ast.Load(),
                            ),
                            args=node_inputs,
                            keywords=[],
                        ),
                    )
                ]
                output_vars = {"out": variable}
            else:
                node_statements, output_vars = self._compile_module_node(
                    node,
                    input_map,
                    prefix,
                )
            statements.extend(node_statements)
            for port, variable in output_vars.items():
                values[(node.id, port)] = ast.Name(
                    id=variable,
                    ctx=ast.Load(),
                )
        output_values = []
        for output_node in [node for node in graph.nodes if node.op == "Output"]:
            edge = incoming[output_node.id][0]
            output_values.append(values[(edge.source.node_id, edge.source.port)])
        return statements, output_values


def _build_class_ast(
    graph: Graph,
    regions: dict[str, GraphRegion],
    resources: list[CompositeResource],
    class_name: str,
    framework: str,
    *,
    depth: int,
    graph_name: Graph | None = None,
    overrides: dict[str, Any] | None = None,
) -> tuple[list[ast.ClassDef], ast.ClassDef]:
    from .resources import resolve_resource_dependencies

    del graph_name
    working_graph = graph.model_copy(deep=True)
    working_regions = {
        key: value.model_copy(deep=True) for key, value in regions.items()
    }
    apply_flat_overrides(
        working_graph,
        working_regions,
        overrides or {},
    )
    ordered_resources = resolve_resource_dependencies(resources)
    compiler = _ClassCompiler(
        framework,
        ordered_resources,
        working_regions,
        depth=depth,
    )
    input_nodes = [node for node in working_graph.nodes if node.op == "Input"]
    input_args = [
        ast.arg(
            arg=_safe_identifier(
                str(node.params.get("name", node.id)),
                f"input_{index + 1}",
            )
        )
        for index, node in enumerate(input_nodes)
    ]
    input_values = [
        ast.Name(id=arg.arg, ctx=ast.Load()) for arg in input_args
    ]
    forward_body, output_values = compiler.compile_graph(
        working_graph,
        input_values,
    )
    if len(output_values) == 1:
        forward_body.append(ast.Return(value=output_values[0]))
    else:
        forward_body.append(
            ast.Return(value=ast.Tuple(elts=output_values, ctx=ast.Load()))
        )
    init_function = ast.FunctionDef(
        name="__init__",
        args=ast.arguments(
            posonlyargs=[],
            args=[ast.arg(arg="self")],
            kwonlyargs=[],
            kw_defaults=[],
            defaults=[],
        ),
        body=compiler.init_body,
        decorator_list=[],
        returns=None,
        type_comment=None,
    )
    forward_function = ast.FunctionDef(
        name="forward",
        args=ast.arguments(
            posonlyargs=[],
            args=[ast.arg(arg="self"), *input_args],
            kwonlyargs=[],
            kw_defaults=[],
            defaults=[],
        ),
        body=forward_body,
        decorator_list=[],
        returns=None,
        type_comment=None,
    )
    module_class = ast.ClassDef(
        name=class_name,
        bases=[
            ast.Attribute(
                value=ast.Name(id="nn", ctx=ast.Load()),
                attr="Layer" if framework == "paddle" else "Module",
                ctx=ast.Load(),
            )
        ],
        keywords=[],
        body=[init_function, forward_function],
        decorator_list=[],
    )
    return compiler.helper_classes, module_class


def _build_source(ir: IRDocument, framework: str, include_demo: bool) -> str:
    return _build_hierarchical_source(ir, framework, include_demo)


def _build_hierarchical_source(
    ir: IRDocument,
    framework: str,
    include_demo: bool,
) -> str:
    imports: list[ast.stmt] = (
        [
            ast.Import(names=[ast.alias(name="paddle")]),
            ast.Import(names=[ast.alias(name="paddle.nn", asname="nn")]),
        ]
        if framework == "paddle"
        else [
            ast.Import(names=[ast.alias(name="torch")]),
            ast.Import(names=[ast.alias(name="torch.nn", asname="nn")]),
        ]
    )
    compiler = _ClassCompiler(
        framework,
        resolve_resource_dependencies(ir.resources),
        ir.regions,
    )
    input_nodes = [node for node in ir.graph.nodes if node.op == "Input"]
    input_args = [
        ast.arg(
            arg=_safe_identifier(
                str(node.params.get("name", node.id)),
                f"input_{index + 1}",
            )
        )
        for index, node in enumerate(input_nodes)
    ]
    input_values = [
        ast.Name(id=argument.arg, ctx=ast.Load()) for argument in input_args
    ]
    forward_body, output_values = compiler.compile_graph(
        ir.graph,
        input_values,
    )
    if len(output_values) == 1:
        forward_body.append(ast.Return(value=output_values[0]))
    else:
        forward_body.append(
            ast.Return(
                value=ast.Tuple(elts=output_values, ctx=ast.Load())
            )
        )
    init_function = ast.FunctionDef(
        name="__init__",
        args=ast.arguments(
            posonlyargs=[],
            args=[ast.arg(arg="self")],
            kwonlyargs=[],
            kw_defaults=[],
            defaults=[],
        ),
        body=compiler.init_body,
        decorator_list=[],
        returns=None,
        type_comment=None,
    )
    forward_function = ast.FunctionDef(
        name="forward",
        args=ast.arguments(
            posonlyargs=[],
            args=[ast.arg(arg="self"), *input_args],
            kwonlyargs=[],
            kw_defaults=[],
            defaults=[],
        ),
        body=forward_body,
        decorator_list=[],
        returns=None,
        type_comment=None,
    )
    class_name = _class_identifier(ir.graph_meta.name)
    base_class = "Layer" if framework == "paddle" else "Module"
    module_class = ast.ClassDef(
        name=class_name,
        bases=[
            ast.Attribute(
                value=ast.Name(id="nn", ctx=ast.Load()),
                attr=base_class,
                ctx=ast.Load(),
            )
        ],
        keywords=[],
        body=[init_function, forward_function],
        decorator_list=[],
    )
    body: list[ast.stmt] = [
        *imports,
        *compiler.helper_classes,
        module_class,
    ]
    if include_demo:
        body.append(_build_demo(class_name, input_nodes, len(output_values), framework))
        body.append(
            ast.If(
                test=ast.Compare(
                    left=ast.Name(id="__name__", ctx=ast.Load()),
                    ops=[ast.Eq()],
                    comparators=[ast.Constant(value="__main__")],
                ),
                body=[
                    ast.Expr(
                        value=ast.Call(
                            func=ast.Name(id="run_demo", ctx=ast.Load()),
                            args=[],
                            keywords=[],
                        )
                    )
                ],
                orelse=[],
            )
        )
    module = ast.Module(body=body, type_ignores=[])
    ast.fix_missing_locations(module)
    source = ast.unparse(module) + "\n"
    compile(source, "<generated-model>", "exec")
    return source


def _legacy_build_source(ir: IRDocument, framework: str, include_demo: bool) -> str:
    ordered_nodes = topological_order(ir)
    input_nodes = [node for node in ordered_nodes if node.op == "Input"]
    output_nodes = [node for node in ordered_nodes if node.op == "Output"]
    incoming = incoming_edges_by_node(ir)
    imports: list[ast.stmt] = []
    if framework == "paddle":
        imports = [
            ast.Import(names=[ast.alias(name="paddle")]),
            ast.Import(names=[ast.alias(name="paddle.nn", asname="nn")]),
        ]
    else:
        imports = [
            ast.Import(names=[ast.alias(name="torch")]),
            ast.Import(names=[ast.alias(name="torch.nn", asname="nn")]),
        ]

    init_body: list[ast.stmt] = [
        ast.Expr(
            value=ast.Call(
                func=ast.Attribute(value=ast.Call(func=ast.Name(id="super", ctx=ast.Load()), args=[], keywords=[]), attr="__init__", ctx=ast.Load()),
                args=[],
                keywords=[],
            )
        )
    ]
    forward_body: list[ast.stmt] = []
    args = [
        ast.arg(arg=_input_identifier(node, index))
        for index, node in enumerate(input_nodes)
    ]
    variable_by_node: dict[str, str] = {
        node.id: _input_identifier(node, index)
        for index, node in enumerate(input_nodes)
    }
    layer_index = 0

    for node in ordered_nodes:
        if node.op in {"Input", "Output"}:
            continue
        values = parameter_values(node)
        inputs = [
            ast.Name(id=variable_by_node[edge.source.node_id], ctx=ast.Load())
            for edge in incoming[node.id]
        ]
        variable = _node_variable(node.id)
        if node.op.startswith("merge."):
            expression = _merge_expression(framework, node.op, inputs, values)
        else:
            spec = BLOCK_BY_OP[node.op]
            class_name = spec.paddle_name if framework == "paddle" else spec.torch_name
            if class_name is None:
                raise ValueError(f"{node.op} 缺少 {framework} 映射")
            layer_name = _layer_name(node.op, layer_index)
            layer_index += 1
            kwargs = _module_kwargs(framework, node.op, values)
            init_body.append(
                ast.Assign(
                    targets=[ast.Attribute(value=ast.Name(id="self", ctx=ast.Load()), attr=layer_name, ctx=ast.Store())],
                    value=ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id="nn", ctx=ast.Load()),
                            attr=class_name,
                            ctx=ast.Load(),
                        ),
                        args=[],
                        keywords=[
                            _keyword(key, value)
                            for key, value in kwargs.items()
                        ],
                    ),
                )
            )
            expression = ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id="self", ctx=ast.Load()),
                    attr=layer_name,
                    ctx=ast.Load(),
                ),
                args=inputs,
                keywords=[],
            )
        forward_body.append(
            ast.Assign(
                targets=[ast.Name(id=variable, ctx=ast.Store())],
                value=expression,
            )
        )
        variable_by_node[node.id] = variable

    return_vars = [
        variable_by_node[incoming[node.id][0].source.node_id]
        for node in output_nodes
    ]
    if len(return_vars) == 1:
        forward_body.append(
            ast.Return(
                value=ast.Name(id=return_vars[0], ctx=ast.Load())
            )
        )
    else:
        forward_body.append(
            ast.Return(value=ast.Tuple(elts=[ast.Name(id=item, ctx=ast.Load()) for item in return_vars], ctx=ast.Load()))
        )

    init_function = ast.FunctionDef(
        name="__init__",
        args=ast.arguments(posonlyargs=[], args=[ast.arg(arg="self")], kwonlyargs=[], kw_defaults=[], defaults=[]),
        body=init_body,
        decorator_list=[],
        returns=None,
        type_comment=None,
    )
    forward_function = ast.FunctionDef(
        name="forward",
        args=ast.arguments(posonlyargs=[], args=[ast.arg(arg="self"), *args], kwonlyargs=[], kw_defaults=[], defaults=[]),
        body=forward_body,
        decorator_list=[],
        returns=None,
        type_comment=None,
    )
    class_name = _class_identifier(ir.graph_meta.name)
    class_def = ast.ClassDef(
        name=class_name,
        bases=[ast.Attribute(value=ast.Name(id="nn", ctx=ast.Load()), attr="Module", ctx=ast.Load())],
        keywords=[],
        body=[init_function, forward_function],
        decorator_list=[],
    )
    body: list[ast.stmt] = [*imports, class_def]
    if include_demo:
        body.append(_build_demo(class_name, input_nodes, len(output_nodes), framework))
        body.append(
            ast.If(
                test=ast.Compare(
                    left=ast.Name(id="__name__", ctx=ast.Load()),
                    ops=[ast.Eq()],
                    comparators=[ast.Constant(value="__main__")],
                ),
                body=[
                    ast.Expr(
                        value=ast.Call(
                            func=ast.Name(id="run_demo", ctx=ast.Load()),
                            args=[],
                            keywords=[],
                        )
                    )
                ],
                orelse=[],
            )
        )

    module = ast.Module(body=body, type_ignores=[])
    ast.fix_missing_locations(module)
    source = ast.unparse(module) + "\n"
    compile(source, "<generated-model>", "exec")
    return source


def _input_identifier(node: Any, index: int) -> str:
    value = parameter_values(node).get("name", f"input_{index + 1}")
    return _safe_identifier(str(value), f"input_{index + 1}")


def _build_demo(
    class_name: str,
    input_nodes: list[Any],
    output_count: int,
    framework: str,
) -> ast.FunctionDef:
    body: list[ast.stmt] = [
        ast.Assign(
            targets=[ast.Name(id="model", ctx=ast.Store())],
            value=ast.Call(func=ast.Name(id=class_name, ctx=ast.Load()), args=[], keywords=[]),
        )
    ]
    if framework == "paddle":
        body.append(_statement("paddle.seed(42)"))
    else:
        body.append(_statement("torch.manual_seed(42)"))

    demo_args: list[str] = []
    for index, node in enumerate(input_nodes):
        values = parameter_values(node)
        arg_name = f"demo_input_{index + 1}"
        demo_args.append(arg_name)
        shape = tuple(int(value) for value in values["sample_shape"])
        dtype = str(values["dtype"])
        if framework == "paddle":
            if dtype == "int64":
                call = _statement(f"{arg_name} = paddle.randint(low=0, high=10, shape={shape!r}, dtype='int64')")
            else:
                call = _statement(f"{arg_name} = paddle.randn(shape={shape!r}, dtype={dtype!r})")
        else:
            if dtype == "int64":
                call = _statement(f"{arg_name} = torch.randint(low=0, high=10, size={shape!r}, dtype=torch.int64)")
            else:
                call = _statement(f"{arg_name} = torch.randn(size={shape!r}, dtype=torch.{dtype})")
        body.append(call)

    body.append(
        ast.Assign(
            targets=[ast.Name(id="outputs", ctx=ast.Store())],
            value=ast.Call(
                func=ast.Name(id="model", ctx=ast.Load()),
                args=[ast.Name(id=item, ctx=ast.Load()) for item in demo_args],
                keywords=[],
            ),
        )
    )
    if output_count == 1:
        body.append(_statement("print('output_shape:', tuple(outputs.shape))"))
    else:
        body.append(
            _statement(
                "print('output_shapes:', tuple(tuple(output.shape) for output in outputs))"
            )
        )

    function = ast.FunctionDef(
        name="run_demo",
        args=ast.arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]),
        body=body,
        decorator_list=[],
        returns=ast.Constant(value=None),
        type_comment=None,
    )
    return function


def generate_code(ir: IRDocument, framework: str, include_demo: bool) -> CodegenResponse:
    analysis = analyze(ir)
    if not analysis.valid or analysis.normalized_ir is None:
        raise CodegenError(analysis.diagnostics)
    source = _build_source(analysis.normalized_ir, framework, include_demo)
    try:
        compile(source, "<generated-model>", "exec")
        syntax_valid = True
    except SyntaxError as exc:
        raise CodegenError(
            [
                Diagnostic(
                    code="GENERATED_SYNTAX_ERROR",
                    message=f"生成的代码语法错误：{exc.msg}",
                    teaching_tip="这是生成器缺陷，请保留当前 IR 用于复现。",
                )
            ]
        ) from exc
    base_name = _safe_identifier(ir.graph_meta.name, "model").lower()
    suffix = "paddle" if framework == "paddle" else "torch"
    return CodegenResponse(
        filename=f"{base_name}_{suffix}.py",
        source=source,
        syntax_valid=syntax_valid,
        warnings=analysis.diagnostics,
    )
