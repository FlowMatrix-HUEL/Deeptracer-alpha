# 文件与教学资产

## 工程 JSON

工程文件扩展名为 `.netbrick.json`，主要内容包括：

| 字段 | 内容 |
| --- | --- |
| `ir_version` | 当前为 `0.3`，兼容加载 `0.2` |
| `target_framework` | `pytorch` 或 `paddle` |
| `graph_meta` | 名称、作者、说明和更新时间 |
| `graph.nodes` | 节点、参数和教学批注 |
| `graph.edges` | 端口级有向连线 |
| `ui.positions` | 节点画布坐标 |
| `ui.zoom` | 画布缩放信息 |
| `regions` | 控制流谓词、分支和循环体子图 |
| `resources` | 工程内嵌的固定复合资源版本 |
| `check_info` | 最近一次校验状态缓存 |

加载时会重新检查版本和结构，不信任文件中的 Shape 或校验缓存。

## 复合模块文件

复合资源扩展名为 `.netbrick-module.json`，包含：

- 稳定资源 ID 和整数版本。
- 自动继承的 Input/Output 接口。
- 内部图、控制区域和局部布局。
- 递归参数默认值。
- 内嵌依赖资源版本。

资源库保存在浏览器 IndexedDB，父工程会嵌入实际引用的版本。

## 旧 Mojo

Mojo 是用户打包的复合子模块快照：

- 在画布中按住 Shift 选择至少两个节点。
- 右键选择“打包为 Mojo”。
- Mojo 会出现在左侧“自定义复合 Mojo”分组。
- 可以重复点击或拖入画布。
- 当前存储在浏览器 `localStorage`。
- 内部节点和连线会复制为新 ID，不影响原图。

旧 Mojo 保留为 Legacy 片段入口，不保证有完整 IO，因此不能直接发布为复合资源。

## 课件包

课件扩展名为 `.netbrick`，本质是受控 ZIP：

```text
manifest.json
graph.ir.json
course.json
```

包含：

- 课件名称、作者和格式版本。
- 一份完整 IR。
- 课堂步骤、Markdown 说明和重点节点。
- JSON 文件 SHA-256 校验。

导入时会拒绝路径穿越、未知文件、重复文件、超大包和哈希不一致。

## 内置示例

### MNIST MLP

`Input → Linear → ReLU → Linear → Output`

用于讲解 784 维输入和 10 分类输出。

### CNN 图像分类

`Conv2d → ReLU → MaxPool2d → Flatten → Linear`

用于观察图像 Shape 如何通过卷积和池化变化。

### 简单 U-Net

编码器、下采样、瓶颈层、上采样和解码器组成的简化结构，用于展示空间分辨率恢复。

### 多输入多输出

展示两条独立数据流，以及单个 Python 文件中的多参数 `forward` 和多返回值。

### 并行分支 Add 汇合

单个 Input fan-out 到两条全连接分支，再通过一个 `Add` 输入端口汇合，最终连接 Output。

## 保存与恢复

- 画布布局保存在 IR 的 `ui.positions`。
- 浏览器不会自动上传工程。
- 关闭包含未保存修改的页面时，浏览器会提示确认。
- 不使用数据库，不提供云端同步。
