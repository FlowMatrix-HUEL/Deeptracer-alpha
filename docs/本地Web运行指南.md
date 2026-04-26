# Deeptracer 本地 Web 运行指南

这份指南面向 Windows + Conda 环境，目标是让你用一条命令启动网页，并在需要时只通过配置模型 API 来开启多智能体分析。

## 1. 准备环境

在项目根目录打开 `Anaconda Prompt` 或 PowerShell：

```powershell
conda create -n deeptracer python=3.11 -y
conda activate deeptracer
python -m pip install --upgrade pip
pip install -e .
```

安装完成后，你已经可以直接启动网页：

```powershell
deeptracer-web
```

浏览器打开：

```text
http://127.0.0.1:8000
```

## 2. 当前默认行为

页面现在支持直接粘贴 Python 代码，不需要先选文件路径。

点击“分析代码”后，后端会统一走 LangGraph 工作流：

1. 本地工具先做 AST、性能、内存分析
2. 多个 agent 分别解释结构、性能和内存
3. 重构 agent 生成建议
4. 教学 agent 把结果翻译成更容易理解的话

如果你还没有配置模型 API，页面也能正常分析，只是此时会自动回退到“本地分析 + 规则化建议”的模式。

## 3. 如何配置模型 API

当前项目已经预留好了模型层，你只需要配置环境变量。

### OpenAI 兼容接口

```powershell
$env:OPENAI_API_KEY="你的 API Key"
$env:OPENAI_MODEL="gpt-4.1-mini"
```

如果你使用的是兼容 OpenAI 协议的第三方网关，还可以额外配置：

```powershell
$env:OPENAI_BASE_URL="https://你的接口地址/v1"
```

项目内部默认读取这些变量：

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `OPENAI_BASE_URL`
- `DEEPTRACER_MODEL_PROVIDER`
- `DEEPTRACER_MODEL_NAME`
- `DEEPTRACER_MODEL_TEMPERATURE`

其中：

- `DEEPTRACER_MODEL_PROVIDER` 默认是 `openai`
- `DEEPTRACER_MODEL_NAME` 优先级高于 `OPENAI_MODEL`
- `DEEPTRACER_MODEL_TEMPERATURE` 默认是 `0.2`

配置完后重新启动：

```powershell
deeptracer-web
```

## 4. 推荐体验路径

1. 打开页面后，先在左侧输入框粘贴一段 Python 代码，或者点击“载入示例”。
2. 点击“分析代码”。
3. 右侧先看“概览”，再切换到“结构 / 性能 / 内存”。
4. 最后查看下方建议列表和差异预览。

如果模型 API 已配置成功：

- 结构、性能、内存的说明会更像自然语言总结
- 建议会更接近真正的多智能体结果
- 返回数据中的 `meta.llmConfigured` 会是 `true`

如果模型 API 还没配置：

- 页面不会报废
- 仍然可以得到本地分析结果
- 返回数据中的 `meta.llmConfigured` 会是 `false`

## 5. 你现在会看到什么

当前版本已经具备这些能力：

- 同页输入 Python 代码并直接分析
- 统一通过 LangGraph 工作流组织分析流程
- 本地工具提供 AST / 性能 / 内存事实数据
- 多智能体层负责总结、解释和建议生成
- 未配置 API 时自动回退，不会白屏

## 6. 已知说明

- 现在的前端主入口是简洁版单页，不再强调技术栈，也不再要求用户理解文件路径。
- 当前只实现了“分析代码”主链路；更深入的追问式对话入口还可以在下一阶段继续接。
- 如果你改了后端代码但页面表现没变，通常是旧服务进程没有重启。

## 7. 启动失败时先检查这几项

1. 当前终端是否已经 `conda activate deeptracer`
2. 是否执行过 `pip install -e .`
3. 修改代码后是否重新执行了 `deeptracer-web`
4. 如果你要启用真实模型，是否已经设置了 `OPENAI_API_KEY`

如果你运行后遇到报错，把终端输出贴出来，我可以继续带你一起排查。
