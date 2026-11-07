import { create } from "zustand";
import { api } from "./api";
import { autoLayout } from "./layout";
import {
  deleteCompositeResources,
  loadCompositeResources,
  resourceKey,
  saveCompositeResource,
} from "./resourceDb";
import type {
  AnalysisResult,
  BlockSpec,
  BottomPanel,
  CodegenResponse,
  CompositeRef,
  CompositeResource,
  Diagnostic,
  Framework,
  GraphEdge,
  GraphNode,
  GraphRegion,
  IRDocument,
  MojoAsset,
  Moment,
  Position,
  PortContract,
  SampleSummary,
  StateContract,
  TraceResponse,
} from "./types";

interface Toast {
  kind: "success" | "error" | "info";
  message: string;
}

interface ViewFrame {
  ir: IRDocument;
  selectedNodeId: string | null;
  undoStack: IRDocument[];
  redoStack: IRDocument[];
  parentView: ActiveView;
  controlNodeId?: string;
  regionId?: string;
}

export interface ActiveView {
  kind: "root" | "control" | "composite";
  label: string;
  controlNodeId?: string;
  regionId?: string;
  resourceId?: string;
  revision?: number;
  readOnly: boolean;
}

interface GraphState {
  catalog: BlockSpec[];
  samples: SampleSummary[];
  resources: CompositeResource[];
  ir: IRDocument;
  selectedNodeId: string | null;
  mojos: MojoAsset[];
  analysis: AnalysisResult | null;
  bottomPanel: BottomPanel | null;
  code: CodegenResponse | null;
  trace: TraceResponse | null;
  moments: Moment[];
  undoStack: IRDocument[];
  redoStack: IRDocument[];
  busy: boolean;
  initialized: boolean;
  dirty: boolean;
  toast: Toast | null;
  validationSequence: number;
  initialize: () => Promise<void>;
  newDocument: () => void;
  loadSample: (id: string) => Promise<void>;
  loadDocument: (ir: IRDocument, message?: string) => void;
  setSelectedNode: (id: string | null) => void;
  addNode: (op: string, position: Position) => void;
  moveNode: (id: string, position: Position) => void;
  updateNodeTeachingNote: (id: string, note: string) => void;
  updateNodeParam: (id: string, key: string, value: unknown) => void;
  removeSelectedNode: () => void;
  removeNode: (id: string) => void;
  connect: (
    sourceId: string,
    targetId: string,
    targetPort: string,
    sourcePort?: string,
  ) => void;
  removeEdge: (edgeId: string) => void;
  clearGraph: () => void;
  addSubgraph: (
    nodes: GraphNode[],
    edges: GraphEdge[],
    positions: Record<string, Position>,
  ) => void;
  createMojo: (nodeIds: string[]) => MojoAsset | null;
  addMojo: (mojoId: string, position: Position) => void;
  updateMeta: (field: "name" | "author" | "note", value: string) => void;
  setFramework: (framework: Framework) => void;
  applyAutoLayout: () => void;
  undo: () => void;
  redo: () => void;
  validateNow: () => Promise<void>;
  generateCode: () => Promise<CodegenResponse | null>;
  runTracePreview: () => Promise<void>;
  runMomentDetection: () => Promise<void>;
  setBottomPanel: (panel: BottomPanel | null) => void;
  showToast: (kind: Toast["kind"], message: string) => void;
  clearToast: () => void;
  markSaved: () => void;
  publishCurrentComposite: (
    name: string,
    description?: string,
  ) => Promise<CompositeResource | null>;
  addComposite: (
    resourceId: string,
    revision: number,
    position: Position,
  ) => void;
  viewStack: ViewFrame[];
  activeView: ActiveView;
  enterNode: (nodeId: string) => void;
  switchControlRegion: (regionName: string) => void;
  createCompositeDraft: () => void;
  saveCompositeDraft: () => Promise<void>;
  exitSubgraph: () => void;
  changeCompositeVersion: (nodeId: string, revision: number) => void;
  setCompositeParamOverride: (
    nodeId: string,
    path: string,
    value: unknown,
  ) => void;
  importCompositeResource: (resource: CompositeResource) => Promise<void>;
  addControlStatePort: (nodeId: string, io: "in" | "out") => void;
  updateControlStatePort: (
    nodeId: string,
    io: "in" | "out",
    index: number,
    field: "name" | "shape" | "dtype" | "data_type",
    value: unknown,
  ) => void;
  addLoopIndexPort: (nodeId: string) => void;
  deleteCompositeResource: (resourceId: string) => Promise<void>;
}

const now = new Date().toISOString();

function baseDocument(): IRDocument {
  return {
    ir_version: "0.3",
    target_framework: "pytorch",
    graph_meta: {
      name: "未命名模型",
      author: "",
      is_composite: false,
      composite_version_tag: null,
      note: "",
      updated_at: now,
    },
    graph: {
      nodes: [
        {
          id: "input_x",
          op: "Input",
          params: { name: "x", sample_shape: [1, 784], dtype: "float32" },
          teaching_note: "模型入口",
        },
        {
          id: "output_y",
          op: "Output",
          params: { name: "logits" },
          teaching_note: "模型出口",
        },
      ],
      edges: [],
    },
    regions: {},
    resources: [],
    ui: {
      positions: {
        input_x: { x: 90, y: 220 },
        output_y: { x: 540, y: 220 },
      },
      zoom: 1,
    },
    check_info: null,
  };
}

function collectResourceBundle(
  resource: CompositeResource,
): CompositeResource[] {
  const found = new Map<string, CompositeResource>();
  const visit = (item: CompositeResource) => {
    const key = resourceKey(item);
    if (found.has(key)) return;
    for (const dependency of item.dependencies) visit(dependency);
    found.set(key, item);
  };
  visit(resource);
  return [...found.values()];
}

