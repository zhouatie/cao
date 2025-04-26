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
    "deepseek": {
        "api_base": "https://api.deepseek.com/v1",
        "model": "deepseek-chat"
    },
    "openai": {
        "api_base": "https://api.openai.com/v1",
        "model": "gpt-4o"
    }
}

DEFAULT_MODEL = "deepseek"

def get_terminal_size():
    """获取终端窗口大小"""
    try:
        h, w, hp, wp = struct.unpack('HHHH',
            fcntl.ioctl(0, termios.TIOCGWINSZ,
            struct.pack('HHHH', 0, 0, 0, 0)))
        return w, h
    except:
        return 80, 24  # 默认大小

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="捕获终端错误并通过 AI 分析")
    parser.add_argument("-m", "--model", default=DEFAULT_MODEL, choices=list(SUPPORTED_MODELS.keys()),
                        help=f"选择 AI 模型 (默认: {DEFAULT_MODEL})")
    parser.add_argument("-n", "--number", type=int,
                        help="分析历史记录中特定行号的错误")
    parser.add_argument("-d", "--debug", action="store_true",
                        help="开启调试模式")
    parser.add_argument("command", nargs="*", help="要执行的命令 (如果提供)")
    
    return parser.parse_args()

def get_shell_history_file() -> str:
    """获取当前 shell 的历史文件路径"""
    shell = os.environ.get('SHELL', '')
    home = os.environ.get('HOME', '')
    
    if 'zsh' in shell:
        return os.path.join(home, '.zsh_history')
    elif 'bash' in shell:
        return os.path.join(home, '.bash_history')
    else:
        # 默认尝试 bash 历史
        return os.path.join(home, '.bash_history')

