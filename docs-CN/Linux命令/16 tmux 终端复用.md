---
title: "16 tmux 终端复用"
tags:
  - linux
  - command
  - tutorial
aliases:
  - Linux tmux 入门
  - tmux 终端复用
source_checked: 2026-07-14
lang: zh-CN
translation_key: Linux命令/16 tmux 终端复用.md
translation_route: en/linux-commands/16-tmux-terminal-multiplexing
translation_default_route: zh-CN/Linux命令/16-tmux-终端复用
---

# 16 tmux 终端复用

## 学习目标

- 能创建、查看、恢复和关闭 tmux 会话。
- 能在一个终端中使用多个窗口和分屏。
- 能在 SSH 断开后恢复原来的工作现场。

## 命令总览

| 命令 | 用途 | 含义 | 基本用法 | 例子 |
|---|---|---|---|---|
| `tmux` | 启动 tmux | 创建一个默认 tmux 会话 | `tmux` | `tmux` |
| `tmux new -s` | 创建命名会话 | new session，方便之后按名称恢复 | `tmux new -s 会话名` | `tmux new -s train` |
| `tmux ls` | 查看会话列表 | list sessions，列出已有 tmux 会话 | `tmux ls` | `tmux ls` |
| `tmux attach -t` | 恢复会话 | attach target，进入指定会话 | `tmux attach -t 会话名` | `tmux attach -t train` |
| `tmux kill-session -t` | 关闭会话 | 结束指定 tmux 会话 | `tmux kill-session -t 会话名` | `tmux kill-session -t train` |
| `Ctrl-b d` | 分离会话 | detach，退出 tmux 但保留里面的任务 | `Ctrl-b` 后按 `d` | 先按 `Ctrl-b`，松开后按 `d` |
| `Ctrl-b c` | 新建窗口 | create window，在会话中新建一个窗口 | `Ctrl-b` 后按 `c` | 先按 `Ctrl-b`，松开后按 `c` |
| `Ctrl-b %` | 左右相邻 pane | tmux 官方称 horizontal split | `Ctrl-b` 后按 `%` | 先按 `Ctrl-b`，松开后按 `%` |
| `Ctrl-b "` | 上下相邻 pane | tmux 官方称 vertical split | `Ctrl-b` 后按 `"` | 先按 `Ctrl-b`，松开后按 `"` |
| `Ctrl-b 方向键` | 切换分屏 | 在 pane 之间移动光标 | `Ctrl-b` 后按方向键 | `Ctrl-b` 后按 `←` |
| `Ctrl-b x` | 请求关闭当前 pane | 默认会先确认 kill-pane | `Ctrl-b` 后按 `x` | 确认目标后回答提示 |

## 常用场景

创建一个不易碰撞的实验会话，并写入只属于本次 Shell 的 marker。任何创建或核验失败都停止：

```bash
session=''
for attempt in 1 2 3 4 5; do
  candidate="agent-cli-lab-${BASHPID}-${RANDOM}"
  if ! tmux has-session -t "=$candidate" 2>/dev/null; then
    session=$candidate
    break
  fi
done
[ -n "$session" ] || { printf 'no unique session name\n' >&2; exit 1; }

marker="marker-${BASHPID}-${RANDOM}"
tmux new-session -d -s "$session" || exit 1
tmux set-option -t "=$session" @agent_cli_marker "$marker" || exit 1
observed=$(tmux show-options -v -t "=$session" @agent_cli_marker) || exit 1
[ "$observed" = "$marker" ] || { printf 'marker mismatch\n' >&2; exit 1; }
tmux list-sessions
```

用非交互命令创建第二个窗口和左右相邻 pane，并做客观计数：

```bash
tmux new-window -d -t "$session:" -n evidence || exit 1
tmux split-window -d -h -t "$session:evidence" || exit 1
tmux send-keys -t "$session:evidence.0" "printf '%s\\n' '$marker'" C-m
window_count=$(tmux list-windows -t "=$session" | wc -l) || exit 1
pane_count=$(tmux list-panes -t "$session:evidence" | wc -l) || exit 1
[ "$window_count" -ge 2 ] && [ "$pane_count" -ge 2 ] || exit 1
printf 'windows=%s evidence_panes=%s\n' "$window_count" "$pane_count"
```

真实长任务的语法可参考 `tmux send-keys`，但必须先审阅任务本身；本练习不启动训练、下载或未知脚本。

临时离开但保留任务：

```bash
# 按 Ctrl-b，然后按 d
```

之后恢复会话：

```bash
if [ -z "${session:-}" ] || [ -z "${marker:-}" ]; then
  printf 'run the creation block in this shell first\n' >&2
  exit 1
fi
observed=$(tmux show-options -v -t "=$session" @agent_cli_marker) || exit 1
[ "$observed" = "$marker" ] || exit 1
tmux attach-session -t "=$session"
```

分屏看日志：

```bash
# 在 tmux 中按 Ctrl-b，然后按 %
tail -f app.log
```

关闭不需要的会话：

```bash
if [ -z "${session:-}" ] || [ -z "${marker:-}" ]; then
  printf 'session identity is unavailable\n' >&2
  exit 1
fi
observed=$(tmux show-options -v -t "=$session" @agent_cli_marker 2>/dev/null) || exit 1
if [ "$observed" != "$marker" ]; then
  printf 'refuse to close unverified session\n' >&2
  exit 1
fi
tmux kill-session -t "=$session" || exit 1
if tmux has-session -t "=$session" 2>/dev/null; then
  printf 'session still exists\n' >&2
  exit 1
fi
```

## 新手注意

- tmux 的默认前缀键是 `Ctrl-b`，很多快捷键都要先按它。
- `Ctrl-b d` 只是分离会话，不会停止会话里的程序。
- 直接在 tmux 里输入 `exit` 会退出当前 shell；如果当前窗口只剩这个 shell，窗口也会关闭。
- 长时间训练、下载、压缩、跑脚本时，优先放在 tmux 里。
- 远程 SSH 断开后，只要同一主机上的 tmux server 和用户会话仍存活，通常可重新 attach；主机重启、tmux server 退出或管理员清理后不能恢复。
- tmux 不是服务管理器，不提供开机启动、重启策略、健康检查或日志治理。生产服务见 [[Linux命令/11 服务与日志|服务与日志]]。
- `capture-pane`、窗口标题和命令行可能含秘密；分享会话输出前先脱敏。

## 最小练习与验收

按顺序运行本页实验：创建唯一会话和 marker；创建至少 2 个窗口；在 `evidence` 窗口创建至少 2 个 pane；attach 后用 `Ctrl-b d` detach；再次核对 marker 后关闭。验收时保存窗口数、pane 数与关闭后的 `has-session` 失败退出码。不要复用 `train`、`work` 等可能属于真实任务的通用名称。

## 参考资料

- [tmux Getting Started](https://github.com/tmux/tmux/wiki/Getting-Started)
- [tmux manual](https://man.openbsd.org/tmux.1)
