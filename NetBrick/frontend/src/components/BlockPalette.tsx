import {
  useMemo,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
} from "react";
import { apiPresentation, plannedApiPresentation } from "../apiNames";
import { useGraphStore } from "../store";
import type {
  BlockSpec,
  CompositeResource,
  Framework,
  MojoAsset,
} from "../types";
import { Icon } from "./Icons";

interface BlockPaletteProps {
  collapsed: boolean;
  onToggle: () => void;
  onResizeStart: (event: ReactPointerEvent) => void;
}

const CATEGORY_ORDER = [
  "输入输出",
  "基础层",
  "卷积与池化",
  "激活函数",
  "归一化",
  "张量与嵌入",
  "合并运算",
  "条件运算",
  "控制流",
  "Padding",
  "序列与注意力",
  "其他模型层",
];

const CATEGORY_LABELS: Record<string, string> = {
  输入输出: "输入输出",
  基础层: "基础层",
  卷积与池化: "卷积池化",
  激活函数: "激活函数",
  归一化: "归一化",
  张量与嵌入: "张量重排",
  合并运算: "合并运算",
  条件运算: "条件运算",
  控制流: "控制流",
  Padding: "Padding",
  序列与注意力: "序列与注意力",
  其他模型层: "其他模型层",
  损失函数: "损失函数",
  优化器: "优化器",
  自定义复合Mojo: "自定义复合 Mojo",
};

const PLANNED_GROUPS = {
  损失函数: [
    { label: "交叉熵损失", op: "CrossEntropyLoss" },
    { label: "均方误差", op: "MSELoss" },
  ],
  优化器: [
    { label: "随机梯度下降", op: "SGD" },
    { label: "Adam", op: "Adam" },
  ],
};

function BlockCard({
  block,
  framework,
}: {
  block: BlockSpec;
  framework: Framework;
}) {
  const addNode = useGraphStore((state) => state.addNode);
  const count = useGraphStore((state) => state.ir.graph.nodes.length);
  const api = apiPresentation(block, framework);
  const unavailable = framework === "paddle" && block.pytorch_only;

  const quickAdd = () => {
    const column = count % 4;
    const row = Math.floor(count / 4) % 5;
    addNode(block.op, { x: 120 + column * 280, y: 100 + row * 132 });
  };

  return (
    <button
      className={`module-row ${block.system ? "module-row--boundary" : ""} ${unavailable ? "module-row--unavailable" : ""}`}
      draggable={!unavailable}
      onDragStart={(event) => {
        event.dataTransfer.setData("application/netbrick-block", block.op);
        event.dataTransfer.effectAllowed = "copy";
      }}
      onClick={() => {
        if (!unavailable) quickAdd();
      }}
      title={
        unavailable
          ? `${block.description} 当前为 PyTorch Only`
          : `${block.description} 点击或拖入画布`
      }
      type="button"
    >
      <span className="module-row__copy">
        <span className="module-row__title">{api.className}</span>
        <span className="module-row__api">{api.path}</span>
      </span>
      {block.system && <span className="module-row__tag">边界</span>}
      {block.pytorch_only && (
        <span className="module-row__tag">PyTorch Only</span>
      )}
    </button>
  );
}

function MojoCard({ asset }: { asset: MojoAsset }) {
  const addMojo = useGraphStore((state) => state.addMojo);
  const nodeCount = useGraphStore((state) => state.ir.graph.nodes.length);
  return (
    <button
      className="module-row module-row--mojo"
      draggable
      onDragStart={(event) => {
        event.dataTransfer.setData("application/netbrick-mojo", asset.id);
        event.dataTransfer.effectAllowed = "copy";
      }}
      onClick={() =>
        addMojo(asset.id, {
          x: 130 + (nodeCount % 3) * 280,
          y: 150 + (Math.floor(nodeCount / 3) % 3) * 140,
        })
      }
      title="拖入或点击复用打包的复合子模块"
      type="button"
    >
      <span className="module-row__copy">
        <span className="module-row__title">{asset.name}</span>
        <span className="module-row__api">
          {asset.nodes.length} 节点 · {asset.edges.length} 连线
        </span>
      </span>
      <span className="module-row__tag">MOJO</span>
    </button>
  );
}

function PlannedCard({
  label,
  op,
  framework,
}: {
  label: string;
  op: string;
  framework: Framework;
}) {
  const api = plannedApiPresentation(op, framework);
  return (
    <div
      className="module-row module-row--planned"
      title={`${label}，训练配置不进入当前推理数据流`}
    >
      <span className="module-row__copy">
        <span className="module-row__title">{api.className}</span>
        <span className="module-row__api">{api.path}</span>
      </span>
      <span className="module-row__tag">训练阶段</span>
    </div>
  );
}

