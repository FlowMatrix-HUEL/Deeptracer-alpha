import type { BlockSpec, GraphNode } from "./types";

export function inputPortIds(
  node: GraphNode,
  block: BlockSpec | undefined,
): string[] {
  if (node.op === "Input") return [];
  if (node.op === "Output") return ["x"];
  if (node.state_contract) {
    return node.state_contract.inputs.map((port) => port.name);
  }
  if (block?.input_ports.length) {
    return block.input_ports.map((port) => port.name);
  }
  if (block?.input_mode === "merge") return ["x"];
  return ["x"];
}

export function outputPortIds(
  node: GraphNode,
  block?: BlockSpec,
): string[] {
  if (node.op === "Output") return [];
  if (node.state_contract) {
    return node.state_contract.outputs.map((port) => port.name);
  }
  if (block?.output_ports.length) {
    return block.output_ports.map((port) => port.name);
  }
  return ["out"];
}
