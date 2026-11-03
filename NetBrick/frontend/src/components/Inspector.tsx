import {
  useEffect,
  useState,
  type PointerEvent as ReactPointerEvent,
} from "react";
import {
  apiPresentation,
  parameterPresentation,
} from "../apiNames";
import { useGraphStore } from "../store";
import type { FieldSpec } from "../types";
import { Icon } from "./Icons";

function ListField({
  field,
  value,
  onChange,
}: {
  field: FieldSpec;
  value: unknown[];
  onChange: (value: number[]) => void;
}) {
  const [text, setText] = useState(value.join(", "));
  useEffect(() => {
    setText(value.join(", "));
  }, [value]);
  const commit = () => {
    const parsed = text
      .split(",")
      .map((item) => Number(item.trim()))
      .filter((item) => Number.isInteger(item));
    if (parsed.length > 0) onChange(parsed);
  };
  return (
    <input
      className="field-input mono"
      value={text}
      onChange={(event) => setText(event.target.value)}
      onBlur={commit}
      aria-label={field.label}
    />
  );
}

function ParameterField({
  field,
  value,
  error,
  onChange,
}: {
  field: FieldSpec;
  value: unknown;
  error?: string;
  onChange: (value: unknown) => void;
}) {
  if (field.type === "bool") {
    return (
      <button
        type="button"
        className={`switch-row ${Boolean(value) ? "switch-row--on" : ""}`}
        onClick={() => onChange(!Boolean(value))}
      >
        <span className="switch">
          <span />
        </span>
        {Boolean(value) ? "开启" : "关闭"}
      </button>
    );
  }
  if (field.type === "enum") {
    return (
      <select
        className="field-input"
        value={String(value)}
        onChange={(event) => onChange(event.target.value)}
      >
        {(field.options ?? []).map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    );
  }
  if (field.type === "int_list" && Array.isArray(value)) {
    return (
      <ListField
        field={field}
        value={value as unknown[]}
        onChange={onChange}
      />
    );
  }
  if (field.type === "int" || field.type === "float") {
    return (
      <input
        className={`field-input ${error ? "field-input--error" : ""}`}
        type="number"
        value={String(value ?? "")}
        min={field.minimum ?? undefined}
        max={field.maximum ?? undefined}
        step={field.step ?? (field.type === "int" ? 1 : "any")}
        onChange={(event) => {
          const raw = event.target.value;
          if (raw === "") return;
          onChange(field.type === "int" ? Number.parseInt(raw, 10) : Number(raw));
        }}
      />
    );
  }
  return (
    <input
      className={`field-input ${error ? "field-input--error" : ""}`}
      value={String(value ?? "")}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}

function NodeInspector({ nodeId }: { nodeId: string }) {
  const ir = useGraphStore((state) => state.ir);
  const resources = useGraphStore((state) => state.resources);
  const framework = useGraphStore((state) => state.ir.target_framework);
  const catalog = useGraphStore((state) => state.catalog);
  const analysis = useGraphStore((state) => state.analysis);
  const updateNodeParam = useGraphStore((state) => state.updateNodeParam);
  const updateNote = useGraphStore(
    (state) => state.updateNodeTeachingNote,
  );
  const removeSelectedNode = useGraphStore(
    (state) => state.removeSelectedNode,
  );
  const changeCompositeVersion = useGraphStore(
    (state) => state.changeCompositeVersion,
  );
  const setCompositeOverride = useGraphStore(
    (state) => state.setCompositeParamOverride,
  );
  const addControlStatePort = useGraphStore(
    (state) => state.addControlStatePort,
  );
  const updateControlStatePort = useGraphStore(
    (state) => state.updateControlStatePort,
  );
  const addLoopIndexPort = useGraphStore(
    (state) => state.addLoopIndexPort,
  );
  const node = ir.graph.nodes.find((item) => item.id === nodeId);
  const [note, setNote] = useState(node?.teaching_note ?? "");

  useEffect(() => {
    setNote(node?.teaching_note ?? "");
  }, [node?.id, node?.teaching_note]);

  if (!node) return null;
  const block = catalog.find((item) => item.op === node.op);
  const api = apiPresentation(block, framework, node.op);
  const nodeAnalysis = analysis?.nodes.find((item) => item.node_id === node.id);
  const inputPorts =
    nodeAnalysis?.ports.filter((port) => port.io === "in") ?? [];
  const outputPort =
    nodeAnalysis?.ports.find((port) => port.io === "out") ??
    nodeAnalysis?.ports[0];
  const errors = analysis?.diagnostics.filter(
    (item) => item.node_id === node.id && item.severity === "error",
  );

  if (node.op === "composite.instance" && node.composite_ref) {
    const resource =
      ir.resources?.find(
        (item) =>
          item.resource_id === node.composite_ref!.resource_id &&
          item.revision === node.composite_ref!.revision,
      ) ??
      resources.find(
        (item) =>
          item.resource_id === node.composite_ref!.resource_id &&
          item.revision === node.composite_ref!.revision,
      );
    const versionMap = new Map(
      [...resources, ...(ir.resources ?? [])].map((item) => [
        `${item.resource_id}@${item.revision}`,
        item,
      ]),
    );
    const versions = [...versionMap.values()]
      .filter(
        (item) => item.resource_id === node.composite_ref!.resource_id,
      )
      .sort((left, right) => right.revision - left.revision);
    return (
      <div className="inspector__body">
        <div className="selected-heading">
          <div className="selected-heading__icon">
            <Icon name="package" size={18} />
          </div>
          <div>
            <h2>{resource?.name ?? "Missing Composite"}</h2>
            <code>复合模型 · v{node.composite_ref.revision}</code>
          </div>
          <button
            className="icon-button"
            type="button"
            onClick={removeSelectedNode}
            title="删除复合节点"
          >
            <Icon name="trash" size={16} />
          </button>
        </div>
        <section className="inspector-section">
          <div className="section-title">
            <span>资源版本</span>
          </div>
          <select
            className="field-input"
            value={node.composite_ref.revision}
            onChange={(event) =>
              changeCompositeVersion(node.id, Number(event.target.value))
            }
          >
            {versions.map((item) => (
              <option key={item.revision} value={item.revision}>
                {item.name} v{item.revision}
              </option>
            ))}
          </select>
          {resource && (
            <div className="composite-interface-summary">
              {resource.inputs.map((port) => (
                <span key={`in-${port.name}`}>
                  IN {port.name} {port.shape ? `[${port.shape.join(", ")}]` : ""}
                </span>
              ))}
              {resource.outputs.map((port) => (
                <span key={`out-${port.name}`}>
                  OUT {port.name} {port.shape ? `[${port.shape.join(", ")}]` : ""}
                </span>
              ))}
            </div>
          )}
        </section>
        {resource && (
          <section className="inspector-section">
            <div className="section-title">
              <span>递归暴露参数</span>
              <span>{Object.keys(resource.parameter_defaults).length} 项</span>
            </div>
            <div className="composite-param-list">
              {Object.entries(resource.parameter_defaults).map(
                ([path, defaultValue]) => {
                  const value =
                    node.param_overrides?.[path] ?? defaultValue;
                  const primitive =
                    ["string", "number", "boolean"].includes(typeof value);
                  return (
                    <label className="field" key={path}>
                      <span className="field__label">
                        <code className="field__api-name">{path}</code>
                      </span>
                      {primitive ? (
                        typeof value === "boolean" ? (
                          <button
                            type="button"
                            className={`switch-row ${value ? "switch-row--on" : ""}`}
                            onClick={() =>
                              setCompositeOverride(node.id, path, !value)
                            }
                          >
                            <span className="switch">
                              <span />
                            </span>
                            {value ? "开启" : "关闭"}
                          </button>
                        ) : (
                          <input
                            className="field-input"
                            type={typeof value === "number" ? "number" : "text"}
                            value={String(value)}
                            onChange={(event) =>
                              setCompositeOverride(
                                node.id,
                                path,
                                typeof value === "number"
                                  ? Number(event.target.value)
                                  : event.target.value,
                              )
                            }
                          />
                        )
                      ) : (
                        <input
                          className="field-input mono"
                          defaultValue={JSON.stringify(value)}
                          onBlur={(event) => {
                            try {
                              setCompositeOverride(
                                node.id,
                                path,
                                JSON.parse(event.target.value),
                              );
                            } catch {
                              // Keep the last valid value.
                            }
                          }}
                        />
                      )}
                    </label>
                  );
                },
              )}
              {Object.keys(resource.parameter_defaults).length === 0 && (
                <div className="empty-note">该复合资源没有可调参数。</div>
              )}
            </div>
          </section>
        )}
      </div>
    );
  }

  return (
    <div className="inspector__body">
      <div className="selected-heading">
        <div className="selected-heading__icon">
          <Icon name="layers" size={18} />
        </div>
        <div>
          <h2>{api.className}</h2>
          <code>{api.path}</code>
        </div>
        <button
          className="icon-button"
          onClick={removeSelectedNode}
          type="button"
          title="删除节点"
        >
          <Icon name="trash" size={16} />
        </button>
      </div>

      <p className="node-description">{block?.description}</p>

      <div className="shape-strip">
        <div>
          <span>IN</span>
          <code>
            {inputPorts.length > 0
              ? inputPorts
                  .map((port) =>
                    port.shape ? `[${port.shape.join(", ")}]` : "—",
                  )
                  .join(" + ")
              : "—"}
          </code>
        </div>
        <Icon name="chevron" size={14} />
        <div>
          <span>OUT</span>
          <code>
            {outputPort?.shape
              ? `[${outputPort.shape.join(", ")}]`
              : "—"}
          </code>
        </div>
      </div>

      {errors && errors.length > 0 && (
        <div className="inline-error">
          <Icon name="warning" size={16} />
          <span>{errors[0].message}</span>
        </div>
      )}

      {node.op.startsWith("control.") && node.state_contract && (
        <section className="inspector-section control-contract-editor">
          <div className="section-title">
            <span>状态端口契约</span>
            <span>所有区域必须一致</span>
          </div>
          {(["in", "out"] as const).map((io) => (
            <div className="control-port-group" key={io}>
              <div className="control-port-group__heading">
                <span>{io === "in" ? "输入状态" : "输出状态"}</span>
                <button
                  type="button"
                  onClick={() => addControlStatePort(node.id, io)}
                >
                  + 端口
                </button>
              </div>
              {(io === "in"
                ? node.state_contract!.inputs
                : node.state_contract!.outputs
              ).map((port, index) => (
                <div className="control-port-row" key={`${io}-${index}`}>
                  <input
                    className="field-input"
                    value={port.name}
                    onChange={(event) =>
                      updateControlStatePort(
                        node.id,
                        io,
                        index,
                        "name",
                        event.target.value,
                      )
                    }
                    aria-label="状态端口名称"
                  />
                  <input
                    className="field-input mono"
                    value={(port.shape ?? []).join(", ")}
                    onBlur={(event) => {
                      const shape = event.target.value
                        .split(",")
                        .map((value) => Number(value.trim()))
                        .filter((value) => Number.isInteger(value));
                      if (shape.length) {
                        updateControlStatePort(
                          node.id,
                          io,
                          index,
                          "shape",
                          shape,
                        );
                      }
                    }}
                    aria-label="状态端口形状"
                  />
                  <select
                    className="field-input"
                    value={port.dtype ?? "float32"}
                    onChange={(event) =>
                      updateControlStatePort(
                        node.id,
                        io,
                        index,
                        "dtype",
                        event.target.value,
                      )
                    }
                  >
                    <option value="float32">float32</option>
                    <option value="float64">float64</option>
                    <option value="int64">int64</option>
                    <option value="bool">bool</option>
                  </select>
                </div>
              ))}
            </div>
          ))}
          {["control.For", "control.While"].includes(node.op) && (
            <button
              type="button"
              className="control-index-action"
              onClick={() => addLoopIndexPort(node.id)}
            >
              + 添加循环 index: ScalarInt
            </button>
          )}
        </section>
      )}

      <section className="inspector-section">
        <div className="section-title">
          <span>参数</span>
          <span>{block?.fields.length ?? 0} 项</span>
        </div>
        <div className="field-list">
          {(block?.fields ?? []).map((field) => {
            const presentation = parameterPresentation(
              node.op,
              field.key,
              node.params[field.key],
              framework,
            );
            if (!presentation) return null;
            const fieldError = analysis?.diagnostics.find(
              (item) =>
                item.node_id === node.id &&
                item.field === field.key &&
                item.severity === "error",
            );
            return (
              <label className="field" key={field.key}>
                <span className="field__label">
                  <code className="field__api-name">{presentation.key}</code>
                  {field.help && (
                    <span
                      className="field__help"
                      title={`${field.label}：${field.help}`}
                    >
                      ?
                    </span>
                  )}
                </span>
                <ParameterField
                  field={{
                    ...field,
                    key: presentation.key,
                    label: presentation.key,
                  }}
                  value={presentation.value}
                  error={fieldError?.message}
                  onChange={(value) =>
                    updateNodeParam(
                      node.id,
                      field.key,
                      presentation.invertBoolean ? !Boolean(value) : value,
                    )
                  }
                />
                {(field.help || field.label) && (
                  <span className="field__hint">
                    {field.help || field.label}
                  </span>
                )}
              </label>
            );
          })}
          {(block?.fields.length ?? 0) === 0 && (
            <div className="empty-note">这个模块没有可调参数。</div>
          )}
        </div>
      </section>

      <section className="inspector-section">
        <div className="section-title">
          <span>教学批注</span>
          <span>仅保存在 IR</span>
        </div>
        <textarea
          className="note-input"
          value={note}
          onChange={(event) => setNote(event.target.value)}
          onBlur={() => updateNote(node.id, note)}
          placeholder="例如：这里的 784 来自 28×28 图像展平"
          rows={4}
        />
      </section>
    </div>
  );
}

function DocumentInspector() {
  const ir = useGraphStore((state) => state.ir);
  const analysis = useGraphStore((state) => state.analysis);
  const updateMeta = useGraphStore((state) => state.updateMeta);
  const errorCount =
    analysis?.diagnostics.filter((item) => item.severity === "error").length ??
    0;

  return (
    <div className="inspector__body">
      <div className="document-card">
        <span className="eyebrow">MODEL OVERVIEW</span>
        <h2>{ir.graph_meta.name}</h2>
        <p>
          {ir.graph_meta.note ||
            "选择画布中的节点查看参数，或在这里补充模型说明。"}
        </p>
        <div className="metric-grid">
          <div>
            <strong>{ir.graph.nodes.length}</strong>
            <span>节点</span>
          </div>
          <div>
            <strong>{ir.graph.edges.length}</strong>
            <span>连线</span>
          </div>
          <div>
            <strong>{analysis?.chain_count ?? 0}</strong>
            <span>数据链</span>
          </div>
          <div className={errorCount ? "metric--error" : ""}>
            <strong>{errorCount}</strong>
            <span>错误</span>
          </div>
        </div>
      </div>

      <section className="inspector-section">
        <div className="section-title">
          <span>工程信息</span>
        </div>
        <label className="field">
          <span className="field__label">模型名称</span>
          <input
            className="field-input"
            value={ir.graph_meta.name}
            onChange={(event) => updateMeta("name", event.target.value)}
          />
        </label>
        <label className="field">
          <span className="field__label">作者</span>
          <input
            className="field-input"
            value={ir.graph_meta.author}
            onChange={(event) => updateMeta("author", event.target.value)}
            placeholder="课堂 / 学生姓名"
          />
        </label>
        <label className="field">
          <span className="field__label">模型说明</span>
          <textarea
            className="note-input"
            rows={4}
            value={ir.graph_meta.note}
            onChange={(event) => updateMeta("note", event.target.value)}
            placeholder="记录模型用途和课堂要点"
          />
        </label>
      </section>

      <div className="teaching-callout">
        <Icon name="spark" size={19} />
        <div>
          <strong>从拖拽走向手写</strong>
          <p>
            画布用于理解结构。完成连接后，导出的 Python
            代码应继续由学生阅读和修改。
          </p>
        </div>
      </div>
    </div>
  );
}

interface InspectorProps {
  collapsed: boolean;
  onToggle: () => void;
  onResizeStart: (event: ReactPointerEvent) => void;
}

export function Inspector({
  collapsed,
  onToggle,
  onResizeStart,
}: InspectorProps) {
  const selectedNodeId = useGraphStore((state) => state.selectedNodeId);
  if (collapsed) {
    return (
      <aside className="inspector inspector--collapsed">
        <button
          type="button"
          className="rail-button"
          onClick={onToggle}
          title="展开 Inspector"
        >
          <Icon name="chevron" size={15} className="chevron--left" />
        </button>
        <button type="button" className="rail-button rail-button--active">
          <Icon name="info" size={17} />
        </button>
        <span className="rail-label rail-label--right">INSPECTOR</span>
        <span className="rail-spacer" />
        <button type="button" className="rail-button" title="工程信息">
          <Icon name="layers" size={16} />
        </button>
      </aside>
    );
  }
  return (
    <aside className="inspector">
      <div
        className="panel-resize-handle panel-resize-handle--left"
        onPointerDown={onResizeStart}
        title="拖拽调整 Inspector 宽度"
      />
      <div className="inspector__header">
        <div>
          <span className="eyebrow">INSPECTOR</span>
          <h2>{selectedNodeId ? "节点参数" : "工程概览"}</h2>
        </div>
        <div className="inspector__heading-actions">
          <span className="inspector__badge">
            {selectedNodeId ? "NODE" : "IR 0.2"}
          </span>
          <button
            type="button"
            className="icon-button"
            onClick={onToggle}
            title="收起 Inspector"
          >
            <Icon name="chevron" size={15} className="chevron--right" />
          </button>
        </div>
      </div>
      <div className="inspector__scroll">
        {selectedNodeId ? (
          <NodeInspector nodeId={selectedNodeId} />
        ) : (
          <DocumentInspector />
        )}
      </div>
    </aside>
  );
}
