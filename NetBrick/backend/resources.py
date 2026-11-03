from __future__ import annotations

from collections.abc import Iterable

from .models import (
    CompositeRef,
    CompositeResource,
    Graph,
    GraphRegion,
    IRDocument,
    Node,
    PortContract,
)


def resource_key(resource: CompositeResource) -> tuple[str, int]:
    return resource.resource_id, resource.revision


def walk_resources(resources: Iterable[CompositeResource]):
    seen: set[tuple[str, int]] = set()
    stack = list(resources)
    while stack:
        resource = stack.pop()
        key = resource_key(resource)
        if key in seen:
            continue
        seen.add(key)
        yield resource
        stack.extend(resource.dependencies)


def resource_index(ir: IRDocument) -> dict[tuple[str, int], CompositeResource]:
    return {resource_key(resource): resource for resource in walk_resources(ir.resources)}


def find_resource(ir: IRDocument, ref: CompositeRef | None) -> CompositeResource | None:
    if ref is None:
        return None
    return resource_index(ir).get((ref.resource_id, ref.revision))


def interface_ports(graph: Graph) -> tuple[list[PortContract], list[PortContract]]:
    inputs: list[PortContract] = []
    outputs: list[PortContract] = []
    for node in graph.nodes:
        if node.op == "Input":
            shape_value = node.params.get("sample_shape", [])
            shape = (
                [int(value) for value in shape_value]
                if isinstance(shape_value, list)
                else []
            )
            inputs.append(
                PortContract(
                    name=str(node.params.get("name", node.id)),
                    data_type=str(node.params.get("data_type", "Tensor")),  # type: ignore[arg-type]
                    shape=shape,
                    dtype=str(node.params.get("dtype", "float32")),
                    required=True,
                )
            )
        elif node.op == "Output":
            outputs.append(
                PortContract(
                    name=str(node.params.get("name", node.id)),
                    data_type=str(node.params.get("data_type", "Tensor")),  # type: ignore[arg-type]
                    required=True,
                )
            )
    return inputs, outputs


def resolve_resource_dependencies(
    resources: Iterable[CompositeResource],
) -> list[CompositeResource]:
    """Return a stable, dependency-first resource list without duplicates."""
    ordered: list[CompositeResource] = []
    visited: set[tuple[str, int]] = set()
    visiting: set[tuple[str, int]] = set()

    def visit(resource: CompositeResource) -> None:
        key = resource_key(resource)
        if key in visited:
            return
        if key in visiting:
            raise ValueError(
                f"复合资源依赖成环：{resource.resource_id}@v{resource.revision}"
            )
        visiting.add(key)
        for dependency in resource.dependencies:
            visit(dependency)
        visiting.remove(key)
        visited.add(key)
        ordered.append(resource)

    for item in resources:
        visit(item)
    return ordered


def find_node(graph: Graph, node_id: str) -> Node | None:
    return next((node for node in graph.nodes if node.id == node_id), None)


def apply_flat_overrides(
    graph: Graph,
    regions: dict[str, GraphRegion],
    overrides: dict[str, object],
) -> None:
    for path, value in overrides.items():
        head, separator, remainder = path.partition("/")
        node_id, dot, key = head.partition(".")
        if not dot:
            continue
        node = find_node(graph, node_id)
        if node is None:
            continue
        if not separator:
            node.params[key] = value
            continue
        region_name, nested_separator, nested_path = remainder.partition("/")
        region_id = node.region_refs.get(region_name)
        if (
            node.op.startswith("control.")
            and region_id
            and nested_separator
            and region_id in regions
        ):
            region = regions[region_id]
            apply_flat_overrides(
                region.graph,
                regions,
                {nested_path: value},
            )
        elif node.op == "composite.instance":
            node.param_overrides[remainder] = value
