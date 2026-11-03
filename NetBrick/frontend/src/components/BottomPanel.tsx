import {
  useEffect,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
} from "react";
import { useGraphStore } from "../store";
import { savePythonFile } from "../saveFile";
import type { BottomPanel as BottomPanelName, Diagnostic } from "../types";
import { Icon } from "./Icons";

function DiagnosticRow({ item }: { item: Diagnostic }) {
  const setSelectedNode = useGraphStore((state) => state.setSelectedNode);
  return (
    <button
      type="button"
      className={`diagnostic-row diagnostic-row--${item.severity}`}
      onClick={() => item.node_id && setSelectedNode(item.node_id)}
    >
      <span className="diagnostic-row__icon">
        <Icon
          name={item.severity === "error" ? "warning" : "info"}
          size={16}
        />
      </span>
      <span className="diagnostic-row__copy">
        <span className="diagnostic-row__title">
          <code>{item.code}</code>
          <strong>{item.message}</strong>
        </span>
        {item.teaching_tip && <span>{item.teaching_tip}</span>}
      </span>
      {item.node_id && <span className="diagnostic-row__node">{item.node_id}</span>}
    </button>
  );
}

function DiagnosticsView() {
  const analysis = useGraphStore((state) => state.analysis);
  const diagnostics = analysis?.diagnostics ?? [];
  if (diagnostics.length === 0) {
    return (
      <div className="panel-empty panel-empty--success">
        <span className="success-orbit">
          <Icon name="check" size={24} />
        </span>
        <div>
          <strong>结构检查通过</strong>
          <p>
            {analysis?.chain_count ?? 0} 条独立数据链均能到达 Output，
            shape 模拟没有发现冲突。
          </p>
        </div>
      </div>
    );
  }
  return (
    <div className="diagnostic-list">
      {diagnostics.map((item, index) => (
        <DiagnosticRow item={item} key={`${item.code}-${index}`} />
      ))}
    </div>
  );
}

