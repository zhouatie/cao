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
    parser.add_argument("-l", "--last", action="store_true", 
                        help="分析最近一次命令的错误")
    parser.add_argument("-n", "--number", type=int, default=100,
                        help="分析历史记录中特定行号的错误")
    parser.add_argument("-d", "--debug", action="store_true",
                        help="开启调试模式")
    parser.add_argument("command", nargs="*", help="要执行的命令")
    
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
    history_file = get_shell_history_file()
    shell = os.environ.get('SHELL', '')
    
    try:
        with open(history_file, 'r', encoding='utf-8', errors='ignore') as f:
            history = f.readlines()
            
        if not history:
            return "未找到历史命令"
        
        # 获取最后一条命令（根据不同 shell 格式处理）
        last_command = history[-1].strip()
        
        if 'zsh' in shell:
            # zsh 历史记录格式: ": timestamp:0;command"
            match = re.search(r';\s*(.*?)$', last_command)
            if match:
                last_command = match.group(1)
        
        # 执行命令并捕获错误
        result = subprocess.run(
            last_command, 
            shell=True, 
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True
        )
        
        if result.returncode != 0:
            return {
                "command": last_command,
                "error": result.stderr or result.stdout,
                "returncode": result.returncode
            }
        else:
            return {
                "command": last_command,
                "message": "这个命令执行成功，没有错误",
                "returncode": 0
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
        
        # 执行命令并捕获错误
        result = subprocess.run(
            command, 
            shell=True, 
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True
        )
        
        if result.returncode != 0:
            return {
                "command": command,
                "error": result.stderr or result.stdout,
                "returncode": result.returncode
            }
        else:
            return {
                "command": command,
                "message": "这个命令执行成功，没有错误",
                "returncode": 0
            }
            
    except Exception as e:
        return f"获取命令时出错: {str(e)}"

def execute_command(command: List[str]):
    """执行命令并捕获错误"""
    cmd = ' '.join(command)
    
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True
        )
        
        if result.returncode != 0:
            return {
                "command": cmd,
                "error": result.stderr or result.stdout,
                "returncode": result.returncode
            }
        else:
            print(result.stdout, end='')
            return None  # 成功执行，无需分析
    except Exception as e:
        return {
            "command": cmd,
            "error": str(e),
            "returncode": 1
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
    command = error_info.get("command", "未知命令")
    error_text = error_info.get("error", "未知错误")
    returncode = error_info.get("returncode", -1)
    
    system_message = "你是一个命令行错误分析专家。分析以下命令行错误并提供解决方案。"
    user_message = f"""
命令: {command}
返回码: {returncode}
错误信息:
{error_text}

请简洁地分析这个错误，并提供解决方案。
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

def print_with_borders(text: str):
    """打印带边框的文本"""
    terminal_width, _ = get_terminal_size()
    width = min(terminal_width - 4, 100)  # 最大宽度限制
    
    # 处理文本换行
    lines = []
    for line in text.split('\n'):
        if len(line) <= width:
            lines.append(line)
        else:
            # 长行分割
            words = line.split(' ')
            current_line = ''
            for word in words:
                if len(current_line) + len(word) + 1 <= width:
                    if current_line:
                        current_line += ' ' + word
                    else:
                        current_line = word
                else:
                    lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
    
    # 打印带边框的文本
    print('╭' + '─' * (width + 2) + '╮')
    print('│ \033[1;36mAI 分析结果\033[0m' + ' ' * (width - 9) + ' │')
    print('├' + '─' * (width + 2) + '┤')
    
    for line in lines:
        padding = ' ' * (width - len(line))
        print('│ ' + line + padding + ' │')
    
    print('╰' + '─' * (width + 2) + '╯')

def main():
    """主函数"""
    args = parse_args()
    
    error_info = None
    
    if args.last:
        error_info = get_last_command_error()
    elif args.number > 0:
        error_info = get_command_by_number(args.number)
    elif args.command:
        error_info = execute_command(args.command)
    else:
        print("错误: 请提供要执行的命令，或使用 --last/-l 分析最后一个命令")
        sys.exit(1)
    
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
        print(f"命令: {error_info.get('command', '未知命令')}")
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
