import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import {
  apiPresentation,
  displayParameterValue,
  parameterPresentation,
} from "../apiNames";
import { inputPortIds, outputPortIds } from "../flowPorts";
import type {
  BlockSpec,
  Framework,
  GraphNode,
  NodeAnalysis,
} from "../types";
import { Icon } from "./Icons";

export interface FlowNodeData extends Record<string, unknown> {
  graphNode: GraphNode;
  block?: BlockSpec;
  analysis?: NodeAnalysis;
  invalid?: boolean;
  framework: Framework;
  connectionPin?: { nodeId: string; port: string } | null;
}

export type OperationFlowNode = Node<FlowNodeData, "operation">;

function formatShape(shape?: Array<number | null> | null): string {
  if (!shape?.length) return "shape 待检查";
  return `[${shape.join(", ")}]`;
}

function parameterSummary(
  block: BlockSpec | undefined,
  node: GraphNode,
  framework: Framework,
): string {
  if (!block) return node.op;
  if (node.op === "Input") {
    return formatShape(
      Array.isArray(node.params.sample_shape)
        ? (node.params.sample_shape as number[])
        : null,
    );
  }
  if (node.op === "Output") return `name=${String(node.params.name ?? "output")}`;
  if (node.op === "composite.instance") {
    return `v${node.composite_ref?.revision ?? "?"} · ${
      node.state_contract?.inputs.length ?? 0
    } in / ${node.state_contract?.outputs.length ?? 0} out`;
  }
  if (node.op.startsWith("control.")) {
    return "结构化控制流 · 双击查看";
  }
  const values = block.fields
    .filter((field) => node.params[field.key] !== undefined)
    .map((field) => ({
      field,
      view: parameterPresentation(
        node.op,
        field.key,
        node.params[field.key],
        framework,
      ),
    }))
    .filter((item) => item.view !== null)
    .slice(0, 3)
    .map(({ view }) => {
      return `${view!.key}=${displayParameterValue(view!.value)}`;
    });
  return values.length ? `(${values.join(", ")})` : "无超参数";
}

export function OperationNode({ data, selected }: NodeProps<OperationFlowNode>) {
  const { graphNode, block, analysis, invalid, framework } = data;
  const isInput = graphNode.op === "Input";
  const isOutput = graphNode.op === "Output";
  const color = "#c9cdd4";
  const outputPort = analysis?.ports.find((port) => port.io === "out");
  const displayShape =
    outputPort?.shape ??
    (isOutput
      ? analysis?.ports.find((port) => port.io === "in")?.shape
      : undefined);
  const api = apiPresentation(block, framework, graphNode.op);
  const inputs = inputPortIds(graphNode, block);
  const outputs = outputPortIds(graphNode, block);
  const multipleInputs = inputs.length > 1;
  const multipleOutputs = outputs.length > 1;
  const apiName =
    graphNode.op === "composite.instance"
      ? String(graphNode.params.name ?? "Composite")
      : api.className;

  return (
    <div
      className={[
        "flow-node",
        `flow-node--${block?.category ?? "other"}`,
        isInput ? "flow-node--input" : "",
        isOutput ? "flow-node--output" : "",
        selected ? "is-selected" : "",
        invalid ? "is-invalid" : "",
      ]
        .filter(Boolean)
        .join(" ")}
      style={{ "--node-color": color } as React.CSSProperties}
      data-node-kind={block?.category ?? "other"}
    >
      {inputs.map((port, index) => (
        <Handle
          key={port}
          type="target"
          position={Position.Left}
          id={port}
          className="flow-handle flow-handle--input"
          title={
            data.connectionPin
              ? `点击连接到 ${data.connectionPin.nodeId}.${data.connectionPin.port}`
              : `输入端口 ${port}：接收 Tensor`
          }
          style={
            multipleInputs
              ? { top: `${((index + 1) * 100) / (inputs.length + 1)}%` }
              : undefined
          }
        />
      ))}
      <div className="flow-node__accent" />
      <div className="flow-node__body">
        <div className="flow-node__heading">
          <span className="flow-node__category">
            {isInput
              ? "INPUT"
              : isOutput
                ? "OUTPUT"
                : graphNode.op === "composite.instance"
                  ? "COMPOSITE"
                  : graphNode.op.startsWith("control.")
                    ? "CONTROL"
                    : block?.category ?? "OP"}
          </span>
          {invalid && (
            <span className="flow-node__warning" title="该节点存在结构冲突">
              <Icon name="warning" size={13} />
            </span>
          )}
        </div>
        <strong>{apiName}</strong>
        <span className="flow-node__params">
          {parameterSummary(block, graphNode, framework)}
        </span>
        <span className="flow-node__shape">{formatShape(displayShape)}</span>
      </div>
      {!isOutput &&
        (outputs.length ? outputs : ["out"]).map((port, index) => {
          const isPinned =
            data.connectionPin?.nodeId === graphNode.id &&
            data.connectionPin?.port === port;
          return (
          <Handle
            key={port}
            type="source"
            position={Position.Right}
            id={port}
            className={`flow-handle flow-handle--output ${isPinned ? "is-pinned" : ""}`}
            title={`输出端口 ${port}：点击固定后，可连续连接多个输入`}
            style={
              multipleOutputs
                ? { top: `${((index + 1) * 100) / (outputs.length + 1)}%` }
                : undefined
            }
          />
          );
        })}
    </div>
  );
}
