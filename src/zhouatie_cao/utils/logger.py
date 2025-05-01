#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一的日志记录模块，提供调试和错误日志功能
"""

import os
import sys
import logging
from typing import Any, Optional, Dict
import inspect
import datetime

# 日志级别映射
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

# 默认配置
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 彩色日志配置
COLORS = {
    "DEBUG": "\033[36m",  # 青色
    "INFO": "\033[32m",  # 绿色
    "WARNING": "\033[33m",  # 黄色
    "ERROR": "\033[31m",  # 红色
    "CRITICAL": "\033[35m",  # 紫色
    "RESET": "\033[0m",  # 重置
}

# 全局日志记录器字典
loggers = {}


class ColoredFormatter(logging.Formatter):
    """自定义的彩色日志格式化器"""

    def format(self, record):
        """格式化日志记录"""
        # 保存原始的levelname
        levelname = record.levelname
        # 添加颜色
        if levelname in COLORS and sys.stdout.isatty():
            record.levelname = f"{COLORS[levelname]}{levelname}{COLORS['RESET']}"

        # 调用父类的format方法
        result = super().format(record)

        # 恢复原始的levelname
        record.levelname = levelname
        return result


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    获取或创建一个命名的日志记录器

    Args:
        name: 日志记录器名称，默认使用调用者的模块名

    Returns:
        logging.Logger: 配置好的日志记录器
    """
    # 如果没有提供名称，尝试获取调用模块的名称
    if name is None:
        # 获取调用方的栈帧
        frame = inspect.currentframe()
        if frame:
            try:
                frame = frame.f_back
                if frame and "f_globals" in dir(frame) and frame.f_globals and frame.f_globals.get("__name__"):
                    name = frame.f_globals["__name__"]
                else:
                    name = "root"  # 默认名称
            finally:
                del frame  # 避免循环引用
        else:
            name = "root"  # 默认名称

    # 检查是否已经创建过这个logger
    if name in loggers:
        return loggers[name]

    # 创建新的logger
    logger = logging.getLogger(name)

    # 读取环境变量中的日志级别设置
    log_level_name = os.environ.get("CAO_LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
    log_level = LOG_LEVELS.get(log_level_name, logging.INFO)

    # 只有在没有处理器的情况下才添加新的处理器
    if not logger.handlers:
        # 设置日志级别
        logger.setLevel(log_level)

        # 创建控制台处理器
        handler = logging.StreamHandler()
        handler.setLevel(log_level)

        # 创建格式化器
        log_format = os.environ.get("CAO_LOG_FORMAT", DEFAULT_LOG_FORMAT)
        date_format = os.environ.get("CAO_LOG_DATE_FORMAT", DEFAULT_DATE_FORMAT)
        formatter = ColoredFormatter(log_format, date_format)

        # 将格式化器添加到处理器
        handler.setFormatter(formatter)

        # 将处理器添加到记录器
        logger.addHandler(handler)

        # 防止日志传递到根记录器
        logger.propagate = False

    # 保存日志记录器的引用
    loggers[name] = logger
    return logger


def is_debug_mode() -> bool:
    """
    检查是否处于调试模式

    Returns:
        bool: 是否启用了调试模式
    """
    return (
        os.environ.get("CAO_DEBUG_MODE") == "1"
        or os.environ.get("CAO_LOG_LEVEL", "").upper() == "DEBUG"
    )


def debug(msg: Any, *args, **kwargs):
    """
    记录调试级别的消息

    Args:
        msg: 日志消息
        *args: 传递给日志记录器的参数
        **kwargs: 传递给日志记录器的关键字参数
    """
    caller_frame = inspect.currentframe()
    if caller_frame:
        caller_frame = caller_frame.f_back
        caller_module = caller_frame.f_globals["__name__"] if caller_frame else "root"
    else:
        caller_module = "root"
    get_logger(caller_module).debug(msg, *args, **kwargs)


def info(msg: Any, *args, **kwargs):
    """
    记录信息级别的消息

    Args:
        msg: 日志消息
        *args: 传递给日志记录器的参数
        **kwargs: 传递给日志记录器的关键字参数
    """
    caller_frame = inspect.currentframe()
    if caller_frame:
        caller_frame = caller_frame.f_back
        caller_module = caller_frame.f_globals["__name__"] if caller_frame else "root"
    else:
        caller_module = "root"
    get_logger(caller_module).info(msg, *args, **kwargs)


def warning(msg: Any, *args, **kwargs):
    """
    记录警告级别的消息

    Args:
        msg: 日志消息
        *args: 传递给日志记录器的参数
        **kwargs: 传递给日志记录器的关键字参数
    """
    caller_frame = inspect.currentframe()
    if caller_frame:
        caller_frame = caller_frame.f_back
        caller_module = caller_frame.f_globals["__name__"] if caller_frame else "root"
    else:
        caller_module = "root"
    get_logger(caller_module).warning(msg, *args, **kwargs)


def error(msg: Any, *args, **kwargs):
    """
    记录错误级别的消息

    Args:
        msg: 日志消息
        *args: 传递给日志记录器的参数
        **kwargs: 传递给日志记录器的关键字参数
    """
    caller_frame = inspect.currentframe()
    if caller_frame:
        caller_frame = caller_frame.f_back
        caller_module = caller_frame.f_globals["__name__"] if caller_frame else "root"
    else:
        caller_module = "root"
    get_logger(caller_module).error(msg, *args, **kwargs)


def critical(msg: Any, *args, **kwargs):
    """
    记录严重错误级别的消息

    Args:
        msg: 日志消息
        *args: 传递给日志记录器的参数
        **kwargs: 传递给日志记录器的关键字参数
    """
    caller_frame = inspect.currentframe()
    if caller_frame:
        caller_frame = caller_frame.f_back
        caller_module = caller_frame.f_globals["__name__"] if caller_frame else "root"
    else:
        caller_module = "root"
    get_logger(caller_module).critical(msg, *args, **kwargs)


def log_function_call(func):
    """
    函数装饰器，记录函数调用的参数和返回值

    Args:
        func: 被装饰的函数

    Returns:
        装饰后的函数
    """

    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)

        # 只在调试模式下记录详细信息
        if is_debug_mode():
            # 记录函数调用
            arg_str = ", ".join([repr(a) for a in args])
            kwarg_str = ", ".join([f"{k}={repr(v)}" for k, v in kwargs.items()])
            all_args = ", ".join(filter(None, [arg_str, kwarg_str]))
            logger.debug(f"调用 {func.__name__}({all_args})")

            # 记录开始时间
            start_time = datetime.datetime.now()

        # 执行函数
        try:
            result = func(*args, **kwargs)

            # 只在调试模式下记录详细信息
            if is_debug_mode():
                # 计算执行时间
                end_time = datetime.datetime.now()
                duration = (end_time - start_time).total_seconds()

                # 记录返回值和执行时间
                logger.debug(
                    f"{func.__name__} 返回: {repr(result)[:200]}... (执行时间: {duration:.6f}秒)"
                )

            return result

        except Exception as e:
            # 记录异常
            logger.exception(f"{func.__name__} 抛出异常: {str(e)}")
            raise

    # 保留原始函数的元数据
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    wrapper.__module__ = func.__module__

    return wrapper


# 初始化根记录器
def setup_root_logger():
    """初始化根记录器"""
    root_logger = get_logger("root")
    # 读取环境变量中的日志级别设置
    log_level_name = os.environ.get("CAO_LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
    log_level = LOG_LEVELS.get(log_level_name, logging.INFO)
    root_logger.setLevel(log_level)
    return root_logger


# 初始化根记录器
root_logger = setup_root_logger()
