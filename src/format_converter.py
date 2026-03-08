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
        
        # 处理多模态内容（可能包含 tool_result、tool_use 等）
        if isinstance(content, list):
            text_parts = []
            tool_results = []  # tool_result 消息列表
            tool_call_parts = []  # tool_use 消息列表
            has_non_tool_content = False
            
            for item in content:
                if not isinstance(item, dict):
                    continue
                    
                item_type = item.get("type", "text")
                
                if item_type == "text":
                    text = item.get("text", "")
                    if text:
                        text_parts.append(text)
                        has_non_tool_content = True
                        
                elif item_type == "image":
                    # 处理图片
                    source = item.get("source", {})
                    if source.get("type") == "base64":
                        has_non_tool_content = True
                        # 图片会放在 text_parts 后面一起处理
                        
                elif item_type == "tool_result":
                    # 处理工具调用结果 - 转换为 OpenAI 的 tool 角色消息
                    tool_content = item.get("content", "")
                    tool_call_id = item.get("tool_use_id", "")
                    
                    # 提取工具结果内容
                    result_text = ""
                    if isinstance(tool_content, list):
                        for tc in tool_content:
                            if isinstance(tc, dict) and tc.get("type") == "text":
                                t = tc.get("text", "")
                                if t:
                                    result_text += t + "\n"
                    elif isinstance(tool_content, str):
                        result_text = tool_content
                    
                    # OpenAI 要求 tool 结果不能为空
                    if not result_text or not result_text.strip():
                        result_text = "(tool executed successfully)"
                    
                    tool_results.append({
                        "role": "tool",
                        "content": result_text.strip(),
                        "tool_call_id": tool_call_id
                    })
                    
                elif item_type == "tool_use":
                    # 工具调用请求 - 转换为 OpenAI tool_calls
                    tool_call_parts.append({
                        "id": item.get("id", ""),
                        "type": "function",
                        "function": {
                            "name": item.get("name", ""),
                            "arguments": json.dumps(item.get("input", {}))
                        }
                    })
            
            # 构建消息
            if role == "assistant" and tool_call_parts:
                # Assistant 的 tool_use 请求
                openai_msg = {
                    "role": "assistant",
                    "content": "\n".join(text_parts) if text_parts else None,
                    "tool_calls": tool_call_parts
                }
                openai_messages.append(openai_msg)
            elif tool_results and not has_non_tool_content:
                # User 消息只包含 tool_result - 拆分为多个 tool 消息
                for tr in tool_results:
                    openai_messages.append(tr)
            else:
                # 普通消息（可能混合了文本和工具结果）
                final_content = "\n".join(text_parts) if text_parts else ""
                if not final_content.strip():
                    final_content = "(tool result)" if tool_results else "..."
                openai_messages.append({"role": role, "content": final_content})
                # 如果有工具结果，额外添加
                for tr in tool_results:
                    openai_messages.append(tr)
                    
        else:
            # 字符串内容
            if not content or not str(content).strip():
                # 空内容处理
                if role == "user":
                    content = "(empty)"
                else:
                    content = "..."
            openai_messages.append({"role": role, "content": content})
    
    # 清理：移除连续的相同角色消息（OpenAI 要求 alternating roles）
    openai_messages = merge_consecutive_messages(openai_messages)
    
    return openai_messages


def merge_consecutive_messages(messages: list[dict]) -> list[dict]:
    """合并连续的相同角色消息（OpenAI 要求角色交替）"""
    if not messages:
        return messages
    
    result = [messages[0]]
    
    for msg in messages[1:]:
        last_msg = result[-1]
        if msg["role"] == last_msg["role"]:
            # 合并相同角色的消息
            last_content = last_msg.get("content", "")
            current_content = msg.get("content", "")
            
            # 处理不同类型的 content
            if isinstance(last_content, list) or isinstance(current_content, list):
                # 至少有一个是列表，都转为列表
                if not isinstance(last_content, list):
                    last_content = [{"type": "text", "text": last_content}] if last_content else []
                if not isinstance(current_content, list):
                    current_content = [{"type": "text", "text": current_content}] if current_content else []
                last_msg["content"] = last_content + current_content
            else:
                # 都是字符串
                sep = "\n" if last_content and current_content else ""
                last_msg["content"] = str(last_content or "") + sep + str(current_content or "")
            
            # 合并 tool_calls（如果有）
            if "tool_calls" in msg:
                if "tool_calls" not in last_msg:
                    last_msg["tool_calls"] = []
                last_msg["tool_calls"].extend(msg["tool_calls"])
        else:
            result.append(msg)
    
    return result


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
