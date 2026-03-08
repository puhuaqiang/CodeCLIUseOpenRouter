#!/usr/bin/env python3
"""
Anthropic-to-OpenRouter 代理启动脚本
"""

import os
import sys


def check_env():
    """检查环境配置"""
    # 优先检查系统环境变量
    api_key = os.environ.get("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY", "")
    
    if not api_key or api_key == "your_openrouter_api_key_here":
        # 尝试从 .env 文件加载
        try:
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.environ.get("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY", "")
        except ImportError:
            pass
    
    if not api_key or api_key == "your_openrouter_api_key_here":
        print("[ERROR] OPENROUTER_API_KEY not configured!")
        print("")
        print("Please set OPENROUTER_API_KEY using one of these methods:")
        print("")
        print("1. System Environment Variable (Recommended):")
        print("   [PowerShell] $env:OPENROUTER_API_KEY = 'sk-or-v1-...'")
        print("   [CMD]        set OPENROUTER_API_KEY=sk-or-v1-...")
        print("   [Linux/Mac]  export OPENROUTER_API_KEY=sk-or-v1-...")
        print("")
        print("2. .env file:")
        print("   Create .env file with: OPENROUTER_API_KEY=sk-or-v1-...")
        print("")
        print("Get API Key: https://openrouter.ai/keys")
        sys.exit(1)
    
    # 隐藏显示部分 API Key
    masked_key = api_key[:10] + "..." + api_key[-4:] if len(api_key) > 14 else "***"
    print(f"[OK] API Key loaded: {masked_key}")
    return True


def main():
    """主函数"""
    # 首先加载 .env 文件（不会覆盖已存在的系统环境变量）
    from dotenv import load_dotenv
    load_dotenv()
    
    print("=" * 60)
    print("  Anthropic-to-OpenRouter Proxy Server")
    print("=" * 60)
    print("")
    
    # 检查环境
    check_env()
    
    # 获取配置 - 优先使用系统环境变量（.env 文件已通过 load_dotenv 加载）
    import os
    host = os.environ.get("PROXY_HOST", "127.0.0.1")
    port = os.environ.get("PROXY_PORT", "8080")
    
    print(f"")
    print(f"[INFO] Starting proxy server...")
    print(f"   URL: http://{host}:{port}")
    print(f"   Forwarding to: https://openrouter.ai/api/v1")
    print("")
    print("-" * 60)
    
    # 使用 uvicorn 启动
    import uvicorn
    uvicorn.run(
        "src.proxy_server:app",
        host=host,
        port=int(port),
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    main()