def get_last_command_error():
    """获取最后一个命令的错误输出"""
    # 尝试使用各种方法获取上一条命令及其错误
    
    # 方法一：通过 fc -ln -1 获取最后执行的命令
    try:
        # 获取最后执行的命令
        last_cmd_proc = subprocess.run(
            'fc -ln -1', 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        if last_cmd_proc.returncode == 0 and last_cmd_proc.stdout.strip():
            last_command = last_cmd_proc.stdout.strip()
            # 过滤掉可能的 cao 自身命令
            if last_command.startswith('cao'):
                # 获取倒数第二条命令
                last_cmd_proc = subprocess.run(
                    'fc -ln -2 -1 | head -1', 
                    shell=True, 
                    stdout=subprocess.PIPE,
                    text=True
                )
                if last_cmd_proc.returncode == 0:
                    last_command = last_cmd_proc.stdout.strip()
            
            # 使用 $? 获取上一条命令的返回码
            returncode_proc = subprocess.run(
                'echo $?', 
                shell=True, 
                stdout=subprocess.PIPE,
                text=True
            )
            
            try:
                returncode = int(returncode_proc.stdout.strip())
            except ValueError:
                returncode = -1  # 默认值，表示未知返回码
                
            # 获取上次命令的错误输出通常需要特殊处理
            # 不过我们可以尝试用干净的方式获取错误信息
            
            # 如果返回码不是0，尝试重新执行这条命令来获取错误
            if returncode != 0:
                # 注意：这里只是为了获取错误信息，可能会有副作用
                # 使用环境变量标记，告诉子进程这是一次错误重现
                os.environ["CAO_REPRODUCING_ERROR"] = "1"
                
                error_proc = subprocess.run(
                    last_command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                error_text = error_proc.stderr or error_proc.stdout
                actual_returncode = error_proc.returncode
                
                # 如果重现的错误返回码与原始返回码一致，则使用重现的错误信息
                if actual_returncode == returncode:
                    return {
                        "command": last_command,
                        "error": error_text,
                        "returncode": returncode,
                        "original_command": last_command
                    }
                
            # 如果无法通过重现获取准确的错误信息，至少返回命令和返回码
            return {
                "command": last_command,
                "error": f"无法获取原始错误信息。命令返回码为 {returncode}。",
                "returncode": returncode,
                "original_command": last_command
            }
    except Exception as e:
        if os.environ.get("CAO_DEBUG_MODE"):
            print(f"[DEBUG] 使用fc方法获取历史命令失败: {str(e)}")
    
    # 方法二：回退到直接读取历史文件（不太可靠，但作为备选）
    try:
        history_file = get_shell_history_file()
        shell = os.environ.get('SHELL', '')
        
        with open(history_file, 'r', encoding='utf-8', errors='ignore') as f:
            history = f.readlines()
            
        if not history:
            return "未找到历史命令"
        
        # 获取最后一条命令（根据不同 shell 格式处理）
        last_entry = history[-1].strip()
        
        if 'zsh' in shell:
            # zsh 历史记录格式: ": timestamp:0;command"
            match = re.search(r';\s*(.*?)$', last_entry)
            if match:
                last_command = match.group(1)
            else:
                last_command = last_entry
        else:
            last_command = last_entry
            
        # 尝试执行命令以获取可能的错误（注意：这可能有副作用）
        os.environ["CAO_REPRODUCING_ERROR"] = "1"
        process = subprocess.Popen(
            last_command,
            shell=True,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
        returncode = process.returncode
        
        return {
            "command": last_command,
            "error": stderr or stdout,
            "returncode": returncode,
            "original_command": last_command
        }
            
    except Exception as e:
        return f"获取最后命令时出错: {str(e)}"
    
def get_command_by_number(number: int):
    """根据历史记录行号获取命令"""
    history_file = get_shell_history_file()
    shell = os.environ.get('SHELL', '')
    
    try:
        with open(history_file, 'r', encoding='utf-8', errors='ignore') as f:
            history = f.readlines()
        
        if number < 1 or number > len(history):
            return f"历史记录行号 {number} 超出范围 (1-{len(history)})"
        
        # 获取指定行号的命令
        command = history[number-1].strip()
        
        if 'zsh' in shell:
            # zsh 历史记录格式: ": timestamp:0;command"
            match = re.search(r';\s*(.*?)$', command)
            if match:
                command = match.group(1)
        
        # 使用Popen执行命令
        process = subprocess.Popen(
            command,
            shell=True,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
        returncode = process.returncode
        
        if returncode != 0:
            return {
                "command": command,
                "error": stderr or stdout,
                "returncode": returncode,
                "original_command": command  # 保存完整的原始命令
            }
        else:
            return {
                "command": command,
                "message": "这个命令执行成功，没有错误",
                "returncode": 0,
                "original_command": command  # 保存完整的原始命令
            }
            
    except Exception as e:
        return f"获取命令时出错: {str(e)}"

def execute_command(command: List[str]):
    """执行命令并捕获错误"""
    # 如果是处理ls命令
    if command and command[0] == 'ls' and len(command) > 1:
        # 直接使用subprocess.run但不使用shell=True，避免shell解析问题
        try:
            result = subprocess.run(
                command,
                shell=False,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True
            )
            if result.returncode != 0:
                return {
                    "command": ' '.join(command), 
                    "error": result.stderr or result.stdout,
                    "returncode": result.returncode,
                    "original_command": ' '.join(command)  # 保存完整的原始命令
                }
            else:
                print(result.stdout, end='')
                return None
        except Exception as e:
            return {
                "command": ' '.join(command),
                "error": str(e),
                "returncode": 1,
                "original_command": ' '.join(command)
            }
    else:
        # 对于其他命令，使用shell执行
        cmd = ' '.join(command)
        
        try:
            process = subprocess.Popen(
                cmd,
                shell=True,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()
            returncode = process.returncode
            
            if returncode != 0:
                return {
                    "command": cmd,
                    "error": stderr or stdout,
                    "returncode": returncode,
                    "original_command": cmd  # 保存完整的原始命令
                }
            else:
                print(stdout, end='')
                return None  # 成功执行，无需分析
        except Exception as e:
            return {
                "command": cmd,
                "error": str(e),
                "returncode": 1,
                "original_command": cmd
            }

def call_ai_api(model_config: Dict, error_info: Dict) -> str:
    """调用 AI API 分析错误"""
    # 根据选择的模型获取对应的 API KEY
    if "openai" in model_config["api_base"]:
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            return "错误: 未设置 OPENAI_API_KEY 环境变量"
    elif "deepseek" in model_config["api_base"]:
        api_key = os.environ.get('DEEPSEEK_API_KEY')
        if not api_key:
            return "错误: 未设置 DEEPSEEK_API_KEY 环境变量"
    else:
        return f"错误: 不支持的 API 基础 URL: {model_config['api_base']}"

    api_base = model_config["api_base"]
    model = model_config["model"]
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
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
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.7,
    }

    try:
        response = requests.post(
            f"{api_base}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
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
    for line in text.split('\n'):
        if get_string_display_width(line) <= content_width:
            lines.append(line)
        else:
            # 长行分割
            # 对于中文文本，按字符分割会更好
            is_cjk_text = any(ord(c) > 127 for c in line)
            
            if is_cjk_text:
                # 中文文本按字符拆分
                current_line = ''
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
                words = line.split(' ')
                current_line = ''
                for word in words:
                    test_line = current_line + (' ' if current_line else '') + word
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
    print('╭' + '─' * border_width + '╮')
    
    # 打印标题行
    title = "\033[1;36mAI 分析结果\033[0m"
    # 计算标题文本的实际显示宽度（不包括ANSI转义序列）
    title_display_width = get_string_display_width("AI 分析结果")
    # 计算需要的填充空格数量
    padding = ' ' * (content_width - title_display_width)
    print('│ ' + title + padding + ' │')
    
    # 打印分隔线
    print('├' + '─' * border_width + '┤')
    
    # 打印内容行
    for line in lines:
        # 计算填充空格，考虑显示宽度而不是字符数
        display_width = get_string_display_width(line)
        padding = ' ' * (content_width - display_width)
        print('│ ' + line + padding + ' │')
    
    # 打印下边框
    print('╰' + '─' * border_width + '╯')

def main():
    """主函数"""
    args = parse_args()
    
    # 如果设置了调试标志，则设置环境变量以便在整个执行过程中使用
    if args.debug:
        os.environ["CAO_DEBUG_MODE"] = "1"
    
    error_info = None
    
    # 检查是否有预先执行的命令结果
    bypass_command = os.environ.get("CAO_BYPASS_COMMAND")
    bypass_error = os.environ.get("CAO_BYPASS_ERROR")
    bypass_returncode = os.environ.get("CAO_BYPASS_RETURN_CODE")
    
    # 检查测试文件（用于调试和测试）
    test_command_file = "test_command.txt"
    test_error_file = "test_error.txt"
    test_returncode_file = "test_returncode.txt"
    if os.path.exists(test_command_file) and os.path.exists(test_error_file) and os.path.exists(test_returncode_file):
        try:
            with open(test_command_file, 'r') as f:
                test_command = f.read().strip()
            with open(test_error_file, 'r') as f:
                test_error = f.read().strip()
            with open(test_returncode_file, 'r') as f:
                test_returncode = int(f.read().strip())
                
            # 使用测试文件中的命令和错误
            if args.debug:
                print("\n--- 使用测试文件的命令结果 ---")
                print(f"命令: {test_command}")
                print(f"返回码: {test_returncode}")
                print(f"错误信息: {test_error}")
                print("------------------------------\n")
                
            error_info = {
                "command": test_command,
                "original_command": test_command,
                "error": test_error,
                "returncode": test_returncode
            }
        except Exception as e:
            if args.debug:
                print(f"[DEBUG] 读取测试文件时出错: {str(e)}")
    elif bypass_command and bypass_error and bypass_returncode:
        # 使用预先执行的命令结果
        if args.debug:
            print("\n--- 使用预执行的命令结果 ---")
            print(f"命令: {bypass_command}")
            print(f"返回码: {bypass_returncode}")
            print(f"错误信息: {bypass_error}")
            print("------------------------------\n")
            
        error_info = {
            "command": bypass_command,
            "original_command": bypass_command,
            "error": bypass_error,
            "returncode": int(bypass_returncode)
        }
    elif args.command:
        # 如果提供了命令参数，执行该命令
        error_info = execute_command(args.command)
    elif args.number is not None:
        # 如果提供了行号参数，获取指定行号的命令
        error_info = get_command_by_number(args.number)
    else:
        # 默认分析最后一个命令
        error_info = get_last_command_error()
    
    if isinstance(error_info, str):
        print(f"错误: {error_info}")
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
        print(error_info.get('error', '无错误信息'))
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
