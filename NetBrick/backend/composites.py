from __future__ import annotations

from copy import deepcopy
from typing import Any

from .models import (
    CompositeResource,
    Graph,
    IRDocument,
    Node,
    PublishCompositeRequest,
    PortContract,
    GraphRegion,
)
from .resources import (
    find_resource,
    interface_ports,
    resolve_resource_dependencies,
)


MAX_NESTING_DEPTH = 3


def flatten_graph_parameters(
    graph: Graph,
    resources: list[CompositeResource],
    regions: dict[str, GraphRegion] | None = None,
    prefix: str = "",
    *,
    depth: int = 0,
    visiting: set[tuple[str, int]] | None = None,
) -> dict[str, Any]:
    if depth > MAX_NESTING_DEPTH:
        return {}
    visiting = visiting or set()
    values: dict[str, Any] = {}
    regions = regions or {}
    for node in graph.nodes:
        if node.op in {"Input", "Output"}:
            continue
        node_prefix = f"{prefix}{node.id}"
        for key, value in node.params.items():
            if node.op.startswith("control.") and key in {
                "iterations",
                "max_iterations",
            }:
                values[f"{node_prefix}.{key}"] = deepcopy(value)
            elif not node.op.startswith("control."):
                values[f"{node_prefix}.{key}"] = deepcopy(value)
        if node.op == "composite.instance":
            resource = find_resource(
                IRDocument(resources=resources),
                node.composite_ref,
            )
            if resource is None:
                continue
            key = (resource.resource_id, resource.revision)
            if key in visiting:
                continue
            values.update(
                flatten_graph_parameters(
                    resource.graph,
                    resource.dependencies,
                    resource.regions,
                    f"{node_prefix}/",
                    depth=depth + 1,
                    visiting={*visiting, key},
                )
            )
        if node.op.startswith("control."):
            for region_name, region_id in node.region_refs.items():
                region = regions.get(region_id)
                if region is None:
                    continue
                values.update(
                    flatten_graph_parameters(
                        region.graph,
                        resources,
                        regions,
                        f"{node_prefix}/{region_name}/",
                        depth=depth + 1,
                        visiting=visiting,
                    )
                )
    return values


def build_composite_resource(
    request: PublishCompositeRequest,
    output_contracts: list[PortContract],
) -> CompositeResource:
    inputs, _ = interface_ports(request.ir.graph)
    resources = resolve_resource_dependencies(request.ir.resources)
    return CompositeResource(
        resource_id=request.resource_id,
        name=request.name,
        revision=request.revision,
        description=request.description,
        author=request.author,
        graph=deepcopy(request.ir.graph),
        regions=deepcopy(request.ir.regions),
        ui=deepcopy(request.ir.ui),
        inputs=inputs,
        outputs=output_contracts,
        dependencies=resources,
        parameter_defaults=flatten_graph_parameters(
            request.ir.graph,
            resources,
            request.ir.regions,
        ),
    )


def composite_depth(
    resource: CompositeResource,
    stack: tuple[tuple[str, int], ...] = (),
) -> int:
    key = (resource.resource_id, resource.revision)
    if key in stack:
        return len(stack)
    return 1 + max(
        (
            composite_depth(dependency, (*stack, key))
            for dependency in resource.dependencies
        ),
        default=0,
    )


def node_parameter_prefix(node: Node) -> str:
    return node.id
