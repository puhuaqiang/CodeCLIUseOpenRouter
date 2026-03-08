"""
Anthropic-to-OpenRouter 代理服务器

将 Claude Code CLI 的 Anthropic 格式请求转换为 OpenAI 格式，
转发到 OpenRouter，然后将响应转换回 Anthropic 格式。
"""

import os
import json
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import httpx
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from dotenv import load_dotenv

from src.format_converter import (
    anthropic_to_openai_request,
    openai_to_anthropic_response,
    openai_stream_to_anthropic_stream,
    create_anthropic_stream_start,
    create_anthropic_stream_ping,
    create_anthropic_content_block_start,
    create_anthropic_stream_stop,
    generate_id,
)

# 加载环境变量（.env 文件中的变量不会覆盖已存在的环境变量）
load_dotenv()

# 配置 - 使用 os.environ（.env 文件已通过 load_dotenv 加载到环境变量）
OPENROUTER_BASE_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
PROXY_HOST = os.environ.get("PROXY_HOST", "127.0.0.1")
PROXY_PORT = int(os.environ.get("PROXY_PORT", "8080"))

# 注意：不进行模型名称转换
# Claude Code CLI 会直接使用 OpenRouter 上的模型名称
# 例如：anthropic/claude-3.5-sonnet, openai/gpt-4o 等


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
            "HTTP-Referer": "https://github.com/claude-code-proxy",
            "X-Title": "Claude Code CLI Proxy",
        },
        "timeout": httpx.Timeout(300.0),  # 5分钟超时
    }
    
    # 如果有代理，添加代理配置
    if proxies:
        client_kwargs["proxy"] = proxies["https://"] or proxies["http://"]
    
    app.state.client = httpx.AsyncClient(**client_kwargs)
    print(f"🚀 代理服务器启动: http://{PROXY_HOST}:{PROXY_PORT}")
    print(f"📡 转发到: {OPENROUTER_BASE_URL}")
    yield
    # 关闭时清理
    await app.state.client.aclose()
    print("👋 代理服务器已关闭")


app = FastAPI(
    title="Anthropic-to-OpenRouter Proxy",
    description="将 Claude Code CLI 的 Anthropic 格式请求转换为 OpenAI 格式并转发到 OpenRouter",
    version="0.1.0",
    lifespan=lifespan,
)


def map_model(model_name: str) -> str:
    """
    模型名称直接透传，不进行转换
    Claude Code CLI 会直接使用 OpenRouter 的模型名称
    例如：anthropic/claude-3.5-sonnet, openai/gpt-4o, google/gemini-pro 等
    """
    return model_name


@app.get("/")
async def root():
    """根路径 - 健康检查"""
    return {
        "status": "ok",
        "service": "Anthropic-to-OpenRouter Proxy",
        "version": "0.1.0"
    }


@app.get("/v1/models")
async def list_models():
    """列出可用模型"""
    try:
        response = await app.state.client.get("/models")
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers)
        )
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"OpenRouter 连接失败: {str(e)}")


@app.post("/v1/messages")
async def create_message(request: Request):
    """
    处理 Anthropic 格式的消息请求，转换为 OpenAI 格式转发到 OpenRouter
    """
    # 读取请求体
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="无效的 JSON 请求体")
    
    # 获取原始模型名并映射
    anthropic_model = body.get("model", "claude-3-5-sonnet-20241022")
    openrouter_model = map_model(anthropic_model)
    
    # 转换请求格式
    openai_body = anthropic_to_openai_request(body)
    openai_body["model"] = openrouter_model
    
    # 检查是否为流式请求
    is_stream = body.get("stream", False)
    
    if is_stream:
        return await handle_streaming_request(openai_body, anthropic_model)
    else:
        return await handle_non_streaming_request(openai_body, anthropic_model)


async def handle_non_streaming_request(openai_body: dict, anthropic_model: str) -> JSONResponse:
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
                content={"error": f"OpenRouter 错误: {error_content}"}
            )
        
        openai_response = response.json()
        anthropic_response = openai_to_anthropic_response(openai_response, anthropic_model)
        
        return JSONResponse(content=anthropic_response)
        
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"OpenRouter 请求失败: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"内部错误: {str(e)}")


async def handle_streaming_request(openai_body: dict, anthropic_model: str) -> StreamingResponse:
    """处理流式请求"""
    message_id = generate_id()
    
    async def generate_stream() -> AsyncGenerator[str, None]:
        """生成 Anthropic 格式的 SSE 流"""
        # 发送 message_start
        start_event = create_anthropic_stream_start(anthropic_model, message_id)
        yield f"event: message_start\ndata: {json.dumps(start_event)}\n\n"
        
        # 发送 ping
        ping_event = create_anthropic_stream_ping()
        yield f"event: ping\ndata: {json.dumps(ping_event)}\n\n"
        
        # 发送 content_block_start
        block_start = create_anthropic_content_block_start()
        yield f"event: content_block_start\ndata: {json.dumps(block_start)}\n\n"
        
        try:
            async with app.state.client.stream(
                "POST",
                "/chat/completions",
                json=openai_body
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    error_event = {
                        "type": "error",
                        "error": {"message": f"OpenRouter 错误: {error_text.decode()}"}
                    }
                    yield f"event: error\ndata: {json.dumps(error_event)}\n\n"
                    return
                
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    
                    data_str = line[6:]  # 去掉 "data: " 前缀
                    
                    if data_str == "[DONE]":
                        break
                    
                    # 转换并发送
                    anthropic_event = openai_stream_to_anthropic_stream(
                        data_str, anthropic_model, message_id
                    )
                    
                    if anthropic_event:
                        if anthropic_event.get("type") == "message_stop":
                            # 发送 message_delta (包含 stop_reason)
                            delta_event = {
                                "type": "message_delta",
                                "delta": {
                                    "stop_reason": anthropic_event.get("stop_reason"),
                                    "stop_sequence": None
                                },
                                "usage": {"output_tokens": 0}  # 实际令牌数会在最后更新
                            }
                            yield f"event: message_delta\ndata: {json.dumps(delta_event)}\n\n"
                            
                            # 发送 message_stop
                            stop_event = create_anthropic_stream_stop()
                            yield f"event: message_stop\ndata: {json.dumps(stop_event)}\n\n"
                        else:
                            yield f"event: content_block_delta\ndata: {json.dumps(anthropic_event)}\n\n"
                            
        except Exception as e:
            error_event = {
                "type": "error",
                "error": {"message": str(e)}
            }
            yield f"event: error\ndata: {json.dumps(error_event)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# 兼容 Anthropic SDK 的其他端点

@app.post("/v1/complete")
async def complete(request: Request):
    """兼容旧的 complete API (很少使用)"""
    raise HTTPException(status_code=501, detail="Complete API 未实现，请使用 Messages API")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "proxy_server:app",
        host=PROXY_HOST,
        port=PROXY_PORT,
        reload=False,
        log_level="info"
    )
