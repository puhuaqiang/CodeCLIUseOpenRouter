# Gemini-to-OpenRouter 代理

将 Google Gemini CLI 的 Gemini 格式请求转换为 OpenAI 格式，转发到 OpenRouter，然后将响应转换回 Gemini 格式。

## 功能特性

- ✅ **格式转换**: Gemini ↔ OpenAI 双向转换
- ✅ **流式响应**: 完整支持 SSE 流式传输
- ✅ **模型透传**: 直接使用 OpenRouter 模型名
- ✅ **代理支持**: 自动检测并使用系统代理 (v2rayN/Clash)
- ✅ **环境变量**: 优先使用系统环境变量

## 快速开始

### 1. 确保 Anthropic 代理已配置

Gemini 代理使用相同的 `OPENROUTER_API_KEY`，参考主 README 进行配置。

### 2. 启动 Gemini 代理

```powershell
# 使用 PowerShell 脚本
.\start_gemini.ps1

# 或使用 Python
python start_gemini.py
```

代理服务器将在 `http://127.0.0.1:8081` 启动。

### 3. 配置 Gemini CLI

Gemini CLI 需要设置 API 端点指向本地代理。

#### 方式一：环境变量

```powershell
# 设置 Gemini CLI 使用代理
$env:GOOGLE_API_KEY = "dummy-key"
$env:GOOGLE_GENAI_API_ENDPOINT = "http://127.0.0.1:8081"

# 然后运行 Gemini CLI
gemini ...
```

#### 方式二：使用 gcloud CLI 配置

如果使用 `gcloud` CLI，需要设置代理：

```powershell
# 设置 gcloud 代理
$env:HTTP_PROXY = "http://127.0.0.1:10809"
$env:HTTPS_PROXY = "http://127.0.0.1:10809"

# 或使用 gcloud 内置代理设置
gcloud config set proxy/type http
gcloud config set proxy/address 127.0.0.1
gcloud config set proxy/port 10809
```

## 使用示例

### 直接 API 调用

```python
import google.generativeai as genai

# 配置指向本地代理
genai.configure(
    api_key="dummy-key",
    transport="rest",
    client_options={
        "api_endpoint": "http://127.0.0.1:8081"
    }
)

# 创建模型实例 - 使用 OpenRouter 模型名
model = genai.GenerativeModel('models/gemini-2.0-flash')

# 生成内容
response = model.generate_content("Hello, how are you?")
print(response.text)
```

### 使用 OpenRouter 特定模型

```python
# 使用 OpenRouter 上的其他模型（通过模型别名）
model = genai.GenerativeModel('models/openai--gpt-4o')  # 对应 openai/gpt-4o
model = genai.GenerativeModel('models/anthropic--claude-3-5-sonnet')  # 对应 anthropic/claude-3.5-sonnet
```

## 模型映射

Gemini CLI 使用的模型名会自动映射到 OpenRouter：

| Gemini CLI 模型名 | OpenRouter 模型名 |
|------------------|------------------|
| `models/gemini-2.0-flash` | `google/gemini-2.0-flash-001` |
| `models/gemini-1.5-flash` | `google/gemini-flash-1.5` |
| `models/gemini-1.5-pro` | `google/gemini-pro-1.5` |

也可以直接使用 OpenRouter 完整模型名：

```python
# 使用任意 OpenRouter 模型
model = genai.GenerativeModel('models/openai--gpt-4o')
model = genai.GenerativeModel('models/anthropic--claude-3-opus')
model = genai.GenerativeModel('models/deepseek--deepseek-chat')
```

查看所有模型：https://openrouter.ai/docs/models

## 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|-------|------|--------|
| `OPENROUTER_API_KEY` | **必需** - OpenRouter API Key | - |
| `GEMINI_PROXY_HOST` | Gemini 代理监听地址 | 127.0.0.1 |
| `GEMINI_PROXY_PORT` | Gemini 代理监听端口 | 8081 |

### 配置优先级

1. **系统环境变量** - 最高优先级
2. **.env 文件** - 如果没有设置系统环境变量
3. **默认值** - 如果连 .env 文件都没有

## 与 Anthropic 代理一起使用

可以同时启动两个代理：

```powershell
# 终端 1: 启动 Claude 代理 (端口 8080)
.\start.ps1

# 终端 2: 启动 Gemini 代理 (端口 8081)
.\start_gemini.ps1
```

配置：

```powershell
# Claude Code CLI -> 端口 8080
$env:ANTHROPIC_BASE_URL = "http://127.0.0.1:8080"

# Gemini CLI -> 端口 8081
$env:GOOGLE_GENAI_API_ENDPOINT = "http://127.0.0.1:8081"
```

## 故障排除

### 连接被拒绝

确保代理服务器已启动：
```bash
curl http://127.0.0.1:8081/
```

### 模型不存在错误

确保使用正确的 OpenRouter 模型名称格式。

### API Key 无效

检查环境变量：
```powershell
$env:OPENROUTER_API_KEY
```

## 技术说明

### 格式转换对照

**请求转换:**
```
Gemini                             OpenAI
------                             ------
POST /v1beta/models/{model}:       POST /v1/chat/completions
generateContent                    {
{                                    "model": "...",
  "contents": [{                      "messages": [{"role": "user", ...}],
    "role": "user",                   "max_tokens": 2048,
    "parts": [{"text": "..."}]        "temperature": 0.9
  }],                               }
  "generationConfig": {
    "maxOutputTokens": 2048,
    "temperature": 0.9
  }
}
```

**响应转换:**
```
OpenAI                             Gemini
------                             ------
{
  "choices": [{                     {
    "message": {                     "candidates": [{
      "content": "..."                 "content": {
    },                                  "parts": [{"text": "..."}],
    "finish_reason": "stop"            "role": "model"
  }]                                   },
}                                      "finishReason": "STOP"
                                     }]
                                   }
```

## 许可证

MIT
