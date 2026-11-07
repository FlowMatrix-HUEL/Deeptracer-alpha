import type {
  AnalysisResult,
  CatalogResponse,
  CodegenResponse,
  CompositeResource,
  CompositeValidateResponse,
  Framework,
  ImportResponse,
  IRDocument,
  Moment,
  SampleSummary,
  TraceResponse,
} from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    let message = `请求失败 (${response.status})`;
    try {
      const payload = (await response.json()) as {
        detail?: string | { message?: string };
      };
      if (typeof payload.detail === "string") {
        message = payload.detail;
      } else if (payload.detail?.message) {
        message = payload.detail.message;
      }
    } catch {
      // Keep the status-only message for non-JSON server failures.
    }
    throw new Error(message);
  }
  return (await response.json()) as T;
}

export const api = {
  catalog: () => request<CatalogResponse>("/api/v1/catalog"),
  samples: () => request<SampleSummary[]>("/api/v1/samples"),
  sample: (id: string) =>
    request<IRDocument>(`/api/v1/samples/${encodeURIComponent(id)}`),
  validate: (ir: IRDocument) =>
    request<AnalysisResult>("/api/v1/graphs/validate", {
      method: "POST",
      body: JSON.stringify(ir),
    }),
  trace: (ir: IRDocument) =>
    request<TraceResponse>("/api/v1/graphs/trace-preview", {
      method: "POST",
      body: JSON.stringify({ ir, seed: 42 }),
    }),
  moments: (trace: TraceResponse) =>
    request<{ moments: Moment[] }>("/api/breakpoints", {
      method: "POST",
      body: JSON.stringify({ world: "netbrick", trace }),
    }),
  codegen: (ir: IRDocument, framework: Framework) =>
    request<CodegenResponse>("/api/v1/graphs/codegen", {
      method: "POST",
      body: JSON.stringify({ ir, framework, include_demo: true }),
    }),
  importPytorch: (source: string, shape: number[]) =>
    request<ImportResponse>("/api/v1/graphs/import/pytorch", {
      method: "POST",
      body: JSON.stringify({
        source,
        source_name: "student_model.py",
        shape,
        dtype: "float32",
      }),
    }),
  exportCourse: async (ir: IRDocument) => {
    const response = await fetch("/api/v1/course-packages/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: ir.graph_meta.name,
        author: ir.graph_meta.author,
        description: ir.graph_meta.note,
        ir,
        steps: [
          {
            title: "观察模型结构",
            markdown: "沿数据流从左到右，检查每个模块的输入与输出形状。",
            focus_node_ids: ir.graph.nodes.slice(0, 3).map((node) => node.id),
          },
        ],
      }),
    });
    if (!response.ok) {
      throw new Error("课件包导出失败");
    }
    return response.blob();
  },
  publishComposite: (
    ir: IRDocument,
    name: string,
    revision: number,
    resourceId: string,
    description = "",
  ) =>
    request<CompositeValidateResponse>("/api/v1/composites/publish", {
      method: "POST",
      body: JSON.stringify({
        resource_id: resourceId,
        name,
        revision,
        description,
        author: ir.graph_meta.author,
        ir,
      }),
    }),
  savePythonNative: (filename: string, source: string) =>
    request<{
      status: "saved" | "cancelled" | "unavailable" | "error";
      path?: string | null;
      message: string;
    }>("/api/v1/files/save-python", {
      method: "POST",
      body: JSON.stringify({ filename, source }),
    }),
};
