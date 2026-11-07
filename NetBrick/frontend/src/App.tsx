import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
} from "react";
import { BlockPalette } from "./components/BlockPalette";
import { BottomPanel } from "./components/BottomPanel";
import { GraphCanvas } from "./components/GraphCanvas";
import { Icon } from "./components/Icons";
import { ImportModal } from "./components/ImportModal";
import { Inspector } from "./components/Inspector";
import { PartnerDock } from "./components/PartnerConsole";
import { PublishCompositeModal } from "./components/PublishCompositeModal";
import { Toolbar } from "./components/Toolbar";
import { useGraphStore } from "./store";

function Toast() {
  const toast = useGraphStore((state) => state.toast);
  const clearToast = useGraphStore((state) => state.clearToast);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(clearToast, 3600);
    return () => window.clearTimeout(timer);
  }, [clearToast, toast]);

  if (!toast) return null;
  return (
    <div className={`toast toast--${toast.kind}`}>
      <span className="toast__icon">
        <Icon
          name={
            toast.kind === "success"
              ? "check"
              : toast.kind === "error"
                ? "warning"
                : "info"
          }
          size={17}
        />
      </span>
      <span>{toast.message}</span>
      <button type="button" onClick={clearToast} aria-label="关闭通知">
        <Icon name="close" size={14} />
      </button>
    </div>
  );
}

export default function App() {
  const initialize = useGraphStore((state) => state.initialize);
  const initialized = useGraphStore((state) => state.initialized);
  const busy = useGraphStore((state) => state.busy);
  const ir = useGraphStore((state) => state.ir);
  const analysis = useGraphStore((state) => state.analysis);
  const validateNow = useGraphStore((state) => state.validateNow);
  const undo = useGraphStore((state) => state.undo);
  const redo = useGraphStore((state) => state.redo);
  const generateCode = useGraphStore((state) => state.generateCode);
  const dirty = useGraphStore((state) => state.dirty);
  const [importOpen, setImportOpen] = useState(false);
  const [publishOpen, setPublishOpen] = useState(false);
  const [leftCollapsed, setLeftCollapsed] = useState(false);
  const [rightCollapsed, setRightCollapsed] = useState(false);
  const [leftWidth, setLeftWidth] = useState(262);
  const [rightWidth, setRightWidth] = useState(326);
  const resizeRef = useRef<{
    side: "left" | "right";
    startX: number;
    startWidth: number;
  } | null>(null);

  const graphSignature = useMemo(() => JSON.stringify(ir.graph), [ir.graph]);

  useEffect(() => {
    void initialize();
  }, [initialize]);

  useEffect(() => {
    if (!initialized) return;
    const timer = window.setTimeout(() => {
      void validateNow();
    }, 520);
    return () => window.clearTimeout(timer);
  }, [graphSignature, initialized, validateNow]);

  useEffect(() => {
    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      if (!dirty) return;
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [dirty]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z") {
        event.preventDefault();
        if (event.shiftKey) redo();
        else undo();
      }
      if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
        event.preventDefault();
        void generateCode();
      }
      if (event.key === "Escape") {
        setImportOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [generateCode, redo, undo]);

  const beginResize = (
    side: "left" | "right",
    event: ReactPointerEvent,
  ) => {
    event.preventDefault();
    resizeRef.current = {
      side,
      startX: event.clientX,
      startWidth: side === "left" ? leftWidth : rightWidth,
    };
    const handleMove = (moveEvent: PointerEvent) => {
      const state = resizeRef.current;
      if (!state) return;
      const delta =
        state.side === "left"
          ? moveEvent.clientX - state.startX
          : state.startX - moveEvent.clientX;
      if (state.side === "left") {
        setLeftWidth(Math.min(390, Math.max(218, state.startWidth + delta)));
      } else {
        setRightWidth(Math.min(440, Math.max(276, state.startWidth + delta)));
      }
    };
    const handleUp = () => {
      resizeRef.current = null;
      window.removeEventListener("pointermove", handleMove);
      window.removeEventListener("pointerup", handleUp);
    };
    window.addEventListener("pointermove", handleMove);
    window.addEventListener("pointerup", handleUp);
  };

  return (
    <div className="app-shell">
      <Toolbar
        onOpenImport={() => setImportOpen(true)}
        onOpenPublish={() => setPublishOpen(true)}
      />
      <main
        className={`workspace ${leftCollapsed ? "workspace--left-collapsed" : ""} ${rightCollapsed ? "workspace--right-collapsed" : ""}`}
        style={{
          gridTemplateColumns: `${leftCollapsed ? 46 : leftWidth}px minmax(0, 1fr) ${rightCollapsed ? 46 : rightWidth}px`,
        }}
      >
        <BlockPalette
          collapsed={leftCollapsed}
          onToggle={() => setLeftCollapsed((value) => !value)}
          onResizeStart={(event) => beginResize("left", event)}
        />
        <section className="studio">
          <div className="studio__topline">
            <div className="studio__crumb">
              <span>工作区</span>
              <Icon name="chevron" size={12} />
              <strong>{ir.graph_meta.name}</strong>
            </div>
            <div className="studio__context">
              <span className={analysis?.valid ? "context-ok" : "context-error"}>
                <span />
                {analysis?.valid ? "结构可用" : "需要检查"}
              </span>
              <span>IR v{ir.ir_version}</span>
              <span>本地模式</span>
            </div>
          </div>
          <GraphCanvas />
          <BottomPanel />
        </section>
        <Inspector
          collapsed={rightCollapsed}
          onToggle={() => setRightCollapsed((value) => !value)}
          onResizeStart={(event) => beginResize("right", event)}
        />
      </main>
      {!initialized && (
        <div className="loading-screen">
          <div className="loading-mark">
            <span />
            <span />
            <span />
          </div>
          <strong>正在铺开模型积木…</strong>
          <span>连接本地 FastAPI 服务</span>
        </div>
      )}
      {busy && initialized && <div className="busy-line" />}
      {importOpen && <ImportModal onClose={() => setImportOpen(false)} />}
      {publishOpen && (
        <PublishCompositeModal onClose={() => setPublishOpen(false)} />
      )}
      <PartnerDock />
      <Toast />
    </div>
  );
}
