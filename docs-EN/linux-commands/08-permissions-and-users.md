---
title: "08 Permissions and Users"
tags:
  - linux
  - command
  - tutorial
aliases:
  - Linux permissions and user commands
source_checked: 2026-07-14
lang: en
translation_key: Linux命令/08 权限与用户.md
translation_source_hash: ac5046796220106e463cf347f57bfea2a4ddd391c13d9150c6fa2b03ab9f5a49
translation_route: zh-CN/Linux命令/08-权限与用户
translation_default_route: zh-CN/Linux命令/08-权限与用户
---

# 08 Permissions and Users

## Learning objectives

- Inspect the current user identity and groups.
- Understand file read, write, and execute permissions.
- Use administrator privileges when required.

## Command overview

| Command | Purpose | Meaning | Basic usage | Example |
|---|---|---|---|---|
| `whoami` | Show the effective user | Displays the effective user of the current process | `whoami` | `whoami` |
| `id` | Show user and group IDs | Displays UID, GID, and group membership | `id [user_name]` | `id` |
| `groups` | Show groups | Displays groups of the current or named user | `groups [user_name]` | `groups` |
| `chmod` | Change permissions | Change mode; changes read/write/execute permission | `chmod permissions file` | `chmod u+x -- script.sh` |
| `chown` | Change ownership | Change owner; usually needs authorization; see syntax reference below | `chown user:group file` | `chown -- USER:GROUP /absolute/path` |
| `sudo` | Change execution identity under policy | Runs a command as root or another user under sudoers policy | `sudo [options] command` | `sudo -l` |
| `su` | Switch user | Substitute user; switches to another user | `su user_name` | `su root` |
| `passwd` | Change a password | Sets a password for the current or named user | `passwd [user_name]` | `passwd` |

## Common scenarios

Inspect the current identity:

```bash
whoami
id
groups
```

Give a script its owner execute permission:

```bash
chmod u+x -- run.sh
./run.sh
```

Set common file modes:

```bash
chmod 644 config.txt
chmod 755 script.sh
```

View sudo policy (authentication may be required):

```text
sudo -l
```

Changing ownership changes external state, so this is syntax reference only:

```text
sudo chown -- USER:GROUP /absolute/path
```

## Notes for beginners

- Linux modes commonly distinguish the file owner, group, and other users. ACLs, capabilities, and SELinux/AppArmor can add constraints.
- `r` means read, `w` means write, and `x` means execute.
- On a directory, `x` means traverse/search directory entries, not “execute the directory.” Reading directory names normally also requires `r`.
- `chmod u+x` explicitly adds execute only for the owner. The result of `chmod +x` without a `who` can be affected by umask.
- `644/755` are common examples, not universal security answers. Secret files, shared directories, and service accounts need an actual access-model design.
- What `sudo` can run is determined by policy; it does not grant unlimited administrator authorization. Reconfirm before deletion, overwriting, or permission changes.
- Do not operate as root long-term. When elevation is necessary, prefer `sudo`.

## A minimal intuition for numeric modes

`r=4`, `w=2`, and `x=1`. Adding each group produces the owner/group/other digits. For example, `640` means owner read/write, group read-only, and no permission for others. Inspect rather than memorize:

```bash
umask
stat --format='%A %a %U:%G %n' -- config.txt
namei -l -- "$PWD/config.txt"
```

`namei` is part of util-linux and can be absent on a minimal system. It helps inspect directory traversal permission one component at a time.

## Exercise without sudo

In your own lab directory, create `run.sh` and `config.txt`, then change only owner permissions:

```bash
chmod u+x,go-x -- run.sh
chmod u=rw,g=r,o= -- config.txt
stat --format='%A %a %U:%G %n' -- run.sh config.txt
```

Do not recurse with `chmod` or `chown`. A real recursive change must verify the canonical absolute path, that owner/group exist, symbolic links, mount boundaries, and authorization.

## References

- [GNU Coreutils: User information](https://www.gnu.org/software/coreutils/manual/html_node/User-information.html)
- [GNU Coreutils chmod](https://www.gnu.org/software/coreutils/manual/html_node/chmod-invocation.html)
- [sudo manual](https://www.sudo.ws/docs/man/sudo.man/)
