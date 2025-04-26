#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
cao - 一个捕获终端错误并使用 AI 分析的命令行工具
"""

import argparse
import os
import sys
import subprocess
import json
from typing import Dict, List, Optional, Union
import fcntl
import termios
import struct
import time
import re

# 支持的 AI 模型
SUPPORTED_MODELS = {
    "deepseek": {"api_base": "https://api.deepseek.com/v1", "model": "deepseek-chat"},
    "openai": {"api_base": "https://api.openai.com/v1", "model": "gpt-4o"},
}

DEFAULT_MODEL = "deepseek"


def get_terminal_size():
    """获取终端窗口大小"""
    try:
        h, w, hp, wp = struct.unpack(
            "HHHH", fcntl.ioctl(0, termios.TIOCGWINSZ, struct.pack("HHHH", 0, 0, 0, 0))
        )
        return w, h
    except:
        return 80, 24  # 默认大小


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="捕获终端错误并通过 AI 分析")
    parser.add_argument(
        "-m",
        "--model",
        default=DEFAULT_MODEL,
        choices=list(SUPPORTED_MODELS.keys()),
        help=f"选择 AI 模型 (默认: {DEFAULT_MODEL})",
    )
    parser.add_argument("-n", "--number", type=int, help="分析历史记录中特定行号的错误")
    parser.add_argument("-d", "--debug", action="store_true", help="开启调试模式")
    parser.add_argument("command", nargs="*", help="要执行的命令 (如果提供)")

    return parser.parse_args()


def get_shell_history_file() -> str:
    """获取当前 shell 的历史文件路径"""
    shell = os.environ.get("SHELL", "")
    home = os.environ.get("HOME", "")

    if "zsh" in shell:
        return os.path.join(home, ".zsh_history")
    elif "bash" in shell:
        return os.path.join(home, ".bash_history")
    else:
        # 默认尝试 bash 历史
        return os.path.join(home, ".bash_history")


def get_last_command_error():
    """获取最后一个命令的错误输出"""
    # 首先检查是否有环境变量设置的命令
    env_command = os.environ.get("CAO_LAST_COMMAND")
    env_returncode = os.environ.get("CAO_RETURN_CODE")

    if env_command:
        try:
            returncode = int(env_returncode) if env_returncode else -1
            if os.environ.get("CAO_DEBUG_MODE"):
                print(f"[DEBUG] 从环境变量获取命令: {env_command}")
                print(f"[DEBUG] 从环境变量获取返回码: {returncode}")

            # 无论返回码如何，都尝试重新执行这条命令来获取输出
            # 设置环境变量标记错误重现
            os.environ["CAO_REPRODUCING_ERROR"] = "1"

            # 添加 10s 超时机制
            import threading
            import time
            from threading import Timer

            result = {"output": "", "completed": False}

            def run_command():
                try:
                    error_proc = subprocess.run(
                        env_command,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=10,  # 设置子进程超时为 10 秒
                    )

                    output_text = error_proc.stderr or error_proc.stdout
                    result["output"] = output_text
                    result["returncode"] = error_proc.returncode
                    result["completed"] = True
                except subprocess.TimeoutExpired:
                    result["output"] = "命令执行超时（超过 10 秒）"
                    result["returncode"] = -1
                    result["completed"] = True
                except Exception as e:
                    result["output"] = f"执行命令时出错: {str(e)}"
                    result["returncode"] = -1
                    result["completed"] = True

            # 启动命令执行线程
            cmd_thread = threading.Thread(target=run_command)
            cmd_thread.daemon = True
            cmd_thread.start()

            # 等待最多 10 秒
            timeout = 10
            start_time = time.time()
            while not result["completed"] and time.time() - start_time < timeout:
                time.sleep(0.1)

            if not result["completed"]:
                return {
                    "command": env_command,
                    "error": "命令执行超时（超过 10 秒）",
                    "returncode": -1,
                    "original_command": env_command,
                }

            return {
                "command": env_command,
                "error": result["output"],
                "returncode": result.get("returncode", -1),
                "original_command": env_command,
            }
        except Exception as e:
            if os.environ.get("CAO_DEBUG_MODE"):
                print(f"[DEBUG] 处理环境变量命令时出错: {str(e)}")

    # 如果没有环境变量或处理失败，继续使用原来的方法

    # 如果方法一失败，返回一个有意义的错误信息
    # 不再默认执行方法二，因为它可能会读取不相关的历史文件
    if os.environ.get("CAO_DEBUG_MODE"):
        print("[DEBUG] 无法获取当前会话的最后执行命令")

    return {
        "command": "未知命令",
        "error": "无法获取最后执行的命令信息。请尝试直接提供命令作为参数，例如：cao [你的命令]",
        "returncode": -1,
        "original_command": "未知命令",
    }


def get_command_by_number(number: int):
    """根据历史记录行号获取命令"""
    history_file = get_shell_history_file()
    shell = os.environ.get("SHELL", "")

    try:
        with open(history_file, "r", encoding="utf-8", errors="ignore") as f:
            history = f.readlines()

        if number < 1 or number > len(history):
            return f"历史记录行号 {number} 超出范围 (1-{len(history)})"

        # 获取指定行号的命令
        command = history[number - 1].strip()

        if "zsh" in shell:
            # zsh 历史记录格式: ": timestamp:0;command"
            match = re.search(r";\s*(.*?)$", command)
            if match:
                command = match.group(1)

        # 使用Popen执行命令
        process = subprocess.Popen(
            command,
            shell=True,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = process.communicate()
        returncode = process.returncode

        if returncode != 0:
            return {
                "command": command,
                "error": stderr or stdout,
                "returncode": returncode,
                "original_command": command,  # 保存完整的原始命令
            }
        else:
            return {
                "command": command,
                "message": "这个命令执行成功，没有错误",
                "returncode": 0,
                "original_command": command,  # 保存完整的原始命令
            }

    except Exception as e:
        return f"获取命令时出错: {str(e)}"


def execute_command(command: List[str]):
    """执行命令并捕获错误"""
    # 对所有命令统一处理，不再区分ls命令
    cmd = " ".join(command)

    try:
        process = subprocess.Popen(
            cmd, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True
        )
        stdout, stderr = process.communicate()
        returncode = process.returncode

        if returncode != 0:
            return {
                "command": cmd,
                "error": stderr or stdout,
                "returncode": returncode,
                "original_command": cmd,  # 保存完整的原始命令
            }
        else:
            print(stdout, end="")
            return None  # 成功执行，无需分析
    except Exception as e:
        return {
            "command": cmd,
            "error": str(e),
            "returncode": 1,
            "original_command": cmd,
        }


def call_ai_api(model_config: Dict, error_info: Dict) -> str:
    """调用 AI API 分析错误"""
    # 根据选择的模型获取对应的 API KEY
    if "openai" in model_config["api_base"]:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return "错误: 未设置 OPENAI_API_KEY 环境变量"
    elif "deepseek" in model_config["api_base"]:
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            return "错误: 未设置 DEEPSEEK_API_KEY 环境变量"
    else:
        return f"错误: 不支持的 API 基础 URL: {model_config['api_base']}"

    api_base = model_config["api_base"]
    model = model_config["model"]

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

    # 构建提示信息
    # 优先使用原始命令（如果存在）
    command = error_info.get("original_command", error_info.get("command", "未知命令"))
    error_text = error_info.get("error", "未知错误")
    returncode = error_info.get("returncode", -1)

    # 调试输出，帮助排查命令传递问题
    if os.environ.get("CAO_DEBUG_MODE"):
        print(f"[DEBUG] 将发送到AI的命令: {command}")

    system_message = """你是一个命令行错误分析专家。
