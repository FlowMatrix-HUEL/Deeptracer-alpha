from __future__ import annotations

import base64
import io
import json
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from backend.app import app, catalog, codegen, health, publish_composite
from backend.catalog import BLOCKS, catalog_response, defaults_for
from backend.codegen import generate_code
from backend.course import create_package, validate_package
from backend.files import (
    SavePythonRequest,
    save_python_with_native_dialog,
)
from backend.importer import import_pytorch
from backend.inference import analyze
from backend.models import (
    CodegenRequest,
    CompositeRef,
    CompositeResource,
    CourseImportRequest,
    CoursePack,
    Edge,
    EdgeEndpoint,
    Graph,
    GraphMeta,
    GraphRegion,
    ImportRequest,
    IRDocument,
    Node,
    PortContract,
    PublishCompositeRequest,
    StateContract,
    UiState,
)
from backend.samples import SAMPLES, multi_chain, parallel_add, simple_cnn
from backend.validation import normalize_and_validate, topological_order


def chain_ir(op: str, input_shape: list[int], dtype: str = "float32") -> IRDocument:
    return IRDocument(
        graph_meta=GraphMeta(name=f"Test {op}"),
        graph=Graph(
            nodes=[
                Node(
                    id="input",
                    op="Input",
                    params={"name": "x", "sample_shape": input_shape, "dtype": dtype},
                ),
                Node(id="op", op=op, params=defaults_for(op)),
                Node(id="output", op="Output", params={"name": "y"}),
            ],
            edges=[
                Edge(
                    id="e1",
                    source=EdgeEndpoint(node_id="input", port="out"),
                    target=EdgeEndpoint(node_id="op", port="x"),
                ),
                Edge(
                    id="e2",
                    source=EdgeEndpoint(node_id="op", port="out"),
                    target=EdgeEndpoint(node_id="output", port="x"),
                ),
            ],
        ),
    )


def state_contract(shape: list[int] | None = None) -> StateContract:
    port = PortContract(
        name="state",
        data_type="Tensor",
        shape=shape or [1, 8],
        dtype="float32",
        required=True,
    )
    return StateContract(inputs=[port], outputs=[port.model_copy()])


def identity_region(
    region_id: str,
    kind: str,
    shape: list[int] | None = None,
) -> GraphRegion:
    contract = state_contract(shape)
    source = contract.inputs[0]
    output = contract.outputs[0]
    nodes = [
        Node(
            id=f"in_{region_id}",
            op="Input",
            params={
                "name": source.name,
                "sample_shape": source.shape,
                "dtype": source.dtype,
                "data_type": source.data_type,
            },
        ),
        Node(id=f"identity_{region_id}", op="nn.Identity", params={}),
        Node(
            id=f"out_{region_id}",
            op="Output",
            params={"name": output.name, "data_type": output.data_type},
        ),
    ]
    edges = [
        Edge(
            id=f"e1_{region_id}",
            source=EdgeEndpoint(node_id=nodes[0].id, port="out"),
            target=EdgeEndpoint(node_id=nodes[1].id, port="x"),
        ),
        Edge(
            id=f"e2_{region_id}",
            source=EdgeEndpoint(node_id=nodes[1].id, port="out"),
            target=EdgeEndpoint(node_id=nodes[2].id, port="x"),
        ),
    ]
    return GraphRegion(
        id=region_id,
        kind=kind,  # type: ignore[arg-type]
        graph=Graph(nodes=nodes, edges=edges),
        inputs=[source],
        outputs=[output],
    )


