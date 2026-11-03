from __future__ import annotations

import asyncio

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
