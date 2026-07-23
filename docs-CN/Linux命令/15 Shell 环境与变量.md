---
title: "15 Shell 环境与变量"
tags:
  - linux
  - command
  - tutorial
aliases:
  - Linux Shell 环境与变量命令
source_checked: 2026-07-14
lang: zh-CN
translation_key: Linux命令/15 Shell 环境与变量.md
translation_route: en/linux-commands/15-shell-environment-and-variables
translation_default_route: zh-CN/Linux命令/15-Shell-环境与变量
---

# 15 Shell 环境与变量

## 学习目标

- 能查看和设置环境变量。
- 能创建命令别名。
- 能重新加载 shell 配置文件。

## 命令总览

| 命令 | 用途 | 含义 | 基本用法 | 例子 |
|---|---|---|---|---|
| `env` | 查看或构造子进程环境 | 不包含所有 Shell 变量，且可能含秘密 | `env` | `env -i PATH=/usr/bin /usr/bin/env` |
| `export` | 标记环境变量 | 供随后启动的子命令继承，不影响父进程或既有进程 | `export 名称=值` | `export APP_ENV=dev` |
| `alias` | 设置命令别名 | 给常用命令设置短名字 | `alias 名称='命令'` | `alias ll='ls -lah'` |
| `source` | 重新加载脚本 | 在当前 shell 中执行脚本内容 | `source 文件` | `source ~/.bashrc` |
| `type` | 查看命令类型 | 判断命令是内建、别名、函数还是可执行文件 | `type 命令` | `type cd` |
| `bash` | 进入 bash shell | 启动 bash 命令解释器 | `bash` | `bash` |
| `zsh` | 进入 zsh shell | 启动 zsh 命令解释器 | `zsh` | `zsh` |

## 常用场景

只查看允许公开的变量：

```bash
printf 'home=%s\n' "$HOME"
printf 'app_env=%s\n' "${APP_ENV:-unset}"
```

临时设置变量：

```bash
export APP_ENV=dev
printf '%s\n' "$APP_ENV"
```

给 PATH 增加目录：

```bash
export PATH="$PATH:$HOME/bin"
```

设置别名：

```bash
alias ll='ls -lah'
alias gs='git status'
```

加载配置会在当前 Shell 执行代码，只作可信文件语法参考：

```text
. "$HOME/.bashrc"
source "$HOME/.bashrc"
```

查看命令来源：

```bash
type cd
type ll
type python3
```

## 新手注意

- 直接 `export` 设置的变量通常只在当前终端会话有效。
- Shell 变量只有经过 export 才进入随后启动的子进程；`env` 不会列出所有未导出的 Shell 变量。
- Bash 登录/非登录、交互/非交互会读取不同启动文件；zsh 规则也不同，不能一律写入 `~/.bashrc`。
- `source` 是 Bash 同义词，POSIX 写法是 `.`；两者都会在当前 Shell 执行任意代码，只加载你已审阅的可信文件。
- `alias` 也通常写入 shell 配置文件才能长期生效。
- `type cd` 会显示 `cd` 是 shell 内建命令，所以 `which cd` 不一定符合直觉。

## 单引号、双引号与秘密

```bash
value='one two'
printf '<%s>\n' "$value"
printf '%s\n' 'literal $value'
printf '%s\n' "expanded $value"
```

变量展开通常应放在双引号中。秘密即使在环境变量里，仍可能出现在进程环境、debug 日志、崩溃转储或子进程中；不要用裸 `env`、`set` 或 `export -p` 收集排障证据。

## PATH 安全

- PATH 从左到右查找；空项或不可信可写目录可能导致命令劫持。
- 添加目录前先检查 canonical path、owner 与权限，不把 `.` 放到 PATH 前部。
- 脚本关键工具可先用 `command -v` 记录来源；高安全场景使用受控绝对路径和最小环境。

```bash
command -v -- python3
printf '%s\n' "$PATH" | tr ':' '\n' | nl -ba
```

公开报告前删去私人路径和内部挂载信息。

## 练习

创建普通 Shell 变量 `LOCAL_ONLY` 和 export 的 `CHILD_VISIBLE`，用一个子 Bash 比较：

```bash
LOCAL_ONLY='local'
export CHILD_VISIBLE='child'
bash -c 'printf "local=%s child=%s\n" "${LOCAL_ONLY:-unset}" "${CHILD_VISIBLE:-unset}"'
```

预期子进程看不到未 export 的变量。练习不使用真实 token，不修改启动文件。

## 参考资料

- [GNU Bash：Bourne Shell Builtins](https://www.gnu.org/software/bash/manual/html_node/Bourne-Shell-Builtins.html)
- [GNU Bash：Startup Files](https://www.gnu.org/software/bash/manual/html_node/Bash-Startup-Files.html)
- [GNU Bash：Quoting](https://www.gnu.org/software/bash/manual/html_node/Quoting.html)
