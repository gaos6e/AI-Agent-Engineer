---
title: "16 tmux Terminal Multiplexing"
tags:
  - linux
  - command
  - tutorial
aliases:
  - Linux tmux introduction
  - tmux terminal multiplexing
source_checked: 2026-07-14
lang: en
translation_key: Linux命令/16 tmux 终端复用.md
translation_source_hash: 7eaf979df28b2105b4ecfbbec42c462e3821027cd9b489e46bef7d181e5c49d6
translation_route: zh-CN/Linux命令/16-tmux-终端复用
translation_default_route: zh-CN/Linux命令/16-tmux-终端复用
---

# 16 tmux Terminal Multiplexing

## Learning objectives

- Create, list, restore, and close tmux sessions.
- Use multiple windows and panes in one terminal.
- Restore prior work after an SSH disconnect.

## Command overview

| Command | Purpose | Meaning | Basic usage | Example |
|---|---|---|---|---|
| `tmux` | Start tmux | Creates a default tmux session | `tmux` | `tmux` |
| `tmux new -s` | Create a named session | New session; a name makes later restoration easier | `tmux new -s session_name` | `tmux new -s train` |
| `tmux ls` | List sessions | List sessions; shows existing tmux sessions | `tmux ls` | `tmux ls` |
| `tmux attach -t` | Restore a session | Attach target; enters a specified session | `tmux attach -t session_name` | `tmux attach -t train` |
| `tmux kill-session -t` | Close a session | Ends a named tmux session | `tmux kill-session -t session_name` | `tmux kill-session -t train` |
| `Ctrl-b d` | Detach a session | Detach; leaves processes inside tmux running | Press `d` after `Ctrl-b` | Press `Ctrl-b`, release it, then press `d` |
| `Ctrl-b c` | Create a window | Create window; makes a new window in the session | Press `c` after `Ctrl-b` | Press `Ctrl-b`, release it, then press `c` |
| `Ctrl-b %` | Split into side-by-side panes | Called a horizontal split by tmux | Press `%` after `Ctrl-b` | Press `Ctrl-b`, release it, then press `%` |
| `Ctrl-b "` | Split into stacked panes | Called a vertical split by tmux | Press `"` after `Ctrl-b` | Press `Ctrl-b`, release it, then press `"` |
| `Ctrl-b arrow key` | Change panes | Moves the cursor among panes | Press an arrow after `Ctrl-b` | Press `Ctrl-b` then `←` |
| `Ctrl-b x` | Request to close the current pane | `kill-pane` prompts for confirmation by default | Press `x` after `Ctrl-b` | Confirm the target, then answer the prompt |

## Common scenarios

Create a collision-resistant lab session and write a marker belonging only to this Shell. Stop if creation or verification fails:

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

Create a second window and side-by-side panes noninteractively, then make an objective count:

```bash
tmux new-window -d -t "$session:" -n evidence || exit 1
tmux split-window -d -h -t "$session:evidence" || exit 1
tmux send-keys -t "$session:evidence.0" "printf '%s\\n' '$marker'" C-m
window_count=$(tmux list-windows -t "=$session" | wc -l) || exit 1
pane_count=$(tmux list-panes -t "$session:evidence" | wc -l) || exit 1
[ "$window_count" -ge 2 ] && [ "$pane_count" -ge 2 ] || exit 1
printf 'windows=%s evidence_panes=%s\n' "$window_count" "$pane_count"
```

For a real long-running job, `tmux send-keys` is syntax to consult only after reviewing the job itself. This exercise starts no training, download, or unknown script.

Detach temporarily while keeping work:

```bash
# Press Ctrl-b, then press d
```

Restore the session later:

```bash
if [ -z "${session:-}" ] || [ -z "${marker:-}" ]; then
  printf 'run the creation block in this shell first\n' >&2
  exit 1
fi
observed=$(tmux show-options -v -t "=$session" @agent_cli_marker) || exit 1
[ "$observed" = "$marker" ] || exit 1
tmux attach-session -t "=$session"
```

Split a pane to inspect logs:

```bash
# In tmux, press Ctrl-b, then %
tail -f app.log
```

Close an unneeded session:

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

## Notes for beginners

- tmux’s default prefix key is `Ctrl-b`, and many shortcuts start with it.
- `Ctrl-b d` only detaches a session; it does not stop programs inside.
- Typing `exit` directly in tmux exits the current Shell. If it is the only Shell in its window, that window closes too.
- Prefer tmux for long training, downloading, compression, or script runs.
- After remote SSH disconnects, you can normally attach again as long as tmux’s server and user session remain alive on the same host. You cannot restore after a host reboot, tmux-server exit, or administrator cleanup.
- tmux is not a service manager. It does not provide boot startup, restart policy, health checks, or log governance. Use [[linux-commands/11-services-and-logs|Services and logs]] for production services.
- `capture-pane`, window titles, and command lines can contain secrets. Redact before sharing session output.

## Minimal exercise and acceptance

Run this page’s lab in sequence: create a unique session and marker, create at least two windows, create at least two panes in the `evidence` window, attach and detach with `Ctrl-b d`, verify the marker again, then close it. Retain the window count, pane count, and `has-session` failure exit status after close. Do not reuse generic names such as `train` or `work` that may belong to real work.

## References

- [tmux Getting Started](https://github.com/tmux/tmux/wiki/Getting-Started)
- [tmux manual](https://man.openbsd.org/tmux.1)
