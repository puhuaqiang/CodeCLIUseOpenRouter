"""
Gemini <-> OpenAI API 格式转换器

将 Google Gemini API 格式转换为 OpenAI 格式，用于转发到 OpenRouter
"""

import json
import uuid
from typing import Any, AsyncGenerator


def generate_id() -> str:
    """生成唯一 ID"""
    return f"gen-{uuid.uuid4().hex[:12]}"


def gemini_to_openai_messages(contents: list[dict]) -> list[dict]:
    """
    将 Gemini 格式的 contents 转换为 OpenAI 格式的 messages
    
    Gemini:
    [
        {
            "role": "user",
            "parts": [{"text": "Hello"}]
        },
        {
            "role": "model", 
            "parts": [{"text": "Hi!"}]
        }
    ]
    
    OpenAI:
    [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi!"}
    ]
    """
    messages = []
    role_map = {
        "user": "user",
        "model": "assistant",
    }
    
    for content in contents:
        role = content.get("role", "user")
        parts = content.get("parts", [])
        
        # 提取文本内容
        text_parts = []
        for part in parts:
            if isinstance(part, dict) and "text" in part:
                text_parts.append(part["text"])
        
        if text_parts:
            messages.append({
                "role": role_map.get(role, "user"),
                "content": "\n".join(text_parts)
            })
    
    return messages


def gemini_to_openai_request(gemini_body: dict, model: str) -> dict:
    """
    将 Gemini 请求体转换为 OpenAI 格式
    
    Gemini:
    {
        "contents": [{"role": "user", "parts": [{"text": "..."}]}],
        "generationConfig": {
            "maxOutputTokens": 2048,
            "temperature": 0.9,
            "topP": 0.95
        }
    }
    
    OpenAI:
    {
        "model": "...",
        "messages": [{"role": "user", "content": "..."}],
        "max_tokens": 2048,
        "temperature": 0.9,
        "top_p": 0.95
    }
    """
    openai_body = {
        "model": model,
        "messages": gemini_to_openai_messages(gemini_body.get("contents", [])),
    }
    
    # 转换 generationConfig
    config = gemini_body.get("generationConfig", {})
    
    if "maxOutputTokens" in config:
        openai_body["max_tokens"] = config["maxOutputTokens"]
    
    if "temperature" in config:
        openai_body["temperature"] = config["temperature"]
    
    if "topP" in config:
        openai_body["top_p"] = config["topP"]
    
    if "topK" in config:
        openai_body["top_k"] = config["topK"]
    
    if "stopSequences" in config:
        openai_body["stop"] = config["stopSequences"]
    
    # 处理 tools/function calling
    if "tools" in gemini_body:
        openai_body["tools"] = convert_tools_gemini_to_openai(gemini_body["tools"])
    
    return openai_body


def convert_tools_gemini_to_openai(gemini_tools: list[dict]) -> list[dict]:
    """转换 Gemini 工具定义到 OpenAI 格式"""
    openai_tools = []
    for tool in gemini_tools:
        if "functionDeclarations" in tool:
            for func in tool["functionDeclarations"]:
                openai_tool = {
                    "type": "function",
                    "function": {
                        "name": func.get("name", ""),
                        "description": func.get("description", ""),
                        "parameters": func.get("parameters", {})
                    }
                }
                openai_tools.append(openai_tool)
    return openai_tools


def openai_to_gemini_response(openai_response: dict) -> dict:
    """
    将 OpenAI 响应转换为 Gemini 格式
    
    OpenAI:
    {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": "...",
                "tool_calls": [...]
            }
        }],
        "usage": {...}
    }
    
    Gemini:
    {
        "candidates": [{
            "content": {
                "role": "model",
                "parts": [{"text": "..."}]
            },
            "finishReason": "STOP"
        }],
        "usageMetadata": {
            "promptTokenCount": ...,
            "candidatesTokenCount": ...
        }
    }
    """
    choice = openai_response.get("choices", [{}])[0]
    message = choice.get("message", {})
    usage = openai_response.get("usage", {})
    
    # 构建 parts
    parts = []
    content = message.get("content")
    if content:
        parts.append({"text": content})
    
    # 处理 tool calls
    tool_calls = message.get("tool_calls", [])
    for tool_call in tool_calls:
        function = tool_call.get("function", {})
        parts.append({
            "functionCall": {
                "name": function.get("name", ""),
                "args": json.loads(function.get("arguments", "{}"))
            }
        })
    
    # 转换 finish reason
    finish_reason = choice.get("finish_reason", "stop")
    finish_reason_map = {
        "stop": "STOP",
        "length": "MAX_TOKENS",
        "tool_calls": "STOP",
        "content_filter": "SAFETY",
    }
    
    gemini_response = {
        "candidates": [{
            "content": {
                "role": "model",
                "parts": parts
            },
            "finishReason": finish_reason_map.get(finish_reason, "OTHER"),
        }],
        "usageMetadata": {
            "promptTokenCount": usage.get("prompt_tokens", 0),
            "candidatesTokenCount": usage.get("completion_tokens", 0),
            "totalTokenCount": usage.get("total_tokens", 0)
        }
    }
    
    return gemini_response


def openai_stream_to_gemini_stream(openai_line: str) -> dict | None:
    """
    将 OpenAI 流式响应行转换为 Gemini 流式事件
    
    Gemini 流式格式:
    {
        "candidates": [{
            "content": {
                "parts": [{"text": "..."}],
                "role": "model"
            }
        }]
    }
    """
    if not openai_line or openai_line == "[DONE]":
        return None
    
    try:
        data = json.loads(openai_line)
    except json.JSONDecodeError:
        return None
    
    choice = data.get("choices", [{}])[0]
    delta = choice.get("delta", {})
    finish_reason = choice.get("finish_reason")
    
    # 构建 Gemini 增量响应
    gemini_chunk = {
        "candidates": [{
            "content": {
                "role": "model",
                "parts": []
            }
        }]
    }
    
    # 处理文本增量
    content = delta.get("content", "")
    if content:
        gemini_chunk["candidates"][0]["content"]["parts"].append({"text": content})
        return gemini_chunk
    
    # 处理结束
    if finish_reason:
        return None  # 流结束
    
    return None
