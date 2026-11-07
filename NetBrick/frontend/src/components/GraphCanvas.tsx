import {
  Background,
  BackgroundVariant,
  ConnectionLineType,
  MarkerType,
  ReactFlow,
  ReactFlowProvider,
  applyEdgeChanges,
  applyNodeChanges,
  useReactFlow,
  type Connection,
  type EdgeChange,
  type NodeChange,
  type OnSelectionChangeParams,
} from "@xyflow/react";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type MouseEvent as ReactMouseEvent,
} from "react";
import { inputPortIds, outputPortIds } from "../flowPorts";
import { useGraphStore } from "../store";
import type { GraphEdge, GraphNode, NodeAnalysis, Position } from "../types";
import {
  OperationNode,
  type FlowNodeData,
  type OperationFlowNode,
} from "./FlowNode";
import { Icon } from "./Icons";
import { ShapeEdge, type DataFlowEdge } from "./ShapeEdge";

const nodeTypes = { operation: OperationNode };
const edgeTypes = { shape: ShapeEdge };
const NODE_WIDTH = 222;
const NODE_HEIGHT = 102;

interface ContextMenuState {
  x: number;
  y: number;
  flowX: number;
  flowY: number;
  kind: "pane" | "node";
  nodeId?: string;
}

interface GraphClipboard {
  nodes: GraphNode[];
  edges: GraphEdge[];
  positions: Record<string, Position>;
}

interface ContextPointerEvent {
  preventDefault: () => void;
  stopPropagation: () => void;
  clientX: number;
  clientY: number;
}

function clone<T>(value: T): T {
  return structuredClone(value);
}

function createId(prefix: string): string {
  const suffix =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID().slice(0, 8)
      : Math.random().toString(36).slice(2, 10);
  return `${prefix}_${suffix}`;
}

function shapeForEdge(
  sourceId: string,
  sourcePort: string,
  analysisMap: Map<string, NodeAnalysis>,
): string {
  const source = analysisMap.get(sourceId);
  const port = source?.ports.find(
    (item) => item.io === "out" && item.name === sourcePort,
  );
  return port?.shape?.length ? `[${port.shape.join(", ")}]` : "shape 待检查";
}

