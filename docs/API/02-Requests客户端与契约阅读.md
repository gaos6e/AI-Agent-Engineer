---
title: Requests 客户端、Session 与契约阅读
tags:
  - ai-agent-engineer
  - API
  - HTTP
  - Requests
aliases:
  - Requests 客户端基础
  - API 契约阅读
source_checked: 2026-07-22
---

# Requests 客户端、Session 与契约阅读

## 本节目标

上一节已经把 HTTP 拆成请求和响应。本节把这些概念落到 Python Requests，并补上初学者最容易跳过的工程边界：隔离依赖、复用 `Session`、验证 TLS、控制重定向、阅读 OpenAPI 契约，以及用测试替身证明客户端行为。

完成后，你应能解释“为什么这样调用”，而不是只会复制一行 `requests.get()`。

## 先固定学习环境

在 Windows 11 + PowerShell 7 中，从自己的练习目录创建虚拟环境：

```powershell
python -m venv .venv  # 在自己的练习目录建立隔离依赖环境。
.\.venv\Scripts\Activate.ps1  # 激活虚拟环境，让之后的 python/pip 都指向它。
python -m pip install --upgrade pip  # 更新当前环境的安装器，而不是调用不确定的全局 pip。
python -m pip install "requests>=2.33,<3"  # 安装课程验证过的 Requests 主版本范围。
python -c "import sys, requests; print(sys.executable); print(requests.__version__)"  # 同时核对解释器位置和实际安装的 Requests 版本。
```

`venv` 把项目依赖与全机 Python 分开，`pip` 安装到当前已激活环境。本知识库的示例约束写在 `examples/requirements.txt`；不要提交 `.venv`、wheel 缓存或解释器生成的 `__pycache__`。

截至 **2026-07-22**，Requests 官方稳定文档显示 2.34.2；本轮离线项目实际运行的是 2.33.0。`requests>=2.33,<3` 表示允许兼容的 2.x 更新，不等于任何未来 2.x 都无需测试。团队项目通常还会用 lock file 或可复现构建工具记录精确解析结果。

## 从一次调用理解生命周期

最小 GET：

```python
import requests  # 导入 Requests 客户端库。

response = requests.get(  # 发送一个最小 GET；真实代码还需验证 endpoint 的 schema 和业务语义。
    "https://example.com/api/items",  # 使用 API 文档给出的资源地址。
    params={"limit": 20},  # 让库把页大小编码为 query 参数。
    headers={"Accept": "application/json"},  # 声明希望服务端返回 JSON 表示。
    timeout=(3.05, 15),  # 同时限制连接与读取等待。
)
response.raise_for_status()  # 先处理 HTTP 层失败，避免错误 body 被当作成功数据。
data = response.json()  # 解析 JSON；下一步仍应检查 data 的类型与必需字段。
```

这段代码做了五件事：

1. 把 `params` 编码进 query string；
2. 声明希望接收 JSON；
3. 设置连接与读取超时；
4. 将 4xx/5xx 转成 `HTTPError`；
5. 尝试把 body 解析成 Python 值。

它仍不完整：自动重定向、响应 media type、schema、重试和资源复用都没有明确契约。`response.json()` 成功也只证明语法可解析，不证明状态或字段正确。

## 为什么使用 Session

`requests.Session` 会在同一会话中复用连接池，并可保存公共 headers、认证和 cookies。批量分页或 Agent 连续调用同一服务时，这比每次创建全新连接更合适：