def predicate_region(region_id: str, shape: list[int] | None = None) -> GraphRegion:
    contract = state_contract(shape)
    source = contract.inputs[0]
    nodes = [
        Node(
            id=f"in_{region_id}",
            op="Input",
            params={
                "name": source.name,
                "sample_shape": source.shape,
                "dtype": source.dtype,
                "data_type": source.data_type,
            },
        ),
        Node(id=f"left_{region_id}", op="nn.Identity", params={}),
        Node(id=f"right_{region_id}", op="nn.Identity", params={}),
        Node(
            id=f"cmp_{region_id}",
            op="logic.Compare",
            params={"operator": "gt"},
        ),
        Node(id=f"all_{region_id}", op="logic.All", params={}),
        Node(
            id=f"out_{region_id}",
            op="Output",
            params={"name": "condition", "data_type": "ScalarBool"},
        ),
    ]
    edges = [
        Edge(
            id=f"p1_{region_id}",
            source=EdgeEndpoint(node_id=nodes[0].id, port="out"),
            target=EdgeEndpoint(node_id=nodes[1].id, port="x"),
        ),
        Edge(
            id=f"p2_{region_id}",
            source=EdgeEndpoint(node_id=nodes[0].id, port="out"),
            target=EdgeEndpoint(node_id=nodes[2].id, port="x"),
        ),
        Edge(
            id=f"p3_{region_id}",
            source=EdgeEndpoint(node_id=nodes[1].id, port="out"),
            target=EdgeEndpoint(node_id=nodes[3].id, port="x"),
        ),
        Edge(
            id=f"p4_{region_id}",
            source=EdgeEndpoint(node_id=nodes[2].id, port="out"),
            target=EdgeEndpoint(node_id=nodes[3].id, port="x"),
        ),
        Edge(
            id=f"p5_{region_id}",
            source=EdgeEndpoint(node_id=nodes[3].id, port="out"),
            target=EdgeEndpoint(node_id=nodes[4].id, port="x"),
        ),
        Edge(
            id=f"p6_{region_id}",
            source=EdgeEndpoint(node_id=nodes[4].id, port="out"),
            target=EdgeEndpoint(node_id=nodes[5].id, port="x"),
        ),
    ]
    return GraphRegion(
        id=region_id,
        kind="predicate",
        graph=Graph(nodes=nodes, edges=edges),
        inputs=[source],
        outputs=[
            PortContract(
                name="condition",
                data_type="ScalarBool",
                shape=[],
                dtype="bool",
            )
        ],
    )


def control_ir(op: str) -> IRDocument:
    contract = state_contract()
    input_node = Node(
        id="input",
        op="Input",
        params={
            "name": "x",
            "sample_shape": [1, 8],
            "dtype": "float32",
            "data_type": "Tensor",
        },
    )
    output_node = Node(
        id="output",
        op="Output",
        params={"name": "y", "data_type": "Tensor"},
    )
    params = (
        {"iterations": 3}
        if op == "control.For"
        else {"max_iterations": 4}
        if op == "control.While"
        else {}
    )
    regions: dict[str, GraphRegion] = {}
    refs: dict[str, str] = {}
    if op == "control.If":
        regions = {
            "pred": predicate_region("pred"),
            "then": identity_region("then", "then"),
            "else": identity_region("else", "else"),
        }
        refs = {"predicate": "pred", "then": "then", "else": "else"}
    elif op == "control.For":
        regions = {"body": identity_region("body", "body")}
        refs = {"body": "body"}
    else:
        regions = {
            "pred": predicate_region("pred"),
            "body": identity_region("body", "body"),
        }
        refs = {"predicate": "pred", "body": "body"}
    node = Node(
        id="control",
        op=op,
        params=params,
        state_contract=contract,
        region_refs=refs,
    )
    return IRDocument(
        graph_meta=GraphMeta(name=op),
        graph=Graph(
            nodes=[input_node, node, output_node],
            edges=[
                Edge(
                    id="e1",
                    source=EdgeEndpoint(node_id="input", port="out"),
                    target=EdgeEndpoint(node_id="control", port="state"),
                ),
                Edge(
                    id="e2",
                    source=EdgeEndpoint(node_id="control", port="state"),
                    target=EdgeEndpoint(node_id="output", port="x"),
                ),
            ],
        ),
        regions=regions,
    )


