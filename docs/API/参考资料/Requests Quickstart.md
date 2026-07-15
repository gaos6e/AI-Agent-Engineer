---
title: Requests Quickstart 中文学习笔记
source: https://docs.python-requests.org/en/stable/user/quickstart/
source_title: Quickstart - Requests 2.34.2 documentation
created: 2026-05-18
tags:
  - API
  - HTTP
  - Python
  - Requests
aliases:
  - Requests 快速入门
  - Python requests
---

# Requests Quickstart 中文学习笔记

> [!source] 来源
>
> 本笔记基于 [Requests 官方 Quickstart](https://docs.python-requests.org/en/stable/user/quickstart/) 整理，目标是把官方快速入门改写成适合 Obsidian 复习的中文学习笔记。代码中的库名、参数名、HTTP 方法和异常类型保留英文。

## 先建立调用模型

用 `requests` 调 API 时，可以先把一次调用拆成两部分：

- 请求：你要访问哪个 `url`，用什么 HTTP 方法，是否带 `params`、`headers`、`data`、`json`、`files`、`cookies`、`timeout`。
- 响应：服务端返回一个 `Response` 对象，常用字段是 `status_code`、`headers`、`text`、`content`、`json()`、`cookies`、`history`。

最小调用通常是这样：

```python
import requests

response = requests.get("https://api.github.com/events", timeout=10)
print(response.status_code)
print(response.text[:200])
```

## 安装和更新

如果本机还没有安装：

```powershell
python -m pip install requests
```

如果需要更新到较新版本：

```powershell
python -m pip install --upgrade requests
```

## 发起请求

`requests` 为常见 HTTP 方法都提供了直接函数：

| 方法 | 常见用途 | Requests 写法 |
| --- | --- | --- |
| `GET` | 获取资源、查询数据 | `requests.get(url)` |
| `POST` | 提交表单、创建资源、调用推理接口 | `requests.post(url, data=...)` 或 `requests.post(url, json=...)` |
| `PUT` | 整体更新资源 | `requests.put(url, data=...)` |
| `DELETE` | 删除资源 | `requests.delete(url)` |
| `HEAD` | 只取响应头，不取响应体 | `requests.head(url)` |
| `OPTIONS` | 查询服务端支持的通信选项 | `requests.options(url)` |

示例：

```python
import requests

get_response = requests.get("https://httpbin.org/get", timeout=10)
post_response = requests.post(
    "https://httpbin.org/post",
    data={"key": "value"},
    timeout=10,
)

print(get_response.status_code)
print(post_response.status_code)
```

## URL 查询参数

查询参数应该优先用 `params=` 传入，不要手工拼接 URL。这样 `requests` 会负责 URL 编码。

```python
import requests

payload = {
    "key1": "value1",
    "key2": "value2",
}

response = requests.get(
    "https://httpbin.org/get",
    params=payload,
    timeout=10,
)

print(response.url)
```

需要注意：

- 字典中值为 `None` 的键不会被加入 query string。
- 一个参数需要多个值时，可以传列表，例如 `{"tag": ["python", "api"]}`。

```python
payload = {
    "tag": ["python", "api"],
}

response = requests.get("https://httpbin.org/get", params=payload, timeout=10)
print(response.url)
```

## 读取响应内容

`Response` 对象提供了几种不同层级的读取方式：

| 属性或方法 | 返回内容 | 适用场景 |
| --- | --- | --- |
| `response.text` | 解码后的字符串 | HTML、纯文本、JSON 原文查看 |
| `response.content` | 原始字节内容 | 图片、文件、二进制响应 |
| `response.json()` | 解析后的 Python 对象 | 服务端返回 JSON |
| `response.raw` | 原始 socket 流 | 少数需要底层流的场景 |

### 文本内容

```python
import requests

response = requests.get("https://api.github.com/events", timeout=10)
print(response.encoding)
print(response.text[:200])
```

`requests` 会根据 HTTP headers 猜测文本编码。必要时可以手动设置：

```python
response.encoding = "utf-8"
print(response.text)
```

### 二进制内容

处理图片或文件时，用 `content` 读取字节：

```python
import requests

response = requests.get("https://httpbin.org/image/png", timeout=10)
response.raise_for_status()

with open("image.png", "wb") as file_handle:
    file_handle.write(response.content)
```

### JSON 内容

如果响应体是 JSON，可以用 `json()`：

```python
import requests

response = requests.get("https://api.github.com/events", timeout=10)
response.raise_for_status()

data = response.json()
print(type(data))
```

要分清两件事：

- `response.json()` 只表示“响应体能否解析成 JSON”，不代表请求成功。
- 请求是否成功应该检查 `status_code`，或者调用 `raise_for_status()`。

如果响应为空、不是合法 JSON，`response.json()` 会抛出 `requests.exceptions.JSONDecodeError`。

## 流式下载

下载较大文件时，不建议一次性把内容全部读进内存。官方推荐用 `stream=True` 配合 `iter_content()` 分块写入：

```python
import requests

url = "https://example.com/file.bin"

with requests.get(url, stream=True, timeout=30) as response:
    response.raise_for_status()
    with open("file.bin", "wb") as file_handle:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                file_handle.write(chunk)
```

`iter_content()` 会处理常见的压缩传输编码。只有确实需要未经处理的底层字节流时，才考虑直接用 `response.raw`。

## 自定义请求头

请求头用 `headers=` 传入字典：

```python
import requests

headers = {
    "User-Agent": "my-api-client/0.1",
    "Accept": "application/json",
}

response = requests.get(
    "https://api.github.com/events",
    headers=headers,
    timeout=10,
)
```

常见用途：

- `User-Agent`：告诉服务端调用方身份。
- `Accept`：声明希望接收的响应类型。
- `Authorization`：传递 token 或其他认证信息。
- `Content-Type`：声明请求体格式。

注意：

- `Authorization` 如果直接放在 `headers=` 中，可能被 `.netrc`、`auth=` 或跨主机重定向规则影响。
- `Content-Length` 通常不需要手动写，`requests` 会根据请求体自动处理。

## POST 表单和 JSON

### 表单数据：`data=`

`data=` 适合提交传统表单，会被编码成 form 格式：

```python
import requests

payload = {
    "username": "alice",
    "action": "login",
}

response = requests.post(
    "https://httpbin.org/post",
    data=payload,
    timeout=10,
)

print(response.json()["form"])
```

同一个 key 需要多个值时，可以用列表：

```python
payload = {
    "tag": ["python", "api"],
}

response = requests.post("https://httpbin.org/post", data=payload, timeout=10)
print(response.json()["form"])
```

### JSON 数据：`json=`

调用现代 API，尤其是 LLM API、后端服务、推理服务时，更常见的是提交 JSON。此时优先用 `json=`，它会自动序列化并设置合适的 JSON 请求头。

```python
import requests

payload = {
    "prompt": "用一句话解释 HTTP API",
    "max_tokens": 64,
}

response = requests.post(
    "https://httpbin.org/post",
    json=payload,
    timeout=10,
)

response.raise_for_status()
print(response.json()["json"])
```

不要把 `data=` 和 `json=` 混用。官方文档说明：如果同时传了 `data` 或 `files`，`json` 参数会被忽略。

## 上传文件

文件上传用 `files=`。文件要用二进制模式打开，避免 `Content-Length` 等计算出错。

```python
import requests

url = "https://httpbin.org/post"

with open("report.xlsx", "rb") as file_handle:
    files = {
        "file": file_handle,
    }
    response = requests.post(url, files=files, timeout=30)

response.raise_for_status()
print(response.json()["files"])
```

如果要显式指定文件名、MIME 类型或额外 header，可以传元组：

```python
with open("report.xlsx", "rb") as file_handle:
    files = {
        "file": (
            "report.xlsx",
            file_handle,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            {"Expires": "0"},
        ),
    }
    response = requests.post("https://httpbin.org/post", files=files, timeout=30)
```

如果要上传非常大的 multipart 文件，官方 Quickstart 提到可以进一步看 `requests-toolbelt`，因为 `requests` 本身默认不负责 multipart 请求体的流式上传。

## 状态码和错误处理

响应状态码在 `status_code`：

```python
import requests

response = requests.get("https://httpbin.org/get", timeout=10)
print(response.status_code)
print(response.status_code == requests.codes.ok)
```

生产代码里更推荐调用 `raise_for_status()`，让 4xx、5xx 变成异常：

```python
import requests

response = requests.get("https://httpbin.org/status/404", timeout=10)
response.raise_for_status()
```

常用模式：

```python
import requests

try:
    response = requests.get("https://httpbin.org/get", timeout=10)
    response.raise_for_status()
except requests.exceptions.Timeout:
    print("请求超时")
except requests.exceptions.HTTPError as exc:
    print(f"HTTP 状态码错误: {exc}")
except requests.exceptions.RequestException as exc:
    print(f"请求失败: {exc}")
else:
    data = response.json()
    print(data)
```

## 响应头

响应头在 `response.headers`，用起来像字典：

```python
import requests

response = requests.get("https://httpbin.org/get", timeout=10)

print(response.headers["Content-Type"])
print(response.headers.get("content-type"))
```

HTTP header 名称大小写不敏感，所以 `Content-Type` 和 `content-type` 都能访问到同一类信息。

## Cookies

读取服务端返回的 cookie：

```python
import requests

response = requests.get("https://httpbin.org/cookies/set/session/abc", timeout=10)
print(response.cookies)
```

主动发送 cookie：

```python
import requests

cookies = {
    "session": "abc",
}

response = requests.get(
    "https://httpbin.org/cookies",
    cookies=cookies,
    timeout=10,
)

print(response.json())
```

复杂场景可以使用 `RequestsCookieJar`，它比普通字典更适合跨域名、路径维护 cookie。

## 重定向和历史记录

`requests` 默认会为大多数请求自动跟随重定向，但 `HEAD` 默认不跟随。

```python
import requests

response = requests.get("http://github.com/", timeout=10)
print(response.url)
print(response.history)
```

如果不想自动跟随：

```python
response = requests.get(
    "http://github.com/",
    allow_redirects=False,
    timeout=10,
)

print(response.status_code)
print(response.history)
```

`response.history` 是一个 `Response` 列表，按从旧到新的顺序记录中间重定向响应。

## Timeout

几乎所有生产代码都应该显式设置 `timeout`。如果不设置，`requests` 默认不会超时，程序可能一直卡住。

```python
import requests

response = requests.get("https://github.com/", timeout=10)
```

重要细节：

- `timeout` 不是“整个下载最多花多少秒”。
- 它表示底层 socket 在指定时间内没有收到数据，就抛出超时异常。
- 如果要控制完整任务耗时，需要在更外层加整体超时或任务取消机制。

也可以把连接超时和读取超时分开：

```python
response = requests.get(
    "https://github.com/",
    timeout=(3.05, 10),
)
```

其中第一个值通常表示连接超时，第二个值表示读取超时。

## 常见异常

官方 Quickstart 中列出的核心异常可以这样理解：

| 异常 | 常见原因 |
| --- | --- |
| `requests.exceptions.ConnectionError` | DNS 失败、连接被拒绝、网络不可达 |
| `requests.exceptions.HTTPError` | 调用 `raise_for_status()` 后遇到 4xx 或 5xx |
| `requests.exceptions.Timeout` | 请求超时 |
| `requests.exceptions.TooManyRedirects` | 重定向次数过多 |
| `requests.exceptions.RequestException` | Requests 显式抛出的异常基类 |

建议先捕获具体异常，最后再用 `RequestException` 兜底。

## 学 API 调用时要重点练的东西

1. 用 `GET + params` 调一个公开 API，并打印最终 `response.url`。
2. 用 `POST + json` 发送一个字典，确认服务端收到的 JSON。
3. 对每个请求都加 `timeout`。
4. 在读取业务数据前先调用 `raise_for_status()`。
5. 练习区分 `response.text`、`response.content`、`response.json()`。
6. 模拟 404、超时、JSON 解析失败，写出对应的异常处理。

## 最常用模板

```python
import requests


def fetch_json(url: str, params: dict | None = None) -> dict | list:
    response = requests.get(
        url,
        params=params,
        headers={"Accept": "application/json"},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


data = fetch_json(
    "https://httpbin.org/get",
    params={"topic": "api"},
)

print(data)
```

## 后续阅读

- [Requests Quickstart](https://docs.python-requests.org/en/stable/user/quickstart/)
- [Requests Advanced Usage](https://docs.python-requests.org/en/stable/user/advanced/)
- [Requests API Reference](https://docs.python-requests.org/en/stable/api/)