```python
from collections.abc import Iterator  # 导入迭代器类型，说明函数会逐页产出结果。

import requests  # 导入可复用连接池与 HTTP 方法的客户端库。


def iter_pages(base_url: str) -> Iterator[dict]:  # 依次请求固定页号，并逐页交还 JSON object。
    with requests.Session() as session:  # 自己创建 Session，也由 with 在结束时负责关闭连接池。
        session.headers.update(  # 把每页都需要的 header 设置为会话默认值。
            {  # 使用字典一次更新多个稳定 header。
                "Accept": "application/json",  # 明确期望 JSON 响应。
                "User-Agent": "agent-course-client/0.1",  # 让服务端日志能识别教学客户端版本。
            }
        )
        for page_number in range(1, 4):  # 示例只请求前三页；真实分页应改用服务端 cursor/next 链接。
            response = session.get(  # 复用 Session 的连接池发送当前页请求。
                f"{base_url.rstrip('/')}/items",  # 去掉尾部斜杠，避免拼出双斜杠路径。
                params={"page": page_number},  # 将当前页号作为 query 参数传给服务端。
                timeout=(3.05, 15),  # 每次请求都显式受连接和读取超时约束。
            )
            response.raise_for_status()  # 让 4xx/5xx 尽早中断，而不是继续解析错误响应。
            value = response.json()  # 把成功响应体解析为 Python 数据。
            if not isinstance(value, dict):  # 本例契约要求每页最外层是 JSON object。
                raise ValueError("预期 JSON object")  # 不让数组或字符串悄悄进入后续业务逻辑。
            yield value  # 逐页产出，调用方可边处理边拉取而无需先积累全部页面。
```

所有权必须明确：谁创建 Session，谁负责关闭。若客户端接受调用方注入的 Session，通常不应擅自关闭它。本库项目只关闭自己创建的 Session，并用测试固定这项契约。

### 环境配置会影响 Session

Requests 默认可能读取代理环境变量和 `.netrc`。这对企业网络或用户配置很有用，却会让“只访问 `127.0.0.1`”的离线测试受本机状态影响。因此本库教学客户端对**自行创建且只服务于本地项目**的 Session 设置 `trust_env=False`。

不要把这条设置机械复制到真实项目。真实服务是否需要代理、企业 CA、`.netrc` 或平台认证，应由部署环境和安全策略决定。

## TLS、代理与重定向边界

### 保持证书验证

Requests 默认验证 HTTPS 证书。不要用 `verify=False` 把证书错误“修好”；它会放弃服务器身份验证，使连接容易遭受中间人攻击。正确做法是核对主机名、系统时间、企业代理和受信任 CA 配置。

证书链或主机名校验失败也不是“短暂网络抖动”：应作为配置/安全事件停止并排查，不要把 `SSLError` 混入可重试的 `ConnectionError` 分支。综合项目为这一继承关系单独设有回归测试。

### API 客户端不应盲目跟随重定向

Requests 的通用 `request()` 默认允许重定向。浏览网页时这很方便，但 API 调用可能携带 Authorization、幂等键或敏感 body。可靠客户端可以先设置：

```python
response = session.request(  # 通过已有 Session 发送请求，继承其受控 header 与连接配置。
    "GET",  # 明确 HTTP 方法，不依赖默认推断。
    url,  # 使用已校验的目标 URL；不要把不可信用户输入直接放进这里。
    timeout=(3.05, 15),  # 限制连接与读取阶段，避免调用无限挂起。
    allow_redirects=False,  # API 客户端默认不自动跟随重定向，先检查 Location 和凭据边界。
)
```

若目标 API 文档要求跟随，再验证 `Location` 的 scheme、host、方法变化和凭据转发规则。不要只因客户端库当前会移除某些 header，就把安全性寄托在未测试的默认行为上。

### 不记录完整 URL

query 可能含签名、游标或用户数据。日志优先记录服务名和路由模板，例如 `/v1/items/{id}`，不要直接输出带 query 的最终 URL。

## 怎样读 OpenAPI，而不是从 SDK 猜契约

OpenAPI 文档常以 YAML 或 JSON 描述 HTTP API。第一次阅读按以下顺序定位：

| 位置 | 你要找什么 |
| --- | --- |
| `servers` | base URL 与环境 |
| `paths` + method | endpoint 与操作语义 |
| `parameters` | path、query、header 参数及必填性 |
| `requestBody` | 请求 media type 与 schema |
| `responses` | 成功/错误状态、headers 与响应 schema |
| `components.schemas` | 可复用对象结构 |
| `securitySchemes` + `security` | 认证方式和适用范围 |

