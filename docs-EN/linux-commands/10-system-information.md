---
title: "10 System Information"
tags:
  - linux
  - command
  - tutorial
aliases:
  - Linux system-information commands
source_checked: 2026-07-14
lang: en
translation_key: Linux命令/10 系统信息.md
translation_source_hash: 8c723f63c22ed0ced067da03488ff31322926b4d67422763103c7890c8d860c7
translation_route: zh-CN/Linux命令/10-系统信息
translation_default_route: zh-CN/Linux命令/10-系统信息
---

# 10 System Information

## Learning objectives

- Inspect system version, hostname, and uptime.
- Inspect CPU, memory, disk space, and block devices.
- Make a quick judgment about resource pressure.

## Command overview

| Command | Purpose | Meaning | Basic usage | Example |
|---|---|---|---|---|
| `uname` | View kernel information | Unix name; shows kernel and architecture information | `uname [options]` | `uname -a` |
| `hostname` | View or set hostname | Shows the current machine name | `hostname` | `hostname` |
| `uptime` | View uptime and load | Shows uptime, user count, and load average | `uptime` | `uptime` |
| `date` | View or set time | Shows current date and time | `date` | `date` |
| `free` | View memory | Shows memory and swap use | `free [options]` | `free -h` |
| `df` | View disk space | Disk free; shows filesystem free space | `df [options]` | `df -h` |
| `du` | View directory use | Disk usage; totals file or directory size | `du [options] path` | `du -sh -- .` |
| `lsblk` | View block devices | List block devices; lists disks and partitions | `lsblk` | `lsblk` |
| `lscpu` | View CPU information | List CPU; shows CPU architecture and core count | `lscpu` | `lscpu` |

## Common scenarios

Show system and host information:

```bash
uname -a
hostname
date
uptime
```

View memory:

```bash
free -h
```

View disk space:

```bash
df -h
df -ih
```

View item sizes in the current directory:

```bash
du -sh -- ./*
```

View disks and CPU:

```bash
lsblk
lscpu
```

## Notes for beginners

- `-h` commonly means human-readable sizes in KB, MB, and GB.
- `df -h` shows filesystem free space; `du -sh` shows actual directory use.
- `df -i` shows inodes. Having free capacity does not prove you can create another file.
- `du -sh -- ./*` excludes hidden entries and can be slow in a large directory containing many files; a script must state its scan scope.
- Interpret `uptime` load average with the CPU core count; it is not a simple percentage.
- `lsblk` only displays devices and partitions. Do not casually format or mount disks.
- `free`, `ps`, and `uptime` commonly come from procps-ng; `lsblk` and `lscpu` from util-linux. Minimal containers and macOS/BSD can lack them.
- Linux commonly uses free memory as cache. For troubleshooting, focus on `available`, swap, and sustained trends rather than the `free` column alone.
- In a container, commands can show different namespace, cgroup, or host views. Do not automatically interpret output as the container limit.

## Read-only resource-evidence exercise

```bash
uname -srm
uptime
free -h
df -h -- .
df -ih -- .
du -sh -- .
lscpu | sed -n '1,12p'
```

A report must distinguish a momentary snapshot, trend, and unknowns. Do not claim a root cause from one load or memory output.

## References

- [procps-ng](https://gitlab.com/procps-ng/procps)
- [util-linux](https://www.kernel.org/pub/linux/utils/util-linux/)
- [Linux cgroup v2](https://docs.kernel.org/admin-guide/cgroup-v2.html)