class CatalogTests(unittest.TestCase):
    def test_catalog_has_full_model_layer_coverage(self) -> None:
        catalog = catalog_response()
        model_ops = [block for block in catalog.blocks if not block.system]
        self.assertEqual(len(model_ops), 138)
        self.assertEqual(
            {block.op for block in catalog.blocks if block.system},
            {"Input", "Output"},
        )
        self.assertTrue(
            all(block.torch_name for block in model_ops if block.op.startswith("nn."))
        )
        self.assertTrue(
            all(
                block.paddle_name
                for block in model_ops
                if block.op.startswith("nn.") and not block.pytorch_only
            )
        )
        self.assertTrue(
            {"merge.Add", "merge.Multiply", "merge.Concat"}.issubset(
                {block.op for block in model_ops}
            )
        )
        self.assertTrue(
            {"control.If", "control.For", "control.While"}.issubset(
                {block.op for block in model_ops}
            )
        )
        registry = json.loads(
            (
                Path(__file__).resolve().parent.parent
                / "backend"
                / "data"
                / "pytorch_2_6_registry.json"
            ).read_text(encoding="utf-8")
        )
        registry_ops = {
            f"nn.{item['class_name']}" for item in registry["classes"]
        }
        self.assertEqual(len(registry_ops), 94)
        self.assertTrue(registry_ops.issubset({block.op for block in model_ops}))
        for block in model_ops:
            if block.op in registry_ops:
                self.assertTrue(block.pytorch_only)
                self.assertTrue(block.input_ports)
                self.assertTrue(block.output_ports)

    def test_every_operator_generates_valid_python_for_both_frameworks(self) -> None:
        cases = {
            "nn.Linear": [1, 784],
            "nn.Identity": [1, 10],
            "nn.Flatten": [1, 2, 5],
            "nn.Unflatten": [1, 784],
            "nn.Dropout": [1, 10],
            "nn.Dropout2d": [1, 4, 8, 8],
            "nn.Conv1d": [1, 1, 8],
            "nn.Conv2d": [1, 1, 8, 8],
            "nn.ConvTranspose2d": [1, 1, 8, 8],
            "nn.MaxPool1d": [1, 1, 8],
            "nn.MaxPool2d": [1, 1, 8, 8],
            "nn.AvgPool1d": [1, 1, 8],
            "nn.AvgPool2d": [1, 1, 8, 8],
            "nn.AdaptiveAvgPool1d": [1, 1, 8],
            "nn.AdaptiveAvgPool2d": [1, 1, 8, 8],
            "nn.Upsample": [1, 1, 8, 8],
            "nn.BatchNorm1d": [1, 8],
            "nn.BatchNorm2d": [1, 8, 4, 4],
            "nn.LayerNorm": [1, 10],
            "nn.GroupNorm": [1, 8],
            "nn.InstanceNorm2d": [1, 8, 4, 4],
            "nn.ReLU": [1, 10],
            "nn.ReLU6": [1, 10],
            "nn.LeakyReLU": [1, 10],
            "nn.ELU": [1, 10],
            "nn.GELU": [1, 10],
            "nn.SiLU": [1, 10],
            "nn.Sigmoid": [1, 10],
            "nn.Tanh": [1, 10],
            "nn.Softmax": [1, 10],
            "nn.LogSoftmax": [1, 10],
            "nn.Embedding": [1, 4],
            "nn.PixelShuffle": [1, 8, 4, 4],
            "nn.PixelUnshuffle": [1, 2, 4, 4],
            "nn.Mish": [1, 10],
        }
        model_ops = {block.op for block in BLOCKS if not block.system}
        self.assertTrue(set(cases).issubset(model_ops))
        for op, shape in cases.items():
            with self.subTest(op=op):
                ir = chain_ir(op, shape, "int64" if op == "nn.Embedding" else "float32")
                analysis = analyze(ir)
                self.assertTrue(
                    analysis.valid,
                    [(item.code, item.message) for item in analysis.diagnostics],
                )
                for framework in ("pytorch", "paddle"):
                    response = generate_code(ir, framework, include_demo=True)
                    self.assertTrue(response.syntax_valid)
                    self.assertIn("def forward", response.source)

    def test_all_pytorch_registry_constructors_are_syntactically_valid(self) -> None:
        registry_blocks = [
            block for block in BLOCKS if block.pytorch_only
        ]
        self.assertEqual(len(registry_blocks), 94)
        for block in registry_blocks:
            kwargs = ", ".join(
                f"{field.key}={field.default!r}"
                for field in block.fields
            )
            source = (
                "import torch.nn as nn\n"
                "def build():\n"
                f"    return nn.{block.torch_name}({kwargs})\n"
            )
            with self.subTest(op=block.op):
                compile(source, f"<{block.op}>", "exec")