function CompositeResourceCard({
  resource,
}: {
  resource: CompositeResource;
}) {
  const addComposite = useGraphStore((state) => state.addComposite);
  const deleteCompositeResource = useGraphStore(
    (state) => state.deleteCompositeResource,
  );
  const count = useGraphStore((state) => state.ir.graph.nodes.length);
  return (
    <div
      className="module-row module-row--composite"
      draggable
      role="button"
      tabIndex={0}
      onDragStart={(event) => {
        event.dataTransfer.setData(
          "application/netbrick-composite",
          JSON.stringify({
            resourceId: resource.resource_id,
            revision: resource.revision,
          }),
        );
        event.dataTransfer.effectAllowed = "copy";
      }}
      onClick={() =>
        addComposite(resource.resource_id, resource.revision, {
          x: 130 + (count % 3) * 280,
          y: 150 + (Math.floor(count / 3) % 3) * 140,
        })
      }
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          addComposite(resource.resource_id, resource.revision, {
            x: 130 + (count % 3) * 280,
            y: 150 + (Math.floor(count / 3) % 3) * 140,
          });
        }
      }}
      title={`${resource.description || resource.name}，双击画布节点可查看内部结构`}
    >
      <span className="module-row__copy">
        <span className="module-row__title">{resource.name}</span>
        <span className="module-row__api">
          {resource.inputs.length} 输入 · {resource.outputs.length} 输出 ·{" "}
          {resource.graph.nodes.length} 节点
        </span>
      </span>
      <span className="module-row__tag">v{resource.revision}</span>
      <button
        type="button"
        className="module-row__export"
        title="导出复合模块文件"
        onClick={(event) => {
          event.stopPropagation();
          const blob = new Blob(
            [JSON.stringify(resource, null, 2)],
            { type: "application/json" },
          );
          const url = URL.createObjectURL(blob);
          const anchor = document.createElement("a");
          anchor.href = url;
          anchor.download = `${resource.name}_v${resource.revision}.netbrick-module.json`;
          anchor.click();
          URL.revokeObjectURL(url);
        }}
      >
        <Icon name="download" size={13} />
      </button>
      <button
        type="button"
        className="module-row__delete"
        title="从复合模块库删除"
        onClick={(event) => {
          event.stopPropagation();
          if (
            window.confirm(
              `确定从复合模块库删除“${resource.name}”的所有版本吗？已有工程内嵌的版本不会丢失。`,
            )
          ) {
            void deleteCompositeResource(resource.resource_id);
          }
        }}
      >
        <Icon name="trash" size={13} />
      </button>
    </div>
  );
}

