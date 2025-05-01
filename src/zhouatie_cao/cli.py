#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
命令行接口模块
"""

import argparse
import os
import sys
import logging
import signal
from typing import Dict, List, Optional, Any
import time

# 导入配置管理模块
from . import config
from .utils.terminal import print_with_borders, get_terminal_size
from .utils.command import execute_command, get_last_command_error
from .ai_client import call_ai_api
from .utils.logger import get_logger, debug, info, warning, error, critical

# 获取日志记录器
logger = get_logger(__name__)

# 导入prompt_toolkit相关库，如果未安装则自动安装
try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.shortcuts import prompt
    from prompt_toolkit.history import InMemoryHistory
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.styles import Style
    from prompt_toolkit.layout.processors import BeforeInput
except ImportError:
    error("依赖库 prompt_toolkit 未安装，正在尝试安装...")
    import subprocess
    import sys

    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "prompt_toolkit"]
        )
        from prompt_toolkit import PromptSession
        from prompt_toolkit.shortcuts import prompt
        from prompt_toolkit.history import InMemoryHistory
        from prompt_toolkit.formatted_text import HTML
        from prompt_toolkit.styles import Style
        from prompt_toolkit.layout.processors import BeforeInput

        info("成功安装 prompt_toolkit")
    except Exception as e:
        error(f"安装 prompt_toolkit 失败: {str(e)}")
        print("请手动安装 prompt_toolkit 库: pip install prompt_toolkit")
        sys.exit(1)


def parse_args():
    """解析命令行参数"""
    # 获取用户配置的模型
    SUPPORTED_MODELS = config.get_supported_models()
    DEFAULT_MODEL = config.get_default_model()

    parser = argparse.ArgumentParser(description="捕获终端错误并通过 AI 分析")
    parser.add_argument(
        "-m",
        "--model",
        default=DEFAULT_MODEL,
        choices=list(SUPPORTED_MODELS.keys()),
        help=f"选择 AI 模型 (默认: {DEFAULT_MODEL})",
    )

    parser.add_argument("-d", "--debug", action="store_true", help="开启调试模式")
    parser.add_argument("--config", action="store_true", help="配置 AI 模型")
    parser.add_argument("-c", "--chat", action="store_true", help="启动持续对话模式")
    parser.add_argument("command", nargs="*", help="要执行的命令 (如果提供)")

    return parser.parse_args()


def handle_interactive_session(
    model_config: Dict[str, Any], initial_error_info: Optional[Dict[str, Any]] = None, is_chat_mode: bool = False
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
                    "content": "嗨！我是小草 🌿，你的编程闲聊伙伴！今天想聊点什么？技术问题、开发困扰，还是只是想放松一下大脑？我随时准备陪你唠嗑～",
                }
            )

            # 打印初始欢迎消息
            print("\ncao 🌿 轻松聊天模式\n")
            print_with_borders("嗨！我是小草 🌿，你的编程闲聊伙伴！今天想聊点什么？技术问题、开发困扰，还是只是想放松一下大脑？我随时准备陪你唠嗑～", mode="chat")
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
            print("\ncao 🌿 对话模式\n")
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
                print("退出对话模式")
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
            import threading
            thread = threading.Thread(target=api_call_thread)
            thread.daemon = True  # 设置为守护线程，这样主线程退出时它会自动退出
            thread.start()
            
            # 显示加载动画，直到API调用完成
            start_time = time.time()
            while not response_result["done"]:
                if time.time() - start_time > 0.1:  # 每100ms更新一次
                    print(f"\r{loading_chars[i % len(loading_chars)]} AI正在思考...", end="", flush=True)
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

            # 添加更多空行作为消息间隔
            print("\n\n")
            # 打印AI响应，聊天模式下使用更轻松的边框样式
            print_with_borders(ai_response, mode="chat" if is_chat_mode else "normal")

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


def main():
    """主函数"""
    args = parse_args()

    # 如果用户请求配置，则运行配置界面
    if args.config:
        from . import config_cli

        config_cli.interactive_config()
        sys.exit(0)

    # 如果设置了调试标志，则设置环境变量以便在整个执行过程中使用
    if args.debug:
        os.environ["CAO_DEBUG_MODE"] = "1"
        os.environ["CAO_LOG_LEVEL"] = "DEBUG"
        logger.setLevel(logging.DEBUG)
        debug("调试模式已启用")

    error_info = None

    # 如果是聊天模式，不需要获取命令错误信息
    if args.chat:
        # 直接进入对话模式，不需要错误信息
        debug("聊天模式启动，跳过错误信息获取")
    else:
        # 确定分析哪个命令的错误
        if args.command:
            # 如果提供了命令参数，执行该命令
            error_info = execute_command(args.command)
        else:
            # 默认分析最后一个命令
            error_info = get_last_command_error()

        # 如果没有获取到错误信息
        if not error_info:
            # 调试模式下尝试从环境变量获取测试数据
            if args.debug:
                bypass_command = os.environ.get("CAO_BYPASS_COMMAND")
                bypass_error = os.environ.get("CAO_BYPASS_ERROR")
                bypass_returncode = os.environ.get("CAO_BYPASS_RETURN_CODE")

                if bypass_command and bypass_error and bypass_returncode:
                    debug("使用环境变量中的命令结果（仅用于测试）")
                    debug(f"命令: {bypass_command}")
                    debug(f"返回码: {bypass_returncode}")
                    debug(f"错误信息: {bypass_error}")

                    error_info = {
                        "command": bypass_command,
                        "original_command": bypass_command,
                        "error": bypass_error,
                        "returncode": int(bypass_returncode),
                    }
            else:
                # 非调试模式下，给出提示并终止程序
                print("未能获取到命令的错误信息，无法进行分析。")
                print("请尝试以下方法：")
                print("1. 直接提供要分析的命令，例如：cao [你的命令]")
                print("2. 先执行一个会出错的命令，然后再运行 cao")
                print("3. 使用 -c 参数启动对话模式: cao -c")
                sys.exit(1)

    if isinstance(error_info, str):
        error(f"`error_info` 是字符串类型错误: {error_info}")
        print(f"错误: {error_info}")
        sys.exit(1)

    if not error_info and not args.chat:
        # 命令成功执行，没有错误
        sys.exit(0)

    if error_info and error_info.get("returncode", -1) == 0 and not args.chat:
        print(f"命令 '{error_info.get('command')}' 执行成功，没有错误。")
        sys.exit(0)

    # 调试模式打印错误信息
    if args.debug and error_info:
        debug("处理命令错误信息")
        debug(f"原始命令: {error_info.get('original_command', '未知命令')}")
        debug(f"解析命令: {error_info.get('command', '未知命令')}")
        debug(f"返回码: {error_info.get('returncode', -1)}")
        debug(f"错误信息: {error_info.get('error', '无错误信息')}")

    # 选择 AI 模型
    SUPPORTED_MODELS = config.get_supported_models()
    model_name = args.model
    if model_name not in SUPPORTED_MODELS:
        print(f"错误: 不支持的模型 '{model_name}'")
        print(f"支持的模型: {', '.join(SUPPORTED_MODELS.keys())}")
        sys.exit(1)

    model_config = SUPPORTED_MODELS[model_name]
    if "provider" not in model_config:
        model_config["provider"] = model_name

    # 调试模式下打印模型信息
    if args.debug:
        debug(f"选择的模型配置: {model_config}")

    # 检查是否进入对话模式
    if args.chat:
        handle_interactive_session(model_config, error_info, is_chat_mode=True)
    else:
        # 调用 AI API
        print("\ncao 🌿\n")
        info(f"正在使用 {model_name} 分析错误...")
        debug(f"错误信息长度: {len(error_info.get('error', '')) if error_info is not None else 0}")
        
        # 显示动画加载指示器
        loading_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        print("", end="\r")
        i = 0
        
        # 启动API调用
        import threading
        response_result = {"ai_response": None, "error": None, "done": False}
        
        def api_call_thread():
            try:
                response_result["ai_response"] = call_ai_api(model_config, error_info)
            except Exception as e:
                response_result["error"] = str(e)
            finally:
                response_result["done"] = True
                
        thread = threading.Thread(target=api_call_thread)
        thread.daemon = True  # 设置为守护线程，这样主线程退出时它会自动退出
        thread.start()
        
        # 显示加载动画，直到API调用完成
        start_time = time.time()
        while not response_result["done"]:
            if time.time() - start_time > 0.1:  # 每100ms更新一次
                print(f"\r{loading_chars[i % len(loading_chars)]} AI正在思考...", end="", flush=True)
                i += 1
                start_time = time.time()
            time.sleep(0.01)  # 小的睡眠以减少CPU使用
            
        # 清除加载动画
        print("\r" + " " * 50 + "\r", end="", flush=True)
        
        # 处理结果
        if response_result["error"]:
            error(f"AI API调用出错: {response_result['error']}")
            ai_response = f"抱歉，我遇到了一些问题: {response_result['error']}"
        else:
            ai_response = response_result["ai_response"]
            debug("AI 响应已接收")

        # 打印 AI 响应
        print("\n\n")  # 添加两个空行作为间隔
        print_with_borders(ai_response)

        # 打印对话模式提示
        print("\n提示: 你可以使用 'cao -c' 启动持续对话模式与AI助手继续交流")
