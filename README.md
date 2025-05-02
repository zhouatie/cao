# cao🌿

一个命令行工具，程序员编程伴侣。

## 功能

-   支持与多种角色对话（可以向他们寻求帮助）
-   支持多种 AI 模型（ollama、deepseek、openai）

## 系统要求

-   Python

## 安装

### 通过 pipx 安装(没有的话，可以用 brew 安装下)

pipx 会自动创建一个独立的虚拟环境来安装 cao，避免依赖冲突。

```bash
pipx install zhouatie-cao
```

## 使用方法

```bash
# 在终端执行 cao，即可唤醒你的编程伴侣
cao
```

### 指定使用的 AI 模型

```bash
cao -m ollama
```

支持的模型:

-   ollama (默认)(本地运行)
-   deepseek
-   openai
-   以及任何支持OpenAI兼容API的模型，如:
    -   anthropic
    -   等更多通过自定义配置添加的模型

### 配置 AI 模型

```bash
cao --config
```

这将启动交互式配置界面，您可以在其中:

-   添加/更新模型配置
-   删除不需要的模型
-   设置默认模型
-   查看当前配置的所有模型

### 开启调试模式

```bash
cao -d
```

## 环境变量和API密钥

设置API密钥的两种方式:

1. **环境变量** (推荐):

    - 自动根据API提供商命名规则使用相应环境变量
    - 命名规则: `<PROVIDER名称大写>_API_KEY`
    - 举例:
        - `OPENAI_API_KEY` - OpenAI模型
        - `DEEPSEEK_API_KEY` - DeepSeek模型
        - `DASHSCOPE_API_KEY` - 阿里云DashScope模型
        - `ANTHROPIC_API_KEY` - Anthropic模型

2. **配置文件**:
    - 通过`cao --config`命令进行配置
    - 支持在配置中直接设置API密钥

注意：

-   使用Ollama模型不需要设置API密钥，因为它在本地运行
-   API提供商名称会自动从API基础URL中提取，例如`api.openai.com` → 使用`OPENAI_API_KEY`

## 示例

```bash
# 执行一个可能会失败的命令
cao python non_existent_file.py

# 分析最近一次失败的命令
cao

# 使用 Ollama 模型分析
cao -m ollama

```

## 本地开发与调试

```bash
# 创建虚拟环境
python3 -m venv cao_venv

# 激活虚拟环境
source cao_venv/bin/activate

# 在虚拟环境中安装开发版本（这会自动安装所有依赖项）
pip install -e .

# 现在您可以直接运行命令
cao ls /nonexistent_directory

# 完成测试后，退出虚拟环境
deactivate
```

## 使用 pipx 开发

在开发过程中，可以使用 pipx 来测试你的包(测试包的安装体验和表现)：

```bash
# 安装开发版本
pipx install --spec . cao

# 更新开发版本
pipx reinstall cao

# 查看安装的包
pipx list

# 卸载
pipx uninstall cao
```

## FEATURE

-   [x] 自定义配置 AI 模型
-   [x] 支持与ai持续性对话

## 许可证

[MIT](LICENSE)
