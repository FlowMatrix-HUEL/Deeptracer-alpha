import { useState } from "react";
import { api } from "../api";
import { useGraphStore } from "../store";
import type { Diagnostic } from "../types";
import { Icon } from "./Icons";

const EXAMPLE = `import torch.nn as nn

class StudentMLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(784, 128)
        self.act = nn.ReLU()
        self.fc2 = nn.Linear(128, 10)

    def forward(self, x):
        x = self.fc1(x)
        x = self.act(x)
        return self.fc2(x)
`;

export function ImportModal({ onClose }: { onClose: () => void }) {
  const loadDocument = useGraphStore((state) => state.loadDocument);
  const showToast = useGraphStore((state) => state.showToast);
  const [source, setSource] = useState(EXAMPLE);
  const [shape, setShape] = useState("1, 784");
  const [diagnostics, setDiagnostics] = useState<Diagnostic[]>([]);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    const parsedShape = shape
      .split(",")
      .map((value) => Number(value.trim()));
    if (
      parsedShape.length === 0 ||
      parsedShape.some((value) => !Number.isInteger(value) || value <= 0)
    ) {
      setDiagnostics([
        {
          code: "INPUT_SHAPE",
          severity: "error",
          message: "示例形状必须是正整数，例如 1, 784",
          teaching_tip: "",
        },
      ]);
      return;
    }
    setBusy(true);
    setDiagnostics([]);
    try {
      const response = await api.importPytorch(source, parsedShape);
      setDiagnostics(response.diagnostics);
      if (response.ir && response.diagnostics.length === 0) {
        loadDocument(response.ir, "Python 结构已导入画布");
        showToast("success", "已解析顺序 forward 链");
        onClose();
      }
    } catch (error) {
      setDiagnostics([
        {
          code: "IMPORT_FAILED",
          severity: "error",
          message: error instanceof Error ? error.message : "导入失败",
          teaching_tip: "请检查后端服务。",
        },
      ]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="import-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="import-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="modal-header">
          <div>
            <span className="eyebrow">RESTRICTED AST IMPORT</span>
            <h2 id="import-title">导入 PyTorch 模型结构</h2>
          </div>
          <button className="icon-button" type="button" onClick={onClose}>
            <Icon name="close" />
          </button>
        </header>
        <div className="modal-note">
          <Icon name="info" size={16} />
          <span>
            只支持单个 <code>nn.Module</code> 和顺序 <code>forward</code>。
            不执行代码，也不支持分支、循环或自定义算子。
          </span>
        </div>
        <div className="import-grid">
          <label className="field">
            <span className="field__label">Python 源码</span>
            <textarea
              className="source-input"
              value={source}
              onChange={(event) => setSource(event.target.value)}
              spellCheck={false}
            />
          </label>
          <label className="field">
            <span className="field__label">示例输入形状</span>
            <input
              className="field-input mono"
              value={shape}
              onChange={(event) => setShape(event.target.value)}
              placeholder="1, 784"
            />
            <span className="field__hint">
              源码不包含 batch 信息，因此需要手动提供。
            </span>
          </label>
        </div>
        {diagnostics.length > 0 && (
          <div className="modal-diagnostics">
            {diagnostics.map((item, index) => (
              <div className="modal-diagnostic" key={`${item.code}-${index}`}>
                <Icon name="warning" size={15} />
                <span>
                  <strong>{item.message}</strong>
                  {item.field && <code>{item.field}</code>}
                </span>
              </div>
            ))}
          </div>
        )}
        <footer className="modal-footer">
          <button className="text-button" type="button" onClick={onClose}>
            取消
          </button>
          <button
            className="primary-action"
            type="button"
            onClick={() => void submit()}
            disabled={busy}
          >
            <Icon name="python" size={16} />
            {busy ? "解析中…" : "解析并导入"}
          </button>
        </footer>
      </section>
    </div>
  );
}
