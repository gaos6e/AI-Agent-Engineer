---
title: "实战：可靠 API 客户端"
tags:
  - ai-agent-engineer
  - API
  - project
aliases:
  - 可靠 API 客户端项目
source_checked: 2026-07-22
lang: zh-CN
translation_key: API/07-实战-可靠API客户端.md
translation_route: en/api/project-reliable-api-client
translation_default_route: zh-CN/API/07-实战-可靠API客户端
---

# 实战：可靠 API 客户端

## 项目目标

在 Windows 11 + PowerShell 7 上启动一个只监听 `127.0.0.1` 的教学 API，再用 Python 客户端完成：

1. cursor 分页读取 3 条数据；
2. 面对前两次 503，有限重试后成功；
3. 服务端已经创建、首次响应却失败时，用同一幂等键恢复且不重复创建；
4. 将 3xx、404、409、无效 JSON、错误 content type 和 schema 错误分类；
5. 对重复 cursor、最大页数、重试耗尽和 `Retry-After` 等边界强制停止；
6. 运行 29 个不需要互联网和真实密钥的可靠客户端 unit + loopback integration 测试，以及 6 个离线 OpenAI 参考页 Markdown 合同测试。

项目代码位于 `Knowledge/AI Agent Engineer/docs-CN/API/examples/`。它是教学实现，不是可直接上线的通用 SDK；生产客户端还要结合目标 API 契约、日志/指标、deadline、认证和 schema 工具。

## 文件与职责

```text
examples/
├── requirements.txt          # 唯一第三方依赖 Requests
├── mock_api_server.py        # 本地教学 API
├── reliable_client.py        # endpoint 方法、内部重试循环与错误分类
├── demo.py                   # 人工演示入口
├── test_reliable_client_unit.py        # 脚本化 Session 的确定性单元测试
├── test_reliable_client_integration.py # 真实 loopback HTTP 集成测试
└── test_openai_api_markdown.py          # 参考页 Python 片段与安全合同的静态测试
```

### 服务端故障场景

| Endpoint | 行为 | 要验证的能力 |
| --- | --- | --- |
| `GET /items` | 两页 cursor 数据 | 完整分页与终止 |
| `GET /looping-items`、`/endless-items` | 重复或永不结束的 cursor | 重复检测与最大页数 |
| `GET /bad-items`、`/bad-cursor` | 错误分页 schema | 格式错误分类 |
| `GET /flaky` | 前两次 503，第三次成功 | 有限重试、`Retry-After` |
| `GET /retry-later` | 503 + `Retry-After: 120` | 超预算时停止，不提前重试 |
| `GET /bad-json` | 声明 JSON 但 body 损坏 | 格式错误分类 |
| `GET /text-json`、`/no-content`、`/redirect` | media type、204、302 | 2xx/3xx 与响应解析边界 |
| `POST /jobs` | 要求 `Idempotency-Key` | 重放去重、同 key 不同 body 冲突 |
| 其他路径 | 404 problem JSON | 保留机器错误码和 request ID |

## 第一步：创建隔离环境

从 vault 根目录执行：

```powershell
python -m venv .venv  # 在 vault 根目录旁建立只属于本机的隔离环境。
.\.venv\Scripts\Activate.ps1  # 在当前 PowerShell 会话激活该环境。
python -m pip install --upgrade pip  # 更新当前环境的安装工具。
python -m pip install -r '.\Knowledge\AI Agent Engineer\docs\API\examples\requirements.txt'  # 按项目锁定的最小依赖清单安装 Requests。
```

`.venv` 只属于本机，不应加入 vault 或 Git。若你已有隔离环境，也可直接安装 requirements。

## 第二步：启动本地服务

终端 A：

```powershell
python -B '.\Knowledge\AI Agent Engineer\docs\API\examples\mock_api_server.py'  # 在终端 A 启动仅绑定 127.0.0.1 的本地教学服务。
```

应看到：

```text
教学 API 已启动：http://127.0.0.1:8765
按 Ctrl+C 停止。
```

服务只绑定本机回环地址，不需要 API key，不访问互联网。端口 8765 被占用时，可停止占用程序；若自行改端口，`demo.py` 中 base URL 也要同步修改。