function collectDependencyBundle(
  resource: CompositeResource,
): CompositeResource[] {
  const found = new Map<string, CompositeResource>();
  const visit = (item: CompositeResource) => {
    const key = resourceKey(item);
    if (found.has(key)) return;
    for (const dependency of item.dependencies) visit(dependency);
    found.set(key, item);
  };
  for (const dependency of resource.dependencies) visit(dependency);
  return [...found.values()];
}

function mergeResourceList(
  existing: CompositeResource[],
  incoming: CompositeResource[],
): CompositeResource[] {
  const merged = new Map(
    existing.map((resource) => [resourceKey(resource), resource]),
  );
  for (const resource of incoming) {
    for (const bundled of collectResourceBundle(resource)) {
      merged.set(resourceKey(bundled), bundled);
    }
  }
  return [...merged.values()];
}

function resourceDocument(
  resource: CompositeResource,
  framework: Framework,
  editable: boolean,
): IRDocument {
  return {
    ir_version: "0.3",
    target_framework: framework,
    graph_meta: {
      name: resource.name,
      author: resource.author,
      is_composite: true,
      composite_version_tag: `v${resource.revision}`,
      note: resource.description,
      updated_at: new Date().toISOString(),
    },
    graph: structuredClone(resource.graph),
    regions: structuredClone(resource.regions),
    resources: structuredClone(collectDependencyBundle(resource)),
    ui: structuredClone(resource.ui),
    check_info: null,
  };
}

function identityRegion(
  id: string,
  kind: GraphRegion["kind"],
  contract: StateContract,
): GraphRegion {
  const input = contract.inputs[0];
  const output = contract.outputs[0];
  return {
    id,
    kind,
    graph: {
      nodes: [
        {
          id: `in_${id}`,
          op: "Input",
          params: {
            name: input.name,
            sample_shape: input.shape ?? [1, 10],
            dtype: input.dtype ?? "float32",
            data_type: input.data_type,
          },
          teaching_note: "",
        },
        {
          id: `identity_${id}`,
          op: "nn.Identity",
          params: {},
          teaching_note: "",
        },
        {
          id: `out_${id}`,
          op: "Output",
          params: { name: output.name, data_type: output.data_type },
          teaching_note: "",
        },
      ],
      edges: [
        {
          id: `edge_in_${id}`,
          source: { node_id: `in_${id}`, port: "out" },
          target: { node_id: `identity_${id}`, port: "x" },
        },
        {
          id: `edge_out_${id}`,
          source: { node_id: `identity_${id}`, port: "out" },
          target: { node_id: `out_${id}`, port: "x" },
        },
      ],
    },
    ui: {
      positions: {
        [`in_${id}`]: { x: 80, y: 160 },
        [`identity_${id}`]: { x: 360, y: 160 },
        [`out_${id}`]: { x: 640, y: 160 },
      },
      zoom: 1,
    },
    inputs: [input],
    outputs: [output],
    read_only: false,
  };
}

function predicateRegion(
  id: string,
  contract: StateContract,
): GraphRegion {
  const input = contract.inputs[0];
  const prefix = id;
  return {
    id,
    kind: "predicate",
    graph: {
      nodes: [
        {
          id: `in_${prefix}`,
          op: "Input",
          params: {
            name: input.name,
            sample_shape: input.shape ?? [1, 10],
            dtype: input.dtype ?? "float32",
            data_type: input.data_type,
          },
          teaching_note: "",
        },
        {
          id: `left_${prefix}`,
          op: "nn.Identity",
          params: {},
          teaching_note: "",
        },
        {
          id: `right_${prefix}`,
          op: "nn.Identity",
          params: {},
          teaching_note: "",
        },
        {
          id: `compare_${prefix}`,
          op: "logic.Compare",
          params: { operator: "gt" },
          teaching_note: "",
        },
        {
          id: `all_${prefix}`,
          op: "logic.All",
          params: {},
          teaching_note: "",
        },
        {
          id: `condition_${prefix}`,
          op: "Output",
          params: { name: "condition", data_type: "ScalarBool" },
          teaching_note: "",
        },
      ],
      edges: [
        {
          id: `p_in_left_${prefix}`,
          source: { node_id: `in_${prefix}`, port: "out" },
          target: { node_id: `left_${prefix}`, port: "x" },
        },
        {
          id: `p_in_right_${prefix}`,
          source: { node_id: `in_${prefix}`, port: "out" },
          target: { node_id: `right_${prefix}`, port: "x" },
        },
        {
          id: `p_left_cmp_${prefix}`,
          source: { node_id: `left_${prefix}`, port: "out" },
          target: { node_id: `compare_${prefix}`, port: "x" },
        },
        {
          id: `p_right_cmp_${prefix}`,
          source: { node_id: `right_${prefix}`, port: "out" },
          target: { node_id: `compare_${prefix}`, port: "x" },
        },
        {
          id: `p_cmp_all_${prefix}`,
          source: { node_id: `compare_${prefix}`, port: "out" },
          target: { node_id: `all_${prefix}`, port: "x" },
        },
        {
          id: `p_all_out_${prefix}`,
          source: { node_id: `all_${prefix}`, port: "out" },
          target: { node_id: `condition_${prefix}`, port: "x" },
        },
      ],
    },
    ui: {
      positions: {
        [`in_${prefix}`]: { x: 40, y: 180 },
        [`left_${prefix}`]: { x: 310, y: 80 },
        [`right_${prefix}`]: { x: 310, y: 290 },
        [`compare_${prefix}`]: { x: 590, y: 180 },
        [`all_${prefix}`]: { x: 870, y: 180 },
        [`condition_${prefix}`]: { x: 1140, y: 180 },
      },
      zoom: 1,
    },
    inputs: [input],
    outputs: [
      {
        name: "condition",
        data_type: "ScalarBool",
        shape: [],
        dtype: "bool",
        required: true,
      },
    ],
    read_only: false,
  };
}

