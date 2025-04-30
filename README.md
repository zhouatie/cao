# cao🌿

一个命令行工具，用于捕获终端错误并使用 AI 进行分析和提供解决方案。

## 功能

-   捕获命令行执行错误并分析
-   支持多种 AI 模型（ollama、deepseek、openai）
-   分析最近执行的命令错误
-   分析特定历史命令错误

## 系统要求

-   Python

## 安装

### 通过 pipx 安装(没有的话，可以用 brew 安装下)

pipx 会自动创建一个独立的虚拟环境来安装 cao，避免依赖冲突。

```bash
pipx install zhouatie-cao
```

## 使用方法

### 设置 shell 函数

为了更好地捕获最近执行的命令及其返回码，建议在您的 shell 配置文件中添加相应的函数：

### 各操作系统与Shell配置指南

#### macOS 系统

##### ZSH 配置 (macOS 默认 shell，~/.zshrc)

```bash
function cao() {
  local last_cmd=$(fc -ln -1 | sed -e 's/^ *//')
  local last_code=$?
  local cao_path=$(which zhouatie_cao)

  if [ -n "$cao_path" ]
  then
    CAO_LAST_COMMAND="$last_cmd" CAO_RETURN_CODE="$last_code" "$cao_path" "$@"
  else
    echo "cao 命令未找到，请确保已正确安装"
    return 1
  fi
}
```

##### Bash 配置 (macOS，~/.bash_profile 或 ~/.bashrc)

```bash
function cao() {
  # 获取上一条命令前先保存返回码
  local last_code=$?
  # 获取函数调用前一条命令
  local last_cmd=$(fc -ln -1 | sed -e 's/^ *//')
  local cao_path=$(command -v zhouatie_cao)
  if [ -n "$cao_path" ]
  then
    CAO_LAST_COMMAND="$last_cmd" CAO_RETURN_CODE="$last_code" "$cao_path" "$@"
  else
    echo "cao 命令未找到，请确保已正确安装"
    return 1
  fi
}
```

#### Linux 系统

##### Bash 配置 (Linux 常见默认 shell，~/.bashrc)

```bash
function cao() {
  # 获取上一条命令前先保存返回码
  local last_code=$?
  # 获取函数调用前一条命令 (bash 中 fc -ln -2 | head -n 1 可以获取上一条命令)
  local last_cmd=$(fc -ln -2 | head -n 1 | sed -e 's/^ *//')
  local cao_path=$(command -v zhouatie_cao)
  if [ -n "$cao_path" ]
  then
    CAO_LAST_COMMAND="$last_cmd" CAO_RETURN_CODE="$last_code" "$cao_path" "$@"
  else
    echo "cao 命令未找到，请确保已正确安装"
    return 1
  fi
}
```

##### ZSH 配置 (Linux，~/.zshrc)

```bash
function cao() {
  # 获取上一条命令前先保存返回码
  local last_code=$?
  # 获取函数调用前一条命令
  local last_cmd=$(fc -ln -2 | head -n 1 | sed -e 's/^ *//')
  local cao_path=$(command -v zhouatie_cao)
  if [ -n "$cao_path" ]
  then
    CAO_LAST_COMMAND="$last_cmd" CAO_RETURN_CODE="$last_code" "$cao_path" "$@"
  else
    echo "cao 命令未找到，请确保已正确安装"
    return 1
  fi
}
```

##### Fish Shell 配置 (Linux，~/.config/fish/functions/cao.fish)

```fish
function cao
  # 获取上一条命令前先保存返回码
  set last_code $status
  # 获取函数调用前一条命令（获取历史中第二条命令，即cao命令之前的命令）
  set last_cmd (history | head -n2 | tail -n1)
  set cao_path (command -v zhouatie_cao)
  if test -n "$cao_path"
    env CAO_LAST_COMMAND="$last_cmd" CAO_RETURN_CODE="$last_code" "$cao_path" $argv
  else
    echo "cao 命令未找到，请确保已正确安装"
    return 1
  end
end
```

#### Windows 系统

##### PowerShell 配置 (Windows，$PROFILE)

```powershell
function cao {
  # 获取上一条命令的返回码
  $last_code = $LASTEXITCODE
  # 获取上一条命令（非cao命令）
  $last_cmd = if ((Get-History).Count -ge 2) { (Get-History)[-2].CommandLine } else { "" }
  $cao_path = (Get-Command zhouatie_cao -ErrorAction SilentlyContinue).Source
  if ($cao_path) {
    $env:CAO_LAST_COMMAND = $last_cmd
    $env:CAO_RETURN_CODE = $last_code
    & $cao_path $args
  } else {
    Write-Output "cao 命令未找到，请确保已正确安装"
    return 1
  }
}
```

##### Command Prompt 配置 (Windows，创建 cao.bat 文件并添加到 PATH)

```batch
@echo off
setlocal enabledelayedexpansion

:: 获取命令历史是 CMD 中的限制
:: 这个实现有限制，只能分析当前执行的命令

set "cao_path="
for %%i in (zhouatie_cao.exe) do set "cao_path=%%~$PATH:i"

if defined cao_path (
  set "CAO_RETURN_CODE=%ERRORLEVEL%"
  "%cao_path%" %*
) else (
  echo cao 命令未找到，请确保已正确安装
  exit /b 1
)
```

> **重要说明**:
>
> 1. Windows CMD 中无法获取上一条命令，功能会受限

### 分析最近一次执行的命令错误（默认行为）

```bash
cao
```

### 执行命令并在出错时分析

```bash
cao your_command_here
```

### 分析历史命令中特定行号的命令(暂时有问题)

```bash
cao -n 42
```

### 指定使用的 AI 模型

```bash
cao -m deepseek
```

支持的模型:

-   ollama (本地运行)
-   deepseek (默认)
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

# 使用 deepseek 模型分析（默认）
cao
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

在开发过程中，可以使用 pipx 来测试你的包：

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
-   [ ] 支持与ai持续性对话

## 许可证

[MIT](LICENSE)
