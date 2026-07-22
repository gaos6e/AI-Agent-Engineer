---
title: Linux 环境与 Shell 基础
aliases:
  - Linux 命令行导论
  - Bash 与安全实验环境
tags:
  - AI-Agent-Engineer
  - Linux
  - Bash
source_checked: 2026-07-14
---

# Linux 环境与 Shell 基础

## 本节目标

先分清“命令在哪里执行、由谁解释、会影响哪台机器”，再学习命令。你将认识终端、Shell、Bash、发行版、WSL、容器与远程主机，理解命令/选项/参数、引号、展开、`--` 和退出码，并创建一个受控临时实验目录。

## 终端不是 Shell，Shell 也不是 Linux

| 概念 | 作用 | 常见例子 |
| --- | --- | --- |
| 终端（terminal） | 显示输入输出，承载交互会话 | Windows Terminal、SSH 客户端 |
| Shell | 解析命令语法、展开变量、启动程序 | PowerShell、Bash、zsh |
| 操作系统/环境 | 提供内核、文件系统、进程与工具 | Ubuntu、Debian、容器镜像、WSL |
| 命令 | Shell builtin、函数、别名或外部程序 | `cd`、`printf`、`grep`、`python3` |

PowerShell 的 `$env:PATH`、管道对象和引号规则不等于 Bash 的 `$PATH`、文本管道和展开规则。看到代码围栏上的 `powershell` 或 `bash`，先切换到对应环境。

## 你可能处于哪种 Linux 环境

- **WSL**：Windows 上运行 Linux 发行版；Windows 路径常挂载在 `/mnt/c`，文件权限和 I/O 语义可能与 Linux 原生文件系统不同。
- **容器**：进程、网络、文件系统和资源视图受 namespace/cgroup 限制；镜像可能没有 `man`、systemd、procps 或编辑器。
- **远程主机**：命令实际影响远端；必须遵守访问、审计、变更和数据边界。
- **原生 Linux**：仍需确认发行版、Shell、权限和工具版本，不能把某个 Ubuntu 教程当成所有系统都相同。

从 PowerShell 只读检查 WSL 状态：

```powershell
wsl --status
wsl --list --verbose
```

没有发行版时不要假装已验证 Linux 命令。安装或启用 WSL 会改变本机状态，应按 Microsoft 当前文档和设备管理策略进行。

## 进入后先建立环境指纹

```bash
id
hostname
pwd
uname -srm
cat -- /etc/os-release
printf 'bash_version=%s\n' "${BASH_VERSION:-not-bash}"
ps -p "$$" -o pid=,comm=,args=
```

- `$SHELL` 通常来自登录环境或账户配置，不能可靠证明当前正在执行的 Shell。
- `$BASH_VERSION` 非空可证明当前进程具有 Bash 变量；`ps -p "$$"` 观察当前 Shell 进程，但依赖 procps。
- `/etc/os-release` 描述发行版用户空间；`uname` 主要描述内核。WSL 和容器中二者来源可能不同。

## 一条命令由什么组成

```text
command [options] [operands]
grep    -n       'ERROR' service.log
```

- **command**：要运行的 builtin、函数或程序。
- **option**：改变行为，常见短选项 `-n` 与长选项 `--line-number`。
- **operand/argument**：文件、文本、PID 等实际对象。
- **`--`**：许多工具把它解释为“选项到此结束”，后面的 `-report.txt` 按路径处理。不是所有命令都支持，先查帮助。

确认 Shell 最终解析到什么：

```bash
command -v -- grep
type -a -- grep
type -a -- cd
```

`command -v` 是脚本中较可移植的查询方式；Bash 的 `type -a` 还能显示别名、函数、builtin 和多个路径。`which` 不能完整代表 Shell 的真实解析结果。

## 引号与展开：Shell 在程序启动前做了什么

```bash
name='Agent log'
printf '%s\n' "$name"
printf '%s\n' '$name'
printf '%s\n' "home=$HOME"
```

- 单引号几乎保持字面值，`'$name'` 不展开变量。
- 双引号允许 `$name`、`$(command)` 等展开，同时把结果保留为一个参数。
- 不加引号的变量展开会再发生字段分割和通配符展开，路径和外部输入通常必须写成 `"$value"`。
- `*`、`?`、`[...]` 是 glob，由 Shell 按文件名展开；它们不是正则表达式。Bash 默认找不到匹配时可能保留原字面模式。

