"""
Anthropic <-> OpenAI API 格式转换器

支持:
- 请求格式转换 (Anthropic -> OpenAI)
- 响应格式转换 (OpenAI -> Anthropic)
- 流式响应转换 (SSE)
"""

import json
import uuid
from typing import Any, AsyncGenerator


def generate_id() -> str:
    """生成 Anthropic 格式的 ID"""
    return f"msg_{uuid.uuid4().hex[:24]}"


def anthropic_to_openai_messages(anthropic_messages: list[dict], system: str | None = None) -> list[dict]:
    """
    将 Anthropic 格式的消息转换为 OpenAI 格式
    
    Anthropic: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    OpenAI: [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, ...]
    """
    openai_messages = []
    
    # 添加 system 消息
    if system:
        openai_messages.append({"role": "system", "content": system})
    
    # 转换消息
    for msg in anthropic_messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        # 处理多模态内容
        if isinstance(content, list):
            openai_content = []
            for item in content:
                if isinstance(item, dict):
                    item_type = item.get("type", "text")
                    if item_type == "text":
                        openai_content.append({
                            "type": "text",
                            "text": item.get("text", "")
                        })
                    elif item_type == "image":
                        # 处理图片
                        source = item.get("source", {})
                        if source.get("type") == "base64":
                            media_type = source.get("media_type", "image/png")
                            data = source.get("data", "")
                            openai_content.append({
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{data}"
                                }
                            })
            openai_messages.append({"role": role, "content": openai_content})
        else:
            openai_messages.append({"role": role, "content": content})
    
    return openai_messages


def anthropic_to_openai_request(anthropic_body: dict) -> dict:
    """
    将 Anthropic 请求体转换为 OpenAI 格式
    
    Anthropic:
    {
        "model": "claude-3-5-sonnet-20241022",
        "messages": [...],
        "system": "...",
        "max_tokens": 4096,
        "temperature": 0.7,
        "stream": true
    }
    
    OpenAI:
    {
        "model": "...",
        "messages": [...],
        "max_completion_tokens": 4096,
        "temperature": 0.7,
        "stream": true
    }
    """
    openai_body = {
        "model": anthropic_body.get("model", ""),
        "messages": anthropic_to_openai_messages(
            anthropic_body.get("messages", []),
            anthropic_body.get("system")
        ),
    }
    
    # 处理 max_tokens
    if "max_tokens" in anthropic_body:
        openai_body["max_tokens"] = anthropic_body["max_tokens"]
    
    # 处理 temperature
    if "temperature" in anthropic_body:
        openai_body["temperature"] = anthropic_body["temperature"]
    
    # 处理 top_p
    if "top_p" in anthropic_body:
        openai_body["top_p"] = anthropic_body["top_p"]
    
    # 处理 stop sequences
    if "stop_sequences" in anthropic_body:
        openai_body["stop"] = anthropic_body["stop_sequences"]
    
    # 处理 stream
    if "stream" in anthropic_body:
        openai_body["stream"] = anthropic_body["stream"]
    
    # 处理 tools/functions
    if "tools" in anthropic_body:
        openai_body["tools"] = convert_tools_anthropic_to_openai(anthropic_body["tools"])
    
    if "tool_choice" in anthropic_body:
        openai_body["tool_choice"] = anthropic_body["tool_choice"]
    
    return openai_body


def convert_tools_anthropic_to_openai(anthropic_tools: list[dict]) -> list[dict]:
    """转换工具定义格式"""
    openai_tools = []
    for tool in anthropic_tools:
        openai_tool = {
            "type": "function",
            "function": {
                "name": tool.get("name", ""),
                "description": tool.get("description", ""),
                "parameters": tool.get("input_schema", {})
            }
        }
        openai_tools.append(openai_tool)
    return openai_tools


