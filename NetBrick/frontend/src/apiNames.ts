import type { BlockSpec, Framework } from "./types";

export interface ApiPresentation {
  className: string;
  path: string;
}

export interface ParameterPresentation {
  key: string;
  value: unknown;
  invertBoolean?: boolean;
}

export function apiPresentation(
  block: BlockSpec | undefined,
  framework: Framework,
  fallbackOp = "Module",
): ApiPresentation {
  if (!block || block.system) {
    return {
      className: block?.op ?? fallbackOp,
      path: block?.op === "Input" || block?.op === "Output" ? "模型边界" : fallbackOp,
    };
  }
  if (framework === "paddle" && block.pytorch_only) {
    const className =
      block.torch_name ?? block.op.replace(/^nn\./, "");
    return {
      className,
      path: block.torch_api ?? `torch.nn.${className}`,
    };
  }
  if (block?.control_type) {
    return {
      className:
        block.control_type === "if"
          ? "If"
          : block.control_type === "for"
            ? "For"
            : "While",
      path: "结构化控制流",
    };
  }
  const explicitPath =
    framework === "paddle" ? block.paddle_api : block.torch_api;
  if (explicitPath) {
    return {
      className: explicitPath.split(".").at(-1) ?? explicitPath,
      path: explicitPath,
    };
  }
  const className =
    framework === "paddle" ? block.paddle_name : block.torch_name;
  const namespace = framework === "paddle" ? "paddle.nn" : "torch.nn";
  return {
    className: className ?? block.op.replace(/^nn\./, ""),
    path: `${namespace}.${className ?? block.op.replace(/^nn\./, "")}`,
  };
}

export function plannedApiPresentation(
  op: string,
  framework: Framework,
): ApiPresentation {
  if (op === "SGD" || op === "Adam") {
    return {
      className: op,
      path: framework === "paddle" ? `paddle.optimizer.${op}` : `torch.optim.${op}`,
    };
  }
  return {
    className: op,
    path: framework === "paddle" ? `paddle.nn.${op}` : `torch.nn.${op}`,
  };
}

export function parameterPresentation(
  op: string,
  key: string,
  value: unknown,
  framework: Framework,
): ParameterPresentation | null {
  if (framework === "pytorch" || op === "Input" || op === "Output") {
    return { key, value };
  }

  if (key === "track_running_stats" || key === "elementwise_affine") {
    return null;
  }
  if (key === "affine" && op !== "nn.Linear") {
    return null;
  }
  if (key === "dilation" && op.includes("Pool")) {
    return null;
  }
  if (key === "inplace" && op !== "nn.SiLU") {
    return null;
  }

  if (key === "bias" && (op.startsWith("nn.Conv") || op === "nn.Linear")) {
    return { key: "bias_attr", value };
  }
  if (op === "nn.Flatten" && key === "start_dim") {
    return { key: "start_axis", value };
  }
  if (op === "nn.Flatten" && key === "end_dim") {
    return { key: "stop_axis", value };
  }
  if (
    key === "dim" &&
    (op === "nn.Unflatten" || op === "nn.Softmax" || op === "nn.LogSoftmax")
  ) {
    return { key: "axis", value };
  }
  if (op === "merge.Concat" && key === "dim") {
    return { key: "axis", value };
  }
  if (op === "nn.Unflatten" && key === "sizes") {
    return { key: "shape", value };
  }
  if (
    key === "eps" &&
    [
      "nn.BatchNorm1d",
      "nn.BatchNorm2d",
      "nn.LayerNorm",
      "nn.GroupNorm",
      "nn.InstanceNorm2d",
    ].includes(op)
  ) {
    return { key: "epsilon", value };
  }
  if (key === "count_include_pad") {
    return {
      key: "exclusive",
      value: !Boolean(value),
      invertBoolean: true,
    };
  }
  return { key, value };
}

export function displayParameterValue(value: unknown): string {
  if (Array.isArray(value)) return `[${value.join(", ")}]`;
  return String(value);
}
