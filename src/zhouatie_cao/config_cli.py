#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Configuration command-line interface for cao
"""

import sys
import argparse
import json
from . import config


def list_models():
    """List all configured models"""
    models = config.get_supported_models()
    default_model = config.get_default_model()

    print("\n现有配置的模型:")
    print("-" * 60)
    print(f"{'模型名称':<15} {'默认':<8} {'API基础URL':<25} {'模型名'}")
    print("-" * 60)

    for name, model_config in models.items():
        is_default = "✓" if name == default_model else ""
        print(
            f"{name:<15} {is_default:<8} {model_config['api_base']:<25} {model_config['model']}"
        )

    print("-" * 60)


def add_model(args):
    """Add or update a model"""
    result = config.add_model(args.name, args.api_base, args.model, getattr(args, 'api_key', None))
    if result:
        print(f"已成功添加/更新模型 '{args.name}'")
    else:
        print(f"添加/更新模型 '{args.name}' 失败")


def remove_model(args):
    """Remove a model"""
    result = config.remove_model(args.name)
    if result:
        print(f"已成功删除模型 '{args.name}'")
    else:
        print(f"无法删除模型 '{args.name}'。它可能是默认模型或不存在。")


def set_default(args):
    """Set default model"""
    result = config.set_default_model(args.name)
    if result:
        print(f"已将 '{args.name}' 设置为默认模型")
    else:
        print(f"无法将 '{args.name}' 设置为默认模型。请确认该模型已配置。")


def export_config(args):
    """Export configuration to stdout or file"""
    cfg = config.load_config()

    if args.file:
        try:
            with open(args.file, "w") as f:
                json.dump(cfg, f, indent=2)
            print(f"配置已导出到 {args.file}")
        except Exception as e:
            print(f"导出配置失败: {e}")
    else:
        print(json.dumps(cfg, indent=2))


def import_config(args):
    """Import configuration from file"""
    try:
        with open(args.file, "r") as f:
            cfg = json.load(f)

        # Validate config format
        if "models" not in cfg or not isinstance(cfg["models"], dict):
            print("错误: 导入的配置文件格式不正确。必须包含 'models' 字典。")
            return

        if "default_model" not in cfg or not isinstance(cfg["default_model"], str):
            print("错误: 导入的配置文件格式不正确。必须包含 'default_model' 字符串。")
            return

        # Save the imported config
        result = config.save_config(cfg)
        if result:
            print("配置已成功导入")
        else:
            print("导入配置失败")
    except json.JSONDecodeError:
        print("错误: 导入的文件不是有效的 JSON 格式")
    except Exception as e:
        print(f"导入配置失败: {e}")


def config_path(args):
    """Show configuration file path"""
    config_file = config.get_config_file()
    print(f"配置文件路径: {config_file}")


def interactive_config():
    """Interactive configuration mode"""
    print("\n欢迎使用 cao 配置向导！")
    print("=" * 50)

    # List current models
    list_models()

    while True:
        print("\n可用操作:")
        print("1. 添加/更新模型")
        print("2. 删除模型")
        print("3. 设置默认模型")
        print("4. 退出")

        choice = input("\n请选择操作 [1-4]: ").strip()

        if choice == "1":
            name = input("输入供应商名称(英文): ").strip()
            api_base = input("输入 API 基础 URL: ").strip()
            model = input("输入模型名称: ").strip()
            api_key = input("输入API密钥 (可选，留空则使用环境变量): ").strip()

            if name and api_base and model:
                # 如果API密钥为空，传递None
                result = config.add_model(name, api_base, model, api_key if api_key else None)
                if result:
                    print(f"已成功添加/更新模型 '{name}'")
                else:
                    print(f"添加/更新模型 '{name}' 失败")
            else:
                print("错误: 供应商名称、API基础URL和模型名称都必须填写")

        elif choice == "2":
            models = config.get_supported_models()
            default = config.get_default_model()

            print("\n可移除的模型:")
            for name in models:
                if name != default:
                    print(f"- {name}")

            name = input("\n输入要删除的模型名称 (或按回车返回): ").strip()
            if not name:
                continue

            if name == default:
                print(f"错误: 无法删除默认模型 '{name}'")
                continue

            if name not in models:
                print(f"错误: 模型 '{name}' 不存在")
                continue

            confirm = input(f"确认删除模型 '{name}'? [y/N]: ").strip().lower()
            if confirm == "y":
                result = config.remove_model(name)
                if result:
                    print(f"已成功删除模型 '{name}'")
                else:
                    print(f"删除模型 '{name}' 失败")
            else:
                print("操作已取消")

        elif choice == "3":
            models = list(config.get_supported_models().keys())
            default = config.get_default_model()

            print("\n可用模型:")
            for name in models:
                mark = " (当前默认)" if name == default else ""
                print(f"- {name}{mark}")

            name = input("\n输入要设为默认的模型名称 (或按回车返回): ").strip()
            if not name:
                continue

            if name not in models:
                print(f"错误: 模型 '{name}' 不存在")
                continue

            if name == default:
                print(f"'{name}' 已经是默认模型")
                continue

            result = config.set_default_model(name)
            if result:
                print(f"已将 '{name}' 设置为默认模型")
            else:
                print(f"设置默认模型失败")

        elif choice == "4":
            print("配置已保存，退出配置向导")
            break

        else:
            print("无效的选择，请输入 1-4 之间的数字")


def run_config_cli():
    """Run the configuration CLI"""
    parser = argparse.ArgumentParser(description="cao 配置工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # List models command
    list_parser = subparsers.add_parser("list", help="列出所有配置的模型")

    # Add model command
    add_parser = subparsers.add_parser("add", help="添加或更新模型配置")
    add_parser.add_argument("name", help="模型名称")
    add_parser.add_argument("api_base", help="API 基础 URL")
    add_parser.add_argument("model", help="模型名称")
    add_parser.add_argument("--api-key", help="API密钥(可选，如不提供则使用环境变量)")

    # Remove model command
    remove_parser = subparsers.add_parser("remove", help="删除模型配置")
    remove_parser.add_argument("name", help="要删除的模型名称")

    # Set default model command
    default_parser = subparsers.add_parser("default", help="设置默认模型")
    default_parser.add_argument("name", help="要设为默认的模型名称")

    # Export config command
    export_parser = subparsers.add_parser("export", help="导出配置")
    export_parser.add_argument("-f", "--file", help="导出到文件")

    # Import config command
    import_parser = subparsers.add_parser("import", help="从文件导入配置")
    import_parser.add_argument("file", help="要导入的配置文件路径")

    # Config path command
    path_parser = subparsers.add_parser("path", help="显示配置文件路径")

    # Interactive config command
    interactive_parser = subparsers.add_parser("interactive", help="交互式配置")

    # Parse arguments
    args = parser.parse_args(sys.argv[1:])

    if args.command == "list" or not args.command:
        list_models()
    elif args.command == "add":
        add_model(args)
    elif args.command == "remove":
        remove_model(args)
    elif args.command == "default":
        set_default(args)
    elif args.command == "export":
        export_config(args)
    elif args.command == "import":
        import_config(args)
    elif args.command == "path":
        config_path(args)
    elif args.command == "interactive":
        interactive_config()
    else:
        parser.print_help()


if __name__ == "__main__":
    run_config_cli()