OpenAPI 描述契约，不保证服务实现一定正确；SDK 也只是契约的一种封装。对关键客户端应保留少量契约测试，验证实际响应仍符合依赖的字段和状态。

### 最小调用卡

读完文档后，先写一张卡再写代码：

```text
文档与获取日期：
base URL / API version：
method + path：
认证与 scope：
path/query/header/body 参数：
成功状态与 schema：
错误状态与机器错误码：
分页、限流、超时、重试、幂等：
弃用或迁移说明：
```

如果某项文档没有说明，写“文档未说明”，不要根据另一家 API 猜一个默认值。

## 版本、弃用与兼容

API 可能在 URL（如 `/v1`）、header、日期或模型名中表达版本。升级前至少检查：

- endpoint、字段、状态码或默认值是否变化；
- 旧字段是立即删除，还是先标记 deprecated；
- SDK 版本和服务端 API 版本是否是两套概念；
- 是否有迁移指南、弃用日期或兼容窗口；
- 回滚时旧客户端还能否读取新响应。

对响应字段通常应“读取所需字段、容忍无害新增、拒绝关键字段缺失或类型变化”。不要把“忽略所有未知内容”误解成无需 schema 验证。

## 测试替身与本地契约测试

客户端可靠性需要两层证据：

1. **脚本化 Session**：不启动网络，精确返回 503、抛 `ReadTimeout`，并记录客户端传入的 timeout、header 和 `allow_redirects`；适合验证重试决策。
2. **loopback 集成测试**：在 `127.0.0.1` 随机端口启动本地服务，验证真实序列化、状态码、headers、分页和资源清理。

替身只能证明“客户端面对设定输入的行为”；它不能证明真实厂商服务、代理、TLS 或计费端点可用。外部调用未执行时必须如实标注。

## 常见错误

- 在全局模块导入时创建永不关闭的 Session。
- 认为 SDK 会自动选择合理 timeout、重试和重定向策略。
- 用 `verify=False` 绕过证书错误。
- 把代理、`.netrc` 和环境变量造成的行为误判成代码确定行为。
- 只读成功响应示例，不读 errors、rate limits、pagination 和 changelog。
- 把 OpenAPI schema 当成运行时验证结果，而不写失败路径测试。

## 练习与自测

1. 为本地教学 `/items` endpoint 写一张完整调用卡。
2. 用脚本化 Session 断言客户端确实传入 `(connect, read)` timeout 和 `allow_redirects=False`。
3. 比较函数级 `requests.get()` 与长生命周期 Session 的所有权和连接复用。
4. 找一份官方 OpenAPI 文档，只记录一个 endpoint 的 method、认证、参数、响应和错误，不调用真实服务。

- [ ] 我能建立 venv，并核对正在使用的解释器与 Requests 版本。
- [ ] 我能解释 Session 的连接池、配置继承和关闭责任。
- [ ] 我不会关闭 TLS 验证来掩盖配置错误。
- [ ] 我会显式决定是否跟随 API 重定向。
- [ ] 我能从 OpenAPI 还原一张调用卡，并区分“文档声明”与“实际验证”。

## 参考资料

- [Requests 2.34.2 官方文档](https://docs.python-requests.org/en/stable/)
- [Requests Advanced Usage：Session、TLS、代理与超时](https://docs.python-requests.org/en/stable/user/advanced/)
- [Requests API：`allow_redirects` 与请求参数](https://docs.python-requests.org/en/stable/api/)
- [OpenAPI Specification 3.1.1](https://spec.openapis.org/oas/v3.1.1.html)

获取日期：2026-07-22。延伸参考见 [[API/参考资料/Requests Quickstart|Requests Quickstart 中文学习笔记]]；下一步进入 [[API/03-认证状态码与凭据安全|认证、状态码与凭据安全]]。
