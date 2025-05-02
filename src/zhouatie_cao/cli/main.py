#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
命令行主逻辑模块
"""

import os
import sys
import threading
import time
import logging
from typing import Dict, Any

from .. import config
from ..utils.terminal import print_with_borders
from ..utils.command import execute_command
from ..ai_client import call_ai_api
from ..utils.logger import get_logger, debug, info, error

# 获取日志记录器
logger = get_logger(__name__)

# 导入CLI模块
from .parser import parse_args
from .interactive import handle_interactive_session


def main():
    """主函数"""
    args = parse_args()

    # 如果用户请求配置，则运行配置界面
    if args.config:
        from .. import config_cli

        config_cli.interactive_config()
        sys.exit(0)

    # 如果设置了调试标志，则设置环境变量以便在整个执行过程中使用
    if args.debug:
        os.environ["CAO_DEBUG_MODE"] = "1"
        os.environ["CAO_LOG_LEVEL"] = "DEBUG"
        logger.setLevel(logging.DEBUG)
        debug("调试模式已启用")

    error_info = None

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
        debug(f"选择的模型配置: {model_config}")

    # 直接进入持续会话模式
    handle_interactive_session(model_config)