function controlRegions(
  nodeId: string,
  op: string,
): {
  contract: StateContract;
  regions: Record<string, GraphRegion>;
  regionRefs: Record<string, string>;
} {
  const input = {
    name: "state",
    data_type: "Tensor" as const,
    shape: [1, 10],
    dtype: "float32",
    required: true,
  };
  const contract: StateContract = {
    inputs: [input],
    outputs: [{ ...input }],
  };
  if (op === "control.If") {
    const predicateId = `${nodeId}_predicate`;
    const thenId = `${nodeId}_then`;
    const elseId = `${nodeId}_else`;
    return {
      contract,
      regions: {
        [predicateId]: predicateRegion(predicateId, contract),
        [thenId]: identityRegion(thenId, "then", contract),
        [elseId]: identityRegion(elseId, "else", contract),
      },
      regionRefs: {
        predicate: predicateId,
        then: thenId,
        else: elseId,
      },
    };
  }
  const bodyId = `${nodeId}_body`;
  if (op === "control.While") {
    const predicateId = `${nodeId}_predicate`;
    return {
      contract,
      regions: {
        [predicateId]: predicateRegion(predicateId, contract),
        [bodyId]: identityRegion(bodyId, "body", contract),
      },
      regionRefs: {
        predicate: predicateId,
        body: bodyId,
      },
    };
  }
  return {
    contract,
    regions: {
      [bodyId]: identityRegion(bodyId, "body", contract),
    },
    regionRefs: { body: bodyId },
  };
}

function clone<T>(value: T): T {
  return structuredClone(value);
}

function uid(prefix: string): string {
  const suffix =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID().slice(0, 8)
      : Math.random().toString(36).slice(2, 10);
  return `${prefix}_${suffix}`;
}

function defaultsFor(block: BlockSpec): Record<string, unknown> {
  return Object.fromEntries(
    block.fields.map((field) => [field.key, structuredClone(field.default)]),
  );
}

const MOJO_STORAGE_KEY = "netbrick.reusable-mojos.v1";

