# 开发与测试

## 环境

- Python：`deeptracer` conda 环境，Python 3.10。
- 后端已使用 FastAPI、Pydantic、Uvicorn。
- 前端构建使用现有 `geass` 环境中的 Node/npm。
- 不需要安装 PyTorch、Paddle 或 ONNX。

VS Code 默认解释器已指向 `deeptracer`。

## 启动

生产前端：

```bash
cd /home/ricaedo/NetBrick
conda run -n deeptracer python -m backend.app
```

访问 `http://127.0.0.1:8000`。

前后端开发模式：

```bash
conda run -n deeptracer python -m backend.app
```

```bash
cd frontend
PATH=/home/ricaedo/下载/yes/envs/geass/bin:$PATH npm run dev
```

访问 `http://127.0.0.1:5173`。

## 构建

```bash
cd frontend
PATH=/home/ricaedo/下载/yes/envs/geass/bin:$PATH npm run build
```

构建结果写入 `frontend/dist/`。

## 测试

```bash
cd /home/ricaedo/NetBrick
conda run -n deeptracer python -m unittest discover -s tests -v
```

当前测试覆盖：

- PyTorch 2.6 公开模型层静态注册表。
- PyTorch/Paddle 源码语法生成。
- 示例 Shape。
- fan-out。
- 2 路和 3 路合并。
- Concat 维度和 Shape。
- 非法图、空图和 Shape 冲突。
- 受限 Python 导入。
- 课件包。
- If/For/While 生成与签名校验。
- 复合资源发布、内嵌和代码生成。
- 多用户类和控制流 Python 导入。
- 核心 API 函数。

## 扩展算子

新增网络层时需要同步修改：

1. `backend/catalog.py`：算子 ID、分类、参数和框架 API。
2. `backend/inference.py`：纯 Python Shape 规则。
3. `backend/codegen.py`：参数映射和 AST 调用。
4. `frontend/src/apiNames.ts`：需要时补充参数显示名称。
5. `tests/test_netbrick.py`：添加 Shape 和双框架语法测试。

新增合并算子还需要设置：

```python
input_mode="merge"
```

这样前端会使用可连接多条入线的聚合输入端口。

## 已知限制

- 没有定义真实 Tensor 运行时。
- Trace 只展示结构推演，不捕获真实梯度或耗时。
- 支持结构化控制流；不支持环、自由跳转或任意自定义 Python 算子。
- 损失函数和优化器仍是训练阶段占位。
- Python 导入只支持可精确映射的 PyTorch 结构子集。
- ONNX 不包含在当前版本。
- Mojo 存在浏览器本地，不跨浏览器同步。