function FlowCanvas() {
  const ir = useGraphStore((state) => state.ir);
  const catalog = useGraphStore((state) => state.catalog);
  const analysis = useGraphStore((state) => state.analysis);
  const selectedNodeId = useGraphStore((state) => state.selectedNodeId);
  const readOnly = useGraphStore((state) => state.activeView.readOnly);
  const activeView = useGraphStore((state) => state.activeView);
  const viewStack = useGraphStore((state) => state.viewStack);
  const enterNode = useGraphStore((state) => state.enterNode);
  const exitSubgraph = useGraphStore((state) => state.exitSubgraph);
  const switchControlRegion = useGraphStore(
    (state) => state.switchControlRegion,
  );
  const createCompositeDraft = useGraphStore(
    (state) => state.createCompositeDraft,
  );
  const saveCompositeDraft = useGraphStore(
    (state) => state.saveCompositeDraft,
  );
  const addNode = useGraphStore((state) => state.addNode);
  const addMojo = useGraphStore((state) => state.addMojo);
  const addSubgraph = useGraphStore((state) => state.addSubgraph);
  const moveNode = useGraphStore((state) => state.moveNode);
  const connect = useGraphStore((state) => state.connect);
  const removeNode = useGraphStore((state) => state.removeNode);
  const removeEdge = useGraphStore((state) => state.removeEdge);
  const clearGraph = useGraphStore((state) => state.clearGraph);
  const createMojo = useGraphStore((state) => state.createMojo);
  const setSelectedNode = useGraphStore((state) => state.setSelectedNode);
  const showToast = useGraphStore((state) => state.showToast);

  const shellRef = useRef<HTMLDivElement>(null);
  const clipboardRef = useRef<GraphClipboard | null>(null);
  const contextIdsRef = useRef<string[]>([]);
  const renderedIdsRef = useRef("");
  const [flowNodes, setFlowNodes] = useState<OperationFlowNode[]>([]);
  const [flowEdges, setFlowEdges] = useState<DataFlowEdge[]>([]);
  const [zoom, setZoom] = useState(1);
  const [contextMenu, setContextMenu] = useState<ContextMenuState | null>(null);
  const [connectionPin, setConnectionPin] = useState<{
    nodeId: string;
    port: string;
  } | null>(null);
  const {
    screenToFlowPosition,
    fitView,
    zoomIn,
    zoomOut,
    getNodes,
  } = useReactFlow<OperationFlowNode, DataFlowEdge>();

  const analysisMap = useMemo(
    () => new Map((analysis?.nodes ?? []).map((item) => [item.node_id, item])),
    [analysis],
  );

  const canConnect = useCallback(
    (
      sourceId: string,
      sourcePort: string,
      targetId: string,
      targetPort: string,
    ) => {
      if (sourceId === targetId) return false;
      const source = getNodes().find((node) => node.id === sourceId);
      const target = getNodes().find((node) => node.id === targetId);
      if (!source || !target) return false;
      if (source.data.graphNode.op === "Output") return false;
      if (target.data.graphNode.op === "Input") return false;
      if (
        !outputPortIds(source.data.graphNode, source.data.block).includes(
          sourcePort,
        ) ||
        !inputPortIds(target.data.graphNode, target.data.block).includes(
          targetPort,
        )
      ) {
        return false;
      }
      if (
        target.data.block?.input_mode !== "merge" &&
        flowEdges.some(
          (edge) =>
            edge.target === targetId && edge.targetHandle === targetPort,
        )
      ) {
        return false;
      }
      return !flowEdges.some(
        (edge) =>
          edge.source === sourceId &&
          edge.sourceHandle === sourcePort &&
          edge.target === targetId &&
          edge.targetHandle === targetPort,
      );
    },
    [flowEdges, getNodes],
  );

  const pinConnectionSource = useCallback(
    (nodeId: string, port: string) => {
      if (readOnly) {
        showToast("info", "当前复合资源版本为只读");
        return;
      }
      setConnectionPin((current) => {
        const same =
          current?.nodeId === nodeId && current?.port === port;
        if (same) {
          showToast("info", "已结束分支连接");
          return null;
        }
        showToast(
          "info",
          `已固定 ${nodeId}.${port}，现在可连续点击多个输入端口`,
        );
        return { nodeId, port };
      });
    },
    [readOnly, showToast],
  );

  const connectFromPinnedSource = useCallback(
    (targetId: string, targetPort: string) => {
      if (!connectionPin) return;
      if (
        !canConnect(
          connectionPin.nodeId,
          connectionPin.port,
          targetId,
          targetPort,
        )
      ) {
        showToast("info", "该输入端口已有连线，或不能接收当前分支");
        return;
      }
      connect(
        connectionPin.nodeId,
        targetId,
        targetPort,
        connectionPin.port,
      );
    },
    [canConnect, connect, connectionPin, showToast],
  );

  const handleHandleClick = useCallback(
    (event: ReactMouseEvent<HTMLDivElement>) => {
      const handle = (event.target as Element).closest<HTMLElement>(
        ".react-flow__handle",
      );
      if (!handle || readOnly) return;
      const nodeId = handle.dataset.nodeid;
      const port = handle.dataset.handleid;
      if (!nodeId || !port) return;
      event.preventDefault();
      event.stopPropagation();
      if (handle.classList.contains("flow-handle--output")) {
        pinConnectionSource(nodeId, port);
      } else if (
        handle.classList.contains("flow-handle--input") &&
        connectionPin
      ) {
        connectFromPinnedSource(nodeId, port);
      }
    },
    [
      connectFromPinnedSource,
      connectionPin,
      pinConnectionSource,
      readOnly,
    ],
  );

  useEffect(() => {
    const blockMap = new Map(catalog.map((block) => [block.op, block]));
    const diagnostics = analysis?.diagnostics ?? [];
    const invalidCodes = new Set([
      "SHAPE_MISMATCH",
      "INVALID_PORT",
      "PARAM_TYPE",
      "PARAM_RANGE",
      "PARAM_OPTION",
      "FRAMEWORK_UNSUPPORTED",
    ]);
    const invalidNodeIds = new Set(
      diagnostics
        .filter((item) => invalidCodes.has(item.code) && item.node_id)
        .map((item) => item.node_id!),
    );
    const nextNodes: OperationFlowNode[] = ir.graph.nodes.map((node) => {
      const point = ir.ui.positions[node.id] ?? { x: 80, y: 120 };
      const data: FlowNodeData = {
        graphNode: node,
        block: blockMap.get(node.op),
        analysis: analysisMap.get(node.id),
        invalid: invalidNodeIds.has(node.id),
        framework: ir.target_framework,
        connectionPin,
      };
      return {
        id: node.id,
        type: "operation",
        position: point,
        data,
        selected: node.id === selectedNodeId,
        width: NODE_WIDTH,
        height: NODE_HEIGHT,
      };
    });
    const nextEdges: DataFlowEdge[] = ir.graph.edges.map((edge) => {
      const targetInvalid = invalidNodeIds.has(edge.target.node_id);
      const sourceInvalid = invalidNodeIds.has(edge.source.node_id);
      return {
        id: edge.id,
        source: edge.source.node_id,
        sourceHandle: edge.source.port,
        target: edge.target.node_id,
        targetHandle: edge.target.port,
        type: "shape",
        data: {
          shape: shapeForEdge(
            edge.source.node_id,
            edge.source.port,
            analysisMap,
          ),
          invalid: targetInvalid || sourceInvalid,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 15,
          height: 15,
          color: targetInvalid || sourceInvalid ? "#f53f3f" : "#c9cdd4",
        },
      };
    });
    setFlowNodes(nextNodes);
    setFlowEdges(nextEdges);
    const ids = ir.graph.nodes.map((node) => node.id).join("|");
    if (ids !== renderedIdsRef.current && ids) {
      renderedIdsRef.current = ids;
      window.setTimeout(() => {
        void fitView({ padding: 0.18, minZoom: 0.45, maxZoom: 1.05 });
      }, 60);
    }
  }, [
    analysis,
    analysisMap,
    catalog,
    connectionPin,
    fitView,
    ir,
  ]);

  useEffect(() => {
    setConnectionPin(null);
  }, [activeView.kind, activeView.controlNodeId, activeView.regionId]);

  const onNodesChange = useCallback(
    (changes: NodeChange<OperationFlowNode>[]) => {
      setFlowNodes((current) => applyNodeChanges(changes, current));
    },
    [],
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange<DataFlowEdge>[]) => {
      setFlowEdges((current) => applyEdgeChanges(changes, current));
    },
    [],
  );

  const onSelectionChange = useCallback(
    ({ nodes }: OnSelectionChangeParams<OperationFlowNode, DataFlowEdge>) => {
      setSelectedNode(nodes.at(-1)?.id ?? null);
    },
    [setSelectedNode],
  );

  const selectedIds = (fallbackId?: string): string[] => {
    const ids = getNodes()
      .filter((node) => node.selected)
      .map((node) => node.id);
    if (ids.length) return ids;
    return fallbackId ? [fallbackId] : [];
  };

  const openContextMenu = (
    event: ContextPointerEvent,
    kind: ContextMenuState["kind"],
    nodeId?: string,
  ) => {
    if (readOnly) {
      showToast("info", "当前复合资源版本为只读");
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    const rect = shellRef.current?.getBoundingClientRect();
    if (!rect) return;
    const point = screenToFlowPosition({
      x: event.clientX,
      y: event.clientY,
    });
    contextIdsRef.current = selectedIds(nodeId);
    setContextMenu({
      x: event.clientX - rect.left,
      y: event.clientY - rect.top,
      flowX: point.x,
      flowY: point.y,
      kind,
      nodeId,
    });
    if (nodeId && contextIdsRef.current.length === 1) {
      setSelectedNode(nodeId);
    }
  };

  const copySelection = () => {
    const ids = new Set(contextIdsRef.current);
    const nodes = ir.graph.nodes.filter((node) => ids.has(node.id));
    if (!nodes.length) return;
    const points = nodes.map(
      (node) => ir.ui.positions[node.id] ?? { x: 0, y: 0 },
    );
    const minX = Math.min(...points.map((point) => point.x));
    const minY = Math.min(...points.map((point) => point.y));
    clipboardRef.current = {
      nodes: clone(nodes),
      edges: clone(
        ir.graph.edges.filter(
          (edge) =>
            ids.has(edge.source.node_id) && ids.has(edge.target.node_id),
        ),
      ),
      positions: Object.fromEntries(
        nodes.map((node) => {
          const point = ir.ui.positions[node.id] ?? { x: 0, y: 0 };
          return [node.id, { x: point.x - minX, y: point.y - minY }];
        }),
      ),
    };
    setContextMenu(null);
    showToast("info", `已复制 ${nodes.length} 个节点`);
  };

  const pasteSelection = (position?: Position) => {
    const clipboard = clipboardRef.current;
    if (!clipboard) return;
    const origin = position ?? {
      x: contextMenu?.flowX ?? 100,
      y: contextMenu?.flowY ?? 100,
    };
    const idMap = new Map<string, string>();
    for (const node of clipboard.nodes) {
      idMap.set(node.id, createId("copy"));
    }
    const nodes = clipboard.nodes.map((node) => ({
      ...clone(node),
      id: idMap.get(node.id)!,
    }));
    const edges = clipboard.edges.map((edge) => ({
      ...clone(edge),
      id: createId("edge"),
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
      Object.entries(clipboard.positions).map(([id, point]) => [
        idMap.get(id)!,
        { x: origin.x + point.x, y: origin.y + point.y },
      ]),
    );
    addSubgraph(nodes, edges, positions);
    setContextMenu(null);
  };

  useEffect(() => {
    const handleClipboard = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.tagName === "SELECT" ||
        target?.isContentEditable
      ) {
        return;
      }
      if (event.key === "Escape" && connectionPin) {
        event.preventDefault();
        setConnectionPin(null);
        showToast("info", "已结束分支连接");
        return;
      }
      if (!event.ctrlKey && !event.metaKey) return;
      if (event.key.toLowerCase() === "c") {
        const ids = selectedIds();
        if (!ids.length) return;
        event.preventDefault();
        contextIdsRef.current = ids;
        copySelection();
      }
      if (event.key.toLowerCase() === "v") {
        if (!clipboardRef.current) return;
        event.preventDefault();
        const rect = shellRef.current?.getBoundingClientRect();
        const point = rect
          ? screenToFlowPosition({
              x: rect.left + rect.width / 2,
              y: rect.top + rect.height / 2,
            })
          : { x: 140, y: 140 };
        pasteSelection({ x: point.x - 40, y: point.y - 40 });
      }
    };
    window.addEventListener("keydown", handleClipboard);
    return () => window.removeEventListener("keydown", handleClipboard);
  }, [
    connectionPin,
    copySelection,
    pasteSelection,
    screenToFlowPosition,
    showToast,
  ]);

  const packSelection = () => {
    if (contextIdsRef.current.length < 2) {
      showToast("info", "请按住 Shift 选择至少两个节点后再打包");
      return;
    }
    createMojo(contextIdsRef.current);
    setContextMenu(null);
  };

  const deleteContextNodes = () => {
    for (const id of contextIdsRef.current) removeNode(id);
    setContextMenu(null);
  };

  const isValidConnection = (connection: Connection | DataFlowEdge) => {
    if (!connection.source || !connection.target) return false;
    if (!connection.sourceHandle || !connection.targetHandle) return false;
    return canConnect(
      connection.source,
      connection.sourceHandle,
      connection.target,
      connection.targetHandle,
    );
  };

  const selectedCount = flowNodes.filter((node) => node.selected).length;

  return (
    <div
      ref={shellRef}
      className={`canvas-shell ${connectionPin ? "is-branch-connecting" : ""}`}
      onClickCapture={handleHandleClick}
      onDragOver={(event) => {
        if (
          event.dataTransfer.types.includes("application/netbrick-block") ||
          event.dataTransfer.types.includes("application/netbrick-mojo")
        ) {
          event.preventDefault();
          event.dataTransfer.dropEffect = "copy";
        }
      }}
      onDrop={(event) => {
        event.preventDefault();
        if (readOnly) {
          showToast("info", "当前复合资源版本为只读");
          return;
        }
        const point = screenToFlowPosition({
          x: event.clientX,
          y: event.clientY,
        });
        const op = event.dataTransfer.getData("application/netbrick-block");
        if (op) {
          addNode(op, {
            x: point.x - NODE_WIDTH / 2,
            y: point.y - NODE_HEIGHT / 2,
          });
          return;
        }
        const mojoId = event.dataTransfer.getData("application/netbrick-mojo");
        if (mojoId) {
          addMojo(mojoId, {
            x: point.x - NODE_WIDTH / 2,
            y: point.y - NODE_HEIGHT / 2,
          });
          return;
        }
        const composite = event.dataTransfer.getData(
          "application/netbrick-composite",
        );
        if (composite) {
          try {
            const ref = JSON.parse(composite) as {
              resourceId: string;
              revision: number;
            };
            useGraphStore
              .getState()
              .addComposite(ref.resourceId, ref.revision, {
                x: point.x - NODE_WIDTH / 2,
                y: point.y - NODE_HEIGHT / 2,
              });
          } catch {
            showToast("error", "复合模块数据无效");
          }
        }
      }}
    >
      {viewStack.length > 0 && (
        <div className="subgraph-breadcrumb">
          <button type="button" onClick={exitSubgraph}>
            <Icon name="chevron" size={13} className="chevron--left" />
            返回父图
          </button>
          <span>{activeView.label}</span>
          {activeView.readOnly && <em>只读</em>}
          {activeView.kind === "composite" && activeView.readOnly && (
            <button
              type="button"
              className="subgraph-edit-version"
              onClick={createCompositeDraft}
            >
              编辑新版本
            </button>
          )}
          {activeView.kind === "composite" && !activeView.readOnly && (
            <button
              type="button"
              className="subgraph-edit-version"
              onClick={() => void saveCompositeDraft()}
            >
              保存新版本
            </button>
          )}
          {activeView.kind === "control" &&
            (() => {
              const frame = viewStack.at(-1);
              const node = frame?.ir.graph.nodes.find(
                (item) => item.id === activeView.controlNodeId,
              );
              return node?.region_refs
                ? Object.keys(node.region_refs).map((regionName) => (
                    <button
                      type="button"
                      key={regionName}
                      className={
                        activeView.regionId ===
                        node.region_refs?.[regionName]
                          ? "active"
                          : ""
                      }
                      onClick={() => switchControlRegion(regionName)}
                    >
                      {regionName === "predicate"
                        ? "谓词"
                        : regionName === "then"
                          ? "Then"
                          : regionName === "else"
                            ? "Else"
                            : "循环体"}
                    </button>
                  ))
                : null;
            })()}
        </div>
      )}
      <div className="canvas-status-row">
        <span
          className={`canvas-validation canvas-validation--${analysis?.valid ? "valid" : "invalid"}`}
        >
          <span />
          {analysis?.valid ? "结构可用" : "结构存在冲突"}
        </span>
        {connectionPin ? (
          <span className="canvas-branch-pin">
            分支连接：{connectionPin.nodeId}.{connectionPin.port}
            <i>点击多个输入端口完成连接</i>
            <button type="button" onClick={() => setConnectionPin(null)}>
              结束
            </button>
          </span>
        ) : (
          <span className="canvas-hint">
            双击连线可删除 · Shift 多选 · 右键拖动画布
          </span>
        )}
      </div>
      <ReactFlow<OperationFlowNode, DataFlowEdge>
        nodes={flowNodes}
        edges={flowEdges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onSelectionChange={onSelectionChange}
        onNodeClick={(_, node) => setSelectedNode(node.id)}
        onNodeDoubleClick={(_, node) => {
          setSelectedNode(node.id);
          if (
            node.data.graphNode.op === "composite.instance" ||
            node.data.graphNode.op.startsWith("control.")
          ) {
            enterNode(node.id);
          }
        }}
        onNodeDragStop={(_, node) => moveNode(node.id, node.position)}
        onNodesDelete={(nodes) => {
          if (!readOnly) nodes.forEach((node) => removeNode(node.id));
        }}
        onEdgesDelete={(edges) => {
          if (!readOnly) edges.forEach((edge) => removeEdge(edge.id));
        }}
        onEdgeDoubleClick={(_, edge) => {
          if (!readOnly) removeEdge(edge.id);
        }}
        onPaneClick={() => {
          setContextMenu(null);
          setSelectedNode(null);
        }}
        onPaneContextMenu={(event) => openContextMenu(event, "pane")}
        onNodeContextMenu={(event, node) => {
          if (!node.selected) {
            setFlowNodes((current) =>
              current.map((item) => ({
                ...item,
                selected: item.id === node.id,
              })),
            );
          }
          openContextMenu(event, "node", node.id);
        }}
        onConnect={(connection) => {
          if (
            !readOnly &&
            connection.source &&
            connection.target
          ) {
            connect(
              connection.source,
              connection.target,
              connection.targetHandle ?? "x",
              connection.sourceHandle ?? "out",
            );
          }
        }}
        isValidConnection={isValidConnection}
        connectionLineType={ConnectionLineType.Bezier}
        connectionLineStyle={{
          stroke: "#3370ff",
          strokeWidth: 2,
          strokeDasharray: "5 4",
        }}
        multiSelectionKeyCode={["Shift", "Meta", "Control"]}
        deleteKeyCode={readOnly ? null : ["Backspace", "Delete"]}
        nodesDraggable={!readOnly}
        nodesConnectable={!readOnly}
        minZoom={0.38}
        maxZoom={1.8}
        snapToGrid
        snapGrid={[12, 12]}
        panOnDrag={[1, 2]}
        panOnScroll
        selectionOnDrag
        fitView
        fitViewOptions={{ padding: 0.18, minZoom: 0.45, maxZoom: 1.05 }}
        onMove={(_, viewport) => setZoom(viewport.zoom)}
        proOptions={{ hideAttribution: true }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={19}
          size={1.2}
          color="#e5e6eb"
        />
      </ReactFlow>

      <div className="canvas-controls">
        <button type="button" onClick={() => void zoomOut()} title="缩小">
          −
        </button>
        <span>{Math.round(zoom * 100)}%</span>
        <button type="button" onClick={() => void zoomIn()} title="放大">
          +
        </button>
        <button
          type="button"
          onClick={() =>
            void fitView({ padding: 0.18, minZoom: 0.45, maxZoom: 1.05 })
          }
          title="适应画布"
        >
          <Icon name="layout" size={15} />
        </button>
      </div>

      {selectedCount > 1 && (
        <div className="selection-count">已选择 {selectedCount} 个节点</div>
      )}

      {contextMenu && (
        <div
          className="canvas-context-menu"
          style={{ left: contextMenu.x, top: contextMenu.y }}
          onMouseDown={(event) => event.stopPropagation()}
        >
          {contextMenu.kind === "node" ? (
            <>
              <button type="button" onClick={deleteContextNodes}>
                <Icon name="trash" size={14} />
                删除节点
                <kbd>Del</kbd>
              </button>
              <button type="button" onClick={copySelection}>
                <Icon name="copy" size={14} />
                复制
                <kbd>Ctrl C</kbd>
              </button>
              <button
                type="button"
                onClick={() => pasteSelection()}
                disabled={!clipboardRef.current}
              >
                <Icon name="plus" size={14} />
                粘贴
                <kbd>Ctrl V</kbd>
              </button>
              <span className="context-separator" />
              <button
                type="button"
                onClick={packSelection}
                disabled={contextIdsRef.current.length < 2}
              >
                <Icon name="package" size={14} />
                打包为 Mojo
                <span className="context-note">
                  {contextIdsRef.current.length < 2 ? "Shift 多选" : "复用子模块"}
                </span>
              </button>
            </>
          ) : (
            <button
              type="button"
              onClick={() => pasteSelection({ x: contextMenu.flowX, y: contextMenu.flowY })}
              disabled={!clipboardRef.current}
            >
              <Icon name="plus" size={14} />
              粘贴到此处
              <kbd>Ctrl V</kbd>
            </button>
          )}
          <span className="context-separator" />
          <button
            type="button"
            className="context-danger"
            onClick={() => {
              if (window.confirm("确定清空当前画布吗？此操作可以使用撤销恢复。")) {
                clearGraph();
                setContextMenu(null);
              }
            }}
          >
            <Icon name="trash" size={14} />
            清空画布
          </button>
        </div>
      )}
    </div>
  );
}

export function GraphCanvas() {
  return (
    <ReactFlowProvider>
      <FlowCanvas />
    </ReactFlowProvider>
  );
}