class InferenceTests(unittest.TestCase):
    def test_samples_have_expected_shapes(self) -> None:
        for sample_id, sample in SAMPLES.items():
            with self.subTest(sample=sample_id):
                result = analyze(sample["ir"]())
                self.assertTrue(result.valid, result.diagnostics)
                for framework in ("pytorch", "paddle"):
                    code = generate_code(
                        sample["ir"](), framework, include_demo=True
                    )
                    self.assertTrue(code.syntax_valid)
        cnn = analyze(simple_cnn())
        linear = next(
            node for node in cnn.nodes if node.node_id == "linear_1"
        )
        output = next(port for port in linear.ports if port.io == "out")
        self.assertEqual(output.shape, [1, 10])
        multi = analyze(multi_chain())
        self.assertEqual(multi.chain_count, 2)

    def test_shape_mismatch_has_teaching_message(self) -> None:
        ir = chain_ir("nn.Linear", [1, 10])
        result = analyze(ir)
        self.assertFalse(result.valid)
        self.assertIn(
            "SHAPE_MISMATCH",
            [diagnostic.code for diagnostic in result.diagnostics],
        )
        self.assertTrue(result.diagnostics[0].teaching_tip)

    def test_fanout_is_allowed(self) -> None:
        ir = chain_ir("nn.ReLU", [1, 10])
        ir.graph.nodes.append(
            Node(id="second", op="nn.Sigmoid", params=defaults_for("nn.Sigmoid"))
        )
        ir.graph.nodes.append(Node(id="out2", op="Output", params={"name": "second_out"}))
        ir.graph.edges.append(
            Edge(
                id="fanout",
                source=EdgeEndpoint(node_id="op", port="out"),
                target=EdgeEndpoint(node_id="second", port="x"),
            )
        )
        ir.graph.edges.append(
            Edge(
                id="out2edge",
                source=EdgeEndpoint(node_id="second", port="out"),
                target=EdgeEndpoint(node_id="out2", port="x"),
            )
        )
        normalized, diagnostics = normalize_and_validate(ir)
        self.assertTrue(normalized.graph.nodes)
        self.assertEqual(diagnostics, [])
        result = analyze(ir)
        self.assertTrue(result.valid, result.diagnostics)
        self.assertEqual(result.chain_count, 2)

    def test_add_merge_and_parallel_branches(self) -> None:
        ir = IRDocument(
            graph_meta=GraphMeta(name="Parallel Add"),
            graph=Graph(
                nodes=[
                    Node(
                        id="input",
                        op="Input",
                        params={"name": "x", "sample_shape": [1, 10], "dtype": "float32"},
                    ),
                    Node(id="left", op="nn.Identity", params={}),
                    Node(id="right", op="nn.Identity", params={}),
                    Node(id="third", op="nn.Identity", params={}),
                    Node(id="merge", op="merge.Add", params={}),
                    Node(id="output", op="Output", params={"name": "y"}),
                ],
                edges=[
                    Edge(
                        id="e1",
                        source=EdgeEndpoint(node_id="input", port="out"),
                        target=EdgeEndpoint(node_id="left", port="x"),
                    ),
                    Edge(
                        id="e2",
                        source=EdgeEndpoint(node_id="input", port="out"),
                        target=EdgeEndpoint(node_id="right", port="x"),
                    ),
                    Edge(
                        id="e2b",
                        source=EdgeEndpoint(node_id="input", port="out"),
                        target=EdgeEndpoint(node_id="third", port="x"),
                    ),
                    Edge(
                        id="e3",
                        source=EdgeEndpoint(node_id="left", port="out"),
                        target=EdgeEndpoint(node_id="merge", port="x"),
                    ),
                    Edge(
                        id="e4",
                        source=EdgeEndpoint(node_id="right", port="out"),
                        target=EdgeEndpoint(node_id="merge", port="x"),
                    ),
                    Edge(
                        id="e4b",
                        source=EdgeEndpoint(node_id="third", port="out"),
                        target=EdgeEndpoint(node_id="merge", port="x"),
                    ),
                    Edge(
                        id="e5",
                        source=EdgeEndpoint(node_id="merge", port="out"),
                        target=EdgeEndpoint(node_id="output", port="x"),
                    ),
                ],
            ),
        )
        result = analyze(ir)
        self.assertTrue(result.valid, result.diagnostics)
        merge = next(node for node in result.nodes if node.node_id == "merge")
        self.assertEqual(
            [port.name for port in merge.ports],
            ["x", "x", "x", "out"],
        )
        output = next(port for port in merge.ports if port.io == "out")
        self.assertEqual(output.shape, [1, 10])
        for framework, token in (
            ("pytorch", "torch.add"),
            ("paddle", "paddle.add"),
        ):
            code = generate_code(ir, framework, include_demo=True)
            self.assertTrue(code.syntax_valid)
            self.assertIn(token, code.source)

        multiply_ir = ir.model_copy(deep=True)
        merge_node = next(
            node for node in multiply_ir.graph.nodes if node.id == "merge"
        )
        merge_node.op = "merge.Multiply"
        merge_node.params = {}
        multiply = generate_code(multiply_ir, "pytorch", include_demo=True)
        self.assertIn("torch.multiply", multiply.source)
        self.assertTrue(multiply.syntax_valid)

    def test_concat_merge_shape_and_code(self) -> None:
        ir = IRDocument(
            graph_meta=GraphMeta(name="Parallel Concat"),
            graph=Graph(
                nodes=[
                    Node(
                        id="input",
                        op="Input",
                        params={"name": "x", "sample_shape": [1, 10], "dtype": "float32"},
                    ),
                    Node(id="left", op="nn.Identity", params={}),
                    Node(id="right", op="nn.Identity", params={}),
                    Node(
                        id="merge",
                        op="merge.Concat",
                        params={"dim": -1},
                    ),
                    Node(id="output", op="Output", params={"name": "y"}),
                ],
                edges=[
                    Edge(
                        id="e1",
                        source=EdgeEndpoint(node_id="input", port="out"),
                        target=EdgeEndpoint(node_id="left", port="x"),
                    ),
                    Edge(
                        id="e2",
                        source=EdgeEndpoint(node_id="input", port="out"),
                        target=EdgeEndpoint(node_id="right", port="x"),
                    ),
                    Edge(
                        id="e3",
                        source=EdgeEndpoint(node_id="left", port="out"),
                        target=EdgeEndpoint(node_id="merge", port="x"),
                    ),
                    Edge(
                        id="e4",
                        source=EdgeEndpoint(node_id="right", port="out"),
                        target=EdgeEndpoint(node_id="merge", port="x"),
                    ),
                    Edge(
                        id="e5",
                        source=EdgeEndpoint(node_id="merge", port="out"),
                        target=EdgeEndpoint(node_id="output", port="x"),
                    ),
                ],
            ),
        )
        result = analyze(ir)
        self.assertTrue(result.valid, result.diagnostics)
        merge = next(node for node in result.nodes if node.node_id == "merge")
        output = next(port for port in merge.ports if port.io == "out")
        self.assertEqual(output.shape, [1, 20])
        paddle = generate_code(ir, "paddle", include_demo=True)
        self.assertIn("paddle.concat", paddle.source)
        self.assertIn("axis=-1", paddle.source)

    def test_empty_canvas_returns_actionable_diagnostics(self) -> None:
        result = analyze(IRDocument())
        self.assertFalse(result.valid)
        codes = {item.code for item in result.diagnostics}
        self.assertIn("MISSING_INPUT", codes)
        self.assertIn("MISSING_OUTPUT", codes)

    def test_if_for_while_generate_real_control_statements(self) -> None:
        for op, token in (
            ("control.If", "if "),
            ("control.For", "for "),
            ("control.While", "while "),
        ):
            with self.subTest(op=op):
                ir = control_ir(op)
                result = analyze(ir)
                self.assertTrue(result.valid, result.diagnostics)
                code = generate_code(ir, "pytorch", include_demo=False)
                self.assertTrue(code.syntax_valid)
                self.assertIn(token, code.source)

    def test_control_if_branch_signature_mismatch(self) -> None:
        ir = control_ir("control.If")
        else_region = ir.regions["else"]
        else_region.graph.nodes.insert(
            2,
            Node(
                id="else_linear",
                op="nn.Linear",
                params={
                    "in_features": 8,
                    "out_features": 9,
                    "bias": True,
                },
            ),
        )
        else_region.graph.edges = [
            Edge(
                id="else_in",
                source=EdgeEndpoint(node_id="in_else", port="out"),
                target=EdgeEndpoint(node_id="identity_else", port="x"),
            ),
            Edge(
                id="else_linear",
                source=EdgeEndpoint(node_id="identity_else", port="out"),
                target=EdgeEndpoint(node_id="else_linear", port="x"),
            ),
            Edge(
                id="else_out",
                source=EdgeEndpoint(node_id="else_linear", port="out"),
                target=EdgeEndpoint(node_id="out_else", port="x"),
            ),
        ]
        result = analyze(ir)
        self.assertFalse(result.valid)
        self.assertIn(
            "IF_BRANCH_SIGNATURE",
            {item.code for item in result.diagnostics},
        )

    def test_multihead_attention_and_lstm_ports(self) -> None:
        mha_nodes = []
        mha_edges = []
        for index, name in enumerate(("query", "key", "value")):
            mha_nodes.append(
                Node(
                    id=name,
                    op="Input",
                    params={
                        "name": name,
                        "sample_shape": [2, 4, 8],
                        "dtype": "float32",
                    },
                )
            )
        mha_nodes.extend(
            [
                Node(
                    id="mha",
                    op="nn.MultiheadAttention",
                    params=defaults_for("nn.MultiheadAttention"),
                ),
                Node(id="out", op="Output", params={"name": "out"}),
            ]
        )
        for index, name in enumerate(("query", "key", "value")):
            mha_edges.append(
                Edge(
                    id=f"mha{index}",
                    source=EdgeEndpoint(node_id=name, port="out"),
                    target=EdgeEndpoint(node_id="mha", port=name),
                )
            )
        mha_edges.append(
            Edge(
                id="mha_out",
                source=EdgeEndpoint(node_id="mha", port="attn_output"),
                target=EdgeEndpoint(node_id="out", port="x"),
            )
        )
        mha_ir = IRDocument(
            graph=Graph(nodes=mha_nodes, edges=mha_edges)
        )
        mha = analyze(mha_ir)
        self.assertTrue(mha.valid, mha.diagnostics)
        mha_code = generate_code(mha_ir, "pytorch", include_demo=False)
        self.assertIn("MultiheadAttention", mha_code.source)
        self.assertIn("attn_weights", mha_code.source)

        lstm_ir = IRDocument(
            target_framework="pytorch",
            graph=Graph(
                nodes=[
                    Node(
                        id="input",
                        op="Input",
                        params={
                            "name": "x",
                            "sample_shape": [5, 2, 8],
                            "dtype": "float32",
                        },
                    ),
                    Node(
                        id="lstm",
                        op="nn.LSTM",
                        params=defaults_for("nn.LSTM"),
                    ),
                    Node(id="out", op="Output", params={"name": "out"}),
                ],
                edges=[
                    Edge(
                        id="l1",
                        source=EdgeEndpoint(node_id="input", port="out"),
                        target=EdgeEndpoint(node_id="lstm", port="input"),
                    ),
                    Edge(
                        id="l2",
                        source=EdgeEndpoint(node_id="lstm", port="output"),
                        target=EdgeEndpoint(node_id="out", port="x"),
                    ),
                ],
            ),
        )
        lstm = analyze(lstm_ir)
        self.assertTrue(lstm.valid, lstm.diagnostics)
        lstm_node = next(item for item in lstm.nodes if item.node_id == "lstm")
        self.assertIn("h_n", {port.name for port in lstm_node.ports})
        self.assertIn("c_n", {port.name for port in lstm_node.ports})

    def test_py02_migrates_to_py03(self) -> None:
        old = SAMPLES["mnist-mlp"]["ir"]().model_copy(deep=True)
        old.ir_version = "0.2"
        result = analyze(old)
        self.assertTrue(result.valid, result.diagnostics)
        self.assertEqual(result.normalized_ir.ir_version, "0.3")


