"""用于学习的可靠 HTTP API 客户端。

模块只依赖 Requests，默认不访问固定外部服务。公开方法绑定教学服务的
具体 endpoint；通用请求循环保持为内部实现，避免调用方仅凭一个 header
就误以为任意 POST 已具备幂等语义。
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from math import isfinite
import random
import time
from typing import Any, Protocol
from urllib.parse import urlsplit

import requests


class HttpSession(Protocol):
    """ReliableApiClient 实际需要的最小 Session 接口。"""

    def request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        ...

    def close(self) -> None:
        ...


class ApiClientError(Exception):
    """客户端可识别错误的基类。"""


class ApiTransportError(ApiClientError):
    """没有取得可用 HTTP 响应。"""

    def __init__(self, message: str, *, attempts: int) -> None:
        super().__init__(message)
        self.attempts = attempts


class ApiHttpError(ApiClientError):
    """服务端返回非成功 HTTP 状态码。"""

    def __init__(
        self,
        status: int,
        *,
        code: str | None = None,
        detail: str | None = None,
        request_id: str | None = None,
        attempts: int = 1,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(
            f"HTTP {status}, code={code!r}, request_id={request_id!r}, attempts={attempts}"
        )
        self.status = status
        self.code = code
        self.detail = detail
        self.request_id = request_id
        self.attempts = attempts
        self.retry_after = retry_after


class ApiResponseError(ApiClientError):
    """响应格式或 schema 不符合客户端预期。"""


def _finite_number(
    value: object,
    field: str,
    *,
    allow_zero: bool,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} 必须是有限数值")
    normalized = float(value)
    if not isfinite(normalized):
        raise ValueError(f"{field} 必须是有限数值")
    if normalized < 0 or (normalized == 0 and not allow_zero):
        relation = "非负数" if allow_zero else "正数"
        raise ValueError(f"{field} 必须是{relation}")
    return normalized


class ReliableApiClient:
    """带显式超时、有限重试和基础响应校验的教学客户端。"""

    IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "PUT", "DELETE"})
    RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})

    def __init__(
        self,
        base_url: str,
        *,
        max_attempts: int = 3,
        connect_timeout: float = 2.0,
        read_timeout: float = 5.0,
        backoff_base: float = 0.2,
        backoff_cap: float = 2.0,
        max_retry_after: float = 30.0,
        jitter_ratio: float = 0.1,
        sleep: Callable[[float], None] = time.sleep,
        random_between: Callable[[float, float], float] = random.uniform,
        session: HttpSession | None = None,
    ) -> None:
        if type(base_url) is not str or not base_url or base_url != base_url.strip():
            raise ValueError("base_url 必须是无首尾空白的非空字符串")
        parsed = urlsplit(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("base_url 必须是完整的 http:// 或 https:// URL")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("base_url 不得内嵌凭据")
        if parsed.query or parsed.fragment:
            raise ValueError("base_url 不得包含 query 或 fragment")
        try:
            parsed.port
        except ValueError as exc:
            raise ValueError("base_url 端口格式无效") from exc

        if type(max_attempts) is not int or max_attempts < 1:
            raise ValueError("max_attempts 必须是至少为 1 的整数")
        connect_timeout = _finite_number(
            connect_timeout,
            "connect_timeout",
            allow_zero=False,
        )
        read_timeout = _finite_number(read_timeout, "read_timeout", allow_zero=False)
        backoff_base = _finite_number(backoff_base, "backoff_base", allow_zero=True)
        backoff_cap = _finite_number(backoff_cap, "backoff_cap", allow_zero=True)
        max_retry_after = _finite_number(
            max_retry_after,
            "max_retry_after",
            allow_zero=True,
        )
        jitter_ratio = _finite_number(jitter_ratio, "jitter_ratio", allow_zero=True)
        if jitter_ratio > 1:
            raise ValueError("jitter_ratio 必须在 0 到 1 之间")

        self.base_url = base_url.rstrip("/")
        self.max_attempts = max_attempts
        self.timeout = (connect_timeout, read_timeout)
        self.backoff_base = backoff_base
        self.backoff_cap = backoff_cap
        self.max_retry_after = max_retry_after
        self.jitter_ratio = jitter_ratio
        self._sleep = sleep
        self._random_between = random_between

        if session is None:
            owned_session = requests.Session()
            # 教学项目只访问 loopback；忽略代理和 .netrc，避免本机环境改变测试。
            owned_session.trust_env = False
            self.session: HttpSession = owned_session
            self._owns_session = True
        else:
            self.session = session
            self._owns_session = False

    def close(self) -> None:
        """只关闭本客户端自行创建的 Session。"""

        if self._owns_session:
            self.session.close()

    def __enter__(self) -> ReliableApiClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def get_flaky_status(self) -> dict[str, Any]:
        """调用教学 GET endpoint，展示临时 503 的安全恢复。"""

        result = self._request_json("GET", "/flaky", retry_authorized=True)
        if not isinstance(result, dict):
            raise ApiResponseError("flaky 响应必须是 JSON object")
        return result

    def iter_items(
        self,
        *,
        page_size: int = 2,
        max_pages: int = 100,
        endpoint: str = "/items",
    ) -> Iterator[dict[str, Any]]:
        """遍历教学服务的 cursor 分页，并阻止无限循环。"""

        if type(page_size) is not int or page_size < 1:
            raise ValueError("page_size 必须是至少为 1 的整数")
        if type(max_pages) is not int or max_pages < 1:
            raise ValueError("max_pages 必须是至少为 1 的整数")
        if type(endpoint) is not str or not endpoint.startswith("/"):
            raise ValueError("endpoint 必须是以 / 开头的字符串")

        cursor: str | None = None
        seen_cursors: set[str] = set()
        for _ in range(max_pages):
            params: dict[str, str | int] = {"limit": page_size}
            if cursor is not None:
                params["cursor"] = cursor

            page = self._request_json(
                "GET",
                endpoint,
                params=params,
                retry_authorized=True,
            )
            if not isinstance(page, dict) or not isinstance(page.get("items"), list):
                raise ApiResponseError("分页响应缺少 items 数组")

            for item in page["items"]:
                if not isinstance(item, dict):
                    raise ApiResponseError("items 中出现非 object 元素")
                yield item

            next_cursor = page.get("next_cursor")
            if next_cursor is None:
                return
            if type(next_cursor) is not str or not next_cursor:
                raise ApiResponseError("next_cursor 格式错误")
            if next_cursor in seen_cursors:
                raise ApiResponseError("检测到重复 next_cursor")
            seen_cursors.add(next_cursor)
            cursor = next_cursor

        raise ApiResponseError(f"分页超过最大页数 {max_pages}")

    def create_job(
        self,
        payload: Mapping[str, Any],
        *,
        idempotency_key: str,
    ) -> dict[str, Any]:
        """调用明确支持幂等键的教学 endpoint。"""

        if not isinstance(payload, Mapping):
            raise ValueError("payload 必须是映射对象")
        self._validate_idempotency_key(idempotency_key)
        result = self._request_json(
            "POST",
            "/jobs",
            json_body=payload,
            idempotency_key=idempotency_key,
            retry_authorized=True,
        )
        if not isinstance(result, dict) or type(result.get("id")) is not str:
            raise ApiResponseError("任务响应缺少字符串 id")
        return result

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, str | int] | None = None,
        json_body: Mapping[str, Any] | None = None,
        idempotency_key: str | None = None,
        retry_authorized: bool = False,
    ) -> Any:
        """内部 JSON 请求循环；endpoint 方法负责授权是否可重试。"""

        if type(method) is not str or not method or method != method.strip():
            raise ValueError("method 必须是无首尾空白的非空字符串")
        if type(path) is not str or not path.startswith("/"):
            raise ValueError("path 必须是以 / 开头的字符串")
        if type(retry_authorized) is not bool:
            raise ValueError("retry_authorized 必须是 bool")
        if idempotency_key is not None:
            self._validate_idempotency_key(idempotency_key)

        normalized_method = method.upper()
        has_retry_contract = normalized_method in self.IDEMPOTENT_METHODS or (
            normalized_method == "POST" and idempotency_key is not None
        )
        if retry_authorized and not has_retry_contract:
            raise ValueError("当前方法没有可证明的重试契约")

        headers = {
            "Accept": "application/json",
            "User-Agent": "api-learning-client/0.2",
        }
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key

        url = f"{self.base_url}{path}"
        for attempt in range(1, self.max_attempts + 1):
            try:
                response = self.session.request(
                    normalized_method,
                    url,
                    params=params,
                    json=json_body,
                    headers=headers,
                    timeout=self.timeout,
                    allow_redirects=False,
                )
            except (
                requests.exceptions.InvalidJSONError,
                requests.exceptions.InvalidURL,
            ) as exc:
                raise ValueError("请求构造失败") from exc
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
            ) as exc:
                if not retry_authorized or attempt >= self.max_attempts:
                    raise ApiTransportError(
                        f"{normalized_method} 请求未取得响应",
                        attempts=attempt,
                    ) from exc
                self._sleep(self._backoff_delay(attempt))
                continue
            except requests.exceptions.RequestException as exc:
                raise ApiTransportError(
                    f"{normalized_method} 请求失败且不自动重试",
                    attempts=attempt,
                ) from exc

            retry_after = self._parse_retry_after(response.headers.get("Retry-After"))
            if (
                response.status_code in self.RETRYABLE_STATUSES
                and retry_authorized
                and attempt < self.max_attempts
            ):
                if retry_after is not None and retry_after > self.max_retry_after:
                    error = self._http_error(
                        response,
                        attempts=attempt,
                        retry_after=retry_after,
                    )
                    response.close()
                    raise error
                delay = (
                    retry_after
                    if retry_after is not None
                    else self._backoff_delay(attempt)
                )
                response.close()
                self._sleep(delay)
                continue

            if not 200 <= response.status_code < 300:
                error = self._http_error(
                    response,
                    attempts=attempt,
                    retry_after=retry_after,
                )
                response.close()
                raise error
            if response.status_code in {204, 205} or normalized_method == "HEAD":
                response.close()
                return None
            try:
                return self._parse_json(response)
            finally:
                response.close()

        raise RuntimeError("重试循环不应到达此处")

    def _backoff_delay(self, attempt: int) -> float:
        upper = min(self.backoff_cap, self.backoff_base * (2 ** (attempt - 1)))
        if self.jitter_ratio == 0 or upper == 0:
            return upper
        lower = upper * (1 - self.jitter_ratio)
        return self._random_between(lower, upper)

    @staticmethod
    def _parse_retry_after(
        raw_value: str | None,
        *,
        now: datetime | None = None,
    ) -> float | None:
        if raw_value is None:
            return None
        stripped = raw_value.strip()
        if stripped.isascii() and stripped.isdecimal():
            try:
                return float(int(stripped))
            except (OverflowError, ValueError):
                return float("inf")
        try:
            retry_at = parsedate_to_datetime(stripped)
        except (TypeError, ValueError, OverflowError):
            return None
        if retry_at.tzinfo is None:
            return None
        reference = now or datetime.now(timezone.utc)
        if reference.tzinfo is None:
            raise ValueError("now 必须包含时区")
        return max(
            0.0,
            (
                retry_at.astimezone(timezone.utc)
                - reference.astimezone(timezone.utc)
            ).total_seconds(),
        )

    @staticmethod
    def _validate_idempotency_key(value: object) -> None:
        if type(value) is not str or not value or value != value.strip():
            raise ValueError("idempotency_key 必须是无首尾空白的非空字符串")
        if any(not 33 <= ord(character) <= 126 for character in value):
            raise ValueError("idempotency_key 只允许不含空格的可打印 ASCII 字符")

    @staticmethod
    def _parse_json(response: requests.Response) -> Any:
        content_type = (
            response.headers.get("Content-Type", "")
            .split(";", 1)[0]
            .strip()
            .lower()
        )
        if content_type != "application/json" and not content_type.endswith("+json"):
            raise ApiResponseError(f"预期 JSON，实际 Content-Type={content_type!r}")
        try:
            return response.json()
        except requests.exceptions.JSONDecodeError as exc:
            raise ApiResponseError("响应声明为 JSON，但内容无法解析") from exc

    @classmethod
    def _http_error(
        cls,
        response: requests.Response,
        *,
        attempts: int,
        retry_after: float | None,
    ) -> ApiHttpError:
        code: str | None = None
        detail: str | None = None
        try:
            payload = response.json()
        except requests.exceptions.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            raw_code = payload.get("code") or payload.get("type")
            raw_detail = payload.get("detail") or payload.get("message")
            code = raw_code if isinstance(raw_code, str) else None
            detail = raw_detail if isinstance(raw_detail, str) else None
        return ApiHttpError(
            response.status_code,
            code=code,
            detail=detail,
            request_id=response.headers.get("X-Request-ID"),
            attempts=attempts,
            retry_after=retry_after,
        )