## 第三步：运行演示

终端 B：

```powershell
python -B '.\Knowledge\AI Agent Engineer\docs\API\examples\demo.py'  # 在终端 B 运行分页、重试和幂等创建的人工演示。
```

检查三件事：

- 分页结果含 `item-1`、`item-2`、`item-3`；
- `/flaky` 最终显示 `attempt: 3`；
- 首次创建与同 key 重放的任务 ID 相同。

## 第四步：运行自动化测试

测试会自行在随机空闲端口启动/关闭服务，不需要先运行终端 A：

```powershell
python -B -W error::ResourceWarning -m unittest discover -s '.\Knowledge\AI Agent Engineer\docs\API\examples' -p 'test_*.py' -v  # 将 ResourceWarning 升级为错误后发现并详细运行所有本地单元与 loopback 测试。
```

通过标准：35 个测试全部 `ok`，进程退出码为 0；其中 29 个验证可靠客户端的 unit + loopback 行为，6 个只静态检查 OpenAI 参考页的代码片段和安全合同。测试结束后 server、thread 与客户端自行创建的 Session 都已关闭。

## 读懂客户端的关键决策

### 1. 每次请求都有超时

`ReliableApiClient.timeout` 是 `(connect_timeout, read_timeout)`。脚本化 Session 测试会断言这个 tuple 确实传到 transport，并模拟 `ReadTimeout` 验证有限重试；它没有声称测试了真实公网延迟。

### 2. 不是所有请求都可重试

通用 `_request_json` 是内部方法，只有 endpoint 方法能声明 `retry_authorized=True`。HTTP 语义上幂等的方法可在明确契约下进入重试；POST 还必须由 `create_job()` 这个已知支持幂等键的 endpoint 方法授权。仅给任意 POST 加一个非空 header 不会自动获得重试资格。教学服务进一步把 key 收窄为不含空格的可打印 ASCII，避免 header 编码错误；真实 API 的字符集和长度仍以其文档为准。

### 3. 临时状态码有白名单

教学实现只把 429、500、502、503、504 视为重试候选。400、401、403、404、409、422 不会因原样等待而修复，因此直接变成 `ApiHttpError`。

### 4. 服务端等待提示不能被截短

服务返回合法 `Retry-After` 且未超过 `max_retry_after` 等待预算时，客户端等待完整时长；若服务要求 120 秒而当前预算只允许 30 秒，立即返回带 `retry_after=120` 的 `ApiHttpError`，交给外层延期，绝不 30 秒后提前请求。非法 header 才回退本地指数退避与 jitter。sleep、时钟和随机函数可注入，使测试不实际等待。

### 5. JSON 需要两层校验

先检查 `Content-Type`，再解析 JSON；分页和任务方法还检查 `items`、`next_cursor`、`id` 的最小 schema。格式错误使用 `ApiResponseError`，不和 404/503 混在一起。

### 6. 分页有三个停止阀

- `next_cursor is None` 正常结束；
- 重复 cursor 视为契约错误；
- 超过 `max_pages` 强制结束。

### 7. 重定向与本机环境显式受控

教学客户端发送 `allow_redirects=False`，把 3xx 暴露给 endpoint 契约决定；自行创建的 Session 使用 `trust_env=False`，确保 loopback 测试不读取代理或 `.netrc`。调用方注入的 Session 仍归调用方所有，客户端不会关闭，也不会改写其环境策略。

## 自动化测试矩阵

| 类别 | 已实际覆盖 |
| --- | --- |
| 分页 | 正常两页、重复 cursor、最大页数、items/cursor 类型错误 |
| 传输与超时 | timeout tuple、`ReadTimeout` 有限重试、其他 `RequestException` 归一化 |
| TLS | `SSLError` 虽继承 `ConnectionError`，仍在第一次失败后停止，避免重试掩盖证书身份验证问题 |
| HTTP | 204、302 不跟随、404、409、503 恢复与耗尽 |
| `Retry-After` | 秒数、HTTP 日期、过去日期、负数、任意文本、非 ASCII 数字、超长 ASCII 数字、超等待预算 |
| 幂等 | 同 key 同 payload、同 key 不同 payload、写入后首次响应失败 |
| 表示 | `application/json`、`application/problem+json`、错误 media type、无效 JSON |
| 配置与资源 | base URL、timeout/jitter/页边界、key 的 ASCII/空格/控制字符、Session 所有权与线程退出 |
| 参考页静态合同 | OpenAI 参考页的 Python fenced code 可解析，存储、文件清理、流终态和工具循环防护不被回归删除 |

