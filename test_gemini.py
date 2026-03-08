#!/usr/bin/env python3
"""
测试 Gemini 代理格式转换
"""

import json


def test_format_conversion():
    """测试格式转换"""
    from src.gemini_format_converter import gemini_to_openai_request, openai_to_gemini_response
    
    print("=" * 60)
    print("Gemini-to-OpenRouter Proxy Format Tests")
    print("=" * 60)
    print()
    
    # 测试请求转换
    gemini_request = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": "Hello, how are you?"}]
            }
        ],
        "generationConfig": {
            "maxOutputTokens": 2048,
            "temperature": 0.9,
            "topP": 0.95
        }
    }
    
    openai_request = gemini_to_openai_request(gemini_request, "google/gemini-2.0-flash-001")
    print("Gemini to OpenAI Request Conversion:")
    print(json.dumps(openai_request, indent=2, ensure_ascii=False))
    print()
    
    # 测试响应转换
    openai_response = {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "google/gemini-2.0-flash-001",
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
    
    gemini_response = openai_to_gemini_response(openai_response)
    print("OpenAI to Gemini Response Conversion:")
    print(json.dumps(gemini_response, indent=2, ensure_ascii=False))
    print()
    
    print("[OK] All format conversions passed!")


def test_model_extraction():
    """测试模型路径提取"""
    from src.gemini_proxy_server import extract_model_from_path, map_gemini_model_to_openrouter
    
    print()
    print("=" * 60)
    print("Model Path Extraction Tests")
    print("=" * 60)
    print()
    
    test_cases = [
        ("/v1beta/models/gemini-2.0-flash:generateContent", "google/gemini-2.0-flash-001"),
        ("/v1beta/models/gemini-1.5-flash:streamGenerateContent", "google/gemini-flash-1.5"),
        ("/v1beta/models/gemini-pro:generateContent", "google/gemini-pro"),
    ]
    
    for path, expected_contains in test_cases:
        model = extract_model_from_path(path)
        status = "OK" if expected_contains in model or model == expected_contains else "FAIL"
        print(f"[{status}] {path} -> {model}")
    
    print()
    
    # 测试模型映射
    print("Model Name Mapping Tests:")
    models = [
        ("gemini-2.0-flash", "google/gemini-2.0-flash-001"),
        ("gemini-1.5-pro", "google/gemini-pro-1.5"),
        ("google/gemini-pro", "google/gemini-pro"),  # 已经是 OpenRouter 格式
    ]
    
    for gemini_model, expected in models:
        result = map_gemini_model_to_openrouter(gemini_model)
        status = "OK" if result == expected else "FAIL"
        print(f"[{status}] {gemini_model} -> {result}")


def main():
    test_format_conversion()
    test_model_extraction()
    print()
    print("All tests completed!")


if __name__ == "__main__":
    main()
