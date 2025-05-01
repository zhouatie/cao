#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
命令行接口模块 - 入口点
"""

# 从CLI包导入必要的功能
from .cli.main import main as main_func

# 重命名为 main 以保持兼容性
main = main_func

# 公开主要的接口
__all__ = ["main"]
