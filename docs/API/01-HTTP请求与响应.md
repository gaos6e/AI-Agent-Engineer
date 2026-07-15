---
title: HTTP 请求与响应
tags:
  - ai-agent-engineer
  - API
  - HTTP
aliases:
  - HTTP API 基础
---

# HTTP 请求与响应

## 本节目标

你将学会拆解一条 HTTP API 调用，理解方法、URL、headers、body、状态码和响应体分别承担什么职责，并能用 Python 发出最小请求。

## 先建立直觉：一次有格式的问答

把 API 想成服务窗口：URL 是窗口地址，HTTP 方法说明意图，headers 是信封外的说明，body 是提交的材料；响应状态码先告诉你结果类别，响应 headers 提供元信息，响应 body 承载数据或错误细节。

HTTP 是无状态的请求/响应协议。这里的“无状态”不是服务永远不保存数据，而是每个请求的语义应能独立理解；登录会话、数据库记录等状态可由应用另行管理。

```text
客户端 -- request --> 服务端
客户端 <-- response -- 服务端
```

## 请求的五个部分

假设要读取第 2 页任务：

```http
GET /v1/tasks?cursor=page-2&limit=20 HTTP/1.1
Host: api.example.com
Accept: application/json
Authorization: Bearer <token>
```

### 1. 方法（method）

| 方法 | 常见意图 | 安全方法 | RFC 语义上幂等 |
| --- | --- | --- | --- |
| `GET` | 读取资源 | 是 | 是 |
| `HEAD` | 只读取响应元信息 | 是 | 是 |
| `POST` | 创建资源或触发动作 | 否 | 否 |
| `PUT` | 用给定表示整体创建/替换资源 | 否 | 是 |
| `PATCH` | 局部修改 | 否 | 不一定 |
| `DELETE` | 删除资源 | 否 | 是 |

“安全”表示客户端没有请求改变服务端状态，不代表没有日志或计费。“幂等”表示重复相同请求的**预期效果**等同于执行一次，不保证每次响应完全相同。不要仅凭方法名推断业务实现，仍要阅读 API 文档。

### 2. URL

```text
https://api.example.com/v1/tasks?cursor=page-2&limit=20
\___/   \_____________/\_______/ \____________________/
scheme       host         path            query
```

- `scheme`：生产 API 通常应使用 `https`；
- `host`：服务所在主机；
- `path`：资源或操作路径；
- `query`：筛选、排序、游标和页大小等参数。

Python 中用 `params=` 传 query，不手工拼 `?` 和 `&`：

```python
import requests

response = requests.get(
    "https://example.com/v1/tasks",
    params={"cursor": "page-2", "limit": 20},
    timeout=(3.05, 15),
)
print(response.request.url)
```

### 3. Headers

headers 是不直接属于业务正文的元数据。字段名大小写不敏感。常见字段：

| Header | 作用 |
| --- | --- |
| `Accept: application/json` | 客户端希望收到 JSON |
| `Content-Type: application/json` | 当前发送的 body 是 JSON |
| `Authorization: Bearer ...` | 携带访问凭据 |
| `User-Agent` | 标识客户端程序与版本 |
| `Idempotency-Key` | 某些 API 用它识别重复创建请求；是否支持由 API 文档决定 |
| `Retry-After` | 服务端建议多久后再试 |
| `X-Request-ID` 或厂商等价字段 | 关联一次调用的诊断标识；名称不是统一标准 |

`Accept` 描述“想收什么”，`Content-Type` 描述“正在发什么”，二者不要混淆。

### 4. Body

GET 通常用 query 参数；创建或执行操作常用 JSON body：

```python
payload = {"title": "学习 API", "priority": 2}

response = requests.post(
    "https://example.com/v1/tasks",
    json=payload,
    timeout=(3.05, 30),
)
```

Requests 的 `json=` 会序列化 Python 对象并设置 JSON content type；`data=` 常用于表单或已编码数据。JSON 只支持有限的数据类型，`datetime`、`Path` 等对象要先转换。

### 5. API 契约（contract）

契约是调用方和服务方共同遵守的约定：路径、参数类型、必填字段、认证、响应 schema、错误格式、限流和版本策略。能发出 HTTP 请求不等于符合契约。例如服务端可能要求 `limit` 在 1～100 之间，或要求 `model` 只能取项目可访问的值。

## 响应的三个部分

```http
HTTP/1.1 200 OK
Content-Type: application/json
X-Request-ID: req_123

{"items": [{"id": "t1", "title": "学习 API"}], "next_cursor": null}
```

### 状态码

先看百位分类，再看具体语义：

- `1xx`：临时信息；
- `2xx`：请求已按相应语义成功处理；
- `3xx`：重定向或缓存相关；
- `4xx`：客户端请求、认证、权限或业务条件不满足；
- `5xx`：服务端未能完成有效请求。

状态码是程序分支的重要依据，但不足以表达全部业务细节；错误 body 可能包含机器可读错误码、字段位置和 request ID。

### Headers 与 body

```python
content_type = response.headers.get("Content-Type", "")
request_id = response.headers.get("X-Request-ID")

response.raise_for_status()
if "application/json" not in content_type.lower():
    raise ValueError("预期 JSON，实际收到其他内容")
data = response.json()
```

`response.json()` 成功只证明 body 能解析成 JSON，不证明 HTTP 或业务成功；因此应先按状态码处理，再校验 schema。反过来，有些 204 响应没有 body，不能无条件调用 `.json()`。

## 从文档还原一次调用

阅读任何 API 文档时按此清单记录：

1. base URL 与版本；
2. method 与 path；
3. 认证方式及 scope；
4. path/query/header/body 参数，哪些必填；
5. 成功状态码与响应 schema；
6. 错误状态码与错误 body；
7. 超时、分页、限流、重试和幂等约定；
8. 是否有 SDK，SDK 是否隐藏了上述细节。

## 常见错误

- 把 token 写进 URL：URL 可能进入浏览器历史、代理日志和监控系统；优先按文档放入 `Authorization` header。
- 不设置超时：Requests 默认不会自动为你设置合理的请求超时。
- 只判断 `status_code == 200`：创建可能返回 201，无正文成功可能返回 204。
- 对所有响应立即 `.json()`：网关错误可能返回 HTML，204 可能为空。
- 手工拼 query：空格、中文、`&` 等需要编码，交给客户端库处理。
- 根据 URL 中的动词猜语义：以 API 文档和 HTTP 方法为准。

## 练习

1. 将一个请求拆成 method、scheme、host、path、query、headers、body。
2. 解释 `Accept` 与 `Content-Type` 的区别。
3. 说明为什么 `DELETE` 的幂等性不等于“每次都返回相同状态码”。
4. 用 Requests 构造一个 `PreparedRequest` 并打印 URL 和 headers，但不要真的发送：

```python
from requests import Request, Session

request = Request("GET", "https://example.com/items", params={"q": "AI Agent"})
prepared = Session().prepare_request(request)
print(prepared.url)
```

## 自测

- [ ] 我能指出请求和响应各部分的职责。
- [ ] 我能解释安全方法与幂等方法的区别。
- [ ] 我知道 JSON 可解析不等于调用成功。
- [ ] 我能从一页 API 文档写出调用清单。

## 参考资料

- [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html)，尤其是消息、方法和状态码章节。
- [Requests Quickstart](https://docs.python-requests.org/en/stable/user/quickstart/)。

获取日期：2026-07-14。下一步：[[API/02-Requests客户端与契约阅读|Requests 客户端、Session 与契约阅读]]。