## 必做实验

### 实验 A：观察重试耗尽

把客户端 `max_attempts` 临时设为 2，再请求一个新启动服务的 `/flaky`。预期收到 `ApiHttpError(status=503)`，因为教学服务第三次才成功。实验后恢复代码，不要为了“通过”把测试期望改错。

### 实验 B：制造幂等冲突

用同一个 key 先发送 `{"value": 1}`，再发送 `{"value": 2}`。预期第二次为 409，机器错误码是 `idempotency_conflict`。这证明 key 不是“无论 body 怎样都返回旧结果”。

### 实验 C：取消分页保护

先不要改成品。在纸上说明：如果服务端永远返回 `next_cursor="page-2"`，缺少重复检测和最大页数会怎样？然后为 mock server 新增一个专门的 `/looping-items` endpoint 和测试，确认客户端能终止。

### 实验 D：确认 POST 的默认策略

阅读 `test_idempotency_header_alone_does_not_authorize_post_retry`：即使内部请求带 key，只要 endpoint 没有授权重试，503 后也只尝试一次。再与 `create_job()` 比较，解释为什么“服务端契约 + endpoint 方法授权 + 复用同一 key”三者缺一不可。

## 常见问题排查

### `ModuleNotFoundError: requests`

确认当前终端已激活正确 `.venv`，并运行：

```powershell
python -c "import sys, requests; print(sys.executable); print(requests.__version__)"  # 输出当前解释器路径与库版本，帮助确认虚拟环境是否真的已激活。
```

这里只输出解释器路径和库版本，不涉及凭据。

### `WinError 10048` 或地址已被占用

通常是 8765 已有服务。回到终端 A 按 Ctrl+C；测试使用随机端口，通常不受影响。

### 测试进程不退出

检查 `tearDown()` 是否依次调用 `shutdown()`、`server_close()` 并等待线程结束。不要通过强制终止来掩盖资源清理错误。

### 收到 HTML 而非 JSON

本项目不会正常返回 HTML。如果出现，先确认 base URL 与端口；真实环境中还要检查代理、登录页、网关和重定向。

## 项目验收清单

- [ ] 我能从空环境安装依赖并运行测试。
- [ ] 我能把 29 个可靠客户端测试与 6 个参考页静态合同分别归入测试矩阵，并任选 8 个解释其失败时意味着哪项契约回归。
- [ ] 我能修改重试次数并预测 `/flaky` 结果。
- [ ] 我能证明同 key 同 payload 不重复创建，同 key 不同 payload 返回冲突。
- [ ] 我能解释为什么 404 与无效 JSON 使用不同异常。
- [ ] 我没有创建或提交真实凭据、`.venv`、`__pycache__` 或 `.pyc`。

## 可选扩展

1. 为客户端加入结构化事件回调，记录 method、route、status、duration、attempt，不记录 body/header 全量。
2. 增加整体 deadline，使 timeout、重试和等待之和不能超过调用预算。
3. 用 dataclass 或 Pydantic 校验 `Job` schema，并为字段缺失写失败测试。
4. 新增可中断的分页检查点，模拟处理第 2 页后重启。
5. 为安全日志增加事件回调，并断言 Authorization、完整 URL 和 body 不会进入事件。

## 参考资料

- [Python `http.server`](https://docs.python.org/3/library/http.server.html)：这里只用于本地教学；官方明确不建议作为生产服务器。
- [Python `unittest`](https://docs.python.org/3/library/unittest.html)
- [Requests 官方文档](https://docs.python-requests.org/en/stable/)

获取日期：2026-07-22。完成项目后进入 [[API/08-练习自测与掌握标准|练习、自测与掌握标准]]。