class ImporterTests(unittest.TestCase):
    SOURCE = """import torch.nn as nn

class Student(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(784, 128)
        self.act = nn.ReLU()
        self.fc2 = nn.Linear(128, 10)

    def forward(self, x):
        x = self.fc1(x)
        x = self.act(x)
        return self.fc2(x)
"""

    def test_sequential_import(self) -> None:
        result = import_pytorch(
            ImportRequest(source=self.SOURCE, shape=[1, 784])
        )
        self.assertIsNotNone(result.ir)
        self.assertEqual(result.diagnostics, [])
        self.assertEqual(len(result.ir.graph.nodes), 5)  # type: ignore[union-attr]

    def test_branch_is_rejected(self) -> None:
        source = self.SOURCE.replace(
            "        x = self.act(x)\n        return self.fc2(x)",
            "        if x.sum() > 0:\n            x = self.act(x)\n        return self.fc2(x)",
        )
        result = import_pytorch(ImportRequest(source=source, shape=[1, 784]))
        self.assertIsNone(result.ir)
        self.assertEqual(result.diagnostics[0].code, "IMPORT_UNSUPPORTED")
        self.assertIn("line", result.diagnostics[0].field or "")

    def test_multiple_user_module_classes_become_resources(self) -> None:
        source = """import torch.nn as nn

class Block(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc = nn.Linear(784, 32)

    def forward(self, x):
        return self.fc(x)

class Model(nn.Module):
    def __init__(self):
        super().__init__()
        self.block = Block()
        self.out = nn.Linear(32, 10)

    def forward(self, x):
        x = self.block(x)
        return self.out(x)
"""
        result = import_pytorch(
            ImportRequest(source=source, shape=[1, 784])
        )
        self.assertIsNotNone(result.ir)
        self.assertEqual(result.diagnostics, [])
        self.assertEqual(result.ir.graph_meta.name, "Model")  # type: ignore[union-attr]
        self.assertEqual(len(result.ir.resources), 1)  # type: ignore[union-attr]
        resource = result.ir.resources[0]  # type: ignore[union-attr]
        self.assertEqual(resource.name, "Block")
        self.assertEqual(resource.inputs[0].shape, [1, 784])
        self.assertEqual(resource.outputs[0].shape, [1, 32])
        composite = next(
            node
            for node in result.ir.graph.nodes  # type: ignore[union-attr]
            if node.op == "composite.instance"
        )
        self.assertEqual(composite.composite_ref.revision, 1)

    def test_structured_control_flow_import(self) -> None:
        source = """import torch.nn as nn

class Model(nn.Module):
    def __init__(self):
        super().__init__()
        self.act = nn.ReLU()

    def forward(self, x):
        if x > 0:
            x = self.act(x)
        else:
            x = self.act(x)
        for _ in range(2):
            x = self.act(x)
        while x > -1:
            x = self.act(x)
        return x
"""
        result = import_pytorch(
            ImportRequest(source=source, shape=[1, 10])
        )
        self.assertIsNotNone(result.ir)
        self.assertEqual(result.diagnostics, [])
        ops = {
            node.op
            for node in result.ir.graph.nodes  # type: ignore[union-attr]
        }
        self.assertTrue(
            {"control.If", "control.For", "control.While"}.issubset(ops)
        )
        code = generate_code(result.ir, "pytorch", include_demo=False)  # type: ignore[arg-type]
        self.assertIn("if ", code.source)
        self.assertIn("for ", code.source)
        self.assertIn("while ", code.source)


