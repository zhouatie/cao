#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
交互式会话处理模块
"""

import signal
import sys
import time
import threading
from typing import Dict, List, Optional, Any

# 尝试导入prompt_toolkit相关库
try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import InMemoryHistory
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.styles import Style
except ImportError:
    from ..utils.logger import error, info
    import subprocess
    import sys

    info("首次使用交互模式，正在为您加载所需依赖...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "prompt_toolkit"]
        )
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import InMemoryHistory
        from prompt_toolkit.formatted_text import HTML
        from prompt_toolkit.styles import Style

        info("依赖加载完成！")
    except Exception as e:
        error(f"安装 prompt_toolkit 失败: {str(e)}")
        print("请手动安装 prompt_toolkit 库: pip install prompt_toolkit")
        sys.exit(1)

from ..utils.terminal import print_with_borders
from ..utils.logger import debug, error
from ..ai_client import call_ai_api


def handle_interactive_session(
    model_config: Dict[str, Any],
):
    """处理交互式对话会话

    Args:
        model_config: AI模型配置
        initial_error_info: 初始错误信息（如果有的话）
        is_chat_mode: 是否是聊天模式，默认为True
    """
    # 创建会话历史
    history = InMemoryHistory()

    # 设置样式
    style = Style.from_dict(
        {
            "prompt": "ansicyan bold",
        }
    )

    # 创建会话对象
    session = PromptSession(history=history)

    # 会话上下文，用于保持与AI的对话历史
    conversation_context = []

    # 当前角色类型
    current_role = "default"

    # 可用角色配置
    roles = {
        "default": {
            "name": "小草",
            "emoji": "🌱",
            "system_prompt": """你是小草 (cao)，一个友好、幽默的编程助手。
            你的性格特点：
            1. 轻松幽默，善于活跃气氛
            2. 对编程知识了如指掌，但表达方式轻松不严肃
            3. 能理解程序员的苦恼和笑话
            4. 善于用比喻和例子解释复杂概念
            5. 有时会开一些程序员才懂的玩笑

            请以轻松自然的口吻与用户交流，像朋友一样陪伴他们编程。如果用户提出技术问题，请提供准确但不呆板的解答。
            """,
            "greeting": "嗨！我是小草 🌱，你的编程闲聊伙伴！今天想聊点什么？技术问题、开发困扰，还是只是想放松一下大脑？我随时准备陪你唠嗑～",
        },
        "frontend": {
            "name": "前端专家",
            "emoji": "🧑‍💻",
            "system_prompt": """你是一位资深前端开发工程师，拥有多年的前端开发经验。
            你精通：
            1. 现代JavaScript框架(React, Vue, Angular等)
            2. CSS预处理器和现代布局技术
            3. 前端性能优化和最佳实践
            4. 响应式设计和移动端开发
            5. 前端工程化和构建工具

            请以专业、有深度但友好的方式回答用户关于前端开发的所有问题，提供具体的代码示例和实用建议。
            """,
            "greeting": "你好！我是前端专家 🧑‍💻，很高兴能协助你解决前端开发问题。无论是React组件设计、CSS布局难题，还是性能优化建议，我都能提供专业支持。有什么我能帮到你的吗？",
        },
        "backend": {
            "name": "后端专家",
            "emoji": "🧑‍💻",
            "system_prompt": """你是一位资深后端开发工程师，拥有丰富的系统架构和API设计经验。
            你精通：
            1. 服务器端编程语言(Python, Java, Go等)
            2. 数据库设计和优化(SQL和NoSQL)
            3. 微服务架构和API设计
            4. 高并发、高可用系统设计
            5. 安全最佳实践和性能调优

            请以专业、有深度但友好的方式回答用户关于后端开发的所有问题，提供具体的代码示例和实用建议。
            """,
            "greeting": "你好！我是后端专家 🔧，很高兴能协助你解决后端开发问题。无论是系统架构设计、数据库优化，还是API接口规范，我都能提供专业支持。有什么技术难题需要我帮助吗？",
        },
        "secretary": {
            "name": "智能秘书",
            "emoji": "📝",
            "system_prompt": """你是一位高效、贴心的智能秘书，擅长帮助用户管理生活与工作。
            你的专长：
            1. 日程安排和时间管理
            2. 任务分解和优先级排序
            3. 信息整理和总结
            4. 提供生活和工作建议
            5. 情感支持和积极鼓励

            请以体贴、专业、高效的方式帮助用户处理各种生活和工作上的事务，提供实用的建议和解决方案。
            """,
            "greeting": "你好！我是你的智能秘书 📝，随时准备帮你安排日程、整理任务、提供建议。无论是工作计划还是生活安排，我都能为你提供贴心的支持。今天有什么我可以帮到你的吗？",
        },
    }

    # 设置初始角色
    # 使用友好的聊天模式人设
    conversation_context.append(
        {
            "role": "system",
            "content": roles[current_role]["system_prompt"],
        }
    )
    conversation_context.append(
        {
            "role": "assistant",
            "content": roles[current_role]["greeting"],
        }
    )

    # 准备角色切换提示信息
    role_switch_guide = "💡 角色切换指令:\n"
    for cmd, role_info in roles.items():
        if cmd != "default":
            role_switch_guide += (
                f"/{cmd} - 与{role_info['name']} {role_info['emoji']} 沟通\n"
            )

    # 打印初始欢迎消息和角色切换指南
    welcome_message = f"{roles[current_role]['greeting']}\n\n{role_switch_guide}"
    print_with_borders(welcome_message, mode="chat")

    # 设置信号处理，优雅地处理Ctrl+C
    def signal_handler(sig, frame):
        print("\n退出对话模式")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # 持续对话循环
    while True:
        try:
            # 获取用户输入
            user_input = session.prompt(
                HTML(
                    f"<ansicyan><b>cao {roles[current_role]['emoji']} > </b></ansicyan>"
                ),
                style=style,
            )

            # 检查退出命令
            if user_input.strip().lower() in ["/exit", "/quit", "exit", "quit"]:
                print("\n退出对话模式")
                break

            # 检查角色切换命令或直接发送给特定角色的内容
            if user_input.strip().startswith("/"):
                # 检查是否是 "/角色 内容" 格式
                parts = user_input.strip()[1:].split(" ", 1)
                cmd = parts[0].lower()
                
                # 如果是 "/角色 内容" 格式
                if cmd in roles and len(parts) > 1:
                    content = parts[1].strip()
                    if not content:  # 如果内容为空，则只切换角色
                        print(f"\n请在命令后输入内容，例如：/{cmd} 你好\n")
                        continue
                        
                    # 切换角色
                    old_role = current_role
                    current_role = cmd
                    
                    # 更新系统提示
                    for i, msg in enumerate(conversation_context):
                        if msg["role"] == "system":
                            conversation_context[i] = {
                                "role": "system",
                                "content": roles[current_role]["system_prompt"],
                            }
                            break
                    
                    # 添加角色切换通知（静默，不显示）
                    # 因为我们要直接响应内容，所以不显示角色切换提示
                    
                    # 添加用户消息到上下文
                    conversation_context.append({"role": "user", "content": content})
                    
                    # 调用AI API获取响应
                    loading_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
                    print("", end="\r")
                    i = 0

                    # 创建结果容器
                    response_result = {"ai_response": None, "error": None, "done": False}

                    # 定义API调用线程函数
                    def api_call_thread():
                        try:
                            response_result["ai_response"] = call_ai_api(
                                model_config, messages=conversation_context
                            )
                        except Exception as e:
                            # 如果API调用失败，记录错误
                            error(f"AI API调用出错: {str(e)}", exc_info=True)
                            response_result["error"] = str(e)
                        finally:
                            response_result["done"] = True

                    # 启动API调用线程
                    thread = threading.Thread(target=api_call_thread)
                    thread.daemon = True  # 设置为守护线程，这样主线程退出时它会自动退出
                    thread.start()

                    # 显示加载动画，直到API调用完成
                    start_time = time.time()
                    while not response_result["done"]:
                        if time.time() - start_time > 0.1:  # 每100ms更新一次
                            print(
                                f"\r{loading_chars[i % len(loading_chars)]} ",
                                end="",
                                flush=True,
                            )
                            i += 1
                            start_time = time.time()
                        time.sleep(0.01)  # 小的睡眠以减少CPU使用

                    # 清除加载动画
                    print("\r" + " " * 50 + "\r", end="", flush=True)

                    # 处理结果
                    if response_result["error"]:
                        ai_response = f"抱歉，我遇到了一些问题: {response_result['error']}"
                    else:
                        ai_response = response_result["ai_response"]

                    # 添加AI响应到上下文
                    conversation_context.append({"role": "assistant", "content": ai_response})

                    # 打印当前角色名称和AI响应，采用聊天风格显示
                    print(
                        f"\n\033[1;32m{roles[current_role]['name']}{roles[current_role]['emoji']}\033[0m:"
                    )
                    # 逐字打印回复，增加互动感
                    for char in ai_response:
                        print(char, end="", flush=True)
                        time.sleep(0.005)  # 每个字符间隔5毫秒，保持流畅
                    print("\n")  # 增加额外的空行，为用户输入提供更多空间

                    continue  # 跳过下面的处理，直接回到循环开始
                elif cmd in roles:
                    # 纯切换角色命令，只显示切换通知，不调用AI API
                    current_role = cmd
                    # 更新系统提示
                    # 找到并更新系统消息
                    for i, msg in enumerate(conversation_context):
                        if msg["role"] == "system":
                            conversation_context[i] = {
                                "role": "system",
                                "content": roles[current_role]["system_prompt"],
                            }
                            break

                    # 添加角色切换通知
                    print_with_borders(
                        f"已切换到 {roles[current_role]['name']} {roles[current_role]['emoji']} 模式",
                        mode="chat",
                    )
                    
                    # 不需要显示AI的响应，只需要显示通知
                    continue
                else:
                    print(f"\n未知命令: {user_input}\n")
                    continue

            # 如果输入为空，则跳过
            if not user_input.strip():
                continue

            # 添加用户消息到上下文
            conversation_context.append({"role": "user", "content": user_input})

            # 调用AI API获取响应 - 使用多线程处理
            loading_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
            print("", end="\r")
            i = 0

            # 创建结果容器
            response_result = {"ai_response": None, "error": None, "done": False}

            # 定义API调用线程函数
            def api_call_thread():
                try:
                    response_result["ai_response"] = call_ai_api(
                        model_config, messages=conversation_context
                    )
                except Exception as e:
                    # 如果API调用失败，记录错误
                    error(f"AI API调用出错: {str(e)}", exc_info=True)
                    response_result["error"] = str(e)
                finally:
                    response_result["done"] = True

            # 启动API调用线程
            thread = threading.Thread(target=api_call_thread)
            thread.daemon = True  # 设置为守护线程，这样主线程退出时它会自动退出
            thread.start()

            # 显示加载动画，直到API调用完成
            start_time = time.time()
            while not response_result["done"]:
                if time.time() - start_time > 0.1:  # 每100ms更新一次
                    print(
                        f"\r{loading_chars[i % len(loading_chars)]} ",
                        end="",
                        flush=True,
                    )
                    i += 1
                    start_time = time.time()
                time.sleep(0.01)  # 小的睡眠以减少CPU使用

            # 清除加载动画
            print("\r" + " " * 50 + "\r", end="", flush=True)

            # 处理结果
            if response_result["error"]:
                ai_response = f"抱歉，我遇到了一些问题: {response_result['error']}"
            else:
                ai_response = response_result["ai_response"]

            # 添加AI响应到上下文
            conversation_context.append({"role": "assistant", "content": ai_response})

            # 打印当前角色名称和AI响应，采用聊天风格显示
            print(
                f"\n\033[1;32m{roles[current_role]['name']}{roles[current_role]['emoji']}\033[0m:"
            )
            # 逐字打印回复，增加互动感
            for char in ai_response:
                print(char, end="", flush=True)
                time.sleep(0.005)  # 每个字符间隔5毫秒，保持流畅
            print("\n")  # 增加额外的空行，为用户输入提供更多空间

            # 如果对话历史太长，清理最早的对话（保留system消息）
            if len(conversation_context) > 20:
                # 保留system消息和最近的对话
                system_messages = [
                    msg for msg in conversation_context if msg["role"] == "system"
                ]
                recent_messages = conversation_context[-10:]
                conversation_context = system_messages + recent_messages
                debug("对话历史已清理，保留system消息和最近10条对话")

        except KeyboardInterrupt:
            # 处理Ctrl+C
            print("\n退出对话模式")
            break
        except EOFError:
            # 处理Ctrl+D
            print("\n退出对话模式")
            break
        except Exception as e:
            error(f"对话模式出错: {str(e)}", exc_info=True)
            print(f"出现错误: {str(e)}")
            # 尝试继续对话
