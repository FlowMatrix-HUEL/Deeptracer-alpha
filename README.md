# DeepTracer
[🌐 Switch to Chinese Version](./README_zh.md)
---
DeepTracer is a code analysis tool designed for Python code understanding, runtime observation, and improvement suggestions. It mainly provides a local Web workbench, supporting the generation of Python code structure, performance analysis and optimization suggestions through an intuitive visual interface. It is suitable for scenarios such as code learning, teaching demonstrations, and lightweight code diagnosis.
**Important Note**: The core runtime entry of the current tool is the `deeptracer-web` command. The `deeptracer` command is retained but is a residual function with incomplete implementation and is not recommended for use.
## 📋 Core Features
DeepTracer focuses on converting Python code into readable, locatable, and discussable analysis results. Its core capabilities are as follows:
- Code Loading: Supports local .py file selection, drag-and-drop upload, direct code pasting, or loading built-in sample code
- Multi-dimensional Analysis: Completes AST structure analysis and performance analysis (based on pyinstrument) using local tools
- Visualization Display: Provides AST syntax tree, performance flame graph visualization, and Python Tutor code execution flow visualization
- Optimization Suggestions: Generates actionable suggestions with priority, risk prompts, code anchors, and modification previews
- Open-ended Q&A: Supports streaming Q&A around the current code and analysis results, with Markdown rendering support
- Model Enhancement (Optional): After configuring an OpenAI-compatible model, more natural multi-agent analysis explanations can be obtained
## 🎯 Target Users
- Python Beginners: Quickly understand code structure, function responsibilities, and key points to focus on
- Teachers/TAs: Intuitively display code runtime behavior, structural logic, and optimization directions
- Developers: Perform quick lightweight diagnosis on a single Python file/code snippet
- Project Analysts: Understand tool input/output, functional boundaries, and core capabilities
## 🚀 Quick Start (Windows + Conda Environment Only)
### 1. Environment Preparation
Open Anaconda Prompt or PowerShell in the project root directory and execute the following commands to configure the environment:
```powershell
# Create and activate a virtual environment
conda create -n deeptracer python=3.11 -y
conda activate deeptracer
# Upgrade pip and install the project
python -m pip install --upgrade pip
pip install -e .
```
### 2. Start the Web Workbench (Core Command)
After the environment is installed, directly execute the core command to start the local Web service:
```powershell
deeptracer-web
```
After the service starts, the browser will open automatically (or access manually):
```text
http://127.0.0.1:8000
```
Note: If you encounter the error "URL spelling may be incorrect, please check" when accessing the URL, please verify that the `deeptracer-web` service has been started successfully and the URL is entered correctly.
### 3. Basic Usage Process
1. After opening the Web page, enter Python code by "Pasting Code", "Uploading .py File", or "Loading Sample"
2. Click "Analyze Code", and the system will automatically execute the LangGraph analysis pipeline to generate analysis results
3. View the analysis results: First understand the overall code situation through "Overview", then switch to the "Structure/Performance" tabs to view details
4. View optimization suggestions and modification previews, and observe the code execution process through the "Execution Flow" visualization on the right
5. (Optional) Continue asking questions around the current code in the Q&A area to get targeted answers
## ⚙️ Optional Configuration: Model Enhancement (OpenAI Compatible)
When the model API is not configured, the tool will automatically fall back to the "local analysis + rule-based suggestions" mode, which does not affect basic usage at all; after configuring the model, more natural multi-agent analysis explanations can be obtained. Note: Environment variables do not need to be set manually; they need to be configured in a specified local file, and only Windows systems are supported currently.
### Configuration Steps (No Manual Environment Variable Setting Required)
```powershell
# 1. Create/edit the local configuration file (fixed path)
~/.deeptracer/.env.local
# 2. Add the following configurations to the file (adjust as needed)
# OpenAI official interface configuration
OPENAI_API_KEY="Your API Key"
OPENAI_MODEL="gpt-4.1-mini"
# If using a third-party OpenAI-compatible gateway, add the following additionally
OPENAI_BASE_URL="https://your-gateway-url/v1"
# Optional configurations (add as needed)
DEEPTRACER_MODEL_NAME="Custom Model Name"  # Has higher priority than OPENAI_MODEL
DEEPTRACER_MODEL_TEMPERATURE=0.2  # Default 0.2, controls the randomness of generated content
```
### Configuration File and Configuration Item Description
- **Configuration File Path**: Fixed as `~/.deeptracer/.env.local` (local configuration file). All environment variables must be configured in this file; there is no need to set system environment variables manually.
- **Mandatory Item**: `OPENAI_API_KEY`, which is your OpenAI interface key.
- **Optional Configuration Items**:
  - `OPENAI_MODEL`: Recommended default is gpt-4.1-mini, which can be adjusted according to needs.
  - `OPENAI_BASE_URL`: Third-party compatible gateway address; no need to configure for the official interface.
  - `DEEPTRACER_MODEL_PROVIDER`: Default is `openai`, no additional configuration required.
  - `DEEPTRACER_MODEL_NAME`: Has higher priority than `OPENAI_MODEL`; custom model name can be set.
  - `DEEPTRACER_MODEL_TEMPERATURE`: Default 0.2, controls the randomness of generated content.
After configuration is completed, re-execute `deeptracer-web` to start the service, and the model enhancement function can be enabled.
## ⚠️ Common Issues and Troubleshooting
### Startup Failure Troubleshooting
1. Confirm that the virtual environment has been activated via `conda activate deeptracer` in the terminal.
2. Confirm that `pip install -e .` has been executed to complete the project installation.
3. After modifying the backend code, you need to re-execute `deeptracer-web` to restart the service.
4. When enabling the model function, confirm that `OPENAI_API_KEY` has been set correctly.
### Other Notes
- The Web frontend only supports .py suffix files; other file types will prompt an error.
- Performance analysis results depend on the local runtime environment and code executability; untrusted code is not recommended to be analyzed directly (implemented based on pyinstrument).
- The model function is an optional enhancement; all local analysis capabilities can be used normally without configuration.
- If an error is encountered, you can provide the terminal output information to facilitate problem troubleshooting.
## 📌 Functional Limitations
- Currently, the model provider only supports OpenAI-compatible interfaces.
- The `deeptracer` command is a residual function with incomplete implementation and is not recommended for use.
## 💡 Core Value
Based on "locally verifiable runtime data" and combined with optional model enhancement, DeepTracer splits complex Python code analysis into intuitive and easy-to-understand modules. It allows people who have not participated in code development to quickly understand code structure, runtime status, and optimization directions, making it an efficient tool for code learning, teaching, and lightweight diagnosis.


🙏 Acknowledgements
Project Contributors

    Xiaocheng Wang | Trae Engineer
    Ran Wei | Former Engineer of Sony & Huawei
    Zhongping Zhou | Joincare Engineer

Community Support

    GTOC Community
    Baidu PFCC Community

Open Source Reference
The core visualization capability of this project is upgraded and iterated based on [OnlinePythonTutor](https://github.com/hcientist/OnlinePythonTutor), with adaptive development and functional expansion implemented. Our contributions were submitted to relevant servers via email instead of being merged into the GitHub repository. DeepTracer achieves further comprehensive upgrades based on the original kernel.