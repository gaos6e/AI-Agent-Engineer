---
title: "Legacy Quick Reference: Common Linux Commands"
tags:
  - linux
  - reference
aliases:
  - Common Linux command quick reference
lang: en
translation_key: Linux命令/00A-常用指令.md
translation_source_hash: 26a3aa9db3af3cf4090148f1d4134fbdf52b90343a28ed343344145ff65fd02d
translation_route: zh-CN/Linux命令/00A-常用指令
translation_default_route: zh-CN/Linux命令/00A-常用指令
---

# Legacy Quick Reference: Common Linux Commands

> [!warning] Templates are not directly runnable scripts
> This page preserves the original quick-reference material. Angle brackets mark placeholders that you must replace. See [[linux-commands/00-index|the unified Linux Commands entry point]] for full explanations, safety guardrails, and runnable exercises. Do not paste placeholders unchanged, and do not recursively remove `/`, a home directory, mount points, or a real project.

## tmux

### Create a session

```text
tmux new -s <session_name>
```

### Enter a session

```text
tmux attach -t <session_name>
```

### List existing sessions

```bash
tmux ls
```

### Remove a session

```text
tmux kill-session -t <session_name>
```

## Directory operations

### Remove a directory and its contents

```text
rm -r <folder_path>
```

### Force-recursive-deletion signature (recognition only)

```text
rm -rf <folder_path>
```

Force-recursive deletion skips some confirmations and can cause irreversible loss when a variable is empty or a path is miscalculated. This knowledge base does not provide a directly runnable version. First study absolute paths, ownership, symbolic links, and target-boundary checks in [[linux-commands/03-file-and-directory-operations|File and directory operations]].

## Compressing and extracting directories

### Create a `.tar` archive

```text
tar -cvf <archive_name>.tar <folder_path>
```

### Create a `.tar.gz` archive

```text
tar -czvf <archive_name>.tar.gz <folder_path>
```

### Create a `.zip` archive

```text
zip -r <archive_name>.zip <folder_path>
```

### Extract a `.tar` archive

```text
tar -xvf <archive_name>.tar
```

### Extract a `.tar.gz` archive

```text
tar -xzvf <archive_name>.tar.gz
```

### Extract a `.zip` archive

```text
unzip <archive_name>.zip
```

Before extracting an untrusted archive, list its contents and constrain the destination to a newly created empty directory. See [[linux-commands/13-archiving-and-extraction|Archiving and extraction]].

## Conda environment management

### Show the Conda version

```bash
conda --version
```

### List all environments

```bash
conda env list
```

The currently active environment is marked with `*`.

### Create an environment

```text
conda create --name <env_name> python=<python_version>
```

For example, create `myenv` with Python 3.11:

```bash
conda create --name myenv python=3.11
```

### Activate and leave an environment

```text
conda activate <env_name>
conda deactivate
```

### List packages in an environment

```text
conda list --name <env_name>
```

### Search, install, update, and remove packages

```text
conda search <package_name>
conda install --name <env_name> <package_name>
conda update --name <env_name> <package_name>
conda remove --name <env_name> <package_name>
```

Install from a named channel:

```text
conda install --name <env_name> --channel conda-forge <package_name>
```

### Clone an environment

```text
conda create --name <new_env_name> --clone <source_env_name>
```

### Export and reproduce an environment

Exporting only the principal manually installed dependencies is usually more suitable for cross-platform reproduction:

```text
conda env export --name <env_name> --from-history > environment.yml
```

Create or update an environment from an environment file:

```bash
conda env create --file environment.yml
conda env update --file environment.yml --prune
```

### Remove an entire environment

```text
conda remove --name <env_name> --all
```

Before removal, confirm the environment name with `conda env list`. When you need `pip`, activate the intended Conda environment first, then run `python -m pip ...` to avoid installing into the wrong Python environment.