function CodeView() {
  const ir = useGraphStore((state) => state.ir);
  const analysis = useGraphStore((state) => state.analysis);
  const code = useGraphStore((state) => state.code);
  const generateCode = useGraphStore((state) => state.generateCode);
  const showToast = useGraphStore((state) => state.showToast);
  const requestedRef = useRef("");
  const sourceSignature = JSON.stringify({
    framework: ir.target_framework,
    graph: ir.graph,
  });

  useEffect(() => {
    if (code || !analysis?.valid || requestedRef.current === sourceSignature) {
      return;
    }
    requestedRef.current = sourceSignature;
    void generateCode();
  }, [analysis?.valid, code, generateCode, sourceSignature]);

  if (!code) {
    return (
      <div className="panel-empty">
        <span className="empty-block-icon">
          <Icon name="code" size={25} />
        </span>
        <div>
          <strong>生成可编辑的模型结构文件</strong>
          <p>
            {analysis?.valid
              ? `正在同步 ${ir.target_framework === "paddle" ? "Paddle" : "PyTorch"} 源码…`
              : "请先修复问题面板中的结构错误，再生成 Python 源码。"}
          </p>
          {analysis?.valid && (
            <button
              className="small-primary"
              type="button"
              onClick={() => void generateCode()}
            >
              <Icon name="spark" size={15} />
              重新生成
            </button>
          )}
        </div>
      </div>
    );
  }
  const keywordPattern =
    /(#[^\n]*|\b(?:import|from|as|class|def|return|if|else|elif|for|while|in|not|and|or|None|True|False)\b|\b(?:torch|nn|paddle|self|super)\b|(?:"[^"]*"|'[^']*')|\b\d+(?:\.\d+)?\b)/g;
  const keywords = new Set([
    "import",
    "from",
    "as",
    "class",
    "def",
    "return",
    "if",
    "else",
    "elif",
    "for",
    "while",
    "in",
    "not",
    "and",
    "or",
    "None",
    "True",
    "False",
  ]);
  const modules = new Set(["torch", "nn", "paddle", "self", "super"]);
  return (
    <div className="code-view">
      <div className="code-view__toolbar">
        <div>
          <span className="file-dot" />
          <strong>{code.filename}</strong>
          <span className="syntax-ok">
            <Icon name="check" size={13} />
            AST 语法通过
          </span>
        </div>
        <div className="inline-actions">
          <button
            type="button"
            className="small-ghost"
            onClick={() => {
              void navigator.clipboard
                .writeText(code.source)
                .then(() => showToast("success", "源码已复制"));
            }}
          >
            <Icon name="copy" size={14} />
            复制
          </button>
          <button
            type="button"
            className="small-ghost"
            onClick={() => {
              void savePythonFile(code.filename, code.source).then(
                (result) => {
                  if (result === "saved") {
                    showToast(
                      "success",
                      "Python 文件已保存到所选位置",
                    );
                  } else if (result === "downloaded") {
                    showToast(
                      "info",
                      "当前浏览器不支持另存为选择器，已使用默认下载目录",
                    );
                  }
                },
              );
            }}
          >
            <Icon name="download" size={14} />
            下载 .py
          </button>
        </div>
      </div>
      <pre className="code-block">
        <code>
          {code.source.split("\n").map((line, lineIndex) => (
            <span className="code-line" key={`${lineIndex}-${line.slice(0, 8)}`}>
              <span className="code-line__number">
                {String(lineIndex + 1).padStart(2, "0")}
              </span>
              <span className="code-line__source">
                {line.split(keywordPattern).map((token, tokenIndex) => {
                  let className = "";
                  if (token.startsWith("#")) className = "tok-comment";
                  else if (/^["']/.test(token)) className = "tok-string";
                  else if (keywords.has(token)) className = "tok-keyword";
                  else if (modules.has(token)) className = "tok-module";
                  else if (/^\d/.test(token)) className = "tok-number";
                  return (
                    <span className={className} key={`${tokenIndex}-${token}`}>
                      {token}
                    </span>
                  );
                })}
              </span>
            </span>
          ))}
        </code>
      </pre>
    </div>
  );
}

function TraceView() {
  const trace = useGraphStore((state) => state.trace);
  const runTracePreview = useGraphStore((state) => state.runTracePreview);
  const setSelectedNode = useGraphStore((state) => state.setSelectedNode);
  if (!trace) {
    return (
      <div className="panel-empty">
        <span className="empty-block-icon empty-block-icon--trace">
          <Icon name="play" size={23} />
        </span>
        <div>
          <strong>逐步查看张量如何流过模型</strong>
          <p>
            此模式仅按结构规则计算 shape，不会创建张量或执行
            PyTorch/Paddle 运算。
          </p>
          <button
            className="small-primary"
            type="button"
            onClick={() => void runTracePreview()}
          >
            <Icon name="play" size={14} />
            开始结构追踪
          </button>
        </div>
      </div>
    );
  }
  return (
    <div className="trace-view">
      <div className="trace-banner">
        <Icon name="info" size={15} />
        {trace.message}
      </div>
      <div className="trace-steps">
        {trace.steps.map((step) => (
          (() => {
            const inputLabel =
              step.input_shapes && step.input_shapes.length > 1
                ? step.input_shapes
                    .map((shape) => `[${shape.join(", ")}]`)
                    .join(" + ")
                : step.input_shape
                  ? `[${step.input_shape.join(", ")}]`
                  : "边界";
            return (
              <button
                type="button"
                className="trace-step"
                key={`${step.node_id}-${step.index}`}
                onClick={() => setSelectedNode(step.node_id)}
              >
                <span className="trace-step__index">
                  {String(step.index + 1).padStart(2, "0")}
                </span>
                <span className="trace-step__body">
                  <strong>{step.label}</strong>
                  <span>
                    {inputLabel}
                    <Icon name="chevron" size={12} />
                    {step.output_shape
                      ? `[${step.output_shape.join(", ")}]`
                      : "—"}
                  </span>
                </span>
                <code>{step.dtype ?? "—"}</code>
              </button>
            );
          })()
        ))}
      </div>
    </div>
  );
}

const TABS: Array<{
  id: BottomPanelName;
  label: string;
  icon: "warning" | "code" | "play";
}> = [
  { id: "diagnostics", label: "问题", icon: "warning" },
  { id: "code", label: "Python", icon: "code" },
  { id: "trace", label: "结构追踪", icon: "play" },
];

export function BottomPanel() {
  const panel = useGraphStore((state) => state.bottomPanel);
  const setPanel = useGraphStore((state) => state.setBottomPanel);
  const analysis = useGraphStore((state) => state.analysis);
  const [height, setHeight] = useState(266);
  const errorCount =
    analysis?.diagnostics.filter((item) => item.severity === "error").length ??
    0;

  if (!panel) {
    return (
      <button
        type="button"
        className="panel-reopen"
        onClick={() => setPanel("diagnostics")}
      >
        <Icon name="chevron" size={14} />
        打开检查面板
      </button>
    );
  }

  const startResize = (event: ReactPointerEvent) => {
    event.preventDefault();
    const startY = event.clientY;
    const startHeight = height;
    const handleMove = (moveEvent: PointerEvent) => {
      const maxHeight = Math.max(220, window.innerHeight - 230);
      setHeight(
        Math.min(
          maxHeight,
          Math.max(150, startHeight + (startY - moveEvent.clientY)),
        ),
      );
    };
    const handleUp = () => {
      window.removeEventListener("pointermove", handleMove);
      window.removeEventListener("pointerup", handleUp);
    };
    window.addEventListener("pointermove", handleMove);
    window.addEventListener("pointerup", handleUp);
  };

  return (
    <section
      className="bottom-panel"
      style={{ height, flexBasis: height }}
    >
      <div
        className="bottom-panel__resizer"
        onPointerDown={startResize}
        title="上下拖拽调整面板高度"
      >
        <span />
      </div>
      <div className="bottom-panel__tabs">
        {TABS.map((tab) => (
          <button
            type="button"
            key={tab.id}
            className={panel === tab.id ? "active" : ""}
            onClick={() => setPanel(tab.id)}
          >
            <Icon name={tab.icon} size={15} />
            {tab.label}
            {tab.id === "diagnostics" && errorCount > 0 && (
              <span className="tab-count">{errorCount}</span>
            )}
          </button>
        ))}
        <span className="bottom-panel__spacer" />
        <span className="bottom-panel__mode">PYTHON STRUCTURE MODE</span>
        <button
          className="icon-button"
          type="button"
          onClick={() => setPanel(null)}
          aria-label="收起面板"
        >
          <Icon name="close" size={15} />
        </button>
      </div>
      <div className="bottom-panel__content">
        {panel === "diagnostics" && <DiagnosticsView />}
        {panel === "code" && <CodeView />}
        {panel === "trace" && <TraceView />}
      </div>
    </section>
  );
}
