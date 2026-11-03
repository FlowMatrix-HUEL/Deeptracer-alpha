import { useRef } from "react";
import { api } from "../api";
import { savePythonFile } from "../saveFile";
import { useGraphStore } from "../store";
import type { IRDocument } from "../types";
import { Icon } from "./Icons";

interface ToolbarProps {
  onOpenImport: () => void;
  onOpenPublish: () => void;
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function safeFilename(name: string): string {
  return (
    name
      .trim()
      .replace(/[\\/:*?"<>|]+/g, "-")
      .replace(/\s+/g, "_") || "netbrick-model"
  );
}

export function Toolbar({ onOpenImport, onOpenPublish }: ToolbarProps) {
  const ir = useGraphStore((state) => state.ir);
  const samples = useGraphStore((state) => state.samples);
  const analysis = useGraphStore((state) => state.analysis);
  const undoStack = useGraphStore((state) => state.undoStack);
  const redoStack = useGraphStore((state) => state.redoStack);
  const dirty = useGraphStore((state) => state.dirty);
  const activeView = useGraphStore((state) => state.activeView);
  const busy = useGraphStore((state) => state.busy);
  const newDocument = useGraphStore((state) => state.newDocument);
  const loadSample = useGraphStore((state) => state.loadSample);
  const loadDocument = useGraphStore((state) => state.loadDocument);
  const updateMeta = useGraphStore((state) => state.updateMeta);
  const setFramework = useGraphStore((state) => state.setFramework);
  const applyAutoLayout = useGraphStore((state) => state.applyAutoLayout);
  const undo = useGraphStore((state) => state.undo);
  const redo = useGraphStore((state) => state.redo);
  const validateNow = useGraphStore((state) => state.validateNow);
  const generateCode = useGraphStore((state) => state.generateCode);
  const runTracePreview = useGraphStore((state) => state.runTracePreview);
  const showToast = useGraphStore((state) => state.showToast);
  const markSaved = useGraphStore((state) => state.markSaved);
  const fileInput = useRef<HTMLInputElement>(null);
  const courseInput = useRef<HTMLInputElement>(null);

  const exportPython = async () => {
    const generated = await generateCode();
    if (!generated) return;
    const result = await savePythonFile(
      generated.filename,
      generated.source,
    );
    if (result === "saved") {
      showToast("success", "Python 文件已保存到所选位置");
    } else if (result === "downloaded") {
      showToast(
        "info",
        "当前浏览器不支持另存为选择器，已使用默认下载目录",
      );
    }
  };

  const saveJson = () => {
    const content = JSON.stringify(ir, null, 2);
    downloadBlob(
      new Blob([content], { type: "application/json" }),
      `${safeFilename(ir.graph_meta.name)}.netbrick.json`,
    );
    markSaved();
    showToast("success", "工程 JSON 已下载");
  };

  const confirmDiscard = () =>
    !dirty || window.confirm("当前工程有未保存修改，确定要打开其他工程吗？");

  const openJson = async (file: File) => {
    try {
      const parsed = JSON.parse(await file.text()) as IRDocument;
      if (
        !["0.2", "0.3"].includes(parsed.ir_version) ||
        !parsed.graph?.nodes
      ) {
        throw new Error("不是受支持的 NetBrick 工程文件");
      }
      loadDocument(parsed, `已打开 ${file.name}`);
    } catch (error) {
      showToast(
        "error",
        error instanceof Error ? error.message : "工程文件读取失败",
      );
    }
  };

  const exportCourse = async () => {
    try {
      const blob = await api.exportCourse(ir);
      downloadBlob(blob, `${safeFilename(ir.graph_meta.name)}.netbrick`);
      showToast("success", "课件包已导出");
    } catch (error) {
      showToast(
        "error",
        error instanceof Error ? error.message : "课件包导出失败",
      );
    }
  };

  const importCourse = async (file: File) => {
    try {
      const bytes = new Uint8Array(await file.arrayBuffer());
      let binary = "";
      for (const byte of bytes) binary += String.fromCharCode(byte);
      const contentBase64 = btoa(binary);
      const response = await fetch("/api/v1/course-packages/validate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content_base64: contentBase64 }),
      });
      const result = (await response.json()) as {
        valid: boolean;
        pack?: { ir: IRDocument };
        diagnostics?: Array<{ message: string }>;
      };
      if (!result.valid || !result.pack) {
        throw new Error(result.diagnostics?.[0]?.message ?? "课件包无效");
      }
      loadDocument(result.pack.ir, `已载入课件 ${file.name}`);
    } catch (error) {
      showToast(
        "error",
        error instanceof Error ? error.message : "课件包导入失败",
      );
    }
  };

  const status =
    analysis == null
      ? { label: "检查中", tone: "pending" }
      : analysis.valid
        ? { label: `${analysis.chain_count} 条数据流`, tone: "valid" }
        : {
            label: `${analysis.diagnostics.filter((item) => item.severity === "error").length} 个问题`,
            tone: "invalid",
          };

  return (
    <header className="toolbar">
      <div className="brand">
        <div className="brand__mark">
          <span />
          <span />
          <span />
        </div>
        <div className="brand__text">
          <strong>NetBrick</strong>
          <span>深度学习积木</span>
        </div>
      </div>

      <label className="framework-picker" title="切换代码生成框架">
        <span className="framework-picker__icon">
          <Icon name="code" size={14} />
        </span>
        <select
          value={ir.target_framework}
          onChange={(event) =>
            setFramework(event.target.value as IRDocument["target_framework"])
          }
          aria-label="代码框架"
        >
          <option value="pytorch">PyTorch 模式</option>
          <option value="paddle">PaddlePaddle 模式</option>
        </select>
        <Icon name="chevron" size={12} className="framework-picker__chevron" />
      </label>

      <div className="toolbar__divider" />

      <div className="project-title">
        <span className="eyebrow">PROJECT</span>
        <input
          value={ir.graph_meta.name}
          onChange={(event) => updateMeta("name", event.target.value)}
          aria-label="项目名称"
        />
      </div>

      <div className="toolbar__status-center">
        <div className={`validation-pill validation-pill--${status.tone}`}>
          <span />
          {status.label}
        </div>
      </div>

      <div className="toolbar__group">
        <button
          className="tool-button tool-button--labeled"
          type="button"
          onClick={() => confirmDiscard() && newDocument()}
          title="新建画布"
        >
          <Icon name="plus" />
          <span className="tool-label">新建</span>
        </button>
        <button
          className="tool-button tool-button--labeled"
          type="button"
          onClick={() => fileInput.current?.click()}
          title="导入 JSON"
        >
          <Icon name="folder" />
          <span className="tool-label">导入 JSON</span>
        </button>
        <button
          className="tool-button tool-button--labeled"
          type="button"
          onClick={saveJson}
          title="保存并导出 JSON"
        >
          <Icon name="save" />
          <span className="tool-label">保存</span>
        </button>
        <button
          className="tool-button tool-button--labeled"
          type="button"
          onClick={saveJson}
          title="导出 JSON"
        >
          <Icon name="download" />
          <span className="tool-label">导出 JSON</span>
        </button>
      </div>

      <select
        className="sample-select"
        value=""
        onChange={(event) => {
          if (event.target.value && confirmDiscard()) {
            void loadSample(event.target.value);
          }
        }}
        aria-label="载入示例"
      >
        <option value="">载入示例</option>
        {samples.map((sample) => (
          <option value={sample.id} key={sample.id}>
            {sample.title}
          </option>
        ))}
      </select>

      <div className="toolbar__group">
        <button
          className="tool-button"
          type="button"
          onClick={undo}
          disabled={undoStack.length === 0}
          title="撤销 Ctrl+Z"
        >
          <Icon name="undo" />
        </button>
        <button
          className="tool-button"
          type="button"
          onClick={redo}
          disabled={redoStack.length === 0}
          title="重做 Ctrl+Shift+Z"
        >
          <Icon name="redo" />
        </button>
        <button className="tool-button" type="button" onClick={applyAutoLayout} title="自动布局">
          <Icon name="layout" />
        </button>
      </div>

      <div className="toolbar__more" aria-label="更多操作">
        <button
          className="tool-button"
          type="button"
          onClick={() => courseInput.current?.click()}
          title="导入 .netbrick 课件"
        >
          <Icon name="upload" />
        </button>
        <button className="tool-button" type="button" onClick={exportCourse} title="导出课件包">
          <Icon name="package" />
        </button>
        <button
          className="tool-button"
          type="button"
          onClick={onOpenPublish}
          title="发布为复合模块"
          disabled={activeView.kind !== "root"}
        >
          <Icon name="layers" />
        </button>
        <button className="tool-button" type="button" onClick={onOpenImport} title="导入 Python">
          <Icon name="python" />
        </button>
        <button
          className="tool-button"
          type="button"
          onClick={() => void validateNow()}
          title="重新校验"
        >
          <Icon name="check" />
        </button>
      </div>

      <button
        className="secondary-action"
        type="button"
        onClick={() => void runTracePreview()}
        disabled={busy}
      >
        <Icon name="play" size={16} />
        结构追踪
      </button>
      <button
        className="primary-action"
        type="button"
        onClick={() => void exportPython()}
        disabled={busy}
      >
        <Icon name="code" size={16} />
        导出代码
      </button>

      <input
        ref={fileInput}
        type="file"
        accept=".json,.netbrick.json,application/json"
        hidden
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file && confirmDiscard()) void openJson(file);
          event.target.value = "";
        }}
      />
      <input
        ref={courseInput}
        type="file"
        accept=".netbrick,application/zip"
        hidden
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file && confirmDiscard()) void importCourse(file);
          event.target.value = "";
        }}
      />
    </header>
  );
}
