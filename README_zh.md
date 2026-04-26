# Deeptracer - 🤖 智能代码分析与重构平台 🚀

[![Python >3.10.9](https://img.shields.io/badge/python-%3E3.10.9-blue.svg)](https://www.python.org/downloads/)
[![Code Analysis](https://img.shields.io/badge/功能-代码分析-blueviolet.svg)](https://github.com/Ricardo-shuo-liu/deeptracer)
[![Performance Analysis](https://img.shields.io/badge/功能-性能分析-green.svg)](https://github.com/Ricardo-shuo-liu/deeptracer)
[![Memory Analysis](https://img.shields.io/badge/功能-内存分析-orange.svg)](https://github.com/Ricardo-shuo-liu/deeptracer)
[![AI Refactoring](https://img.shields.io/badge/功能-智能重构-purple.svg)](https://github.com/Ricardo-shuo-liu/deeptracer)

---

[🌐 切换到英文版本 (Switch to English)](./README.md)

---

## 📋 项目概述

Deeptracer 是一个 🤖 AI驱动的智能代码分析与重构平台，通过深度代码理解、多维度可视化分析和自然语言交互，为开发者提供专业级的代码优化解决方案 🚀。

### 🌟 核心价值

- **🧠 智能分析**：结合本地工具与云端智能体，提供深度代码洞察
- **📊 多维度可视化**：性能、内存、执行流程的直观展示
- **💡 智能重构建议**：AI生成具体可执行的代码优化方案
- **🎨 用户友好界面**：三窗口可调整布局，Git风格diff界面
- **🔒 安全执行环境**：代码沙箱配置，资源限制保护

### 📌 版本规划

- **MVP版本**：聚焦核心分析流程与基础重构功能
- **完整版本**：扩展智能对话、动态更新等高级特性

## ✨ 核心功能

### 1. 🔍 代码分析模块

- **AST结构分析**：解析代码生成抽象语法树，识别代码模式和潜在问题
- **执行流程可视化**：基于Python Tutor的执行轨迹和变量状态变化展示
- **代码质量评估**：识别常见代码问题和优化机会

### 2. ⚡ 性能分析模块

- **使用工具**：Pyinstrument
- **功能**：函数调用时间分析、调用关系可视化、性能瓶颈检测
- **输出**：JSON格式跟踪数据，可交互时间线

### 3. 🧠 内存分析模块

- **使用工具**：Python `tracemalloc`
- **功能**：峰值内存跟踪、分配热点摘要、运行期内存快照
- **输出**：应用内内存卡片与结构化内存摘要

### 4. 🤖 智能重构建议

- **AI驱动**：基于Coze智能体平台的深度代码理解
- **具体可执行**：Git风格diff界面展示修改建议
- **技术解释**：每个建议附带技术原理说明和修改影响评估
- **交互控制**：接受/拒绝单个重构建议，批量应用选中修改

### 5. 🖥️ 可视化界面

- **三窗口布局**：
  - 📈 分析可视化窗口：性能时间线、执行流程、代码结构的多标签视图
  - 💻 代码重构窗口：Git风格diff界面，智能重构建议与交互控制
  - 💬 智能体对话窗口：技术解释与自然语言交互界面
- **交互特性**：自由拖拽调整的窗口分割，响应式布局适配

## 🛠️ 技术栈

### 前端

- React 18 + TypeScript
- Vite（构建工具）
- React Split Panes（窗口布局）
- Monaco Editor（代码编辑器）
- ECharts（图表可视化）
- Tailwind CSS（样式框架）

### 后端

- FastAPI（Web框架）
- Python >3.10.9
- 分析工具：
  - Pyinstrument（性能分析）
  - Python `tracemalloc`（内存分析）
  - Python Tutor（执行可视化）
  - AST模块（代码结构分析）
- AI平台：Coze API集成
- 模板引擎：Jinja2

### 部署

- Docker容器化
- 命令行工具

## 📦 安装与使用

### 环境要求

- Python >3.10.9 (3.10.10+)
- Node.js 16+
- 现代浏览器（Chrome/Firefox/Safari）

### 安装步骤

1. **克隆仓库**

```bash
git clone <repository-url>
cd deeptracer
```

2. **安装Python依赖**

```bash
pip install -e .
```

3. **安装前端依赖**

```bash
npm install
```

### 基本使用

#### 命令行接口

```bash
#配置你的coze key
deeptracer --key yourKeys

# 基础分析命令
deeptracer script.py

# 启用完整AST语法树可视化
deeptracer script.py --all
# 或使用简短形式
deeptracer script.py -a
```

#### 配置说明

- **环境变量**：
  - `COZE_API_TOKEN`：Coze API令牌
  - `COZE_BOT_ID`：Coze机器人ID
  - `COZE_WORKFLOW_ID`：Coze工作流ID

- **配置文件**：
  - `~/.deeptracer/.env.local`：本地配置文件

## 🏗️ 系统架构

### 整体架构

```
🤖 用户命令行输入 → 🚀 分析引擎 → 📊 数据收集 → 💡 智能体处理 → 📋 报告生成 → 🖥️ 浏览器展示
```

### 分层处理管道💫

1. **📊 数据采集层**：并行执行多分析工具（Pyinstrument、`tracemalloc`、Python Tutor、AST解析）
2. **💡 智能分析层**：AI智能体综合解读，识别优化机会
3. **💡 建议生成层**：生成具体代码修改方案
4. **💬 交互响应层**：处理用户反馈与对话请求

### 数据流流程💥

```
📄 原始代码
    → 🚀 并行分析工具执行
    → 📊 统一数据格式
    → 💡 智能体处理
    → 💡 结构化建议
    → 🖥️ 前端动态渲染
    → 💬 用户交互
    → 📋 最终输出
```

## 🔧 工具链说明🧐

| 工具类型 | 使用工具 | 负责功能 |
|---------|----------|----------|
| 性能分析 | Pyinstrument | 函数调用时间分析、性能瓶颈检测 |
| 内存分析 | `tracemalloc` | 峰值内存跟踪、分配热点摘要 |
| 执行可视化 | Python Tutor | 执行流程、变量状态变化 |
| 代码结构分析 | AST模块 | 代码结构解析、抽象语法树生成 |

## 📖 开发指南

### 编码规范🫣

1. **文件编码**：所有文件必须使用UTF-8编码
2. **文件操作**：所有文件的open必须显式标注encoding='utf-8'
3. **Python版本**：统一使用Python >3.10.9开发
4. **函数定义**：使用类型注解和文档字符串

```python
def function(element:int)->int:
    """返回1(说明函数的作用！)"""
    return 1
```

### 贡献流程🤗

1. 提交Issue汇报问题或功能建议
2. Fork仓库并创建特性分支
3. 实现功能并编写测试
4. 提交Pull Request，说明功能变更
5. 代码审查通过后合并

### 测试说明🤤

- **测试框架**：pytest
- **测试目录**：`tests/`目录下按模块组织测试用例

## 🙏 致谢🤗

- [Pyinstrument](https://github.com/joerick/pyinstrument)：性能分析工具🥳
- [Python Tutor](https://github.com/hcientist/OnlinePythonTutor)：执行可视化工具👻
- [cozepy](https://github.com/coze-dev/coze-py)：智能体平台🤖
- [python-dotenv](https://github.com/theskumar/python-dotenv):加载环境变量😤
- [objprint](https://github.com/gaogaotiantian/objprint):打印Python对象以人类可读格式😈
- [tqdm](https://github.com/tqdm/tqdm):进度条😇
- [pyvis](https://github.com/WestHealth/pyvis):可视化网络🧩
- [networkx](https://github.com/networkx/networkx):网络分析🎲
- [fastapi](https://github.com/fastapi/fastapi):后端核心工具🚀
- [uvicorn](https://github.com/Kludex/uvicorn):启动app服务💥
---

## 📞 联系方式

如有问题或建议，欢迎通过Issue或邮件联系我们。

---

**🚀 最重要的是，玩的开心！** 🎉
