#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
命令行参数解析模块
"""

import argparse
from .. import config


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
    # 移除了命令参数，因为不再支持直接执行命令并分析错误

    return parser.parse_args()
