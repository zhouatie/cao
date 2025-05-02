#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
命令执行和错误信息获取相关函数
"""

import os
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional, Union, Mapping


def execute_command(command: List[str]) -> Optional[Dict[str, Any]]:
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