function loadMojos(): MojoAsset[] {
  try {
    const raw = localStorage.getItem(MOJO_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as MojoAsset[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function persistMojos(mojos: MojoAsset[]) {
  try {
    localStorage.setItem(MOJO_STORAGE_KEY, JSON.stringify(mojos));
  } catch {
    // A full or disabled localStorage should not break the editor.
  }
}

function analysisDiagnostics(
  analysis: AnalysisResult | null,
  fallback: string | null,
): Diagnostic[] {
  if (analysis?.diagnostics.length) {
    return analysis.diagnostics;
  }
  if (fallback) {
    return [
      {
        code: "CLIENT_ERROR",
        severity: "error",
        message: fallback,
        teaching_tip: "请检查后端是否已启动，或稍后重试。",
      },
    ];
  }
  return [];
}

export const useGraphStore = create<GraphState>((set, get) => {
  const commit = (mutator: (draft: IRDocument) => void) => {
    const state = get();
    if (state.activeView.readOnly) {
      state.showToast("info", "当前复合资源版本为只读，请先创建新版本");
      return;
    }
    const draft = clone(state.ir);
    mutator(draft);
    draft.graph_meta.updated_at = new Date().toISOString();
    draft.check_info = null;
    set({
      ir: draft,
      undoStack: [...state.undoStack.slice(-49), clone(state.ir)],
      redoStack: [],
      code: null,
      trace: null,
      moments: [],
      dirty: true,
    });
  };

  const replaceWithoutHistory = (ir: IRDocument) => {
    set({
      ir,
      code: null,
      trace: null,
      moments: [],
      analysis: null,
      dirty: false,
    });
  };

  const appendSubgraph = (
    nodes: GraphNode[],
    edges: GraphEdge[],
    positions: Record<string, Position>,
  ) => {
    if (nodes.length === 0) return;
    commit((draft) => {
      draft.graph.nodes.push(...clone(nodes));
      draft.graph.edges.push(...clone(edges));
      Object.assign(draft.ui.positions, clone(positions));
    });
    set({ selectedNodeId: nodes[0]?.id ?? null });
  };

  return {
    catalog: [],
    samples: [],
    resources: [],
    ir: baseDocument(),
    selectedNodeId: null,
    mojos: loadMojos(),
    analysis: null,
    bottomPanel: "diagnostics",
    code: null,
    trace: null,
    moments: [],
    undoStack: [],
    redoStack: [],
    busy: false,
    initialized: false,
    dirty: false,
    toast: null,
    validationSequence: 0,
    viewStack: [],
    activeView: {
      kind: "root",
      label: "工作区",
      readOnly: false,
    },

    initialize: async () => {
      if (get().initialized) return;
      set({ busy: true });
      try {
        const [catalog, samples] = await Promise.all([
          api.catalog(),
          api.samples(),
        ]);
        let resources: CompositeResource[] = [];
        try {
          resources = await loadCompositeResources();
        } catch {
          resources = [];
        }
        set({ catalog: catalog.blocks, samples, resources });
        const first = samples[0];
        if (first) {
          const ir = await api.sample(first.id);
          replaceWithoutHistory(ir);
          set({ initialized: true, busy: false });
          await get().validateNow();
        } else {
          set({ initialized: true, busy: false });
        }
      } catch (error) {
        set({
          initialized: true,
          busy: false,
          toast: {
            kind: "error",
            message:
              error instanceof Error
                ? `初始化失败：${error.message}`
                : "初始化失败",
          },
        });
      }
    },

    newDocument: () => {
      replaceWithoutHistory(baseDocument());
      set({
        selectedNodeId: null,
        undoStack: [],
        redoStack: [],
        bottomPanel: "diagnostics",
        viewStack: [],
        activeView: {
          kind: "root",
          label: "工作区",
          readOnly: false,
        },
      });
      void get().validateNow();
    },

    loadSample: async (id) => {
      set({ busy: true });
      try {
        const ir = await api.sample(id);
        replaceWithoutHistory(ir);
        set({
          selectedNodeId: null,
          undoStack: [],
          redoStack: [],
          bottomPanel: "diagnostics",
          viewStack: [],
          activeView: {
            kind: "root",
            label: "工作区",
            readOnly: false,
          },
          busy: false,
          toast: { kind: "success", message: `已载入 ${ir.graph_meta.name}` },
        });
        await get().validateNow();
      } catch (error) {
        set({
          busy: false,
          toast: {
            kind: "error",
            message: error instanceof Error ? error.message : "示例载入失败",
          },
        });
      }
    },

    loadDocument: (ir, message = "工程已载入") => {
      const state = get();
      replaceWithoutHistory(ir);
      const embedded = ir.resources ?? [];
      const resources = mergeResourceList(state.resources, embedded);
      set({
        selectedNodeId: null,
        undoStack: [...state.undoStack.slice(-49), clone(state.ir)],
        redoStack: [],
        bottomPanel: "diagnostics",
        viewStack: [],
        activeView: {
          kind: "root",
          label: "工作区",
          readOnly: false,
        },
        resources,
        toast: { kind: "success", message },
      });
      for (const resource of embedded) {
        void saveCompositeResource(resource).catch(() => undefined);
      }
      void get().validateNow();
    },

    setSelectedNode: (id) => set({ selectedNodeId: id }),

    addNode: (op, position) => {
      if (get().activeView.readOnly) {
        get().showToast("info", "当前复合资源版本为只读，请先创建新版本");
        return;
      }
      const block = get().catalog.find((item) => item.op === op);
      if (!block) return;
      const id = uid(op === "Input" ? "input" : op === "Output" ? "output" : "node");
      const control = op.startsWith("control.")
        ? controlRegions(id, op)
        : null;
      commit((draft) => {
        draft.graph.nodes.push({
          id,
          op,
          params: defaultsFor(block),
          teaching_note: "",
          ...(control
            ? {
                state_contract: control.contract,
                region_refs: control.regionRefs,
              }
            : {}),
        });
        draft.ui.positions[id] = position;
        if (control) {
          draft.regions = {
            ...(draft.regions ?? {}),
            ...control.regions,
          };
        }
      });
      set({ selectedNodeId: id });
    },

    moveNode: (id, position) => {
      if (get().activeView.readOnly) return;
      const ir = clone(get().ir);
      ir.ui.positions[id] = position;
      ir.graph_meta.updated_at = new Date().toISOString();
      set({ ir, dirty: true });
    },

    updateNodeTeachingNote: (id, note) => {
      commit((draft) => {
        const node = draft.graph.nodes.find((item) => item.id === id);
        if (node) node.teaching_note = note;
      });
    },

    updateNodeParam: (id, key, value) => {
      commit((draft) => {
        const node = draft.graph.nodes.find((item) => item.id === id);
        if (node) node.params[key] = value;
      });
    },

    removeSelectedNode: () => {
      const id = get().selectedNodeId;
      if (!id) return;
      commit((draft) => {
        draft.graph.nodes = draft.graph.nodes.filter((node) => node.id !== id);
        draft.graph.edges = draft.graph.edges.filter(
          (edge) =>
            edge.source.node_id !== id && edge.target.node_id !== id,
        );
        delete draft.ui.positions[id];
      });
      set({ selectedNodeId: null });
      void get().validateNow();
    },

    removeNode: (id) => {
      commit((draft) => {
        draft.graph.nodes = draft.graph.nodes.filter((node) => node.id !== id);
        draft.graph.edges = draft.graph.edges.filter(
          (edge) =>
            edge.source.node_id !== id && edge.target.node_id !== id,
        );
        delete draft.ui.positions[id];
      });
      if (get().selectedNodeId === id) set({ selectedNodeId: null });
      void get().validateNow();
    },

    connect: (sourceId, targetId, targetPort, sourcePort = "out") => {
      const { ir, catalog } = get();
      if (
        ir.graph.edges.some(
          (edge) =>
            edge.source.node_id === sourceId &&
            edge.source.port === sourcePort &&
            edge.target.node_id === targetId &&
            edge.target.port === targetPort,
        )
      ) {
        return;
      }
      const edge: GraphEdge = {
        id: uid("edge"),
        source: { node_id: sourceId, port: sourcePort },
        target: { node_id: targetId, port: targetPort },
      };
      const targetNode = ir.graph.nodes.find((node) => node.id === targetId);
      const targetBlock = catalog.find(
        (block) => block.op === targetNode?.op,
      );
      const acceptsMultipleInputs =
        targetBlock?.input_mode === "merge" && targetPort === "x";
      commit((draft) => {
        if (!acceptsMultipleInputs) {
          draft.graph.edges = draft.graph.edges.filter(
            (item) =>
              !(
                item.target.node_id === targetId &&
                item.target.port === targetPort
              ),
          );
        }
        draft.graph.edges.push(edge);
      });
      void get().validateNow();
    },

    removeEdge: (edgeId) => {
      commit((draft) => {
        draft.graph.edges = draft.graph.edges.filter(
          (edge) => edge.id !== edgeId,
        );
      });
      void get().validateNow();
    },

    clearGraph: () => {
      commit((draft) => {
        draft.graph.nodes = [];
        draft.graph.edges = [];
        draft.ui.positions = {};
      });
      set({ selectedNodeId: null });
      void get().validateNow();
    },

    addSubgraph: (nodes, edges, positions) => {
      appendSubgraph(nodes, edges, positions);
    },

    createMojo: (nodeIds) => {
      const state = get();
      const selected = state.ir.graph.nodes.filter((node) =>
        nodeIds.includes(node.id),
      );
      if (selected.length < 2) return null;
      const selectedIds = new Set(selected.map((node) => node.id));
      const points = selected.map(
        (node) => state.ir.ui.positions[node.id] ?? { x: 0, y: 0 },
      );
      const minX = Math.min(...points.map((point) => point.x));
      const minY = Math.min(...points.map((point) => point.y));
      const asset: MojoAsset = {
        id: uid("mojo"),
        name: `Mojo 复合块 ${state.mojos.length + 1}`,
        createdAt: new Date().toISOString(),
        nodes: clone(selected),
        edges: clone(
          state.ir.graph.edges.filter(
            (edge) =>
              selectedIds.has(edge.source.node_id) &&
              selectedIds.has(edge.target.node_id),
          ),
        ),
        positions: Object.fromEntries(
          selected.map((node) => {
            const point = state.ir.ui.positions[node.id] ?? { x: 0, y: 0 };
            return [node.id, { x: point.x - minX, y: point.y - minY }];
          }),
        ),
      };
      const mojos = [...state.mojos, asset];
      persistMojos(mojos);
      set({
        mojos,
        toast: {
          kind: "success",
          message: `${asset.name} 已加入模块库，可重复拖拽`,
        },
      });
      return asset;
    },

    addMojo: (mojoId, position) => {
      const asset = get().mojos.find((item) => item.id === mojoId);
      if (!asset) return;
      const idMap = new Map<string, string>();
      for (const node of asset.nodes) {
        idMap.set(node.id, uid(node.op === "Input" ? "input" : node.op === "Output" ? "output" : "node"));
      }
      const nodes = asset.nodes.map((node) => ({
        ...clone(node),
        id: idMap.get(node.id)!,
      }));
      const edges = asset.edges.map((edge) => ({
        ...clone(edge),
        id: uid("edge"),
        source: {
          ...edge.source,
          node_id: idMap.get(edge.source.node_id)!,
        },
        target: {
          ...edge.target,
          node_id: idMap.get(edge.target.node_id)!,
        },
      }));
      const positions = Object.fromEntries(
        Object.entries(asset.positions).map(([id, point]) => [
          idMap.get(id)!,
          { x: position.x + point.x, y: position.y + point.y },
        ]),
      );
      appendSubgraph(nodes, edges, positions);
      set({
        toast: {
          kind: "success",
          message: `${asset.name} 已展开到画布`,
        },
      });
    },

    updateMeta: (field, value) => {
      commit((draft) => {
        draft.graph_meta[field] = value;
      });
    },

    setFramework: (framework) => {
      commit((draft) => {
        draft.target_framework = framework;
      });
      set({ code: null });
    },

    applyAutoLayout: () => {
      commit((draft) => {
        draft.ui.positions = autoLayout(draft);
      });
    },

    undo: () => {
      const state = get();
      const previous = state.undoStack.at(-1);
      if (!previous) return;
      set({
        ir: clone(previous),
        undoStack: state.undoStack.slice(0, -1),
        redoStack: [...state.redoStack, clone(state.ir)],
        code: null,
        trace: null,
        dirty: true,
      });
      void get().validateNow();
    },

    redo: () => {
      const state = get();
      const next = state.redoStack.at(-1);
      if (!next) return;
      set({
        ir: clone(next),
        undoStack: [...state.undoStack, clone(state.ir)],
        redoStack: state.redoStack.slice(0, -1),
        code: null,
        trace: null,
        dirty: true,
      });
      void get().validateNow();
    },

    validateNow: async () => {
      const sequence = get().validationSequence + 1;
      set({ validationSequence: sequence });
      try {
        const analysis = await api.validate(get().ir);
        if (get().validationSequence !== sequence) return;
        set({ analysis });
        if (analysis.normalized_ir) {
          const current = get().ir;
          current.check_info = {
            static_shape_pass: analysis.valid,
            error_count: analysis.diagnostics.filter(
              (item) => item.severity === "error",
            ).length,
            checked_at: new Date().toISOString(),
          };
        }
      } catch (error) {
        if (get().validationSequence !== sequence) return;
        set({
          analysis: {
            valid: false,
            normalized_ir: null,
            nodes: [],
            diagnostics: analysisDiagnostics(
              null,
              error instanceof Error ? error.message : "校验请求失败",
            ),
            chain_count: 0,
          },
        });
      }
    },

    generateCode: async () => {
      set({ busy: true });
      try {
        const code = await api.codegen(get().ir, get().ir.target_framework);
        set({
          code,
          bottomPanel: "code",
          busy: false,
          toast: {
            kind: "success",
            message: `已生成 ${code.filename}，语法校验通过`,
          },
        });
        return code;
      } catch (error) {
        set({
          busy: false,
          bottomPanel: "diagnostics",
          toast: {
            kind: "error",
            message: error instanceof Error ? error.message : "代码生成失败",
          },
        });
        await get().validateNow();
        return null;
      }
    },

    runTracePreview: async () => {
      set({ busy: true });
      try {
        const trace = await api.trace(get().ir);
        set({
          trace,
          moments: [],
          bottomPanel: "trace",
          busy: false,
          toast:
            trace.diagnostics.length > 0
              ? { kind: "error", message: "结构追踪前请先修正错误" }
              : { kind: "success", message: "结构追踪已生成" },
        });
        void get().runMomentDetection();
      } catch (error) {
        set({
          busy: false,
          toast: {
            kind: "error",
            message:
              error instanceof Error ? error.message : "结构追踪请求失败",
          },
        });
      }
    },

    runMomentDetection: async () => {
      const trace = get().trace;
      if (!trace || trace.steps.length === 0) {
        set({ moments: [] });
        return;
      }
      try {
        const result = await api.moments(trace);
        if (get().trace !== trace) return;
        set({ moments: result.moments ?? [] });
      } catch {
        if (get().trace === trace) set({ moments: [] });
      }
    },

    setBottomPanel: (panel) => set({ bottomPanel: panel }),
    showToast: (kind, message) => set({ toast: { kind, message } }),
    clearToast: () => set({ toast: null }),
    markSaved: () => set({ dirty: false }),

    publishCurrentComposite: async (name, description = "") => {
      const state = get();
      const resourceId = uid("composite");
      set({ busy: true });
      try {
        const response = await api.publishComposite(
          state.ir,
          name,
          1,
          resourceId,
          description,
        );
        if (!response.valid || !response.resource) {
          set({
            busy: false,
            analysis: {
              valid: false,
              normalized_ir: null,
              nodes: [],
              diagnostics: response.diagnostics,
              chain_count: 0,
            },
            bottomPanel: "diagnostics",
            toast: {
              kind: "error",
              message: response.diagnostics[0]?.message ?? "复合资源校验失败",
            },
          });
          return null;
        }
        await saveCompositeResource(response.resource);
        const resources = [
          ...state.resources.filter(
            (item) =>
              !(
                item.resource_id === response.resource!.resource_id &&
                item.revision === response.resource!.revision
              ),
          ),
          response.resource,
        ];
        set({
          resources,
          busy: false,
          toast: {
            kind: "success",
            message: `${name} v1 已加入复合模块库`,
          },
        });
        return response.resource;
      } catch (error) {
        set({
          busy: false,
          toast: {
            kind: "error",
            message:
              error instanceof Error ? error.message : "复合资源发布失败",
          },
        });
        return null;
      }
    },

    addComposite: (resourceId, revision, position) => {
      if (get().activeView.readOnly) {
        get().showToast("info", "当前视图为只读");
        return;
      }
      const state = get();
      const resource =
        state.resources.find(
          (item) =>
            item.resource_id === resourceId && item.revision === revision,
        ) ??
        state.ir.resources?.find(
          (item) =>
            item.resource_id === resourceId && item.revision === revision,
        );
      if (!resource) {
        get().showToast("error", "找不到复合资源版本");
        return;
      }
      const id = uid("composite");
      const contract: StateContract = {
        inputs: structuredClone(resource.inputs),
        outputs: structuredClone(resource.outputs),
      };
      const bundle = collectResourceBundle(resource);
      commit((draft) => {
        draft.graph.nodes.push({
          id,
          op: "composite.instance",
          params: { name: resource.name },
          teaching_note: resource.description,
          composite_ref: {
            resource_id: resource.resource_id,
            revision: resource.revision,
          },
          state_contract: contract,
          param_overrides: {},
        });
        const existing = new Map(
          (draft.resources ?? []).map((item) => [resourceKey(item), item]),
        );
        for (const item of bundle) existing.set(resourceKey(item), item);
        draft.resources = [...existing.values()];
        draft.ui.positions[id] = position;
      });
      set({ selectedNodeId: id });
    },

    enterNode: (nodeId) => {
      const state = get();
      const node = state.ir.graph.nodes.find((item) => item.id === nodeId);
      if (!node) return;
      const frame: ViewFrame = {
        ir: clone(state.ir),
        selectedNodeId: state.selectedNodeId,
        undoStack: clone(state.undoStack),
        redoStack: clone(state.redoStack),
        parentView: state.activeView,
      };
      if (node.op === "composite.instance" && node.composite_ref) {
        const resource =
          state.resources.find(
            (item) =>
              item.resource_id === node.composite_ref!.resource_id &&
              item.revision === node.composite_ref!.revision,
          ) ??
          state.ir.resources?.find(
            (item) =>
              item.resource_id === node.composite_ref!.resource_id &&
              item.revision === node.composite_ref!.revision,
          );
        if (!resource) {
          state.showToast("error", "复合资源版本缺失");
          return;
        }
        set({
          ir: resourceDocument(resource, state.ir.target_framework, false),
          viewStack: [...state.viewStack, frame],
          activeView: {
            kind: "composite",
            label: `${resource.name} v${resource.revision}`,
            resourceId: resource.resource_id,
            revision: resource.revision,
            readOnly: true,
          },
          selectedNodeId: null,
          undoStack: [],
          redoStack: [],
          code: null,
          trace: null,
        });
        void get().validateNow();
        return;
      }
      if (node.op.startsWith("control.") && node.region_refs) {
        const preferred =
          node.region_refs.predicate ?? node.region_refs.body;
        if (preferred) {
          get().switchControlRegion(
            Object.entries(node.region_refs).find(
              ([, regionId]) => regionId === preferred,
            )?.[0] ?? "body",
          );
        }
      }
    },

    switchControlRegion: (regionName) => {
      const state = get();
      const isSwitching =
        state.activeView.kind === "control" &&
        Boolean(state.activeView.controlNodeId);
      const frame = isSwitching ? state.viewStack.at(-1) : null;
      const rootIr = clone(frame?.ir ?? state.ir);
      const controlNodeId =
        (isSwitching
          ? state.activeView.controlNodeId
          : state.selectedNodeId) ?? null;
      const node = rootIr.graph.nodes.find(
        (item) => item.id === controlNodeId,
      );
      if (!node?.region_refs?.[regionName]) {
        state.showToast("info", "请先选中一个控制容器");
        return;
      }
      const regionId = node.region_refs[regionName];
      const region = rootIr.regions?.[regionId];
      if (!region) {
        state.showToast("error", `区域 ${regionId} 不存在`);
        return;
      }
      if (isSwitching && state.activeView.regionId && frame) {
        const currentRegion = rootIr.regions?.[state.activeView.regionId];
        if (currentRegion) {
          currentRegion.graph = clone(state.ir.graph);
          currentRegion.ui = clone(state.ir.ui);
          frame.ir = rootIr;
        }
      }
      const childIr: IRDocument = {
        ...clone(rootIr),
        graph_meta: {
          ...rootIr.graph_meta,
          name: `${node.op} · ${region.kind}`,
          is_composite: true,
        },
        graph: clone(region.graph),
        ui: clone(region.ui),
      };
      set({
        ir: childIr,
        viewStack: isSwitching
          ? state.viewStack
          : [
              ...state.viewStack,
              {
                ir: rootIr,
                selectedNodeId: state.selectedNodeId,
                undoStack: clone(state.undoStack),
                redoStack: clone(state.redoStack),
                parentView: state.activeView,
                controlNodeId: node.id,
                regionId,
              },
            ],
        activeView: {
          kind: "control",
          label: `${node.op} · ${regionName}`,
          controlNodeId: node.id,
          regionId,
          readOnly: false,
        },
        selectedNodeId: null,
        undoStack: [],
        redoStack: [],
        code: null,
        trace: null,
      });
      void get().validateNow();
    },

    createCompositeDraft: () => {
      const state = get();
      if (
        state.activeView.kind !== "composite" ||
        !state.activeView.resourceId ||
        !state.activeView.revision
      ) {
        return;
      }
      const resource = state.resources.find(
        (item) =>
          item.resource_id === state.activeView.resourceId &&
          item.revision === state.activeView.revision,
      );
      if (!resource) return;
      const draft = {
        ...clone(resource),
        revision: resource.revision + 1,
      };
      set({
        ir: resourceDocument(draft, state.ir.target_framework, true),
        activeView: {
          ...state.activeView,
          label: `${draft.name} v${draft.revision}（草稿）`,
          revision: draft.revision,
          readOnly: false,
        },
        undoStack: [],
        redoStack: [],
        dirty: true,
        toast: {
          kind: "info",
          message: "已创建新版本草稿，保存后才会进入资源库",
        },
      });
    },

    saveCompositeDraft: async () => {
      const state = get();
      if (
        state.activeView.kind !== "composite" ||
        !state.activeView.resourceId ||
        !state.activeView.revision
      ) {
        return;
      }
      set({ busy: true });
      try {
        const response = await api.publishComposite(
          state.ir,
          state.ir.graph_meta.name,
          state.activeView.revision,
          state.activeView.resourceId,
          state.ir.graph_meta.note,
        );
        if (!response.valid || !response.resource) {
          set({
            busy: false,
            bottomPanel: "diagnostics",
            analysis: {
              valid: false,
              normalized_ir: null,
              nodes: [],
              diagnostics: response.diagnostics,
              chain_count: 0,
            },
          });
          return;
        }
        await saveCompositeResource(response.resource);
        set({
          resources: [
            ...state.resources.filter(
              (item) =>
                !(
                  item.resource_id === response.resource!.resource_id &&
                  item.revision === response.resource!.revision
                ),
            ),
            response.resource,
          ],
          activeView: {
            ...state.activeView,
            readOnly: true,
            label: `${response.resource.name} v${response.resource.revision}`,
          },
          busy: false,
          dirty: false,
          toast: { kind: "success", message: "复合资源新版本已保存" },
        });
      } catch (error) {
        set({
          busy: false,
          toast: {
            kind: "error",
            message:
              error instanceof Error ? error.message : "复合资源保存失败",
          },
        });
      }
    },

    exitSubgraph: () => {
      const state = get();
      const frame = state.viewStack.at(-1);
      if (!frame) return;
      if (
        state.activeView.kind === "composite" &&
        !state.activeView.readOnly &&
        state.dirty &&
        !window.confirm("新版本草稿尚未保存，确定返回父图吗？")
      ) {
        return;
      }
      let parentIr = clone(frame.ir);
      const wasControl = state.activeView.kind === "control";
      if (
        wasControl &&
        state.activeView.regionId
      ) {
        const region = parentIr.regions?.[state.activeView.regionId];
        if (region) {
          region.graph = clone(state.ir.graph);
          region.ui = clone(state.ir.ui);
        }
      }
      set({
        ir: parentIr,
        viewStack: state.viewStack.slice(0, -1),
        activeView: frame.parentView,
        selectedNodeId: frame.selectedNodeId,
        undoStack: frame.undoStack,
        redoStack: frame.redoStack,
        code: null,
        trace: null,
        dirty: wasControl ? true : state.dirty,
      });
      void get().validateNow();
    },

    changeCompositeVersion: (nodeId, revision) => {
      const state = get();
      const node = state.ir.graph.nodes.find((item) => item.id === nodeId);
      if (!node?.composite_ref) return;
      const resource =
        state.resources.find(
          (item) =>
            item.resource_id === node.composite_ref!.resource_id &&
            item.revision === revision,
        ) ??
        state.ir.resources?.find(
          (item) =>
            item.resource_id === node.composite_ref!.resource_id &&
            item.revision === revision,
        );
      if (!resource) return;
      const validPaths = new Set(Object.keys(resource.parameter_defaults));
      commit((draft) => {
        const target = draft.graph.nodes.find((item) => item.id === nodeId);
        if (!target) return;
        target.composite_ref = {
          resource_id: resource.resource_id,
          revision: resource.revision,
        };
        target.state_contract = {
          inputs: structuredClone(resource.inputs),
          outputs: structuredClone(resource.outputs),
        };
        target.param_overrides = Object.fromEntries(
          Object.entries(target.param_overrides ?? {}).filter(([path]) =>
            validPaths.has(path),
          ),
        );
        const existing = new Map(
          (draft.resources ?? []).map((item) => [resourceKey(item), item]),
        );
        for (const item of collectResourceBundle(resource)) {
          existing.set(resourceKey(item), item);
        }
        draft.resources = [...existing.values()];
      });
      void get().validateNow();
    },

    setCompositeParamOverride: (nodeId, path, value) => {
      if (get().activeView.readOnly) return;
      commit((draft) => {
        const node = draft.graph.nodes.find((item) => item.id === nodeId);
        if (!node?.composite_ref) return;
        node.param_overrides = {
          ...(node.param_overrides ?? {}),
          [path]: value,
        };
      });
      void get().validateNow();
    },

    importCompositeResource: async (resource) => {
      if (
        resource?.schema_version !== "1.0" ||
        !resource.resource_id ||
        !resource.revision ||
        !resource.graph
      ) {
        get().showToast("error", "不是有效的 NetBrick 复合模块文件");
        return;
      }
      await saveCompositeResource(resource);
      const state = get();
      set({
        resources: [
          ...state.resources.filter(
            (item) =>
              !(
                item.resource_id === resource.resource_id &&
                item.revision === resource.revision
              ),
          ),
          resource,
        ],
        toast: {
          kind: "success",
          message: `${resource.name} v${resource.revision} 已导入`,
        },
      });
    },

    addControlStatePort: (nodeId, io) => {
      commit((draft) => {
        const node = draft.graph.nodes.find((item) => item.id === nodeId);
        if (!node?.state_contract || !node.op.startsWith("control.")) return;
        const ports =
          io === "in"
            ? node.state_contract.inputs
            : node.state_contract.outputs;
        const port: PortContract = {
          name: `${io === "in" ? "input" : "output"}_${ports.length + 1}`,
          data_type: "Tensor",
          shape: [1, 10],
          dtype: "float32",
          required: true,
        };
        ports.push(port);
        for (const [regionName, regionId] of Object.entries(
          node.region_refs ?? {},
        )) {
          if (regionName === "predicate" && io === "out") continue;
          const region = draft.regions?.[regionId];
          if (!region) continue;
          const boundaryList = io === "in" ? region.inputs : region.outputs;
          boundaryList.push(structuredClone(port));
          const nodeIdBoundary = uid(io === "in" ? "input" : "output");
          if (io === "in") {
            region.graph.nodes.push({
              id: nodeIdBoundary,
              op: "Input",
              params: {
                name: port.name,
                sample_shape: port.shape,
                dtype: port.dtype,
                data_type: port.data_type,
              },
              teaching_note: "",
            });
          } else {
            region.graph.nodes.push({
              id: nodeIdBoundary,
              op: "Output",
              params: {
                name: port.name,
                data_type: port.data_type,
              },
              teaching_note: "",
            });
          }
          region.ui.positions[nodeIdBoundary] = {
            x: io === "in" ? 40 : 900,
            y: 160 + (ports.length - 1) * 130,
          };
        }
      });
      void get().validateNow();
    },

    updateControlStatePort: (nodeId, io, index, field, value) => {
      commit((draft) => {
        const node = draft.graph.nodes.find((item) => item.id === nodeId);
        if (!node?.state_contract) return;
        const ports =
          io === "in"
            ? node.state_contract.inputs
            : node.state_contract.outputs;
        const port = ports[index];
        if (!port) return;
        const previousName = port.name;
        if (field === "shape") {
          port.shape = Array.isArray(value)
            ? value.map((item) => Number(item))
            : [1, 10];
        } else if (field === "data_type") {
          port.data_type = value as PortContract["data_type"];
        } else {
          (port as unknown as Record<string, unknown>)[field] = value;
        }
        for (const [regionName, regionId] of Object.entries(
          node.region_refs ?? {},
        )) {
          if (regionName === "predicate" && io === "out") continue;
          const region = draft.regions?.[regionId];
          if (!region) continue;
          const boundary = io === "in" ? region.inputs : region.outputs;
          if (boundary[index]) {
            (boundary[index] as unknown as Record<string, unknown>)[field] =
              field === "shape" ? structuredClone(port.shape) : port[field];
          }
          const matchingNode = region.graph.nodes.find(
            (item) =>
              item.op === (io === "in" ? "Input" : "Output") &&
              item.params.name === previousName,
          );
          if (matchingNode) {
            if (matchingNode.op === "Output") {
              if (field === "name" || field === "data_type") {
                matchingNode.params[field] = value;
              }
            } else if (field === "shape") {
              matchingNode.params.sample_shape = structuredClone(port.shape);
            } else if (field === "data_type") {
              matchingNode.params.data_type = port.data_type;
            } else {
              matchingNode.params[field] = value;
            }
          }
        }
      });
      void get().validateNow();
    },

    addLoopIndexPort: (nodeId) => {
      commit((draft) => {
        const node = draft.graph.nodes.find((item) => item.id === nodeId);
        if (
          !node ||
          !["control.For", "control.While"].includes(node.op)
        ) {
          return;
        }
        for (const regionName of ["predicate", "body"]) {
          const regionId = node.region_refs?.[regionName];
          const region = regionId ? draft.regions?.[regionId] : null;
          if (!region || region.inputs.some((port) => port.name === "index")) {
            continue;
          }
          region.inputs.push({
            name: "index",
            data_type: "ScalarInt",
            shape: [],
            dtype: "int64",
            required: false,
          });
          const boundaryId = uid("index");
          region.graph.nodes.push({
            id: boundaryId,
            op: "Input",
            params: {
              name: "index",
              sample_shape: [],
              dtype: "int64",
              data_type: "ScalarInt",
            },
            teaching_note: "当前循环索引",
          });
          region.ui.positions[boundaryId] = {
            x: 40,
            y: 430,
          };
        }
      });
      void get().validateNow();
    },

    deleteCompositeResource: async (resourceId) => {
      const state = get();
      const removed = state.resources.filter(
        (resource) => resource.resource_id === resourceId,
      );
      if (removed.length === 0) return;
      try {
        await deleteCompositeResources(resourceId);
      } catch {
        get().showToast("error", "复合模块删除失败");
        return;
      }
      set({
        resources: state.resources.filter(
          (resource) => resource.resource_id !== resourceId,
        ),
        toast: {
          kind: "success",
          message: `${removed[0].name} 已从复合模块库删除`,
        },
      });
    },
  };
});

export function selectedNode(): GraphNode | undefined {
  const state = useGraphStore.getState();
  return state.ir.graph.nodes.find(
    (node) => node.id === state.selectedNodeId,
  );
}
