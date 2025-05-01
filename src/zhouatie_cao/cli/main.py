#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
命令行主逻辑模块
"""

import os
import sys
import threading
import time
import logging
from typing import Dict, Any

from .. import config
from ..utils.terminal import print_with_borders
from ..utils.command import execute_command, get_last_command_error
from ..ai_client import call_ai_api
from ..utils.logger import get_logger, debug, info, error

# 获取日志记录器
logger = get_logger(__name__)

# 导入CLI模块
from .parser import parse_args
from .interactive import handle_interactive_session


def main():
    """主函数"""
    args = parse_args()

    # 如果用户请求配置，则运行配置界面
    if args.config:
        from .. import config_cli

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
        print(f"\n正在使用 {model_name} 分析错误...")
        debug(
            f"错误信息长度: {len(error_info.get('error', '')) if error_info is not None else 0}"
        )

        # 显示动画加载指示器
        loading_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        print("", end="\r")
        i = 0

        # 启动API调用
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
                print(
                    f"\r{loading_chars[i % len(loading_chars)]} AI正在思考...",
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
            error(f"AI API调用出错: {response_result['error']}")
            ai_response = f"抱歉，我遇到了一些问题: {response_result['error']}"
        else:
            ai_response = response_result["ai_response"]
            debug("AI 响应已接收")

        print()
        print_with_borders(ai_response)

        # 打印对话模式提示
        print("\n提示: 你可以使用 'cao -c' 启动持续对话模式与 AI 助手继续交流")
