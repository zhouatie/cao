#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
cao - 一个捕获终端错误并使用 AI 分析的命令行工具
"""

from .cli.main import main as cli_main

# 作为包入口点
def main():
    """包的主入口点"""
    return cli_main()

if __name__ == "__main__":
    main()
