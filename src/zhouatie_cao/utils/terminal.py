#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
终端相关的辅助函数
"""

import os
import platform

# 根据平台导入不同的模块
_IS_WINDOWS = platform.system() == "Windows"

# 在非Windows平台上导入Unix特定的模块
if not _IS_WINDOWS:
    try:
        import fcntl
        import termios
        import struct
    except ImportError:
        pass


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


def get_string_display_width(s: str) -> int:
    """获取字符串在终端中的显示宽度，考虑中文等宽字符"""
    width = 0
    for char in s:
        # 中文字符宽字符通常显示宽度为2
        if ord(char) > 127:
            width += 2
        else:
            width += 1
    return width


def _process_text_to_lines(text: str, content_width: int) -> list:
    """处理文本换行，将文本按照指定宽度拆分成多行

    Args:
        text: 要处理的文本
        content_width: 内容区域宽度

    Returns:
        list: 拆分后的文本行列表
    """
    lines = []
    for line in text.split("\n"):
        if get_string_display_width(line) <= content_width:
            lines.append(line)
        else:
            # 长行分割
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

    return lines


def _print_normal_mode(text: str):
    """以标准模式（带边框）打印文本

    Args:
        text: 要打印的文本
    """
    terminal_width, _ = get_terminal_size()
    content_width = terminal_width - 4  # 左右各2个字符的边框

    # 处理文本换行
    lines = _process_text_to_lines(text, content_width)

    # 绘制边框和内容
    horizontal_border = "─" * (terminal_width - 2)
    print(f"┌{horizontal_border}┐")

    # 添加小草标题行
    title = "\033[1;32m小草 🌱\033[0m"
    # 计算标题文本的实际显示宽度（不包括ANSI颜色代码）
    title_display_width = get_string_display_width("小草 🌱")
    title_padding = " " * (content_width - title_display_width)
    print(f"│ {title}{title_padding} │")

    # 添加分隔线
    print(f"├{horizontal_border}┤")

    # 打印正文内容
    for line in lines:
        padding = " " * (content_width - get_string_display_width(line))
        print(f"│ {line}{padding} │")

    print(f"└{horizontal_border}┘")


def _print_chat_mode(text: str):
    """以聊天模式（带前缀）打印文本

    Args:
        text: 要打印的文本
    """
    terminal_width, _ = get_terminal_size()

    # 处理文本换行
    lines = _process_text_to_lines(text, terminal_width)

    # 小草消息使用绿色前缀
    prefix = "\033[1;32m小草 🌱\033[0m: "
    print(prefix)
    for line in lines:
        print(line)


def print_with_borders(text: str, mode: str = "normal", role: str = "assistant"):
    """打印文本，添加边框或前缀

    Args:
        text: 要打印的文本
        mode: 打印模式，可选值：normal(标准模式), chat(聊天模式)
        role: 消息角色，可选值: assistant(小草消息), user(用户消息)
    """
    # 用户消息不需要显示，因为CLI中已经有"cao 🌿 > "前缀
    if role != "assistant":
        return

    # 根据模式选择相应的打印函数
    if mode == "normal":
        _print_normal_mode(text)
    else:
        _print_chat_mode(text)

    # 打印额外的换行符以增加间距
    # print()
