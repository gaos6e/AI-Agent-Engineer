---
title: "14 Package Management and Safe Downloads"
aliases:
  - Linux package-management introduction
  - Safe download and installation
tags:
  - AI-Agent-Engineer
  - Linux
  - package-management
  - supply-chain
source_checked: 2026-07-14
lang: en
translation_key: Linux命令/14 软件包管理与安全下载.md
translation_source_hash: 660ec30ba247d0de345c37fbe1d275bc207dfcaf2f25ab027e7e99057db5f1d9
translation_route: zh-CN/Linux命令/14-软件包管理与安全下载
translation_default_route: zh-CN/Linux命令/14-软件包管理与安全下载
---

# 14 Package Management and Safe Downloads

## Learning objectives

Identify the distribution and package manager; distinguish system packages from Python/Node project dependencies; query installed versions and origins read-only; and establish a supply-chain workflow of “download, verify, review, execute with least privilege.”

## Identify the system first; do not guess a command

```bash
cat -- /etc/os-release
uname -srm
for tool in apt-get dnf5 dnf pacman apk; do
  if command -v -- "$tool" >/dev/null 2>&1; then
    printf 'package_manager=%s\n' "$tool"
  fi
done
```

Common mapping:

| Distribution family | Common tools | Package-database query |
| --- | --- | --- |
| Debian / Ubuntu | APT, dpkg | `apt-cache`, `dpkg-query` |
| Fedora / RHEL | DNF5, DNF, RPM | `dnf5`/`dnf`, `rpm` |
| Arch | pacman | `pacman -Q` |
| Alpine | apk | `apk info` |

A container image can deliberately omit a package manager, and enterprise images can use internal repositories. Do not install another distribution’s manager merely to make commands “consistent.”

## System packages and project dependencies are not one layer

- A system package manager maintains shared libraries, commands, and system integration.
- Python’s `venv + pip`, Node lockfiles, and a project directory maintain application dependencies.
- Packages with the same name in a system repository and language repository might not be the same release artifact.
- Do not casually run `sudo pip install` in the system Python. Create a virtual environment as described in [[python-fundamentals/00-index|Python Fundamentals]].

## Read-only query examples

Debian/Ubuntu:

```bash
apt-cache policy curl
dpkg-query --show --showformat='${Package}\t${Version}\n' curl
```

Fedora/RHEL:

```bash
rpm -q --queryformat '%{NAME}\t%{VERSION}-%{RELEASE}\n' curl
```

Arch:

```bash
pacman -Qi curl
```

Alpine:

```bash
apk info -a curl
```

When a command reports “not installed,” the course has not failed. Record the distribution, available tool, and exit status. Repository queries can access the network, refresh metadata, or disclose internal source names, so confirm policy in a real environment.

## Installation and upgrade change external state

```text
sudo apt-get update
sudo apt-get install PACKAGE
sudo dnf5 install PACKAGE
sudo dnf install PACKAGE
sudo pacman -S PACKAGE
sudo apk add PACKAGE
```

These are syntax entry points only and are not executed in this course. Effects can include:

- Modifying system files, services, shared libraries, and the dependency set;
- Triggering maintainer scripts or service restarts;
- Holding the package-manager lock and conflicting with automated updates;
- Changing image reproducibility or remote-host audit state.

Install on production and shared hosts through image builds, configuration management, or an approved change process. Retain versions, origins, dependencies, disk impact, tests, and a rollback plan first.

## Why blind `curl | sh` is prohibited

```text
curl URL | sh
curl URL | sudo sh
```

A pipeline hands a network response straight to a Shell: you cannot first verify final redirect content, an HTTP error page, script version, signature, or effective privilege. TLS protects a particular transport connection; it does not automatically prove that a publisher, content, or future behavior is trustworthy.

A safer general workflow:

1. Get a fixed-version URL from the project’s official release page.
2. Download to a new file; do not execute it directly.
3. Obtain a checksum or signature through an independent official channel.
4. After verification, review the script manually or inspect the archive listing.
5. Run with least privilege in an isolated environment, recording source and version.

Syntax illustration:

```text
curl --fail --location --show-error \
  --connect-timeout 5 --max-time 120 \
  --output tool-v1.2.3.tar.gz \
  https://OFFICIAL-HOST/releases/tool-v1.2.3.tar.gz

printf '%s  %s\n' EXPECTED_SHA256 tool-v1.2.3.tar.gz | sha256sum --check -
tar -tzf tool-v1.2.3.tar.gz
```

Angle brackets and uppercase placeholder values must be replaced. This block is a process template, not a directly runnable example. `--fail` makes only some HTTP errors fail; it does not prove content is safe. A checksum retrieved from the same compromised page is not independent trust evidence.

## Repository and key boundaries

- Do not casually add third-party repositories, import signing keys, or disable signature verification.
- Do not use obsolete global-trust methods to bypass repository instructions. Follow the distribution’s current official documentation to configure a minimum-scope keyring.
- Proxy, repository-URL, and authentication configuration can contain internal information or credentials; do not paste them completely into logs.
- SBOMs, lockfiles, image digests, and signatures can improve traceability, but they still need vulnerability and provenance review.

## Hands-on exercise: read-only asset inventory

In a Linux lab environment you own, make a report that contains no private repository URL:

```bash
printf 'os_id='
. /etc/os-release
printf '%s\n' "$ID"
printf 'kernel=%s\n' "$(uname -r)"
for tool in apt-get dnf5 dnf pacman apk; do
  if command -v -- "$tool" >/dev/null 2>&1; then
    printf 'found=%s path=%s\n' "$tool" "$(command -v -- "$tool")"
  fi
done
command -v -- curl || true
command -v -- sha256sum || true
```

`. /etc/os-release` executes this trusted system file in the current Shell. Do not generalize `source`/`.` to an unknown downloaded script. This exercise identifies capabilities only; it does not install, upgrade, or download anything.

## Mastery check

- [ ] I can choose the right package manager from `/etc/os-release` instead of guessing.
- [ ] I can distinguish system packages, Python virtual-environment dependencies, and container-image layers.
- [ ] I can explain why installation/upgrading needs authorization, tests, and rollback.
- [ ] I can separate a network download into fixed version, download, independent verification, review, and least-privilege execution.
- [ ] I do not solve installation problems by disabling signature verification or using `curl | sh`.

Next: [[linux-commands/15-shell-environment-and-variables|Shell environment and variables]].

## References

Retrieved on **2026-07-14**.

- [APT manual](https://manpages.debian.org/stable/apt/apt.8.en.html)
- [DNF5 documentation](https://dnf5.readthedocs.io/en/latest/)
- [DNF 4 documentation](https://dnf.readthedocs.io/en/latest/)
- [pacman manual](https://man.archlinux.org/man/pacman.8)
- [Alpine Package Keeper](https://wiki.alpinelinux.org/wiki/Alpine_Package_Keeper)
- [curl command-line manual](https://curl.se/docs/manpage.html)
- [GNU Coreutils sha2 utilities](https://www.gnu.org/software/coreutils/manual/html_node/sha2-utilities.html)