class CompositeResourceTests(unittest.TestCase):
    def _publish_parallel(self, resource_id: str = "parallel-block") -> CompositeResource:
        response = publish_composite(
            PublishCompositeRequest(
                resource_id=resource_id,
                name="Parallel Block",
                revision=1,
                ir=parallel_add(),
            )
        )
        self.assertTrue(response.valid, response.diagnostics)
        self.assertIsNotNone(response.resource)
        return response.resource  # type: ignore[return-value]

    def _parent_ir(self, resource: CompositeResource) -> IRDocument:
        contract = StateContract(
            inputs=resource.inputs,
            outputs=resource.outputs,
        )
        return IRDocument(
            graph=Graph(
                nodes=[
                    Node(
                        id="input",
                        op="Input",
                        params={
                            "name": "x",
                            "sample_shape": [1, 784],
                            "dtype": "float32",
                        },
                    ),
                    Node(
                        id="composite",
                        op="composite.instance",
                        params={"name": resource.name},
                        composite_ref=CompositeRef(
                            resource_id=resource.resource_id,
                            revision=resource.revision,
                        ),
                        state_contract=contract,
                    ),
                    Node(
                        id="output",
                        op="Output",
                        params={"name": "y"},
                    ),
                ],
                edges=[
                    Edge(
                        id="e1",
                        source=EdgeEndpoint(node_id="input", port="out"),
                        target=EdgeEndpoint(
                            node_id="composite",
                            port=resource.inputs[0].name,
                        ),
                    ),
                    Edge(
                        id="e2",
                        source=EdgeEndpoint(
                            node_id="composite",
                            port=resource.outputs[0].name,
                        ),
                        target=EdgeEndpoint(node_id="output", port="x"),
                    ),
                ],
            ),
            resources=[resource],
        )

    def test_publish_interface_and_embedded_module_code(self) -> None:
        resource = self._publish_parallel()
        self.assertEqual([port.name for port in resource.inputs], ["x"])
        self.assertEqual([port.name for port in resource.outputs], ["y"])
        self.assertGreater(len(resource.parameter_defaults), 0)
        ir = self._parent_ir(resource)
        result = analyze(ir)
        self.assertTrue(result.valid, result.diagnostics)
        code = generate_code(ir, "pytorch", include_demo=False)
        self.assertIn("class ParallelBlock1CompositeModel", code.source)
        self.assertIn("ParallelBlock1CompositeModel()", code.source)

    def test_missing_composite_version_is_rejected(self) -> None:
        resource = self._publish_parallel("missing-resource")
        ir = self._parent_ir(resource)
        ir.resources = []
        result = analyze(ir)
        self.assertFalse(result.valid)
        self.assertIn(
            "MISSING_COMPOSITE_RESOURCE",
            {item.code for item in result.diagnostics},
        )

    def test_composite_param_overrides_recompute_shape(self) -> None:
        resource = self._publish_parallel("override-resource")
        ir = self._parent_ir(resource)
        composite = next(
            node for node in ir.graph.nodes if node.id == "composite"
        )
        composite.param_overrides = {
            "left_linear.out_features": 64,
            "right_linear.out_features": 64,
        }
        result = analyze(ir)
        self.assertTrue(result.valid, result.diagnostics)
        node = next(
            item for item in result.nodes if item.node_id == "composite"
        )
        output = next(port for port in node.ports if port.io == "out")
        self.assertEqual(output.shape, [1, 64])
        code = generate_code(ir, "pytorch", include_demo=False)
        self.assertIn("out_features=64", code.source)


