#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Configuration management for cao tool
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

# Default configuration
DEFAULT_CONFIG = {
    "models": {
        "deepseek": {"api_base": "https://api.deepseek.com/v1", "model": "deepseek-coder", "provider": "deepseek"},
        "openai": {"api_base": "https://api.openai.com/v1", "model": "gpt-4o", "provider": "openai"},
        "ollama": {"api_base": "http://localhost:11434/v1", "model": "qwen2.5-coder:7b", "provider": "ollama"},
    },
    "default_model": "deepseek"
}

def get_config_dir() -> Path:
    """Get the configuration directory path."""
    # Use XDG_CONFIG_HOME if available, otherwise use ~/.cao
    xdg_config_home = os.environ.get('XDG_CONFIG_HOME')
    if xdg_config_home:
        config_dir = Path(xdg_config_home) / "cao"
    else:
        config_dir = Path.home() / ".cao"
    
    # Ensure directory exists
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir

def get_config_file() -> Path:
    """Get the configuration file path."""
    return get_config_dir() / "config.json"

def load_config() -> Dict[str, Any]:
    """Load configuration from file or return defaults."""
    config_file = get_config_file()
    
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                user_config = json.load(f)
            
            # Merge with defaults to ensure all required fields exist
            # Start with default config
            config = DEFAULT_CONFIG.copy()
            
            # Override with user config
            if "models" in user_config:
                config["models"].update(user_config["models"])
            
            if "default_model" in user_config:
                if user_config["default_model"] in config["models"]:
                    config["default_model"] = user_config["default_model"]
            
            return config
        except Exception as e:
            print(f"Error loading config file: {e}")
            return DEFAULT_CONFIG
    else:
        # Create default config if it doesn't exist
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG

def save_config(config: Dict[str, Any]) -> bool:
    """Save configuration to file."""
    config_file = get_config_file()
    
    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving config file: {e}")
        return False

def add_model(name: str, api_base: str, model: str, api_key: Optional[str] = None) -> bool:
    """Add or update a model in the configuration."""
    config = load_config()
    
    # Update or add the model
    model_config = {
        "api_base": api_base,
        "model": model,
        "provider": name  # 添加provider字段，默认与模型名称相同
    }
    
    # 如果提供了API密钥，也添加到配置中
    if api_key:
        model_config["api_key"] = api_key
    
    config["models"][name] = model_config
    
    return save_config(config)

def remove_model(name: str) -> bool:
    """Remove a model from the configuration."""
    config = load_config()
    
    # Check if model exists
    if name not in config["models"]:
        return False
    
    # Check if it's the default model
    if name == config["default_model"]:
        return False
    
    # Remove the model
    del config["models"][name]
    return save_config(config)

def set_default_model(name: str) -> bool:
    """Set the default model."""
    config = load_config()
    
    # Check if model exists
    if name not in config["models"]:
        return False
    
    # Set as default
    config["default_model"] = name
    return save_config(config)

def get_supported_models() -> Dict[str, Dict[str, str]]:
    """Get all supported models from config."""
    config = load_config()
    return config["models"]

def get_default_model() -> str:
    """Get the default model name."""
    config = load_config()
    return config["default_model"]