export function BlockPalette({
  collapsed,
  onToggle,
  onResizeStart,
}: BlockPaletteProps) {
  const blocks = useGraphStore((state) => state.catalog);
  const mojos = useGraphStore((state) => state.mojos);
  const resources = useGraphStore((state) => state.resources);
  const framework = useGraphStore((state) => state.ir.target_framework);
  const importCompositeResource = useGraphStore(
    (state) => state.importCompositeResource,
  );
  const showToast = useGraphStore((state) => state.showToast);
  const [query, setQuery] = useState("");
  const [folded, setFolded] = useState<Set<string>>(new Set());
  const resourceInputRef = useRef<HTMLInputElement>(null);

  const needle = query.trim().toLowerCase();
  const grouped = useMemo(
    () =>
      CATEGORY_ORDER.map((category) => ({
        category,
        items: blocks.filter(
          (block) =>
            block.category === category &&
            (() => {
              const api = apiPresentation(block, framework);
              return (
                !needle ||
                block.label.toLowerCase().includes(needle) ||
                block.op.toLowerCase().includes(needle) ||
                api.className.toLowerCase().includes(needle) ||
                api.path.toLowerCase().includes(needle)
              );
            })(),
        ),
      })).filter((group) => group.items.length > 0),
    [blocks, framework, needle],
  );
  const planned = useMemo(
    () =>
      Object.entries(PLANNED_GROUPS)
        .map(([category, items]) => ({
          category,
          items: items.filter(
            (item) => {
              const api = plannedApiPresentation(item.op, framework);
              return (
                !needle ||
                item.label.toLowerCase().includes(needle) ||
                item.op.toLowerCase().includes(needle) ||
                api.className.toLowerCase().includes(needle) ||
                api.path.toLowerCase().includes(needle)
              );
            },
          ),
        }))
        .filter((group) => group.items.length > 0),
    [framework, needle],
  );
  const filteredMojos = useMemo(
    () =>
      mojos.filter(
        (asset) =>
          !needle ||
          asset.name.toLowerCase().includes(needle) ||
          asset.nodes.some((node) => node.op.toLowerCase().includes(needle)),
      ),
    [mojos, needle],
  );
  const latestResources = useMemo(() => {
    const latest = new Map<string, CompositeResource>();
    for (const resource of resources) {
      const current = latest.get(resource.resource_id);
      if (!current || resource.revision > current.revision) {
        latest.set(resource.resource_id, resource);
      }
    }
    return [...latest.values()].filter(
      (resource) =>
        !needle ||
        resource.name.toLowerCase().includes(needle) ||
        resource.description.toLowerCase().includes(needle),
    );
  }, [needle, resources]);

  const toggle = (category: string) => {
    setFolded((current) => {
      const next = new Set(current);
      if (next.has(category)) next.delete(category);
      else next.add(category);
      return next;
    });
  };

  const groupHeader = (category: string, count: number) => (
    <button
      type="button"
      className="block-group__header"
      onClick={() => toggle(category)}
    >
      <span>{CATEGORY_LABELS[category] ?? category}</span>
      <span className="block-group__meta">
        {count}
        <Icon
          name="chevron"
          size={14}
          className={folded.has(category) ? "chevron chevron--closed" : "chevron"}
        />
      </span>
    </button>
  );

  if (collapsed) {
    return (
      <aside className="palette palette--collapsed">
        <button
          type="button"
          className="rail-button rail-button--active"
          onClick={onToggle}
          title="展开模块库"
        >
          <Icon name="layers" size={18} />
        </button>
        <span className="rail-label">MODULES</span>
        <button type="button" className="rail-button" title="搜索模块">
          <Icon name="search" size={17} />
        </button>
        <button type="button" className="rail-button" title="复合 Mojo">
          <Icon name="package" size={17} />
        </button>
        <span className="rail-spacer" />
        <button type="button" className="rail-button" onClick={onToggle}>
          <Icon name="chevron" size={15} className="chevron--right" />
        </button>
      </aside>
    );
  }

  return (
    <aside className="palette">
      <div
        className="panel-resize-handle panel-resize-handle--right"
        onPointerDown={onResizeStart}
        title="拖拽调整模块库宽度"
      />
      <div className="palette__heading">
        <div>
          <span className="eyebrow">MODULE LIBRARY</span>
          <h2>模块积木</h2>
        </div>
        <div className="palette__heading-actions">
          <span className="count-pill">{blocks.length}</span>
          <button
            type="button"
            className="icon-button"
            onClick={onToggle}
            title="收起模块库"
          >
            <Icon name="chevron" size={15} className="chevron--left" />
          </button>
        </div>
      </div>
      <label className="search-box">
        <Icon name="search" size={16} />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="搜索层、算子…"
          aria-label="搜索算子"
        />
        {query && (
          <button
            className="icon-button icon-button--tiny"
            onClick={() => setQuery("")}
            type="button"
            aria-label="清空搜索"
          >
            <Icon name="close" size={13} />
          </button>
        )}
      </label>
      <p className="palette__hint">
        拖入画布，所有连线表示 Tensor 前向数据流
      </p>
      <div className="palette__scroll">
        {grouped.map(({ category, items }) => (
          <section className="block-group" key={category}>
            {groupHeader(category, items.length)}
            {!folded.has(category) && (
              <div className="block-group__items">
                {items.map((block) => (
                  <BlockCard
                    block={block}
                    framework={framework}
                    key={block.op}
                  />
                ))}
              </div>
            )}
          </section>
        ))}
        {planned.map(({ category, items }) => (
          <section className="block-group" key={category}>
            {groupHeader(category, items.length)}
            {!folded.has(category) && (
              <div className="block-group__items">
                {items.map((item) => (
                  <PlannedCard
                    key={item.op}
                    label={item.label}
                    op={item.op}
                    framework={framework}
                  />
                ))}
              </div>
            )}
          </section>
        ))}
        {(!needle || "自定义复合mojo".includes(needle)) && (
          <section className="block-group">
            {groupHeader("自定义复合Mojo", filteredMojos.length)}
            {!folded.has("自定义复合Mojo") && (
              <div className="block-group__items">
                {filteredMojos.map((asset) => (
                  <MojoCard asset={asset} key={asset.id} />
                ))}
                {filteredMojos.length === 0 && (
                  <div className="mojo-empty">
                    在画布中多选节点，右键打包为 Mojo
                  </div>
                )}
              </div>
            )}
          </section>
        )}
        {(!needle || "复合模型".includes(needle)) && (
          <section className="block-group">
            {groupHeader("复合模型", latestResources.length)}
            {!folded.has("复合模型") && (
              <div className="block-group__items">
                {latestResources.map((resource) => (
                  <CompositeResourceCard
                    key={resource.resource_id}
                    resource={resource}
                  />
                ))}
                {latestResources.length === 0 && (
                  <div className="mojo-empty">
                    发布当前网络后，会以带版本的小网络模块出现在这里
                  </div>
                )}
                <button
                  type="button"
                  className="resource-import-row"
                  onClick={() => resourceInputRef.current?.click()}
                >
                  <Icon name="upload" size={13} />
                  导入 .netbrick-module.json
                </button>
              </div>
            )}
          </section>
        )}
        {grouped.length === 0 &&
          planned.length === 0 &&
          filteredMojos.length === 0 &&
          latestResources.length === 0 && (
            <div className="empty-inline">
              <Icon name="search" />
              <span>没有匹配的模块</span>
            </div>
          )}
      </div>
      <div className="palette__footer">
        <span>Python 结构模式，不执行张量运算</span>
      </div>
      <input
        ref={resourceInputRef}
        type="file"
        accept=".json,.netbrick-module.json,application/json"
        hidden
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (!file) return;
          void file
            .text()
            .then(async (text) => {
              await importCompositeResource(
                JSON.parse(text) as CompositeResource,
              );
            })
            .catch(() =>
              showToast("error", "复合模块文件解析失败"),
            );
          event.target.value = "";
        }}
      />
    </aside>
  );
}