class CoursePackageTests(unittest.TestCase):
    def test_round_trip_and_hash_validation(self) -> None:
        pack = CoursePack(
            title="MLP 课堂",
            ir=SAMPLES["mnist-mlp"]["ir"](),
            steps=[],
        )
        content = create_package(pack)
        response = validate_package(
            CourseImportRequest(content_base64=base64.b64encode(content).decode())
        )
        self.assertTrue(response.valid)
        self.assertEqual(response.pack.title, "MLP 课堂")  # type: ignore[union-attr]

        source = io.BytesIO(content)
        destination = io.BytesIO()
        with zipfile.ZipFile(source) as input_zip, zipfile.ZipFile(
            destination, "w"
        ) as output_zip:
            for info in input_zip.infolist():
                output_zip.writestr(info.filename, input_zip.read(info.filename) + b" ")
        invalid = validate_package(
            CourseImportRequest(
                content_base64=base64.b64encode(destination.getvalue()).decode()
            )
        )
        self.assertFalse(invalid.valid)


class ApiTests(unittest.TestCase):
    def test_health_catalog_and_codegen_routes(self) -> None:
        health_response = health()
        self.assertEqual(health_response.status, "ok")

        catalog_response = catalog()
        self.assertEqual(len(catalog_response.blocks), 140)

        request = CodegenRequest(
            ir=SAMPLES["mnist-mlp"]["ir"](),
            framework="pytorch",
            include_demo=True,
        )
        response = codegen(request)
        self.assertTrue(response.syntax_valid)
        self.assertIn("class MNISTMLPModel", response.source)
        route_paths = {route.path for route in app.routes}
        self.assertIn("/api/v1/graphs/codegen", route_paths)
        self.assertIn("/api/v1/graphs/import/pytorch", route_paths)

    def test_native_python_save_writes_selected_path(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "generated.py"
            with patch(
                "backend.files.shutil.which",
                return_value="/usr/bin/zenity",
            ), patch(
                "backend.files.subprocess.run",
                return_value=SimpleNamespace(
                    returncode=0,
                    stdout=f"{target}\n",
                    stderr="",
                ),
            ):
                response = save_python_with_native_dialog(
                    SavePythonRequest(
                        filename="generated.py",
                        source="print('ok')\n",
                    )
                )
            self.assertEqual(response.status, "saved")
            self.assertEqual(target.read_text(encoding="utf-8"), "print('ok')\n")


if __name__ == "__main__":
    unittest.main()
