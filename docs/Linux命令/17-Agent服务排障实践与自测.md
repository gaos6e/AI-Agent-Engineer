---
title: Agent服务排障实践与自测
tags:
  - AI-Agent-Engineer
  - Linux
  - 综合实践
aliases:
  - Linux 排障项目
source_checked: 2026-07-14
---

# Agent 服务排障实践与自测

## 项目目标

在一个完整、独立的 Bash 脚本中完成两类受控任务：

1. 对确定性虚构 Agent 日志做行数、错误数、状态分布、延迟与缺失字段验证。
2. 启动只绑定 `127.0.0.1` 的短生命周期 HTTP 服务，核对 PID、请求日志、监听证据、HTTP 响应与停止结果。

最终产物是 `report.md` 和配套证据文件。报告必须区分事实、推断与限制，不能用“命令没有报错”替代断言。

完整实现见 [run-agent-cli-lab.sh](Linux%E5%91%BD%E4%BB%A4/examples/run-agent-cli-lab.sh)。本页只解释设计与验收，不再让学习者跨多个代码围栏维持变量和 trap；脚本才是唯一执行单元。

> [!important] 安全边界
> 脚本拒绝 root，拒绝临时根目录与 `/`、家目录或启动时工作区存在父子路径重叠；检查原始实验路径不是符号链接、canonical path 位于预期前缀、目录属于当前用户，并在写入前再次断言 `pwd -P`。它不使用 sudo、不扫描所有用户进程、不读取完整环境、不连接公网，也不自动递归删除实验目录。

## 前置课程

- [[Linux命令/00A-Linux环境与Shell基础|Linux 环境与 Shell 基础]]：Shell、退出状态、引用与实验边界。
- [[Linux命令/05 搜索与查找|搜索与查找]]、[[Linux命令/06 文本处理|文本处理]]：限定范围并生成统计。
- [[Linux命令/07 管道重定向与命令组合|管道与重定向]]：stdout、stderr、`pipefail` 和分段失败。
- [[Linux命令/09 进程管理|进程管理]]：PID、owner、SIGTERM、`wait` 与停止核验。
- [[Linux命令/12 网络与端口|网络与端口]]：loopback、监听 socket 与 HTTP 证据边界。

## 为什么使用完整脚本

交互式复制多个代码块会产生两种相反风险：

- 每块单独启动 Shell：`lab_real`、PID、退出状态和 trap 会丢失。
- 全部粘贴到日常交互 Shell：`exit` 可能关闭当前 Shell，trap 也可能残留。

完整脚本以 `bash script` 启动专用子进程；失败只退出该子 Bash，EXIT trap 只负责停止脚本自己保存并核对过 owner 的实验 PID。INT 与 TERM 分别保留 130、143 退出语义。

## 第 0 阶段：先做静态检查

在本知识库目录中运行：

```bash
bash --noprofile --norc -n ./examples/run-agent-cli-lab.sh
```

退出码 0 只证明 Bash 能解析脚本，不证明命令存在、Linux 行为正确或项目运行成功。

## 第 1 阶段：日志与资源模式

先运行不启动网络服务的模式：

```bash
bash --noprofile --norc ./examples/run-agent-cli-lab.sh --log-only
```

脚本输出唯一 `lab=` 与 `report=` 绝对路径。不要把它改成 `/`、`$HOME`、真实项目或共享挂载点。

### 1.1 原始样本保持不变

`service.log` 固定为 4 条虚构记录：

```text
2026-07-14T10:00:01Z level=INFO run_id=r1 latency_ms=120 status=ok
2026-07-14T10:00:02Z level=ERROR run_id=r2 latency_ms=2200 status=timeout
2026-07-14T10:00:03Z level=WARNING run_id=r3 latency_ms=950 status=retry
2026-07-14T10:00:04Z level=ERROR run_id=r4 latency_ms=1800 status=timeout
```

脚本必须用代码断言：

- 主样本行数为 4；
- `level=ERROR` 为 2 条；
- 状态分布为 `ok=1`、`retry=1`、`timeout=2`；
- 延迟摘要为 `count=4 mean=1267.5`。

状态 pipeline 的退出码和实际文件都会保存；预期文件与实际文件必须通过 `cmp`，而不是靠肉眼猜“看起来一样”。

### 1.2 缺失字段只污染副本

脚本复制主样本为 `service-with-missing.log`，再追加第 5 条缺少 `latency_ms` 的记录。随后断言：

- 副本总行数为 5；
- 可用于延迟统计的记录仍为 4；
- 延迟摘要与主样本完全一致。

