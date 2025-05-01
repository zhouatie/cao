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


def print_with_borders(text: str):
    """打印带边框的文本"""
    terminal_width, _ = get_terminal_size()
    content_width = min(terminal_width - 4, 100)  # 最大内容宽度限制

    # 处理文本换行
    lines = []
    for line in text.split("\n"):
        if get_string_display_width(line) <= content_width:
            lines.append(line)
        else:
            # 长行分割
            # 对于中文文本，按字符分割会更好
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

    # 计算边框宽度为内容宽度+2（两侧各1个空格）
    border_width = content_width + 2

    # 打印上边框
    print("╭" + "─" * border_width + "╮")

    # 打印标题行
    title = "\033[1;36mAI 分析结果\033[0m"
    # 计算标题文本的实际显示宽度（不包括ANSI转义序列）
    title_display_width = get_string_display_width("AI 分析结果")
    # 计算需要的填充空格数量
    padding = " " * (content_width - title_display_width)
    print("│ " + title + padding + " │")

    # 打印分隔线
    print("├" + "─" * border_width + "┤")

    # 打印内容行
    for line in lines:
        # 计算填充空格，考虑显示宽度而不是字符数
        display_width = get_string_display_width(line)
        padding = " " * (content_width - display_width)
        print("│ " + line + padding + " │")

    # 打印下边框
    print("╰" + "─" * border_width + "╯")
