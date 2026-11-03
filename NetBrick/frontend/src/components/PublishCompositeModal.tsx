import { useState } from "react";
import { useGraphStore } from "../store";
import { Icon } from "./Icons";

export function PublishCompositeModal({
  onClose,
}: {
  onClose: () => void;
}) {
  const ir = useGraphStore((state) => state.ir);
  const analysis = useGraphStore((state) => state.analysis);
  const publish = useGraphStore(
    (state) => state.publishCurrentComposite,
  );
  const [name, setName] = useState(`${ir.graph_meta.name} Block`);
  const [description, setDescription] = useState(ir.graph_meta.note);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    if (!analysis?.valid) return;
    setBusy(true);
    const resource = await publish(name.trim() || ir.graph_meta.name, description);
    setBusy(false);
    if (resource) onClose();
  };

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="import-modal composite-publish-modal"
        role="dialog"
        aria-modal="true"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="modal-header">
          <div>
            <span className="eyebrow">COMPOSITE RESOURCE</span>
            <h2>发布为复合模块</h2>
          </div>
          <button type="button" className="icon-button" onClick={onClose}>
            <Icon name="close" />
          </button>
        </header>
        <div className="modal-note">
          <Icon name="info" size={16} />
          <span>
            当前完整网络的 Input/Output 会自动成为模块接口，内部全部参数将递归暴露。
          </span>
        </div>
        <div className="publish-form">
          <label className="field">
            <span className="field__label">模块名称</span>
            <input
              className="field-input"
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </label>
          <label className="field">
            <span className="field__label">模块说明</span>
            <textarea
              className="note-input"
              rows={4}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </label>
          <div className="publish-summary">
            <span>{ir.graph.nodes.filter((node) => node.op === "Input").length} 个输入</span>
            <span>{ir.graph.nodes.filter((node) => node.op === "Output").length} 个输出</span>
            <span>版本 v1</span>
          </div>
        </div>
        {!analysis?.valid && (
          <div className="modal-diagnostics">
            <div className="modal-diagnostic">
              <Icon name="warning" size={15} />
              <span>请先修复当前网络的结构错误。</span>
            </div>
          </div>
        )}
        <footer className="modal-footer">
          <button className="text-button" type="button" onClick={onClose}>
            取消
          </button>
          <button
            className="primary-action"
            type="button"
            disabled={busy || !analysis?.valid}
            onClick={() => void submit()}
          >
            <Icon name="package" size={15} />
            {busy ? "发布中…" : "发布 v1"}
          </button>
        </footer>
      </section>
    </div>
  );
}