这样 `service.log`、`status-counts.txt` 和报告中的主样本事实仍保持 4 条，不会出现“追加后文件有 5 条、报告却写 4 条”的矛盾。

### 1.3 资源证据的边界

`resource-evidence.txt` 只调查实验路径，并按可用性调用 `df`、`du`、`uptime` 和 `free`。瞬时资源快照不等于根因；Git Bash、最小容器、WSL 与原生 Linux 的工具和资源视图可能不同。

脚本只输出 `APP_ENV` 的单个允许字段，不运行裸 `env`、`set`、`export -p` 或 `ps -ef`，避免收集无关秘密与其他用户命令行。

## 第 2 阶段：完整 loopback 服务

仅在自有 WSL、容器或 Linux 环境运行：

```bash
bash --noprofile --norc ./examples/run-agent-cli-lab.sh
```

默认端口是 8765。只有在确认冲突且统一调整实验配置时，才使用无前导 0 的 1–5 位十进制 `LAB_PORT`，脚本再强制按十进制解析并限定到 1024–65535；不要终止占用端口的未知进程。

### 2.1 启动前证据

脚本要求可运行的 `python3` 与 curl，而不只检查同名路径存在。服务使用：

```text
python3 -m http.server PORT --bind 127.0.0.1 --directory LAB_REAL
```

`http.server` 只用于受控实验，不是生产服务器。绑定 `127.0.0.1` 避免暴露到其他接口；服务 PID 来自 `$!`，随后用 `ps` 核对 owner 并保存进程证据。

### 2.2 就绪、响应与请求日志

就绪循环把 `--disable` 放在 curl 的第一个选项，并使用 `--noproxy '*'`，从而忽略 `.curlrc` 和代理环境变量，直接访问 loopback；它还同时设置连接超时和总超时，并在进程提前退出时停止等待。成功必须满足：

- curl 返回成功；
- `health-response.json` 与固定 `health.json` 通过 `cmp`；
- `server.log` 中出现 `/health.json` 的 GET 200 记录；
- 请求日志命中数写入证据文件与报告。

这才形成“请求—响应—应用日志—PID”的正向闭环。它仍不证明远程可达、TLS、认证、依赖或生产健康。

### 2.3 端口证据

若 `ss` 可用，脚本保存 `ss -lntp` 的限定端口输出，并分别记录：

- 是否观察到目标端口监听；
- 输出是否允许核对到实验 PID。

普通用户或特定环境可能看不到 process 字段；此时报告必须写 `unavailable`，不能伪造“已验证端口所有者”。

### 2.4 TERM、等待与停止后请求

脚本保存并检查：

- `kill -TERM` 的退出码必须为 0；
- `wait` 的实际退出码；
- `kill -0` 是否仍观察到 PID；
- 停止后 curl 的精确退出码。

本实验要求停止后 loopback 连接得到 curl 7（无法连接），并同时要求 PID 已消失；其他非零值视为不同失败类别，不能笼统写成“停止成功”。没有使用 SIGKILL。

## 证据文件

| 文件 | 证明什么 | 不能证明什么 |
| --- | --- | --- |
| `report.md` | 本次脚本实际记录的断言结果与限制 | 不是生产事故报告 |
| `service.log` | 4 条确定性主样本 | 不代表真实流量分布 |
| `service-with-missing.log` | 缺字段副本有 5 条 | 不改变主样本 |
| `status-counts.txt` | 状态 pipeline 的实际输出 | 不代表未来趋势 |
| `latency-summary*.txt` | 主样本与脏副本的可解析延迟摘要 | 缺失字段不是 0 |
| `shell-process-evidence.txt` | 当前子 Shell 的有限进程证据或不可用声明 | 不扫描其他用户 |
| `resource-evidence.txt` | 实验路径的瞬时资源证据 | 不等于根因 |
| `server-process-evidence.txt` | 实验服务 PID、owner 与命令行 | 只在完整模式生成 |
| `request-log-evidence.txt` | 成功健康请求对应的日志行 | 不证明业务依赖健康 |
| `port-evidence.txt` | `ss` 可用时的限定监听输出 | process 字段可能不可见 |

## 报告写作

阅读 `report.md` 后，另写以下四段，不把推测混入事实：

### Confirmed facts

只写断言和证据文件直接支持的内容，例如主样本行数、统计结果、PID 与退出码。

### Reasonable inferences

说明证据组合支持但未直接证明的判断，例如“实验子进程很可能是本次 HTTP 服务”。

### Unknowns

列出未验证的远程网络、TLS、认证、依赖、生产流量和真实 service manager 状态。

