#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
交互式会话处理模块
"""

import signal
import sys
import time
import threading
from typing import Dict, List, Optional, Any

# 尝试导入prompt_toolkit相关库
try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import InMemoryHistory
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.styles import Style
except ImportError:
    from ..utils.logger import error, info
    import subprocess
    import sys

    error("依赖库 prompt_toolkit 未安装，正在尝试安装...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "prompt_toolkit"]
        )
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import InMemoryHistory
        from prompt_toolkit.formatted_text import HTML
        from prompt_toolkit.styles import Style

        info("成功安装 prompt_toolkit")
    except Exception as e:
        error(f"安装 prompt_toolkit 失败: {str(e)}")
        print("请手动安装 prompt_toolkit 库: pip install prompt_toolkit")
        sys.exit(1)

from ..utils.terminal import print_with_borders
from ..utils.logger import debug, error
from ..ai_client import call_ai_api


def handle_interactive_session(
    model_config: Dict[str, Any],
    initial_error_info: Optional[Dict[str, Any]] = None,
    is_chat_mode: bool = False,
):
    """处理交互式对话会话

    Args:
        model_config: AI模型配置
        initial_error_info: 初始错误信息（如果有的话）
        is_chat_mode: 是否是通过 --chat 参数启动的聊天模式
    """
    # 创建会话历史
    history = InMemoryHistory()

    # 设置样式
    style = Style.from_dict(
        {
            "prompt": "ansicyan bold",
        }
    )

    # 创建会话对象
    session = PromptSession(history=history)

    # 会话上下文，用于保持与AI的对话历史
    conversation_context = []

    # 检查是否为纯聊天模式
    is_pure_chat_mode = not initial_error_info and is_chat_mode

    # 如果有初始错误信息，添加到上下文
    if initial_error_info:
        command = initial_error_info.get(
            "original_command", initial_error_info.get("command", "未知命令")
        )
        error_text = initial_error_info.get("error", "未知错误")
        returncode = initial_error_info.get("returncode", -1)

        # 添加初始错误信息到上下文
        conversation_context.append(
            {
                "role": "system",
                "content": "你是一个命令行错误分析专家。请分析以下命令错误并提供解决方案。",
            }
        )
        conversation_context.append(
            {
                "role": "user",
                "content": f"""
            命令: {command}
            返回码: {returncode}
            错误信息:
            {error_text}
            
            请分析这个特定命令产生的错误，并提供准确的解决方案。
            """,
            }
        )
    else:
        # 纯聊天模式下，使用更友好的人设
        if is_pure_chat_mode:
            conversation_context.append(
                {
                    "role": "system",
                    "content": """你是小草 (cao)，一个友好、幽默的编程助手。
                    你的性格特点：
                    1. 轻松幽默，善于活跃气氛
                    2. 对编程知识了如指掌，但表达方式轻松不严肃
                    3. 能理解程序员的苦恼和笑话
                    4. 善于用比喻和例子解释复杂概念
                    5. 有时会开一些程序员才懂的玩笑

                    请以轻松自然的口吻与用户交流，像朋友一样陪伴他们编程。如果用户提出技术问题，请提供准确但不呆板的解答。
                    """,
                }
            )
            conversation_context.append(
                {
                    "role": "assistant",
                    "content": "嗨！我是小草 🌱，你的编程闲聊伙伴！今天想聊点什么？技术问题、开发困扰，还是只是想放松一下大脑？我随时准备陪你唠嗑～",
                }
            )

            # 打印初始欢迎消息
            print_with_borders(
                "嗨！我是小草 🌱，你的编程闲聊伙伴！今天想聊点什么？技术问题、开发困扰，还是只是想放松一下大脑？我随时准备陪你唠嗑～",
                mode="chat",
            )
        else:
            # 如果没有初始错误，且不是纯聊天模式，则使用一般的问候
            conversation_context.append(
                {
                    "role": "system",
                    "content": "你是一个命令行助手，可以帮助用户解决各种命令行相关问题。",
                }
            )
            conversation_context.append(
                {
                    "role": "assistant",
                    "content": "你好！我是命令行助手，有什么可以帮助你的吗？",
                }
            )

            # 打印初始欢迎消息
            print("\ncao 🌱 对话模式\n")
            print_with_borders("你好！我是命令行助手，有什么可以帮助你的吗？")

    # 设置信号处理，优雅地处理Ctrl+C
    def signal_handler(sig, frame):
        print("\n退出对话模式")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # 持续对话循环
    while True:
        try:
            # 获取用户输入
            user_input = session.prompt(
                HTML("<ansicyan><b>cao 🌿 > </b></ansicyan>"), style=style
            )

            # 检查退出命令
            if user_input.strip().lower() in ["/exit", "/quit", "exit", "quit"]:
                print("\n退出对话模式")
                break

            # 如果输入为空，则跳过
            if not user_input.strip():
                continue

            # 添加用户消息到上下文
            conversation_context.append({"role": "user", "content": user_input})

            # 调用AI API获取响应 - 使用多线程处理
            loading_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
            print("", end="\r")
            i = 0

            # 创建结果容器
            response_result = {"ai_response": None, "error": None, "done": False}

            # 定义API调用线程函数
            def api_call_thread():
                try:
                    response_result["ai_response"] = call_ai_api(
                        model_config, error_info=None, messages=conversation_context
                    )
                except Exception as e:
                    # 如果API调用失败，记录错误
                    error(f"AI API调用出错: {str(e)}", exc_info=True)
                    response_result["error"] = str(e)
                finally:
                    response_result["done"] = True

            # 启动API调用线程
            thread = threading.Thread(target=api_call_thread)
            thread.daemon = True  # 设置为守护线程，这样主线程退出时它会自动退出
            thread.start()

            # 显示加载动画，直到API调用完成
            start_time = time.time()
            while not response_result["done"]:
                if time.time() - start_time > 0.1:  # 每100ms更新一次
                    print(
                        f"\r{loading_chars[i % len(loading_chars)]} ",
                        end="",
                        flush=True,
                    )
                    i += 1
                    start_time = time.time()
                time.sleep(0.01)  # 小的睡眠以减少CPU使用

            # 清除加载动画
            print("\r" + " " * 50 + "\r", end="", flush=True)

            # 处理结果
            if response_result["error"]:
                ai_response = f"抱歉，我遇到了一些问题: {response_result['error']}"
            else:
                ai_response = response_result["ai_response"]

            # 添加AI响应到上下文
            conversation_context.append({"role": "assistant", "content": ai_response})

            # 打印小草的名字和AI响应，聊天模式下不使用边框
            if is_chat_mode:
                print("\n\033[1;32m小草🌱\033[0m:")
                # 逐字打印回复，增加互动感
                for char in ai_response:
                    print(char, end="", flush=True)
                    time.sleep(0.005)  # 每个字符间隔5毫秒，保持流畅
                print("\n")  # 增加额外的空行，为用户输入提供更多空间
            else:
                print("小草🌱:")
                print_with_borders(ai_response, mode="normal")
                print()  # 增加额外的空行，为用户输入提供更多空间

            # 如果对话历史太长，清理最早的对话（保留system消息）
            if len(conversation_context) > 20:
                # 保留system消息和最近的对话
                system_messages = [
                    msg for msg in conversation_context if msg["role"] == "system"
                ]
                recent_messages = conversation_context[-10:]
                conversation_context = system_messages + recent_messages
                debug("对话历史已清理，保留system消息和最近10条对话")

        except KeyboardInterrupt:
            # 处理Ctrl+C
            print("\n退出对话模式")
            break
        except EOFError:
            # 处理Ctrl+D
            print("\n退出对话模式")
            break
        except Exception as e:
            error(f"对话模式出错: {str(e)}", exc_info=True)
            print(f"出现错误: {str(e)}")
            # 尝试继续对话
