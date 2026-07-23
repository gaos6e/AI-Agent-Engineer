---
title: "Git 状态模型与提交图"
aliases:
  - Git 心智模型
  - 工作区、暂存区与 HEAD
tags:
  - AI-Agent-Engineer
  - Git
  - version-control
source_checked: 2026-07-14
source_version: Git 2.55.0 docs
lang: zh-CN
translation_key: Git/02A-Git 状态模型与提交图.md
translation_route: en/git/02a-git-state-model-and-commit-graph
translation_default_route: zh-CN/Git/02A-Git-状态模型与提交图
---

# Git 状态模型与提交图

## 本节目标

学完本节，你应能解释 Git 保存了什么、一次 `add` 与一次 `commit` 分别改变哪一层，以及 `HEAD`、分支和提交图之间的关系。先建立模型，再记命令，遇到撤销或冲突时才不会靠猜。

## 先用一个类比理解

把项目想成一张需要反复出版的技术手册：

- **工作区（working tree）**：你桌上正在修改的稿件。
- **暂存区（index / staging area）**：下一版准备印刷的目录树。
- **提交（commit）**：一次已经编号归档的版本快照。
- **分支（branch）**：贴在某个提交上的可移动书签。
- **`HEAD`**：当前正在使用哪个书签；处于 detached HEAD 时，它会直接指向提交。

`git add` 不是“告诉 Git 文件存在”，而是把选定路径当前内容复制到 index。`git commit` 再根据 index 创建新提交，并让当前分支书签向前移动。工作区里尚未暂存的内容不会进入这次提交。

## Git 主要保存快照，而不是操作录像

从使用者视角看，每个提交描述一个完整目录树。Git 会复用未变化的对象，并在存储与传输层做压缩，因此不等于每次机械复制全部文件。关键是：提交记录“这一刻的树是什么”，而不是一串必须顺序重放的编辑动作。

最常见的对象有：

| 对象 | 保存什么 | 为什么重要 |
| --- | --- | --- |
| blob | 文件内容，不含文件名 | 相同内容可以复用 |
| tree | 文件名、目录结构和对象引用 | 表示一次目录树快照 |
| commit | tree、父提交、作者、时间和消息 | 把快照接入历史图 |
| annotated tag | 对象、标签作者、消息等 | 给发布位置增加有说明的稳定名称 |

对象名称由内容计算得到。内容变化会得到不同对象 ID；这让 Git 能发现对象损坏，但 Git 本身不是访问控制或秘密保险箱。

## 三层状态如何比较

| 想回答的问题 | 比较对象 | 常用命令 |
| --- | --- | --- |
| 工作区相对 index 改了什么 | working tree ↔ index | `git diff` |
| index 将比 `HEAD` 多什么 | index ↔ `HEAD` | `git diff --staged` |
| 当前已跟踪内容总体比 `HEAD` 多什么 | working tree + index ↔ `HEAD` | `git diff HEAD` |
| 未跟踪文件有哪些 | Git 状态数据库 ↔ 工作区路径 | `git status --short` |

普通未跟踪文件不会出现在 `git diff HEAD`。提交前必须同时看 `status` 和 diff。

```text
编辑文件                  git add                  git commit
工作区  ─────────────────▶  index  ─────────────────▶  新 commit
  ▲                           │                         │
  └──── git restore ──────────┘                         └── 当前分支向前移动
```

## `HEAD`、分支与提交图

普通状态下，`HEAD` 是一个符号引用，例如它指向 `refs/heads/main`；`main` 再指向某个提交。创建新提交时，Git 让该提交把原提交记为父提交，然后移动 `main`。

```text
A ← B ← C   main, HEAD
         \
          D ← E   feature/demo
```

当两条分支分别新增提交，就形成分叉。历史不是简单列表，而是由“父提交”关系构成的有向无环图（DAG）。合并提交可以有两个或更多父提交。

两个容易混淆的状态：

- **unborn branch**：刚 `git init`、尚无首个提交时，分支名称存在于意图层面，但还没有可指向的提交。
- **detached HEAD**：`HEAD` 直接指向某个提交，而不是本地分支。此时能提交，但若不创建分支，后续切走后新提交可能变得难以找到。

检查当前情况：

```powershell
git branch --show-current
git status --short --branch
git symbolic-ref --short HEAD
```

detached HEAD 下第三条会失败；这正是证据，不要为了消除报错随意创建或切换分支。

## 用只读命令观察对象

在已经至少有一次提交的隔离仓库中运行：

```powershell
git rev-parse --show-toplevel
git rev-parse HEAD
git cat-file -t HEAD
git cat-file -p HEAD
git ls-files --stage
git log --graph --oneline --decorate --all
```

观察要点：

1. `cat-file -p HEAD` 中能看到 tree、parent（首个提交除外）、author、committer 与消息。
2. `ls-files --stage` 展示 index 条目；它不是普通文件夹，也不等于工作区。
3. `log --graph` 展示引用与父子关系；分支名不是提交的永久组成部分。

## 常见误区

- **“commit 保存当前目录所有东西”**：错。它保存 index 对应的树；未跟踪和未暂存内容可能不在其中。
- **“分支复制了一套文件”**：错。分支通常只是一个很小的引用，文件内容来自它指向的提交树。
- **“Git 记录了重命名事件”**：提交保存前后快照；查看历史时 Git 依据相似度推断 rename。
- **“哈希能保护秘密”**：错。进入对象数据库的凭据可能仍可从历史读取，必须轮换并按流程清理。
- **“reflog 是永久备份”**：错。它是本地且会过期，不能替代远程备份和制品归档。

## 练习与自测

写出以下三个动作之后，工作区、index、`HEAD` 和当前分支分别发生什么变化：

1. 修改 `README.md`，尚未 `add`。
2. 执行 `git add -- README.md`。
3. 执行 `git commit -m "docs: update readme"`。

再回答：为什么 `git restore --staged -- README.md` 不应删除工作区修改？为什么 detached HEAD 中的新提交需要创建分支才能长期保留一个易用入口？

动手验证请进入 [[Git/12-版本控制实战与自测|版本控制实战与自测]]，不要在真实项目中为了学习制造提交。

## 小结与下一步

Git 的核心不是命令数量，而是“对象 + 引用 + 三层状态”。下一步学习 [[Git/03-暂存区与文件操作|暂存区与文件操作]]，把这个模型映射到精确的路径选择。

## 参考资料

按 Git 2.55.0 官方文档核验，获取日期：**2026-07-14**。

- [Git Glossary](https://git-scm.com/docs/gitglossary)
- [Git User Manual：The Object Database](https://git-scm.com/docs/user-manual#the-object-database)
- [Git Repository Layout](https://git-scm.com/docs/gitrepository-layout)
- [git status](https://git-scm.com/docs/git-status)
- [git diff](https://git-scm.com/docs/git-diff)

