#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI API 客户端
"""

import os
import json
import requests
from typing import Dict, Any
from urllib.parse import urlparse


def call_ai_api(model_config: Dict, error_info: Dict) -> str:
    """调用 AI API 分析错误"""
    # 导入日志记录器
    from .utils.logger import get_logger, debug, info, warning, error, critical

    logger = get_logger(__name__)

    # 根据选择的模型获取对应的 API KEY
    # 针对不同的 API 获取对应的 API KEY

    # 处理不同的API提供商
    api_key = None
    api_provider = model_config.get("provider", "").lower()  # 优先使用provider字段
    api_base = model_config["api_base"]

    # 如果未指定provider，尝试从api_base推断
    if not api_provider:
        # 检查本地模型
        if "localhost" in api_base or "127.0.0.1" in api_base:
            api_provider = "ollama"
            debug(f"检测到本地模型: {api_provider}")
        else:
            # 从URL中提取可能的提供商名称
            # 移除了硬编码的提供商检测，改为从URL中提取域名部分作为提供商名称
            parsed_url = urlparse(api_base)
            domain = parsed_url.netloc
            debug(f"从URL提取域名: {domain}")

            # 如果域名包含端口，去掉端口
            if ":" in domain:
                domain = domain.split(":")[0]
                debug(f"去除端口后的域名: {domain}")

            # 提取域名中的主要部分，如 api.openai.com -> openai
            domain_parts = domain.split(".")
            if len(domain_parts) >= 2:
                # 尝试找到主域名部分
                if domain_parts[-2] not in ["com", "org", "net", "io"]:
                    api_provider = domain_parts[-2]
                else:
                    # 如果是二级域名，尝试获取子域名部分
                    if len(domain_parts) > 2:
                        api_provider = domain_parts[-3]
                debug(f"从域名提取的提供商: {api_provider}")

            # 如果无法从域名提取，尝试从路径中提取
            if not api_provider and parsed_url.path:
                path_parts = parsed_url.path.strip("/").split("/")
                if path_parts and path_parts[0] not in ["v1", "v2", "v3", "api"]:
                    api_provider = path_parts[0]
                    debug(f"从路径提取的提供商: {api_provider}")

            # 如果仍然无法确定提供商，使用完整域名
            if not api_provider:
                api_provider = domain.replace(".", "_")
                debug(f"使用完整域名作为提供商: {api_provider}")

    # 检查是否为不需要API密钥的本地模型
    if api_provider == "ollama" or "localhost" in api_base or "127.0.0.1" in api_base:
        # 本地模型不需要API key
        debug("本地模型不需要API密钥")
        api_key = None
    elif api_provider:
        # 任何其他提供商，统一从环境变量获取API密钥
        env_var_name = f"{api_provider.upper()}_API_KEY"
        api_key = os.environ.get(env_var_name)
        debug(f"尝试从环境变量获取API密钥: {env_var_name}")
        debug(f"API提供商: {api_provider}")

        # 尝试从配置中获取API密钥
        if not api_key and "api_key" in model_config:
            api_key = model_config["api_key"]
            debug("从模型配置中获取API密钥")

        # 如果存在兼容性标识符（如dashscope通过compatible-mode提供的OpenAI兼容接口）
        if not api_key and "compatible-mode" in api_base:
            # 从URL中提取实际提供商名称
            compat_provider = None
            if "dashscope" in api_base:
                compat_provider = "DASHSCOPE"
            elif "baichuan" in api_base:
                compat_provider = "BAICHUAN"

            if compat_provider:
                compat_env_var = f"{compat_provider}_API_KEY"
                api_key = os.environ.get(compat_env_var)
                debug(f"检测到兼容模式，尝试从环境变量获取API密钥: {compat_env_var}")

                if api_key:
                    debug(f"从兼容模式环境变量成功获取API密钥")

        if not api_key:
            error(f"未设置 {env_var_name} 环境变量，也未在配置中提供API密钥")
            return f"错误: 未设置 {env_var_name} 环境变量，也未在配置中提供API密钥"
    else:
        error("无法确定API提供商")
        return f"错误: 无法确定API提供商，请在配置中指定provider字段或使用标准URL格式"

    api_base = model_config["api_base"]
    model = model_config["model"]

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    # 构建提示信息
    # 优先使用原始命令（如果存在）
    command = error_info.get("original_command", error_info.get("command", "未知命令"))
    error_text = error_info.get("error", "未知错误")
    returncode = error_info.get("returncode", -1)

    # 调试输出，帮助排查命令传递问题
    debug(f"将发送到AI的命令: {command}")

    system_message = """你是一个命令行错误分析专家。
请分析以下命令错误并提供解决方案。重要提示：你接收的命令是用户真实输入的，不要猜测他输入了其他命令。
例如，如果错误显示命令未找到，请分析实际给出的命令，而不是猜测用户可能想输入的其他命令。"""

    user_message = f"""
命令: {command}
返回码: {returncode}
错误信息:
{error_text}

请分析这个特定命令产生的错误，并提供准确的解决方案。避免猜测用户可能想要运行的其他命令，除非错误信息明确显示命令被系统解析为其他内容。
"""

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.7,
    }

    try:
        debug(f"发送请求到 {api_base}/chat/completions")
        debug(f"请求头: {headers}")

        response = requests.post(
            f"{api_base}/chat/completions", headers=headers, json=payload, timeout=30
        )

        debug(f"API响应状态码: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            debug("API请求成功，解析响应")

            # Ollama API 与 OpenAI API 有稍微不同的响应格式
            if "localhost" in api_base or "127.0.0.1" in api_base:
                debug("检测到本地 Ollama API 格式")
                # Ollama 响应格式
                if "message" in result and "content" in result["message"]:
                    debug("成功从 Ollama 响应中提取内容")
                    return result["message"]["content"]
                else:
                    # 兜底处理
                    debug("使用兜底逻辑处理 Ollama 响应")
                    return (
                        result.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "无法解析 Ollama API 响应")
                    )
            else:
                # OpenAI/DeepSeek 响应格式
                debug("使用标准 OpenAI 格式解析响应")
                return result["choices"][0]["message"]["content"]
        else:
            error(f"API 请求失败 (状态码: {response.status_code}): {response.text}")
            return f"API 请求失败 (状态码: {response.status_code}): {response.text}"

    except Exception as e:
        error(f"调用 AI API 时出错: {str(e)}", exc_info=True)
        return f"调用 AI API 时出错: {str(e)}"
