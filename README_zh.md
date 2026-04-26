# DeepTracer
[🌐 切换到英文版本 (Switch to English)](./README.md)
---

DeepTracer 是一个面向 Python 代码理解、运行观察和改进建议的代码分析工具，核心提供本地 Web 工作台，支持通过直观的可视化界面完成 Python 代码的结构、性能分析及优化建议生成，适用于代码学习、教学演示、轻量级代码诊断等场景。
**重要说明**：当前工具核心运行入口为 `deeptracer-web` 命令，`deeptracer` 命令虽保留但为残余功能，具体实现不完善，不推荐使用。
## 📋 核心功能
DeepTracer 专注于将 Python 代码转化为可阅读、可定位、可讨论的分析结果，核心能力如下：
- 代码载入：支持本地 .py 文件选择、拖拽上传，或直接粘贴代码、载入内置示例
- 多维度分析：基于本地工具完成 AST 结构分析、性能分析（pyinstrument）
- 可视化展示：提供 AST 语法树、性能火焰图可视化，以及 Python Tutor 代码执行流程可视化
- 优化建议：生成带优先级、风险提示、代码锚点及修改预览的可操作建议
- 开放式答疑：围绕当前代码和分析结果进行流式问答，支持 Markdown 渲染
- 模型增强（可选）：配置 OpenAI 兼容模型后，可获得更自然的多智能体分析解释
## 🎯 目标用户
- Python 初学者：快速理解代码结构、函数职责及重点关注内容
- 教学者/助教：直观展示代码运行行为、结构逻辑及优化方向
- 开发者：对单个 Python 文件/代码片段进行快速轻量级诊断
- 项目分析人员：理解工具输入输出、功能边界及核心能力
## 🚀 快速开始（仅支持 Windows + Conda 环境）
### 1. 环境准备
在项目根目录打开 Anaconda Prompt 或 PowerShell，执行以下命令配置环境：
```powershell
# 创建并激活虚拟环境
conda create -n deeptracer python=3.11 -y
conda activate deeptracer
# 升级 pip 并安装项目
python -m pip install --upgrade pip
pip install -e .
```
### 2. 启动 Web 工作台（核心命令）
环境安装完成后，直接执行核心命令启动本地 Web 服务：
```powershell
deeptracer-web
```
服务启动后，浏览器自动打开（或手动访问）：
```text
http://127.0.0.1:8000
```
### 3. 基础使用流程
1. 打开 Web 页面后，通过「粘贴代码」「上传 .py 文件」或「载入示例」输入 Python 代码
2. 点击「分析代码」，系统自动执行 LangGraph 分析流水线，生成分析结果
3. 查看分析结果：先通过「概览」了解代码整体情况，再切换「结构/性能」标签查看详情
4. 查看优化建议及修改预览，可通过右侧「执行流程」可视化观察代码运行过程
5. （可选）在答疑区域围绕当前代码继续提问，获取针对性解答
## ⚙️ 可选配置：模型增强（OpenAI 兼容）
未配置模型 API 时，工具会自动回退到「本地分析 + 规则化建议」模式，完全不影响基础使用；配置模型后，可获得更自然的多智能体分析解释。需注意：环境变量无需手动设置，需配置在指定本地文件中，且当前仅支持 Windows 系统运行。
### 配置步骤（无需手动设置环境变量）
```powershell
# 1. 新建/编辑本地配置文件（路径固定）
~/.deeptracer/.env.local
# 2. 在文件中添加以下配置（根据需求调整）
# OpenAI 官方接口配置
OPENAI_API_KEY="你的 API Key"
OPENAI_MODEL="gpt-4.1-mini"
# 若使用第三方 OpenAI 兼容网关，额外添加
OPENAI_BASE_URL="https://你的接口地址/v1"
# 可选配置（按需添加）
DEEPTRACER_MODEL_NAME="自定义模型名称"  # 优先级高于 OPENAI_MODEL
DEEPTRACER_MODEL_TEMPERATURE=0.2  # 默认0.2，控制生成内容随机性
```
### 配置文件及配置项说明
- **配置文件路径**：固定为 `~/.deeptracer/.env.local`（本地配置文件），所有环境变量需在此文件中配置，无需手动设置系统环境变量
- **必配项**：`OPENAI_API_KEY`，即你的 OpenAI 接口密钥
- **可选配置项**：
  - `OPENAI_MODEL`：默认推荐 gpt-4.1-mini，可根据需求调整
  - `OPENAI_BASE_URL`：第三方兼容网关地址，官方接口无需配置
  - `DEEPTRACER_MODEL_PROVIDER`：默认是 `openai`，无需额外配置
  - `DEEPTRACER_MODEL_NAME`：优先级高于 `OPENAI_MODEL`，可自定义模型名称
  - `DEEPTRACER_MODEL_TEMPERATURE`：默认 0.2，控制生成内容的随机性
配置完成后，重新执行 `deeptracer-web` 启动服务，即可启用模型增强功能。
## ⚠️ 常见问题与排查
### 启动失败排查
1. 确认终端已通过 `conda activate deeptracer` 激活虚拟环境
2. 确认已执行 `pip install -e .` 完成项目安装
3. 修改后端代码后，需重新执行 `deeptracer-web` 重启服务
4. 启用模型功能时，确认已正确设置 `OPENAI_API_KEY`
### 其他说明
- Web 前端仅支持 .py 后缀文件，其他文件类型会提示错误
- 性能分析结果依赖本地运行环境和代码可执行性，不可信代码不建议直接分析（基于pyinstrument实现）
- 模型功能为可选增强，不配置也可正常使用所有本地分析能力
- 若遇到报错，可提供终端输出信息，便于排查问题
## 📌 功能限制
- 当前模型提供方仅支持 OpenAI 兼容接口
- `deeptracer` 命令为残余功能，实现不完善，不推荐使用
## 💡 核心价值
DeepTracer 以「本地可验证的运行数据」为基础，结合可选的模型增强，将复杂的 Python 代码分析拆分为直观、易懂的模块，让未参与代码开发的人也能快速理解代码结构、运行状态及优化方向，是代码学习、教学和轻量级诊断的高效工具。