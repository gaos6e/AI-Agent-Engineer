---
title: Git Cheat Sheet：本机安装 Git
source: https://git-scm.com/install/windows
retrieved: 2026-06-04
source_checked: 2026-07-14
tags:
  - git
  - version-control
  - installation
  - windows
---

# 本机安装 Git

这一章用于在 Windows 本机安装 Git，并确认 PowerShell 可以直接调用 `git` 命令。后续教程默认已经完成本章的安装和基础配置。

## 推荐方式：使用 `winget`

```powershell
winget install --id Git.Git -e --source winget
```

用途：通过 Windows 包管理器安装 Git for Windows。安装完成后，通常会同时提供 `git.exe`、Git Bash 和常用凭据管理组件。

> [!warning] 这是本机状态变更
> 安装、升级和 `--global` 配置会影响当前 Windows 用户或整台机器，不属于隔离仓库练习。先确认设备管理策略；在公司设备上不要绕过管理员限制。

适用场景：

- 当前 Windows 已安装 App Installer / winget。
- 希望用命令行安装，后续也方便升级。
- 不想手动下载 `.exe` 安装包。

如果 winget 源较久没有刷新，可以先执行：

```powershell
winget source update
```

注意点：

- 安装完成后，关闭并重新打开 PowerShell，让新的 `PATH` 生效。
- 如果公司电脑限制 winget 或商店源，可以改用下面的官方下载器方式。
- 如果系统提示需要提升权限，按实际安全策略用管理员 PowerShell 重新执行。

## 备用方式：下载安装器

打开 Git 官方 Windows 安装页：

<https://git-scm.com/install/windows>

下载 Git for Windows 安装器后运行。没有特殊要求时，安装向导中的大多数选项使用默认值即可。

建议确认的选项：

- **PATH 环境变量**：选择让 Git 可在 PowerShell / CMD 中使用，避免只能在 Git Bash 中使用。
- **默认编辑器**：不熟悉 Vim 时，可以选择 VS Code、Notepad 或其他常用编辑器。
- **换行符处理**：Windows 单人学习场景通常保留默认选项即可；跨平台项目按项目规范决定。
- **终端模拟器和凭据管理**：一般使用默认选项。

## 验证安装

重新打开 PowerShell 后执行：

```powershell
git --version
Get-Command git
```

正常情况下，`git --version` 会输出当前安装的 Git 版本，`Get-Command git` 会显示 `git.exe` 的实际路径。

如果提示找不到命令：

- 先关闭并重新打开 PowerShell。
- 检查 Git 是否确实安装完成。
- 检查安装时是否选择了把 Git 加入 `PATH`。
- 如果仍然失败，可以重新运行安装器并修复 PATH 相关选项。

## 首次使用配置

Git 提交需要用户名和邮箱。首次安装后建议先配置：

```powershell
git config set --global user.name "Your Name"
git config set --global user.email "you@example.com"
```

只查看本课设置的字段：

```powershell
git config get --global user.name
git config get --global user.email
```

注意点：

- `user.name` 和 `user.email` 会写入提交作者信息，不一定等同于系统登录名。
- 邮箱可能属于个人信息；公开提交前确认平台隐私邮箱或团队身份规范。
- 如果公司项目和个人项目需要不同身份，可以在具体仓库内设置仓库级配置，详见 [[Git/11-Git 配置与关键文件|Git 配置与关键文件]]。
- 如果要连接 GitHub、GitLab 等远程仓库，还需要根据平台选择 HTTPS 登录、凭据管理器或 SSH key。
- 不要把 token 写进远程 URL，也不要把完整 `git config --list` 或凭据管理器输出粘贴到笔记、日志和求助消息。

## 本课完成检查

```powershell
git --version
Get-Command git
git config get --global user.name
git config get --global user.email
```

能解释四条输出分别来自 Git 程序、PowerShell 命令解析和用户级配置，即可进入下一课。若身份字段为空，可以现在设置，也可以等进入隔离实验仓库后只设置仓库级身份。

> [!note] 旧版写法
> `git config --global user.name "Your Name"`、`git config --global --get user.name` 在现有版本中仍兼容，但 Git 2.55 文档已把这种“无子命令”模式标为 deprecated。本库主示例采用 `set`、`get`、`list` 子命令。

## 后续阅读

安装完成后，继续看 [[Git/02-入门与仓库创建|入门与仓库创建]]，学习如何初始化本地仓库或克隆远程仓库。
