---
title: "11 Services and Logs"
aliases:
  - Linux service troubleshooting
  - systemd and journalctl introduction
tags:
  - AI-Agent-Engineer
  - Linux
  - systemd
  - logging
source_checked: 2026-07-14
lang: en
translation_key: Linux命令/11 服务与日志.md
translation_source_hash: 3fa26d4645ed13f146b05cba79b4090447e2026bc7c2f791cd3dee6c950eda78
translation_route: zh-CN/Linux命令/11-服务与日志
translation_default_route: zh-CN/Linux命令/11-服务与日志
---

# 11 Services and Logs

## Learning objectives

Determine whether the current environment uses systemd to manage services; distinguish “running now” from “enabled at boot”; inspect unit configuration, status, and journal data with read-only commands; and separate log evidence from service changes.

## A service is more than “a process in the background”

A service manager commonly owns startup order, execution identity, environment, restart policy, resource limits, log connection, and dependencies. `nohup` or tmux can keep a process in a session, but cannot replace service lifecycle, health checks, or crash recovery.

Linux commonly uses systemd, but not always:

- A native distribution commonly runs systemd as PID 1.
- Whether WSL runs systemd as PID 1 depends on the WSL version, distribution, and configuration; read current-environment evidence.
- A container commonly runs a single application process instead of systemd as PID 1.
- macOS uses launchd, so `systemctl` does not apply.

Identify the environment first:

```bash
ps -p 1 -o pid=,comm=,args=
command -v -- systemctl
systemctl --version
```

The existence of a command does not prove systemd manages the current environment. When `systemctl` cannot connect, record that limitation; do not install or force-start systemd merely to “fix the exercise.”

## Units, active, and enabled

systemd uses units to describe services, sockets, timers, mounts, and other objects. Two state dimensions are easy to confuse:

- **active**: the unit’s current state, such as active, inactive, or failed.
- **enabled**: whether installation relationships include it in a future startup. Enabled does not guarantee currently active, and active does not guarantee enabled.

List running services:

```bash
systemctl list-units --type=service --state=running --no-pager
```

Inspect one unit that commonly exists:

```bash
systemctl status --no-pager --lines=50 systemd-journald.service
systemctl is-active systemd-journald.service
systemctl is-enabled systemd-journald.service
```

`is-active` and `is-enabled` use exit status to communicate their result. “Not active/enabled” does not necessarily mean the command itself is broken. Save `$?` immediately before executing another command.

## Configuration evidence: cat and show

```bash
systemctl cat systemd-journald.service
systemctl show \
  --property=Id,LoadState,ActiveState,SubState,MainPID,User,Group,ExecStart,Restart \
  systemd-journald.service
```

- `cat` displays unit files and drop-ins, which is useful for understanding declaration sources.
- `show` returns machine-readable properties. Without an explicit property limit, it can include many paths or environment details.
- `status` is human-oriented; its output can be truncated and can include recent logs.

Unit names differ by distribution. Find a real Agent service from a deployment manifest or `systemctl list-unit-files --type=service`; do not guess `agent.service`.

## Journal: limit by time and unit

```bash
journalctl --unit=systemd-journald.service \
  --since '-10 min' \
  --lines=50 \
  --no-pager
```

Common read-only filters:

```bash
journalctl --priority=warning..alert --since today --no-pager
journalctl --boot=0 --lines=100 --no-pager
journalctl --disk-usage
```

Notes:

- Accessing the system journal can require group permission or sudo. Without authorization, record “insufficient permission”; do not elevate by default.
- Logs can contain tokens, user input, internal addresses, and request bodies. Limit the unit, time window, and line count before copying anything; do not paste a raw full set.
- `--follow` occupies the terminal continuously; stop it with `Ctrl-c`.
- Container applications commonly write logs to stdout/stderr for collection by the container runtime. In that case, host journal, container logs, and application files are different layers.

## User services and system services

Ordinary users can also have user units:

```bash
systemctl --user list-units --type=service --state=running --no-pager
```

`systemctl --user` connects to a user-level manager; it is not a system-level service. A troubleshooting report must record which layer, user, and unit it inspected.

## Change commands are syntax reference only

```text
systemctl start SERVICE
systemctl stop SERVICE
systemctl restart SERVICE
systemctl enable SERVICE
systemctl disable SERVICE
systemctl daemon-reload
```

These commands change external state and can interrupt traffic or alter boot behavior. This course does not use them as exercises. A real operation needs change authorization, dependency checks, health checks, traffic strategy, and a rollback plan. Whether a unit modification requires `daemon-reload` must be decided from the actual change.

## Read-only troubleshooting flow

1. Confirm the host, user, PID 1, and systemd availability.
2. Confirm the unit name from the deployment manifest.
3. Retain `status`, key `show` properties, and journal data with an explicit time window.
4. Separate facts: unit state, MainPID, exit reason, and log timestamps.
5. Check processes, ports, and resources next. Do not restart immediately because of one error line.
6. List actions needing elevation or state change as “pending approval”; do not execute them during investigation.

## Hands-on exercise

In an environment you own that really uses systemd, investigate only `systemd-journald.service`:

```bash
unit='systemd-journald.service'
systemctl status --no-pager --lines=20 "$unit"
status_rc=$?
systemctl show --property=ActiveState,SubState,MainPID "$unit"
journalctl --unit="$unit" --since '-5 min' --lines=20 --no-pager
printf 'status_rc=%s\n' "$status_rc"
```

If the environment does not use systemd, write only the environment evidence and an “not applicable” conclusion; do not install an alternative. The report must distinguish the `status` command’s exit status, the unit’s current state, and application health you have not verified.

## Mastery check

- [ ] I can explain why active and enabled differ.
- [ ] I can distinguish a system unit, user unit, and container application process.
- [ ] I can limit a journal by unit, time, and lines, and explain the secret-exposure risk.
- [ ] I can list the authorization and rollback evidence needed before start/restart.

Next: [[linux-commands/12-networking-and-ports|Networking and ports]].

## References

Retrieved on **2026-07-14**.

- [systemctl](https://www.freedesktop.org/software/systemd/man/latest/systemctl.html)
- [journalctl](https://www.freedesktop.org/software/systemd/man/latest/journalctl.html)
- [systemd.unit](https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html)
- [Microsoft: Use systemd to manage Linux services with WSL](https://learn.microsoft.com/windows/wsl/systemd)
