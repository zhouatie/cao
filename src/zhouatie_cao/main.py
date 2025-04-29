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
import time
import re

# 根据平台导入不同的模块
import platform

_IS_WINDOWS = platform.system() == "Windows"

# 在非Windows平台上导入Unix特定的模块
if not _IS_WINDOWS:
    try:
        import fcntl
        import termios
        import struct
    except ImportError:
        pass

# 导入配置管理模块
from . import config

# 获取用户配置的模型
SUPPORTED_MODELS = config.get_supported_models()
DEFAULT_MODEL = config.get_default_model()


def get_terminal_size():
    """获取终端窗口大小"""
    if _IS_WINDOWS:
        # Windows 平台使用 os.get_terminal_size
        try:
            from os import get_terminal_size as os_get_terminal_size

            size = os_get_terminal_size()
            return size.columns, size.lines
        except:
            return 80, 24  # 默认大小
    else:
        # Unix 平台使用 fcntl
        try:
            # 在函数内部进行导入，以确保这些模块只在需要时被访问
            import struct
            import fcntl
            import termios

            # 只使用我们需要的变量，忽略不需要的变量
            h, w, _, _ = struct.unpack(
                "HHHH",
                fcntl.ioctl(0, termios.TIOCGWINSZ, struct.pack("HHHH", 0, 0, 0, 0)),
            )
            return w, h
        except Exception:
            # 如果发生任何错误（包括模块不可用），返回默认值
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
    parser.add_argument("--config", action="store_true", help="配置 AI 模型")
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

            # 检查是否已经在错误重现模式，避免递归执行
            if os.environ.get("CAO_REPRODUCING_ERROR"):
                return {
                    "command": env_command,
                    "error": "检测到递归执行cao，避免执行命令以防止进程爆炸",
                    "returncode": -1,
                    "original_command": env_command,
                }

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
                        universal_newlines=True,  # 兼容 Python 3.6 及更早版本
                        timeout=20,  # 设置子进程超时为 20 秒
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
            universal_newlines=True,  # 兼容 Python 3.6 及更早版本
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
            cmd,
            shell=True,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            universal_newlines=True,  # 兼容 Python 3.6 及更早版本
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
    # 针对不同的 API 获取对应的 API KEY

    # 处理不同的API提供商
    api_key = None
    api_provider = model_config.get("provider", "").lower()  # 优先使用provider字段
    api_base = model_config["api_base"]

    # 如果未指定provider，尝试从api_base推断
    if not api_provider:
        # 检查本地模型
        if "localhost" in api_base or "127.0.0.1" in api_base:
            api_provider = "ollama"
        else:
            # 从URL中提取可能的提供商名称
            # 移除了硬编码的提供商检测，改为从URL中提取域名部分作为提供商名称
            import re
            from urllib.parse import urlparse

            parsed_url = urlparse(api_base)
            domain = parsed_url.netloc

            # 如果域名包含端口，去掉端口
            if ":" in domain:
                domain = domain.split(":")[0]

            # 提取域名中的主要部分，如 api.openai.com -> openai
            domain_parts = domain.split(".")
            if len(domain_parts) >= 2:
                # 尝试找到主域名部分
                if domain_parts[-2] not in ["com", "org", "net", "io"]:
                    api_provider = domain_parts[-2]
                else:
                    # 如果是二级域名，尝试获取子域名部分
                    if len(domain_parts) > 2:
                        api_provider = domain_parts[-3]

            # 如果无法从域名提取，尝试从路径中提取
            if not api_provider and parsed_url.path:
                path_parts = parsed_url.path.strip("/").split("/")
                if path_parts and path_parts[0] not in ["v1", "v2", "v3", "api"]:
                    api_provider = path_parts[0]

            # 如果仍然无法确定提供商，使用完整域名
            if not api_provider:
                api_provider = domain.replace(".", "_")

    # 检查是否为不需要API密钥的本地模型
    if api_provider == "ollama" or "localhost" in api_base or "127.0.0.1" in api_base:
        # 本地模型不需要API key
        api_key = None
    elif api_provider:
        # 任何其他提供商，统一从环境变量获取API密钥
        env_var_name = f"{api_provider.upper()}_API_KEY"
        api_key = os.environ.get(env_var_name)

        if os.environ.get("CAO_DEBUG_MODE"):
            print(f"尝试从环境变量获取API密钥: {env_var_name}")
            print(f"API提供商: {api_provider}")

        # 尝试从配置中获取API密钥
        if not api_key and "api_key" in model_config:
            api_key = model_config["api_key"]

        # 如果存在兼容性标识符（如dashscope通过compatible-mode提供的OpenAI兼容接口）
        if not api_key and "compatible-mode" in api_base:
            # 从URL中提取实际提供商名称
            compat_provider = None
            if "dashscope" in api_base:
                compat_provider = "DASHSCOPE"
            elif "baichuan" in api_base:
                compat_provider = "BAICHUAN"

            if compat_provider:
                compat_env_var = f"{compat_provider}_API_KEY"
                api_key = os.environ.get(compat_env_var)

                if os.environ.get("CAO_DEBUG_MODE") and api_key:
                    print(f"从兼容模式环境变量获取API密钥: {compat_env_var}")

        if not api_key:
            return f"错误: 未设置 {env_var_name} 环境变量，也未在配置中提供API密钥"
    else:
        return f"错误: 无法确定API提供商，请在配置中指定provider字段或使用标准URL格式"

    api_base = model_config["api_base"]
    model = model_config["model"]

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

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
        # debug 模式下打印请求的 payload
        # if os.environ.get("CAO_DEBUG_MODE"):
        #     print(f"[DEBUG] 请求的 payload: {json.dumps(payload, indent=2)}")

        response = requests.post(
            f"{api_base}/chat/completions", headers=headers, json=payload, timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            # Ollama API 与 OpenAI API 有稍微不同的响应格式
            if "localhost" in api_base or "127.0.0.1" in api_base:
                # Ollama 响应格式
                if "message" in result and "content" in result["message"]:
                    return result["message"]["content"]
                else:
                    # 兜底处理
                    return (
                        result.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "无法解析 Ollama API 响应")
                    )
            else:
                # OpenAI/DeepSeek 响应格式
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
    if "provider" not in model_config:
        model_config["provider"] = model_name

    print("model_config", model_config)
    # 调试模式下打印模型信息
    if args.debug:
        print(f"选择的模型配置: {model_config}")

    # 调用 AI API
    print("\ncao🌿\n")
    print(f"正在使用 {model_name} 分析错误...")
    print()
    ai_response = call_ai_api(model_config, error_info)

    # 打印 AI 响应
    print_with_borders(ai_response)


if __name__ == "__main__":
    main()
