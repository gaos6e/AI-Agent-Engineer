---
title: Git Cheat Sheet：Git 配置与关键文件
source: https://git-scm.com/cheat-sheet
retrieved: 2026-05-13
source_checked: 2026-07-14
tags:
  - git
  - version-control
  - config
---

# Git 配置与关键文件

Git 配置决定用户名、邮箱、默认分支、别名、换行符处理和合并工具等行为。配置可以分为仓库级、用户级和系统级。

## `git config set user.name 'Your Name'`

```powershell
git config set user.name "Your Name"
```

用途：设置当前仓库的提交作者名称。

适用场景：

- 某个仓库需要使用不同身份。
- 公司项目和个人项目需要不同作者信息。

常见搭配：

```powershell
git config set user.email "you@example.com"
```

检查当前仓库配置：

```powershell
git config get --local user.name
git config get --local user.email
```

## `git config --global ...`

```powershell
git config set --global user.name "Your Name"
git config set --global user.email "you@example.com"
```

用途：设置当前用户的全局 Git 配置，默认影响该用户下所有仓库。

适用场景：

- 首次安装 Git 后设置默认身份。
- 配置全局编辑器、默认分支名或常用别名。

示例：

```powershell
git config set --global init.defaultBranch main
git config set --global core.editor "code --wait"
```

说明：仓库级配置优先级高于全局配置。

## `git config alias.st status`

```powershell
git config set alias.st status
```

用途：创建 Git 命令别名。之后可以用 `git st` 代替 `git status`。

常见别名：

```powershell
git config set --global alias.st status
git config set --global alias.co checkout
git config set --global alias.br branch
git config set --global alias.cm commit
git config set --global alias.lg "log --oneline --graph --decorate"
```

注意：

- 简短别名适合高频命令。
- 不建议给高风险命令设置过短别名，例如 `reset --hard` 或强制推送。

## `man git-config`

```powershell
man git-config
```

用途：查看 Git 配置项手册。

Windows 说明：

- 如果本机没有 `man`，可以改用：

```powershell
git help config
git config -h
```

适用场景：

- 查某个配置项的精确定义。
- 确认配置项支持哪些值。

## `.git/config`

```text
.git/config
```

用途：当前仓库的本地配置文件。

特点：

- 只影响当前仓库。
- 常保存 remote 地址、分支 upstream、仓库级用户名等。
- 通常不直接提交到版本库，因为它位于 `.git/` 内部。

查看方式：

```powershell
git config get --local --regexp '^(user|core|branch)\.'
```

## `~/.gitconfig`

```text
~/.gitconfig
```

用途：当前用户的全局 Git 配置文件。

特点：

- 影响当前用户下的大多数仓库。
- 常保存全局用户名、邮箱、别名、默认编辑器等。

查看方式：

```powershell
git config get --global user.name
git config get --global user.email
```

Windows 上 `~` 通常对应用户主目录，例如 `C:\Users\<用户名>`。

## `.gitignore`

```text
.gitignore
```

用途：声明哪些未跟踪文件应被 Git 忽略。

适用场景：

- 忽略缓存、日志、构建产物、本地配置和依赖目录。
- 避免误提交临时文件。

示例：

```gitignore
__pycache__/
.env
*.log
dist/
node_modules/
```

注意：

- `.gitignore` 只影响未跟踪文件。已经被 Git 跟踪的文件，加入 `.gitignore` 后仍会继续被跟踪。
- 若要停止跟踪已提交文件，但保留本地文件，用：

```powershell
git rm --cached -- .env
```

## `.gitattributes`

`.gitattributes` 是随仓库共享的路径属性规则，可声明文本规范化、diff 驱动和导出行为。跨 Windows 与 Linux 协作时，可从保守规则开始：

```gitattributes
* text=auto
*.sh text eol=lf
*.ps1 text eol=crlf
```

它不会自动修复所有历史换行问题。新增规则前先与项目约定一致，并用 `git diff --check` 和实际测试核对，避免一次提交出现无关的全文件换行变化。

## `.gitmodules` 与子模块边界

子模块本身是独立 Git 仓库；父仓库记录的是子模块 URL 配置和一个特定提交指针，而不是把子模块内部历史合并进父仓库。检查和提交时分别查看两层状态：

```powershell
git status --short
git submodule status
git diff --submodule=short
```

在子模块内完成提交后，父仓库只会看到指针变化。不要把“父仓库干净”误解为所有子模块都没有本地改动。

## 配置优先级

常见优先级从高到低：

1. 命令行参数。
2. 可选的 worktree 级配置。
3. 仓库级配置：`.git/config`。
4. 用户级配置：`~/.gitconfig`。
5. 系统级配置。

排查配置来源：

```powershell
git config list --show-origin --show-scope
```

> [!warning] 输出可能含敏感信息
> Remote URL、代理、凭据助手配置或自定义 header 可能出现在 `.git/config` 和完整配置输出中。排障时优先用 `git config get <具体键>`；不要把完整输出直接复制到公开笔记、日志或工单，也不要把 token 嵌入 URL。

> [!note] 兼容性说明
> `git config user.name "Your Name"`、`git config --get user.name` 等旧模式目前仍兼容，但 Git 2.55 文档已标为 deprecated。新课程示例使用 `set`、`get`、`list` 子命令；在旧 Git 上若子命令不可用，再查本机 `git config -h`。

## 参考资料

按 Git 2.55.0 官方文档核验，获取日期：**2026-07-14**。

- [git config](https://git-scm.com/docs/git-config)
- [gitignore](https://git-scm.com/docs/gitignore)
- [gitattributes](https://git-scm.com/docs/gitattributes)
- [gitmodules](https://git-scm.com/docs/gitmodules)