### Actions requiring approval

列出 restart、提权、安装软件、改防火墙、改端口暴露、删除目录等外部状态变更；本项目不执行。

## 练习目录为什么不自动删除

自动清理会破坏审阅证据，也可能把路径计算错误升级成递归删除事故。完成后先人工检查输出的绝对路径、owner、符号链接、内容与报告。递归删除签名只作识别：

```text
rm -rf -- VERIFIED_ABSOLUTE_LAB_PATH
```

不要在课程中直接运行这条模板；是否清理由学习者在独立确认后决定。

## 自测

1. 为什么 `$SHELL` 不能证明当前正在运行的 Shell？
2. 为什么脚本拒绝 `/`、家目录与启动工作区作为 `$TMPDIR` canonical root？
3. 为什么既检查原始 `lab_dir` 是否为 symlink，又检查 canonical prefix？
4. `wc -l` 数的是记录、逻辑行还是换行符？
5. GNU grep 的 0、1、2 分别表示什么？
6. 为什么状态 pipeline 要保存退出码并与预期文件比较？
7. 为什么缺少 latency 的记录放入副本，而不是直接追加主样本？
8. 为什么 `count=4 mean=1267.5` 不能外推到生产总体？
9. `127.0.0.1`、`0.0.0.0` 与端口映射有什么区别？
10. curl 成功、HTTP 200、响应体匹配、请求日志各增加了什么证据？
11. `ss` 看不到 PID 时，报告应该写什么？
12. 为什么 SIGTERM 后要同时检查 kill rc、wait rc、PID 和停止后 curl rc？
13. 为什么 curl 的任意非零值不能都解释为“连接被拒绝”？
14. 为什么脚本使用专用子 Bash，而不是跨围栏复制或污染日常 Shell？
15. 哪些真实修复动作需要授权、回滚与 service manager？

## 评分与验收

| 项目 | 分值 | 客观证据 |
| --- | ---: | --- |
| 路径与身份护栏 | 15 | 非 root；危险 root 拒绝；raw symlink、canonical prefix、owner 与 `pwd -P` 断言通过 |
| 主日志断言 | 15 | 4 行、2 ERROR、固定状态分布均由代码断言 |
| 缺失字段测试 | 10 | 副本 5 行但 latency count 仍为 4，摘要一致 |
| 管道与退出码 | 10 | 状态 pipeline rc 为 0，实际文件与预期文件一致 |
| 请求闭环 | 15 | 固定响应匹配，GET 200 日志证据存在 |
| PID 与监听 | 10 | PID owner 已核对；`ss` 证据如实标记 yes/unavailable |
| 停止验证 | 15 | TERM rc、wait rc、PID 消失和 curl rc 7 全部记录 |
| 报告边界 | 10 | 事实、推断、未知和需授权动作分开 |

满分 100，至少 80 分且“路径与身份护栏”“请求闭环”“停止验证”不得为 0。`--log-only` 只验收日志与资源部分，不能获得完整项目通过结论。

## 掌握标准

- [ ] 能先限定环境、用户、路径和对象，再执行写操作或发送信号。
- [ ] 能把日志统计写成可失败的断言，而不是手工描述预期值。
- [ ] 能用 PID、HTTP、日志与可选 socket 证据形成有限闭环。
- [ ] 能准确记录未验证项，不把 Git Bash 或静态语法检查冒充 Linux 实测。
- [ ] 能说明为什么生产服务应交给 service manager、监控与变更流程。

## 本轮实际验证边界

获取日期：**2026-07-14**。本轮已对完整脚本与课程 Bash 围栏做 Git Bash 静态语法检查，并在 Git Bash 运行 `--log-only` 以验证确定性日志断言；本机没有可用 WSL 发行版，因此完整 loopback、systemd、iproute2 和 tmux 行为未在 Linux 实机执行。Git Bash 结果不能替代 Linux 验收。

Obsidian Reading View 也未在本轮自动验证。

## 参考资料

- [GNU Bash Reference Manual](https://www.gnu.org/software/bash/manual/bash.html)
- [GNU grep Exit Status](https://www.gnu.org/software/grep/manual/html_node/Exit-Status.html)
- [GNU Coreutils Manual](https://www.gnu.org/software/coreutils/manual/coreutils.html)
- [Python `http.server`](https://docs.python.org/3/library/http.server.html)
- [curl command-line manual](https://curl.se/docs/manpage.html)
- [kill(2)](https://man7.org/linux/man-pages/man2/kill.2.html)
- [ss(8)](https://man7.org/linux/man-pages/man8/ss.8.html)
