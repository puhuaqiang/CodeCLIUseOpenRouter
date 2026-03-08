#!/usr/bin/env python3
"""
测试代理服务器
"""

import json
import httpx


def test_health():
    """测试健康检查"""
    try:
        response = httpx.get("http://127.0.0.1:8080/")
        print(f"Health Check: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Health Check Failed: {e}")
        return False


def test_format_conversion():
    """测试格式转换"""
    from src.format_converter import anthropic_to_openai_request, openai_to_anthropic_response
    
    # 测试请求转换
    anthropic_request = {
        "model": "claude-3-5-sonnet-20241022",
        "messages": [
            {"role": "user", "content": "Hello, how are you?"}
        ],
        "system": "You are a helpful assistant.",
        "max_tokens": 100,
        "temperature": 0.7,
        "stream": False
    }
    
    openai_request = anthropic_to_openai_request(anthropic_request)
    print("\nAnthropic to OpenAI Request Conversion:")
    print(json.dumps(openai_request, indent=2, ensure_ascii=False))
    
    # 测试响应转换
    openai_response = {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "anthropic/claude-3.5-sonnet",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "I'm doing well, thank you for asking!"
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 10,
            "total_tokens": 20
        }
    }
    
    anthropic_response = openai_to_anthropic_response(openai_response, "claude-3-5-sonnet-20241022")
    print("\nOpenAI to Anthropic Response Conversion:")
    print(json.dumps(anthropic_response, indent=2, ensure_ascii=False))
    
    return True


def main():
    print("=" * 60)
    print("Anthropic-to-OpenRouter Proxy Tests")
    print("=" * 60)
    
    # 测试格式转换（不需要服务器运行）
    print("\n--- Testing Format Conversion ---")
    test_format_conversion()
    
    # 测试代理服务器（需要服务器运行）
    print("\n--- Testing Proxy Server ---")
    if test_health():
        print("\n[OK] Proxy server is running!")
    else:
        print("\n[WARN] Proxy server is not running.")
        print("   Start it with: python start_proxy.py")


if __name__ == "__main__":
    main()
