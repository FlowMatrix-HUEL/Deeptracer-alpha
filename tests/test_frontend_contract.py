from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = (ROOT / "deeptracer" / "templates" / "index.html").read_text(
    encoding="utf-8"
)
SCRIPT = (ROOT / "deeptracer" / "static" / "app.js").read_text(encoding="utf-8")
API_DOCS = (ROOT / "deeptracer" / "templates" / "api_docs.html").read_text(
    encoding="utf-8"
)
SAMPLE = SCRIPT.split("const sampleCode = `", 1)[1].split("`;", 1)[0]


def test_every_literal_javascript_element_id_exists_in_template():
    template_ids = set(re.findall(r'\bid="([^"]+)"', TEMPLATE))
    script_ids = set(re.findall(r'getElementById\("([^"]+)"\)', SCRIPT))

    assert script_ids <= template_ids


def test_analysis_workspace_has_three_exclusive_primary_views():
    workspaces = set(re.findall(r'data-workspace="([^"]+)"', TEMPLATE))
    panels = set(re.findall(r'data-workspace-panel="([^"]+)"', TEMPLATE))

    assert workspaces == {"analysis", "visualization", "chat"}
    assert panels == workspaces


def test_sample_code_exercises_core_analysis_and_tracing_features():
    compile(SAMPLE, "sample.py", "exec")

    assert "def clamp_score(" in SAMPLE
    assert "recursive_match_count(" in SAMPLE
    assert "**overrides" in SAMPLE
    assert "build_learning_summary(" in SAMPLE
    assert 'if __name__ == "__main__":' in SAMPLE


def test_collapsible_sections_keep_function_rows_visible():
    assert TEMPLATE.count("section-disclosure") >= 3
    assert 'class="source-header"' in TEMPLATE
    assert "sourceDetails" not in TEMPLATE
    assert "function-signature-card" in SCRIPT
    assert 'details class="trace-node" open' in SCRIPT
    assert "expandTraceTree" in TEMPLATE
    assert "collapseTraceTree" in TEMPLATE


def test_execution_panel_has_tutor_tracer_and_terminal_modes():
    modes = set(re.findall(r'data-execution-mode="([^"]+)"', TEMPLATE))

    assert modes == {"tutor", "tracer", "terminal"}
    assert "运行终端" in TEMPLATE
    assert "/api-docs" in TEMPLATE
    assert "API 文档" in TEMPLATE
    assert 'href="/netbrick/"' in TEMPLATE
    assert "home-tool-copy" not in TEMPLATE


def test_api_docs_uses_in_page_hierarchical_pages_without_scroll_navigation():
    targets = set(re.findall(r'data-api-target="([^"]+)"', API_DOCS))
    pages = set(
        re.findall(
            r'<article class="api-page" data-api-page="([^"]+)"',
            API_DOCS,
        )
    )

    assert targets == pages
    assert {"run", "analyze", "tracer", "tutor", "chat"} <= pages
    assert {"tracer-overview", "tracer-decorator", "tracer-context"} <= pages
    assert "position: sticky" not in API_DOCS
    assert 'href="#' not in API_DOCS
    assert API_DOCS.count('class="api-tree-group"') >= 3
    assert '"api-block-chevron"' in API_DOCS
    assert 'document.createElement("details")' in API_DOCS
    assert "运行示范" in API_DOCS
    assert "demoSpecs" in API_DOCS
    assert 'button.dataset.demoTarget = target' in API_DOCS


def test_builtin_sample_is_read_only_and_source_buttons_are_neutral():
    assert "isBuiltInSample" in SCRIPT
    assert "官方示例 · 只读" in SCRIPT
    assert 'class="action-button small primary" id="runAnalysis"' not in TEMPLATE
    assert 'class="action-button small success" id="saveEdit"' not in TEMPLATE
    assert 'class="action-button small danger" id="clearCode"' not in TEMPLATE


def test_source_diff_uses_lcs_and_flame_iframe_allows_required_storage():
    assert "最长公共子序列" in SCRIPT
    assert "lcs[oldIndex + 1][newIndex]" in SCRIPT
    assert 'sandbox", "allow-scripts allow-same-origin"' in SCRIPT
    assert "buildDiffHunks" in SCRIPT
    assert '"diff-column-head"' in SCRIPT
