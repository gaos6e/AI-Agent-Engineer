---
title: "09 Process Management"
tags:
  - linux
  - command
  - tutorial
aliases:
  - Linux process-management commands
source_checked: 2026-07-14
lang: en
translation_key: Linux命令/09 进程管理.md
translation_source_hash: b155728bbacaa99b57a2af8e095e47c081941fd13225cadb859e9e0bd171bc0f
translation_route: zh-CN/Linux命令/09-进程管理
translation_default_route: zh-CN/Linux命令/09-进程管理
---

# 09 Process Management

## Learning objectives

- Inspect programs running in the system.
- Stop a stuck or unneeded process.
- Understand foreground jobs, background jobs, and long-running work.

## Command overview

| Command | Purpose | Meaning | Basic usage | Example |
|---|---|---|---|---|
| `ps` | View a process snapshot | Process status; shows current process state | `ps [options]` | `ps aux` |
| `top` | View processes live | Dynamically shows CPU, memory, and processes | `top` | `top` |
| `htop` | More friendly live process tool | Interactive enhancement of top; may need installation | `htop` | `htop` |
| `pgrep` | Find and display matching processes | Verify PID, name, and command line first | `pgrep [options] name` | `pgrep -a -x sleep` |
| `kill` | Send a signal to a PID | Sends SIGTERM by default and does not guarantee immediate exit | `kill PID` | `kill -TERM "$pid"` |
| `pkill` | Send a signal by match | Can match several processes; not used directly in beginner practice | `pkill [options] name` | `pkill -TERM -x sleep` |
| `jobs` | View current Shell background jobs | Shows jobs started by this terminal | `jobs` | `jobs` |
| `fg` | Bring a background job to foreground | Foreground; brings a job back | `fg %job_number` | `fg %1` |
| `bg` | Continue a suspended job in background | Background; resumes a job in background | `bg %job_number` | `bg %1` |
| `nohup` | Run while ignoring SIGHUP | `&` is what backgrounds a Shell job; nohup does not provide restart, health checks, or service lifecycle | `nohup command >log 2>&1 &` | `nohup python3 reviewed_app.py > agent-lab.log 2>&1 &` |

## Common scenarios

Inspect Python-process clues for the current user:

```bash
pgrep -a -u "$(id -u)" -f 'python3'
```

Observe system processes live:

```bash
top
```

For a real process, do not copy example PIDs or use `pkill` with a broad name. First verify PID, owner, start time, parent process, and complete command, then consider a signal.

Run a command in the background:

```text
python3 reviewed_app.py &
jobs
fg %1
```

This is interactive-syntax reference. Run it only after confirming the script path, arguments, and side effects. The runnable main exercise below uses `sleep`, created by the current Shell and saved by PID.

Run for a long time while preserving a log:

```text
nohup python3 reviewed_app.py > agent-lab.log 2>&1 &
```

`nohup` does not govern a service; this course does not run this template.

## Notes for beginners

- A `PID` is a process identifier; `kill` needs a PID.
- Default `kill` sends SIGTERM, which a program can handle or ignore. Wait and verify after sending it.
- SIGKILL (often `kill -9`) cannot be caught and gives a process no cleanup opportunity. Use it only as a last resort after confirming the object, confirming TERM was ineffective, and receiving authorization.
- procps-ng `pgrep`/`pkill` match process names by default, whose name field can be truncated. `-f` matches the full command line. `pkill` can stop multiple processes, so the main exercise does not use it.
- `jobs` manages only background jobs started by the current Shell, not all system processes.
- `nohup` primarily handles SIGHUP and redirection; it does not provide restart, health checks, or service lifecycle. tmux is not a service manager either.

## Terminate only an experimental process you started

```bash
sleep 300 &
pid=$!
ps -p "$pid" -o pid=,ppid=,user=,lstart=,comm=,args=
if [ "$(ps -o uid= -p "$pid" | tr -d ' ')" != "$(id -u)" ]; then
  printf 'owner mismatch\n' >&2
  exit 1
fi
kill -TERM "$pid"
if wait "$pid"; then
  wait_rc=0
else
  wait_rc=$?
fi
printf 'wait_rc=%s\n' "$wait_rc"
if kill -0 "$pid" 2>/dev/null; then
  printf 'process still exists\n' >&2
  exit 1
fi
```

`wait` commonly returns nonzero for a child ended by SIGTERM. That reflects the signal outcome and should not be silently cut short by `set -e`. `kill -0` only checks clues about signal permission/process existence, and PIDs can be reused; hand real services to a service manager.

## References

- [procps-ng pgrep/pkill](https://man7.org/linux/man-pages/man1/pgrep.1.html)
- [kill(2)](https://man7.org/linux/man-pages/man2/kill.2.html)
- [GNU Bash Job Control](https://www.gnu.org/software/bash/manual/html_node/Job-Control.html)
