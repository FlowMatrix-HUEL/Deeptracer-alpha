import {
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
  type Edge,
  type EdgeProps,
} from "@xyflow/react";
import { useState } from "react";

export interface ShapeEdgeData extends Record<string, unknown> {
  shape: string;
  invalid?: boolean;
}

export type DataFlowEdge = Edge<ShapeEdgeData, "shape">;

export function ShapeEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  markerEnd,
  selected,
}: EdgeProps<DataFlowEdge>) {
  const [hovered, setHovered] = useState(false);
  const [path, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
    curvature: 0.34,
  });
  const invalid = Boolean(data?.invalid);

  return (
    <g
      className={`shape-edge ${invalid ? "shape-edge--invalid" : ""} ${selected ? "is-selected" : ""}`}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <BaseEdge
        id={id}
        path={path}
        markerEnd={markerEnd}
        interactionWidth={26}
        style={{
          stroke: invalid ? "#f53f3f" : selected ? "#3370ff" : "#c9cdd4",
          strokeWidth: selected ? 2.4 : 1.8,
        }}
      />
      <EdgeLabelRenderer>
        <div
          className={`edge-shape-tooltip ${hovered || selected ? "is-visible" : ""} ${invalid ? "is-invalid" : ""}`}
          style={{
            transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
          }}
        >
          {invalid ? "Shape 冲突" : data?.shape || "Tensor"}
        </div>
      </EdgeLabelRenderer>
    </g>
  );
}
