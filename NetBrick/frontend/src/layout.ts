import dagre from "dagre";
import type { IRDocument, Position } from "./types";

export function autoLayout(ir: IRDocument): Record<string, Position> {
  const graph = new dagre.graphlib.Graph();
  graph.setGraph({
    rankdir: "LR",
    nodesep: 82,
    ranksep: 92,
    marginx: 60,
    marginy: 60,
  });
  graph.setDefaultEdgeLabel(() => ({}));

  for (const node of ir.graph.nodes) {
    graph.setNode(node.id, { width: 222, height: 102 });
  }
  for (const edge of ir.graph.edges) {
    graph.setEdge(edge.source.node_id, edge.target.node_id);
  }
  dagre.layout(graph);

  return Object.fromEntries(
    ir.graph.nodes.map((node) => {
      const point = graph.node(node.id) as { x: number; y: number };
      return [
        node.id,
        {
          x: Math.round(point.x - 111),
          y: Math.round(point.y - 51),
        },
      ];
    }),
  );
}
