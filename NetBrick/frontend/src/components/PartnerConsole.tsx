import { useEffect, useRef } from "react";
import { useGraphStore } from "../store";

interface PartnerTarget {
  nodeId?: string | null;
  stepIndex?: number | null;
  line?: number | null;
}

interface PartnerDockHandle {
  element: HTMLElement;
  open: () => void;
  close: () => void;
  focus: () => void;
}

declare global {
  interface Window {
    createPartnerDock?: (
      mount: HTMLElement,
      options: {
        workbench: string;
        getContext: () => Record<string, unknown>;
        onHighlight?: (target: PartnerTarget) => void;
        onJump?: (target: PartnerTarget) => void;
        onInsert?: (proposal: Record<string, unknown>) => boolean | void;
        onRun?: (action: Record<string, unknown>) => unknown;
        onDone?: () => void;
      },
    ) => PartnerDockHandle;
    __netbrickPartnerDock?: PartnerDockHandle;
  }
}

function ensurePartnerAssets(): HTMLScriptElement {
  if (!document.querySelector('link[data-partner-console="1"]')) {
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "/static/partner.css";
    link.dataset.partnerConsole = "1";
    document.head.appendChild(link);
  }
  const existing = document.querySelector(
    'script[data-partner-console="1"]',
  ) as HTMLScriptElement | null;
  if (existing) return existing;
  const script = document.createElement("script");
  script.src = "/static/partner.js";
  script.dataset.partnerConsole = "1";
  document.body.appendChild(script);
  return script;
}

function selectPartnerTarget(target: PartnerTarget | undefined) {
  if (!target) return;
  const state = useGraphStore.getState();
  if (target.nodeId) {
    state.setSelectedNode(String(target.nodeId));
    return;
  }
  if (target.stepIndex != null) {
    const step = state.trace?.steps?.[Number(target.stepIndex)];
    if (step?.node_id) {
      state.setSelectedNode(step.node_id);
    }
  }
}

function buildNetBrickContext() {
  const state = useGraphStore.getState();
  const ir = state.ir;
  return {
    graph: {
      meta: ir.graph_meta,
      nodes: ir.graph.nodes.slice(0, 80).map((node) => ({
        id: node.id,
        op: node.op,
        params: node.params,
        teaching_note: node.teaching_note,
      })),
      edges: ir.graph.edges,
    },
    trace: state.trace ? { steps: state.trace.steps.slice(0, 80) } : {},
    diagnostics: state.analysis?.diagnostics || [],
  };
}

export function PartnerDock() {
  const mountRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    const existing = window.__netbrickPartnerDock;
    if (existing) {
      mount.appendChild(existing.element);
      return;
    }

    let cancelled = false;
    const init = () => {
      if (cancelled || !mountRef.current || !window.createPartnerDock) {
        return;
      }
      const instance = window.createPartnerDock(mountRef.current, {
        workbench: "netbrick",
        getContext: buildNetBrickContext,
        onHighlight: selectPartnerTarget,
        onJump: selectPartnerTarget,
      });
      window.__netbrickPartnerDock = instance;
    };

    if (window.createPartnerDock) {
      init();
      return () => {
        cancelled = true;
      };
    }

    const script = ensurePartnerAssets();
    if (window.createPartnerDock) {
      init();
    } else {
      script.addEventListener("load", init);
    }
    return () => {
      cancelled = true;
      script.removeEventListener("load", init);
    };
  }, []);

  return <div className="netbrick-partner-dock-host" ref={mountRef} />;
}
