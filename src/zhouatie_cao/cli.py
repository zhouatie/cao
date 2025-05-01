#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
命令行接口模块
"""

import argparse
import os
import sys
from typing import Dict, List, Optional

# 导入配置管理模块
from . import config
from .utils.terminal import print_with_borders
from .utils.command import execute_command, get_last_command_error
from .ai_client import call_ai_api


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
    parser.add_argument("command", nargs="*", help="要执行的命令 (如果提供)")

    return parser.parse_args()


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

    error_info = None

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
                print("\n--- 使用环境变量中的命令结果（仅用于测试） ---")
                print(f"命令: {bypass_command}")
                print(f"返回码: {bypass_returncode}")
                print(f"错误信息: {bypass_error}")
                print("------------------------------\n")

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
            sys.exit(1)

    if isinstance(error_info, str):
        print(f"`error_info` 是否是字符串类型 错误: {error_info}")
        sys.exit(1)

    if not error_info:
        # 命令成功执行，没有错误
        sys.exit(0)

    if error_info.get("returncode", -1) == 0:
        print(f"命令 '{error_info.get('command')}' 执行成功，没有错误。")
        sys.exit(0)

    # 调试模式打印错误信息
    if args.debug:
        print("\n--- 调试信息 ---")
        print(f"原始命令: {error_info.get('original_command', '未知命令')}")
        print(f"解析命令: {error_info.get('command', '未知命令')}")
        print(f"返回码: {error_info.get('returncode', -1)}")
        print("错误信息:")
        print(error_info.get("error", "无错误信息"))
        print("----------------\n")

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
        print(f"选择的模型配置: {model_config}")

    # 调用 AI API
    print("\ncao 🌿\n")
    print(f"正在使用 {model_name} 分析错误...")
    print()
    ai_response = call_ai_api(model_config, error_info)

    # 打印 AI 响应
    print_with_borders(ai_response)
