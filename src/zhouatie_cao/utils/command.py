#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
命令执行和错误信息获取相关函数
"""

import os
import subprocess
import threading
import time
from typing import Dict, List, Optional, Union


def execute_command(command: List[str]) -> Optional[Dict[str, str]]:
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


def get_last_command_error() -> Dict[str, Union[str, int]]:
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
