#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI API 客户端
"""

import os
import json
import requests
import re
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse


def filter_think_tags(content: str) -> str:
    """过滤掉模型响应中的 <think>...</think> 标签及其内容，
    并去除前后多余的空格和换行
    
    Args:
        content: 原始模型响应内容
        
    Returns:
        过滤、整理后的内容
    """
    # 使用正则表达式移除开头的 <think>...</think> 标签及其内容
    filtered = re.sub(r'^<think>.*?</think>\s*', '', content, flags=re.DOTALL)
    
    # 去除前后多余的空格和换行
    filtered = filtered.strip()
    
    return filtered


def call_ai_api(
    model_config: Dict,
    messages: List,
) -> str:
    """调用 AI API 分析错误或处理会话消息

    Args:
        model_config: 模型配置信息
        error_info: 错误信息字典，用于构建错误分析提示
        messages: 会话消息列表，如果提供则直接使用
    """
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

    # 直接使用提供的消息内容
    payload_messages = messages

    payload = {
        "model": model,
        "messages": payload_messages,
        "temperature": 0.7,
    }

    # debug 模式把消息打印出来
    # debug(f"将发送到AI的消息: {json.dumps(payload, indent=2, ensure_ascii=False)}")

    try:
        debug(f"发送请求到 {api_base}/chat/completions")
        # 打印请求头时对Authorization进行脱敏处理
        debug_headers = headers.copy()
        if "Authorization" in debug_headers:
            auth_value = debug_headers["Authorization"]
            if auth_value.startswith("Bearer "):
                token = auth_value[7:]  # 移除 "Bearer " 前缀
                if len(token) > 10:
                    # 保留前4位和后4位，中间用****替换
                    masked_token = token[:4] + "****" + token[-4:]
                    debug_headers["Authorization"] = f"Bearer {masked_token}"
                else:
                    debug_headers["Authorization"] = "Bearer ****"

        debug(f"请求头: {debug_headers}")

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
                    content = result["message"]["content"]
                    filtered_content = filter_think_tags(content)
                    return filtered_content
                else:
                    # 兜底处理
                    debug("使用兜底逻辑处理 Ollama 响应")
                    content = (
                        result.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "无法解析 Ollama API 响应")
                    )
                    filtered_content = filter_think_tags(content)
                    return filtered_content
            else:
                # OpenAI/DeepSeek 响应格式
                debug("使用标准 OpenAI 格式解析响应")
                content = result["choices"][0]["message"]["content"]
                filtered_content = filter_think_tags(content)
                return filtered_content
        else:
            error(f"API 请求失败 (状态码: {response.status_code}): {response.text}")
            return f"API 请求失败 (状态码: {response.status_code}): {response.text}"

    except Exception as e:
        error(f"调用 AI API 时出错: {str(e)}", exc_info=True)
        return f"调用 AI API 时出错: {str(e)}"
