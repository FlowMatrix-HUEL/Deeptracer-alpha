from __future__ import annotations

import asyncio
import sys

from deeptracer.netbrick_support import get_netbrick_dist, get_netbrick_root
from deeptracer.server.app import create_app


def test_netbrick_source_and_built_frontend_are_available():
    root = get_netbrick_root(required=True)
    dist = get_netbrick_dist()

    assert (root / "backend" / "app.py").exists()
    assert dist is not None
    assert (dist / "index.html").exists()


def test_netbrick_routes_are_mounted_in_deeptracer():
    app = create_app()
    paths = {getattr(route, "path", "") for route in app.routes}

    assert "/netbrick/" in paths
    assert "/netbrick-assets/{asset_path:path}" in paths
    assert "/api/v1/health" in paths
    assert "/api/v1/graphs/validate" in paths


def test_netbrick_index_rewrites_assets_for_mount_path():
    app = create_app()
    page_route = next(
        route for route in app.routes if getattr(route, "path", "") == "/netbrick/"
    )

    response = asyncio.run(page_route.endpoint())

    assert "/netbrick-assets/assets/" in response.body.decode("utf-8")
    assert "/netbrick-assets/favicon.svg" in response.body.decode("utf-8")


def test_netbrick_linear_output_supports_residual_fanout_and_add():
    root = get_netbrick_root(required=True)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from backend.codegen import generate_code
    from backend.inference import analyze
    from backend.models import (
        Edge,
        EdgeEndpoint,
        Graph,
        GraphMeta,
        IRDocument,
        Node,
    )

    ir = IRDocument(
        graph_meta=GraphMeta(name="Residual Add"),
        graph=Graph(
            nodes=[
                Node(
                    id="input",
                    op="Input",
                    params={
                        "name": "x",
                        "sample_shape": [1, 32],
                        "dtype": "float32",
                    },
                ),
                Node(
                    id="linear_1",
                    op="nn.Linear",
                    params={
                        "in_features": 32,
                        "out_features": 32,
                        "bias": True,
                    },
                ),
                Node(
                    id="linear_2",
                    op="nn.Linear",
                    params={
                        "in_features": 32,
                        "out_features": 32,
                        "bias": True,
                    },
                ),
                Node(id="residual_add", op="merge.Add", params={}),
                Node(id="output", op="Output", params={"name": "y"}),
            ],
            edges=[
                Edge(
                    id="input_linear_1",
                    source=EdgeEndpoint(node_id="input", port="out"),
                    target=EdgeEndpoint(node_id="linear_1", port="x"),
                ),
                Edge(
                    id="linear_1_linear_2",
                    source=EdgeEndpoint(node_id="linear_1", port="out"),
                    target=EdgeEndpoint(node_id="linear_2", port="x"),
                ),
                Edge(
                    id="linear_1_add",
                    source=EdgeEndpoint(node_id="linear_1", port="out"),
                    target=EdgeEndpoint(node_id="residual_add", port="x"),
                ),
                Edge(
                    id="linear_2_add",
                    source=EdgeEndpoint(node_id="linear_2", port="out"),
                    target=EdgeEndpoint(node_id="residual_add", port="x"),
                ),
                Edge(
                    id="add_output",
                    source=EdgeEndpoint(node_id="residual_add", port="out"),
                    target=EdgeEndpoint(node_id="output", port="x"),
                ),
            ],
        ),
    )

    result = analyze(ir)

    assert result.valid, result.diagnostics
    assert not any(
        diagnostic.code == "SHAPE_MISMATCH"
        for diagnostic in result.diagnostics
    )
    generated = generate_code(ir, "pytorch", include_demo=True)
    assert generated.syntax_valid
    assert "torch.add" in generated.source


def test_netbrick_canvas_supports_pinned_multi_target_connections():
    root = get_netbrick_root(required=True)
    canvas = (root / "frontend" / "src" / "components" / "GraphCanvas.tsx").read_text(
        encoding="utf-8"
    )
    flow_node = (root / "frontend" / "src" / "components" / "FlowNode.tsx").read_text(
        encoding="utf-8"
    )
    store = (root / "frontend" / "src" / "store.ts").read_text(encoding="utf-8")

    assert "connectionPin" in canvas
    assert "connectFromPinnedSource" in canvas
    assert "connection.sourceHandle ?? \"out\"" in canvas
    assert "onClickCapture={handleHandleClick}" in canvas
    assert "flow-handle--output" in flow_node
    assert "sourcePort = \"out\"" in store
    assert "edge.source.port === sourcePort" in store
