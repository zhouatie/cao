# cao

一个命令行工具，用于捕获终端错误并使用 AI 进行分析和提供解决方案。

## 功能

-   捕获命令行执行错误并分析
-   支持多种 AI 模型（deepseek、openai）
-   分析最近执行的命令错误
-   分析特定历史命令错误

## 安装

### 通过 Homebrew 安装

```bash
brew tap zhouatie/cao
brew install cao
```

### 通过源码安装

```bash
git clone https://github.com/zhouatie/cao.git
cd cao
pip install -e .
```

## 使用方法

### 执行命令并在出错时分析

```bash
cao your_command_here
```

### 分析最近一次执行的命令错误

```bash
cao -l
```

或

```bash
cao --last
```

### 分析历史命令中特定行号的命令

```bash
cao -n 42
```

### 指定使用的 AI 模型

```bash
cao -m openai your_command_here
```

支持的模型:

-   deepseek (默认)
-   openai

### 开启调试模式

```bash
cao -d your_command_here
```

## 环境变量

需要设置以下环境变量（取决于您使用的AI模型）:

-   `OPENAI_API_KEY` - 使用 OpenAI 模型时需要
-   `DEEPSEEK_API_KEY` - 使用 DeepSeek 模型时需要

## 示例

```bash
# 执行一个可能会失败的命令
cao python non_existent_file.py

# 分析最近一次失败的命令
cao --last

# 使用 OpenAI 模型分析
cao -m openai -l
```

## 本地调试

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

## 许可证

[MIT](LICENSE)