查看参数边界的最小实验：

```bash
value='one two'
printf '<%s>\n' "$value"
printf '<%s>\n' $value
```

第一条传一个参数，第二条通常变成两个。真实脚本优先引用变量，除非你明确需要字段分割。

## 退出状态不是屏幕文字

程序用 0 表示成功，非 0 表示不同类别的未满足或错误；具体含义以工具文档为准。

```bash
grep -q -- 'needle' /dev/null
status=$?
printf 'grep_status=%s\n' "$status"
```

GNU grep 的 1 表示“没有匹配”，2 表示错误。`$?` 只保存最近一条前台 pipeline 的状态，运行另一条命令后就会被覆盖。pipeline 的中间失败传播在 [[Linux命令/07 管道重定向与命令组合|管道、重定向与命令组合]] 详讲。

## 创建受控实验目录

以下代码只适用于 GNU/Linux 或具有 GNU `realpath` 的环境；它创建唯一目录，不自动删除：

```bash
lab_root=${TMPDIR:-/tmp}
lab_root_real=$(realpath -e -- "$lab_root") || exit 1
lab_dir=$(mktemp -d "$lab_root_real/agent-shell-lab.XXXXXX") || exit 1
lab_real=$(realpath -e -- "$lab_dir") || exit 1
case "$lab_real" in
  "$lab_root_real"/agent-shell-lab.*) ;;
  *) printf 'unexpected lab path: %s\n' "$lab_real" >&2; exit 1 ;;
esac
if [ ! -O "$lab_real" ] || [ -L "$lab_real" ]; then
  printf 'lab ownership or symlink check failed\n' >&2
  exit 1
fi
cd -- "$lab_real" || exit 1
printf 'lab=%s\n' "$PWD"
```

`mktemp -d` 避免名称碰撞；`realpath`、所有权和符号链接检查限制了后续写操作的边界。不要把变量替换成 `/`、家目录或真实项目。课程故意不自动 `rm -rf`，清理要等学完文件删除护栏后再决定。

## 动手练习

在上述目录中运行：

```bash
touch -- 'report one.txt' '--literal-name'
printf '%s\n' ./*
printf 'line one\nline two\n' > 'report one.txt'
wc -l -- 'report one.txt'
command -v -- wc
printf 'last_status=%s\n' "$?"
```

解释：为什么创建 `--literal-name` 时需要 `--`；为什么带空格路径必须引用；`./*` 由谁展开；最后一个 `$?` 实际对应哪条命令。

## 常见误区

- **“代码在我的电脑上，所以只影响本机 Windows”**：SSH/容器终端里的命令可能影响远端或容器挂载。
- **“Linux 命令都能在 macOS 直接照抄”**：GNU 与 BSD 选项经常不同。
- **“有 sudo 就能执行”**：权限存在不等于获得授权，提权会扩大事故半径。
- **“命令没输出就是成功”**：必须看退出状态和预期副作用。
- **“把秘密放环境变量就不会泄露”**：进程环境、调试输出、历史和崩溃材料都可能暴露它。

## 掌握检查

- [ ] 能区分终端、Shell、Bash、WSL、容器和远程主机。
- [ ] 能说明 POSIX、GNU 扩展与 Linux 专属工具不是同一层。
- [ ] 能用 `command -v` 与 `type -a` 判断命令来源。
- [ ] 能解释单引号、双引号、未引用变量和 glob 的差异。
- [ ] 能在唯一临时目录中完成练习，并说清为什么不自动清理。

下一步：[[Linux命令/01 帮助与基础|帮助与基础]]。

## 参考资料

获取日期：**2026-07-14**。

- [GNU Bash Manual：Shell Expansions](https://www.gnu.org/software/bash/manual/html_node/Shell-Expansions.html)
- [GNU Bash Manual：Bash Variables](https://www.gnu.org/software/bash/manual/html_node/Bash-Variables.html)
- [POSIX.1-2024 Shell Command Language](https://pubs.opengroup.org/onlinepubs/9799919799.2024edition/utilities/V3_chap02.html)
- [POSIX command](https://pubs.opengroup.org/onlinepubs/9799919799.2024edition/utilities/command.html)
- [Microsoft WSL basic commands](https://learn.microsoft.com/windows/wsl/basic-commands)

