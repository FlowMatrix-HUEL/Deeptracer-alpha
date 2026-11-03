# NetBrick

NetBrick 是面向深度学习入门课堂的可视化神经网络搭建工具。它通过拖拽节点、并行分支和 Shape 推演，帮助学生理解张量如何在网络结构中流动，并生成可继续阅读和修改的 PyTorch/Paddle Python 代码。

## 基本功能

- 使用 React Flow 搭建多输入、多输出、可 fan-out 的无环网络。
- 覆盖 PyTorch 2.6 的 129 个公开模型层相关 API，并保留 Paddle 有明确等价实现的模块。
- 支持 `Add`、`Multiply`、`Concat` 多路汇合，以及结构化 `If`、`For`、`While` 控制流。
- 实时检查 Shape、数据类型、端口连接和网络完整性。
- 同一张图可切换 PyTorch/Paddle，并按照当前框架官方 API 生成代码。
- 支持版本化复合资源、内部结构下钻、本地 JSON、课件包和结构追踪。
- 仅做结构推演，不安装或执行 PyTorch/Paddle，不进行真实训练。

## 快速使用

环境：Python 使用 `deeptracer` conda 环境；如需重新构建前端，使用现有 `geass` 环境中的 Node。

```bash
cd /home/ricaedo/NetBrick
conda run -n deeptracer python -m backend.app
```

打开 <http://127.0.0.1:8000>。

开发模式：

```bash
# 后端
conda run -n deeptracer python -m backend.app

# 前端
cd frontend
PATH=/home/ricaedo/下载/yes/envs/geass/bin:$PATH npm run dev
```

开发前端访问 <http://127.0.0.1:5173>。

## 文档

完整能力说明、数据结构、算子清单、代码生成、文件格式和 API 文档见：

[NetBrick 文档索引](doc/README.md)
