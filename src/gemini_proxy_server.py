"""
Gemini-to-OpenRouter 代理服务器

将 Google Gemini CLI 的 Gemini 格式请求转换为 OpenAI 格式，
转发到 OpenRouter，然后将响应转换回 Gemini 格式。
"""

import os
import json
import re
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import httpx
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from dotenv import load_dotenv

from src.gemini_format_converter import (
    gemini_to_openai_request,
    openai_to_gemini_response,
    openai_stream_to_gemini_stream,
)

# 加载环境变量（.env 文件中的变量不会覆盖已存在的环境变量）
load_dotenv()

# 配置 - 使用 os.environ（.env 文件已通过 load_dotenv 加载到环境变量）
OPENROUTER_BASE_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
GEMINI_PROXY_HOST = os.environ.get("GEMINI_PROXY_HOST", "127.0.0.1")
GEMINI_PROXY_PORT = int(os.environ.get("GEMINI_PROXY_PORT", "8081"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 检测系统代理环境变量 (v2rayN/Clash 等会设置这些)
    http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
    https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    
    # 创建代理配置
    proxies = None
    if http_proxy or https_proxy:
        proxies = {
            "http://": http_proxy or https_proxy,
            "https://": https_proxy or http_proxy,
        }
        print(f"🔗 检测到系统代理: {proxies}")
    
    # 启动时创建 HTTP 客户端
    client_kwargs = {
        "base_url": OPENROUTER_BASE_URL,
        "headers": {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://github.com/gemini-openrouter-proxy",
            "X-Title": "Gemini CLI Proxy",
        },
        "timeout": httpx.Timeout(300.0),
    }
    
    if proxies:
        client_kwargs["proxy"] = proxies["https://"] or proxies["http://"]
    
    app.state.client = httpx.AsyncClient(**client_kwargs)
    print(f"🚀 Gemini 代理服务器启动: http://{GEMINI_PROXY_HOST}:{GEMINI_PROXY_PORT}")
    print(f"📡 转发到: {OPENROUTER_BASE_URL}")
    yield
    # 关闭时清理
    await app.state.client.aclose()
    print("👋 Gemini 代理服务器已关闭")


app = FastAPI(
    title="Gemini-to-OpenRouter Proxy",
    description="将 Gemini CLI 的 Gemini 格式请求转换为 OpenAI 格式并转发到 OpenRouter",
    version="0.1.0",
    lifespan=lifespan,
)


def extract_model_from_path(path: str) -> str:
    """
    从 Gemini API 路径中提取模型名称
    
    路径格式: /v1beta/models/{model}:generateContent
              /v1beta/models/{model}:streamGenerateContent
    """
    # 匹配 models/{model}:generateContent 或 models/{model}:streamGenerateContent
    match = re.search(r'/models/([^:]+):(generate|streamGenerate)Content', path)
    if match:
        model = match.group(1)
        # Gemini 模型名通常是 models/gemini-pro 格式，提取后面的部分
        if model.startswith("models/"):
            model = model[7:]  # 去掉 "models/" 前缀
        # 映射到 OpenRouter 格式
        return map_gemini_model_to_openrouter(model)
    return "google/gemini-2.0-flash-001"  # 默认模型


def map_gemini_model_to_openrouter(gemini_model: str) -> str:
    """
    将 Gemini 模型名映射到 OpenRouter 模型名
    如果传入的已经是 OpenRouter 格式（包含 /），直接返回
    """
    if "/" in gemini_model:
        return gemini_model
    
    # Gemini 官方模型名到 OpenRouter 的映射
    model_map = {
        "gemini-2.0-flash": "google/gemini-2.0-flash-001",
        "gemini-2.0-flash-exp": "google/gemini-2.0-flash-exp:free",
        "gemini-2.0-pro-exp": "google/gemini-2.0-pro-exp-02-05:free",
        "gemini-1.5-flash": "google/gemini-flash-1.5",
        "gemini-1.5-pro": "google/gemini-pro-1.5",
        "gemini-1.0-pro": "google/gemini-pro",
        "gemini-pro": "google/gemini-pro",
    }
    
    return model_map.get(gemini_model, f"google/{gemini_model}")


@app.get("/")
async def root():
    """根路径 - 健康检查"""
    return {
        "status": "ok",
        "service": "Gemini-to-OpenRouter Proxy",
        "version": "0.1.0"
    }


@app.post("/{full_path:path}")
async def gemini_proxy(request: Request, full_path: str):
    """
    处理所有 Gemini 格式的请求，转换为 OpenAI 格式转发到 OpenRouter
    """
    # 读取请求体
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="无效的 JSON 请求体")
    except Exception:
        body = {}
    
    # 从路径提取模型
    model = extract_model_from_path(full_path)
    
    # 判断是否为流式请求
    is_stream = ":streamGenerateContent" in full_path
    
    # 转换请求格式
    openai_body = gemini_to_openai_request(body, model)
    
    # 处理流式/非流式请求
    if is_stream:
        return await handle_streaming_request(openai_body)
    else:
        return await handle_non_streaming_request(openai_body)


async def handle_non_streaming_request(openai_body: dict) -> JSONResponse:
    """处理非流式请求"""
    try:
        response = await app.state.client.post(
            "/chat/completions",
            json=openai_body
        )
        
        if response.status_code != 200:
            error_content = response.text
            print(f"OpenRouter 错误: {response.status_code} - {error_content}")
            return JSONResponse(
                status_code=response.status_code,
                content={"error": {"message": f"OpenRouter 错误: {error_content}", "code": response.status_code}}
            )
        
        openai_response = response.json()
        gemini_response = openai_to_gemini_response(openai_response)
        
        return JSONResponse(content=gemini_response)
        
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"OpenRouter 请求失败: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"内部错误: {str(e)}")


async def handle_streaming_request(openai_body: dict) -> StreamingResponse:
    """处理流式请求"""
    openai_body["stream"] = True
    
    async def generate_stream() -> AsyncGenerator[str, None]:
        """生成 Gemini 格式的流式响应"""
        try:
            async with app.state.client.stream(
                "POST",
                "/chat/completions",
                json=openai_body
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    error_json = {
                        "error": {
                            "message": f"OpenRouter 错误: {error_text.decode()}",
                            "code": response.status_code
                        }
                    }
                    yield f"data: {json.dumps(error_json)}\n\n"
                    return
                
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    
                    data_str = line[6:]  # 去掉 "data: " 前缀
                    
                    if data_str == "[DONE]":
                        break
                    
                    # 转换并发送
                    gemini_chunk = openai_stream_to_gemini_stream(data_str)
                    
                    if gemini_chunk:
                        yield f"data: {json.dumps(gemini_chunk)}\n\n"
                        
        except Exception as e:
            error_json = {"error": {"message": str(e)}}
            yield f"data: {json.dumps(error_json)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.get("/v1beta/models")
async def list_models():
    """
    列出可用模型 - 返回 Gemini 格式的模型列表
    """
    try:
        response = await app.state.client.get("/models")
        if response.status_code == 200:
            openai_models = response.json()
            # 转换为 Gemini 格式
            gemini_models = []
            for model in openai_models.get("data", []):
                model_id = model.get("id", "")
                gemini_models.append({
                    "name": f"models/{model_id.replace('/', '--')}",
                    "version": "1.0",
                    "displayName": model.get("name", model_id),
                    "description": model.get("description", ""),
                    "inputTokenLimit": 128000,
                    "outputTokenLimit": 4096,
                    "supportedGenerationMethods": ["generateContent", "countTokens"],
                })
            return {"models": gemini_models}
        else:
            # 返回一个默认的 Gemini 模型列表
            return {
                "models": [
                    {
                        "name": "models/gemini-2.0-flash",
                        "version": "2.0",
                        "displayName": "Gemini 2.0 Flash",
                        "description": "Fast and versatile multimodal model",
                        "inputTokenLimit": 1000000,
                        "outputTokenLimit": 8192,
                        "supportedGenerationMethods": ["generateContent", "streamGenerateContent"],
                    },
                    {
                        "name": "models/gemini-1.5-flash",
                        "version": "1.5",
                        "displayName": "Gemini 1.5 Flash",
                        "description": "Fast and efficient multimodal model",
                        "inputTokenLimit": 1000000,
                        "outputTokenLimit": 8192,
                        "supportedGenerationMethods": ["generateContent", "streamGenerateContent"],
                    }
                ]
            }
    except Exception as e:
        print(f"获取模型列表失败: {e}")
        return {"models": []}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.gemini_proxy_server:app",
        host=GEMINI_PROXY_HOST,
        port=GEMINI_PROXY_PORT,
        reload=False,
        log_level="info"
    )
