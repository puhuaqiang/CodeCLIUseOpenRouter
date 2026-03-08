# Claude & Gemini to OpenRouter Proxy

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

一个代理服务器，让 [Claude Code CLI](https://github.com/anthropics/anthropic-quickstarts) 和 [Google Gemini CLI](https://github.com/google-gemini/gemini-cli) 能够使用 [OpenRouter](https://openrouter.ai/) 的 API 密钥访问各种 AI 模型。

## ✨ 功能特性

- 🔀 **双向格式转换**: Anthropic/Gemini ↔ OpenAI 格式自动转换
- 🌊 **流式响应**: 完整支持 SSE 流式传输
- 🤖 **多模型支持**: 通过 OpenRouter 访问 Claude、GPT、Gemini 等上百种模型
- 🌍 **代理支持**: 自动检测并使用系统代理 (v2rayN/Clash 等)
- ⚙️ **灵活配置**: 支持环境变量和 `.env` 文件配置
- 🚀 **双服务架构**: 同时支持 Claude Code CLI 和 Gemini CLI

## 📁 项目结构

```
.
├── src/
│   ├── proxy_server.py           # Claude Code CLI 代理 (端口 8080)
│   ├── gemini_proxy_server.py    # Gemini CLI 代理 (端口 8081)
│   ├── format_converter.py       # Anthropic ↔ OpenAI 格式转换
│   └── gemini_format_converter.py # Gemini ↔ OpenAI 格式转换
├── start.ps1                     # 启动 Claude 代理 (PowerShell)
├── start_gemini.ps1              # 启动 Gemini 代理 (PowerShell)
├── start_proxy.py                # 启动 Claude 代理 (Python)
├── start_gemini.py               # 启动 Gemini 代理 (Python)
├── pyproject.toml                # Python 项目配置
├── .env.example                  # 环境变量示例
└── README.md                     # 本文件
```

## 🚀 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/yourusername/CodeCLIUseOpenRouter.git
cd CodeCLIUseOpenRouter
```

### 2. 安装依赖

使用 [uv](https://github.com/astral-sh/uv)（推荐）:

```bash
uv sync
```

或使用 pip:

```bash
pip install -e "."
```

### 3. 配置 API 密钥

从 [OpenRouter](https://openrouter.ai/keys) 获取 API Key，然后选择以下任一方式配置：

**方式一：系统环境变量（推荐）**

```powershell
# PowerShell (当前会话)
$env:OPENROUTER_API_KEY = "sk-or-v1-..."

# PowerShell (永久保存到用户环境)
[Environment]::SetEnvironmentVariable('OPENROUTER_API_KEY', 'sk-or-v1-...', 'User')
```

**方式二：.env 文件**

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 API Key
```

### 4. 启动代理服务器

**启动 Claude Code CLI 代理（端口 8080）:**

```powershell
# PowerShell
.\start.ps1

# 或 Python
python start_proxy.py
```

**启动 Gemini CLI 代理（端口 8081）:**

```powershell
# PowerShell
.\start_gemini.ps1

# 或 Python
python start_gemini.py
```

**同时启动两个代理：**

```powershell
# 终端 1
.\start.ps1

# 终端 2
.\start_gemini.ps1
```

## 🔧 CLI 配置

### Claude Code CLI

设置环境变量指向本地代理：

```powershell
$env:ANTHROPIC_BASE_URL = "http://127.0.0.1:8080"

# 然后运行 claude
claude
```

### Gemini CLI

设置环境变量指向本地代理：

```powershell
$env:GOOGLE_API_KEY = "dummy-key"
$env:GOOGLE_GENAI_API_ENDPOINT = "http://127.0.0.1:8081"

# 然后运行 gemini
gemini
```

## ⚙️ 环境变量配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `OPENROUTER_API_KEY` | **必需** - OpenRouter API Key | - |
| `OPENROUTER_BASE_URL` | OpenRouter API 基础 URL | `https://openrouter.ai/api/v1` |
| `PROXY_HOST` | Claude 代理监听地址 | `127.0.0.1` |
| `PROXY_PORT` | Claude 代理监听端口 | `8080` |
| `GEMINI_PROXY_HOST` | Gemini 代理监听地址 | `127.0.0.1` |
| `GEMINI_PROXY_PORT` | Gemini 代理监听端口 | `8081` |

### 配置优先级

1. **系统环境变量** - 最高优先级
2. **`.env` 文件** - 如果没有设置系统环境变量
3. **默认值** - 如果连 `.env` 文件都没有

## 🎯 使用示例

### 在 Claude Code CLI 中使用 OpenRouter 模型

```powershell
# 设置代理
$env:ANTHROPIC_BASE_URL = "http://127.0.0.1:8080"

# 使用 Claude 模型
claude --model "anthropic/claude-3.5-sonnet"

# 使用 GPT 模型
claude --model "openai/gpt-4o"

# 使用 Gemini 模型
claude --model "google/gemini-2.0-flash-001"

# 使用 DeepSeek 模型
claude --model "deepseek/deepseek-chat"
```

### 在 Gemini CLI 中使用 OpenRouter 模型

```powershell
# 设置代理
$env:GOOGLE_API_KEY = "dummy-key"
$env:GOOGLE_GENAI_API_ENDPOINT = "http://127.0.0.1:8081"

# Gemini CLI 会使用 Gemini 格式，自动映射到 OpenRouter
gemini --model "gemini-2.0-flash"
```

### 模型映射（Gemini CLI）

| Gemini CLI 模型名 | OpenRouter 模型名 |
|------------------|------------------|
| `gemini-2.0-flash` | `google/gemini-2.0-flash-001` |
| `gemini-1.5-flash` | `google/gemini-flash-1.5` |
| `gemini-1.5-pro` | `google/gemini-pro-1.5` |

也可以使用 OpenRouter 的任意模型：

```python
# 在代码中使用任意 OpenRouter 模型
model = genai.GenerativeModel('models/openai--gpt-4o')
model = genai.GenerativeModel('models/anthropic--claude-3-opus')
```

## 🔍 API 端点

### Claude 代理 (端口 8080)

| 端点 | 说明 |
|------|------|
| `GET /` | 健康检查 |
| `GET /v1/models` | 列出可用模型 |
| `POST /v1/messages` | Anthropic Messages API |

### Gemini 代理 (端口 8081)

| 端点 | 说明 |
|------|------|
| `GET /` | 健康检查 |
| `GET /v1beta/models` | 列出可用模型 |
| `POST /v1beta/models/{model}:generateContent` | 生成内容 |
| `POST /v1beta/models/{model}:streamGenerateContent` | 流式生成内容 |

## 🛠️ 技术说明

### 格式转换

**Claude 代理的请求/响应转换:**

```
Anthropic Request                 OpenAI Request
-----------------                 --------------
POST /v1/messages       →        POST /v1/chat/completions
{
  "model": "claude-3.5",          {
  "messages": [...],                "model": "anthropic/claude-3.5-sonnet",
  "stream": true                    "messages": [...],
}                                    "stream": true
                                  }
```

**Gemini 代理的请求/响应转换:**

```
Gemini Request                    OpenAI Request
--------------                    --------------
POST /v1beta/models/...  →       POST /v1/chat/completions
generateContent                   {
{                                   "model": "google/gemini-2.0-flash-001",
  "contents": [{                    "messages": [{"role": "user", ...}]
    "role": "user",               }
    "parts": [{"text": "..."}]
  }]
}
```

## 🌐 代理配置

如果需要通过代理访问 OpenRouter，代理服务器会自动检测并使用系统代理环境变量：

```powershell
# v2rayN / Clash 等会自动设置这些变量
$env:HTTP_PROXY = "http://127.0.0.1:10809"
$env:HTTPS_PROXY = "http://127.0.0.1:10809"
```

## 🐛 故障排除

### 连接被拒绝

确保代理服务器已启动：

```bash
curl http://127.0.0.1:8080/  # Claude 代理
curl http://127.0.0.1:8081/  # Gemini 代理
```

### API Key 无效

检查环境变量是否正确设置：

```powershell
$env:OPENROUTER_API_KEY
```

### 模型不存在错误

确保使用正确的 OpenRouter 模型名称格式。查看所有可用模型：
https://openrouter.ai/docs/models

### 依赖问题

如果使用 uv：

```bash
uv sync --force
```

## 📝 许可证

[MIT](LICENSE)

## 🙏 致谢

- [OpenRouter](https://openrouter.ai/) - 统一的 AI 模型 API 平台
- [Anthropic](https://www.anthropic.com/) - Claude AI
- [Google](https://ai.google.dev/) - Gemini AI
- [FastAPI](https://fastapi.tiangolo.com/) - 高性能 Web 框架