def openai_to_anthropic_response(openai_response: dict, model: str) -> dict:
    """
    将 OpenAI 响应转换为 Anthropic 格式
    
    OpenAI:
    {
        "id": "chatcmpl-...",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "...",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "...",
                "tool_calls": [...]
            },
            "finish_reason": "stop"
        }],
        "usage": {...}
    }
    
    Anthropic:
    {
        "id": "msg_...",
        "type": "message",
        "role": "assistant",
        "model": "...",
        "content": [{"type": "text", "text": "..."}],
        "stop_reason": "end_turn",
        "usage": {"input_tokens": ..., "output_tokens": ...}
    }
    """
    choice = openai_response.get("choices", [{}])[0]
    message = choice.get("message", {})
    usage = openai_response.get("usage", {})
    
    # 构建 content
    content = []
    
    # 处理文本内容
    msg_content = message.get("content")
    if msg_content:
        content.append({"type": "text", "text": msg_content})
    
    # 处理 tool calls
    tool_calls = message.get("tool_calls", [])
    for tool_call in tool_calls:
        function = tool_call.get("function", {})
        content.append({
            "type": "tool_use",
            "id": tool_call.get("id", ""),
            "name": function.get("name", ""),
            "input": json.loads(function.get("arguments", "{}"))
        })
    
    # 转换 stop_reason
    finish_reason = choice.get("finish_reason")
    stop_reason_map = {
        "stop": "end_turn",
        "length": "max_tokens",
        "tool_calls": "tool_use",
        "content_filter": "content_filter"
    }
    stop_reason = stop_reason_map.get(finish_reason, finish_reason)
    
    anthropic_response = {
        "id": generate_id(),
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": content,
        "stop_reason": stop_reason,
        "usage": {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0)
        }
    }
    
    return anthropic_response


def openai_stream_to_anthropic_stream(openai_line: str, model: str, message_id: str) -> dict | None:
    """
    将 OpenAI 流式响应行转换为 Anthropic 流式事件
    
    返回 Anthropic 格式的 SSE 事件数据
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
    
    # 构建 Anthropic 事件
    event = {
        "type": "content_block_delta",
        "index": 0,
        "delta": {}
    }
    
    # 处理内容增量
    content = delta.get("content", "")
    if content:
        event["delta"] = {"type": "text_delta", "text": content}
        return event
    
    # 处理 tool calls
    tool_calls = delta.get("tool_calls", [])
    if tool_calls:
        tool_call = tool_calls[0]
        event["delta"] = {
            "type": "tool_use_delta",
            "id": tool_call.get("id", ""),
            "name": tool_call.get("function", {}).get("name", ""),
            "partial_json": tool_call.get("function", {}).get("arguments", "")
        }
        return event
    
    # 处理结束
    if finish_reason:
        stop_reason_map = {
            "stop": "end_turn",
            "length": "max_tokens",
            "tool_calls": "tool_use",
            "content_filter": "content_filter"
        }
        return {
            "type": "message_stop",
            "stop_reason": stop_reason_map.get(finish_reason, finish_reason)
        }
    
    return None


def create_anthropic_stream_start(model: str, message_id: str) -> dict:
    """创建 Anthropic 流式响应的开始事件"""
    return {
        "type": "message_start",
        "message": {
            "id": message_id,
            "type": "message",
            "role": "assistant",
            "model": model,
            "content": [],
            "stop_reason": None,
            "stop_sequence": None,
            "usage": {"input_tokens": 0, "output_tokens": 0}
        }
    }


def create_anthropic_stream_ping() -> dict:
    """创建 Anthropic ping 事件"""
    return {"type": "ping"}


def create_anthropic_content_block_start() -> dict:
    """创建内容块开始事件"""
    return {
        "type": "content_block_start",
        "index": 0,
        "content_block": {"type": "text", "text": ""}
    }


def create_anthropic_stream_stop() -> dict:
    """创建流结束事件"""
    return {"type": "message_stop"}