请分析以下命令错误并提供解决方案。重要提示：你接收的命令是用户真实输入的，不要猜测他输入了其他命令。
例如，如果错误显示命令未找到，请分析实际给出的命令，而不是猜测用户可能想输入的其他命令。"""

    user_message = f"""
命令: {command}
返回码: {returncode}
错误信息:
{error_text}

请分析这个特定命令产生的错误，并提供准确的解决方案。避免猜测用户可能想要运行的其他命令，除非错误信息明确显示命令被系统解析为其他内容。
"""

    import requests

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.7,
    }

    try:
        response = requests.post(
            f"{api_base}/chat/completions", headers=headers, json=payload, timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            return f"API 请求失败 (状态码: {response.status_code}): {response.text}"

    except Exception as e:
        return f"调用 AI API 时出错: {str(e)}"


def get_string_display_width(s: str) -> int:
    """获取字符串在终端中的显示宽度，考虑中文等宽字符"""
    width = 0
    for char in s:
        # 中文字符、日文、韩文等宽字符通常显示宽度为2
        if ord(char) > 127:
            width += 2
        else:
            width += 1
    return width


def print_with_borders(text: str):
    """打印带边框的文本"""
    terminal_width, _ = get_terminal_size()
    content_width = min(terminal_width - 4, 100)  # 最大内容宽度限制

    # 处理文本换行
    lines = []
    for line in text.split("\n"):
        if get_string_display_width(line) <= content_width:
            lines.append(line)
        else:
            # 长行分割
            # 对于中文文本，按字符分割会更好
            is_cjk_text = any(ord(c) > 127 for c in line)

            if is_cjk_text:
                # 中文文本按字符拆分
                current_line = ""
                for char in line:
                    test_line = current_line + char
                    if get_string_display_width(test_line) <= content_width:
                        current_line = test_line
                    else:
                        lines.append(current_line)
                        current_line = char
                if current_line:
                    lines.append(current_line)
            else:
                # 英文文本按单词拆分
                words = line.split(" ")
                current_line = ""
                for word in words:
                    test_line = current_line + (" " if current_line else "") + word
                    if get_string_display_width(test_line) <= content_width:
                        current_line = test_line
                    else:
                        lines.append(current_line)
                        current_line = word
                if current_line:
                    lines.append(current_line)

    # 计算边框宽度为内容宽度+2（两侧各1个空格）
    border_width = content_width + 2

    # 打印上边框
    print("╭" + "─" * border_width + "╮")

    # 打印标题行
    title = "\033[1;36mAI 分析结果\033[0m"
    # 计算标题文本的实际显示宽度（不包括ANSI转义序列）
    title_display_width = get_string_display_width("AI 分析结果")
    # 计算需要的填充空格数量
    padding = " " * (content_width - title_display_width)
    print("│ " + title + padding + " │")

    # 打印分隔线
    print("├" + "─" * border_width + "┤")

    # 打印内容行
    for line in lines:
        # 计算填充空格，考虑显示宽度而不是字符数
        display_width = get_string_display_width(line)
        padding = " " * (content_width - display_width)
        print("│ " + line + padding + " │")

    # 打印下边框
    print("╰" + "─" * border_width + "╯")


def main():
    """主函数"""
    args = parse_args()

    # 如果设置了调试标志，则设置环境变量以便在整个执行过程中使用
    if args.debug:
        os.environ["CAO_DEBUG_MODE"] = "1"

    error_info = None

    # 确定分析哪个命令的错误
    if args.command:
        # 如果提供了命令参数，执行该命令
        error_info = execute_command(args.command)
    elif args.number is not None:
        # 如果提供了行号参数，获取指定行号的命令
        error_info = get_command_by_number(args.number)
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
            print("2. 使用 -n 参数指定历史命令号，例如：cao -n 10")
            print("3. 先执行一个会出错的命令，然后再运行 cao")
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
    model_name = args.model
    if model_name not in SUPPORTED_MODELS:
        print(f"错误: 不支持的模型 '{model_name}'")
        print(f"支持的模型: {', '.join(SUPPORTED_MODELS.keys())}")
        sys.exit(1)

    model_config = SUPPORTED_MODELS[model_name]

    # 调用 AI API
    print(f"正在使用 {model_name} 分析错误...")
    ai_response = call_ai_api(model_config, error_info)

    # 打印 AI 响应
    print_with_borders(ai_response)


if __name__ == "__main__":
    main()
