"""Deterministic realtime-session event simulator.

The simulator models contracts and recovery boundaries only.  It does not
capture audio, open sockets, call a model, or execute a real external tool.
"""

from __future__ import annotations  # 延迟类型注解求值，保持教学代码在现代 Python 中可读

import argparse  # 解析 fixture 与 --pretty 命令行选项
import hashlib  # 为 event ID 去重保存内容摘要
import json  # 严格读取事件 fixture，并输出会话摘要 JSON
import re  # 限制工具名称可接受的字符范围
from pathlib import Path  # 表示离线 fixture 路径
from typing import Any, Mapping  # 描述 JSON 值与经校验的只读映射


class SessionContractError(ValueError):  # 事件、时序或恢复合同不成立时的受控错误类型
    """Raised when an event violates the realtime-session contract."""  # CLI 会把它转换为用户可修复提示


_EVENT_KEYS = {"event_id", "type", "at_ms", "payload"}  # 每条事件都必须携带的最小信封字段
_EVENT_TYPES = {
    "audio.frame",  # 一帧用户输入音频的元数据
    "turn.commit",  # 用户轮次已提交，可开始生成响应
    "response.started",  # assistant 某条响应开始
    "response.audio",  # assistant 输出音频 chunk
    "user.interrupt",  # 用户打断当前响应
    "tool.call",  # assistant 请求受控工具调用
    "tool.result",  # 工具 adapter 返回结果
    "response.completed",  # assistant 响应正常结束
    "transport.disconnected",  # 传输链路断开
    "transport.resumed",  # 使用恢复 token/状态重新连接
    "session.timeout",  # 会话超时终止
    "session.completed",  # 会话整体完成终止
}  # 结束该离线模拟器支持的事件类型集合
_TOOL_NAME = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")  # 防止工具名携带空白、控制字符或无界长度
# These are deliberately conservative simulator contracts, not codec, provider,
# or product limits.  A production adapter may apply flow control or an explicit
# quality downgrade before it reaches the same safety boundary.
_MAX_MEDIA_CHUNK_MS = 200  # 单帧最大时长；是教学资源预算而非真实编解码器限制
_MAX_PLAYBACK_QUEUE_MS = 1_000  # 播放队列最大积压；超过后需要背压/降级而非无限排队


def _is_int(value: object) -> bool:  # 判断 JSON 语义上的整数，额外排除 Python 的 bool 子类
    return isinstance(value, int) and not isinstance(value, bool)  # True/False 不能伪装成 1/0 时间或序号


def _require_text(value: object, field: str) -> str:  # 检查标识符、理由等字段为非空文本
    if not isinstance(value, str) or not value.strip():  # 拒绝 None、非文本与纯空白内容
        raise SessionContractError(f"{field} must be a non-empty string")  # 保留字段路径，方便定位 fixture 问题
    return value  # 返回已通过类型/非空检查的原始文本


def _require_int(value: object, field: str, minimum: int = 0) -> int:  # 检查时间、序号等字段的下界与整数语义
    if not _is_int(value) or value < minimum:  # 不接受浮点、bool 与小于最小值的数字
        raise SessionContractError(f"{field} must be an integer >= {minimum}")  # 给出字段及要求的边界
    return value  # 返回可安全比较和累加的整数


def _require_bool(value: object, field: str) -> bool:  # 检查 speech 等字段必须为真正布尔值
    if not isinstance(value, bool):  # 字符串 "true" 或整数 1 都会被拒绝
        raise SessionContractError(f"{field} must be a boolean")  # 保持跨语言 JSON 合同一致
    return value  # 返回经验证布尔值


def _exact_keys(value: object, expected: set[str], field: str) -> Mapping[str, Any]:  # 对事件/载荷使用封闭 schema，而非忽略未知字段
    if not isinstance(value, dict):  # 根类型不是对象时无法读取命名字段
        raise SessionContractError(f"{field} must be an object")  # 立即失败关闭
    actual = set(value)  # 取得实际所有键名，便于比较缺失和多余项
    if actual != expected:  # 缺字段或夹带未知字段都会导致解释歧义
        missing = sorted(expected - actual)  # 计算并排序缺失字段，便于人读输出
        extra = sorted(actual - expected)  # 计算并排序未知字段，防止静默扩展合同
        raise SessionContractError(  # 用一个稳定错误同时报告两种差异
            f"{field} keys mismatch; missing={missing}, extra={extra}"  # 不继续尝试“尽量解析”
        )  # 结束异常构造
    return value  # 只有精确键集合匹配时才把映射交给后续处理


def _reject_json_constant(value: str) -> None:
    """Reject JSON extensions whose meaning is not portable or finite."""
    raise SessionContractError(f"non-standard JSON constant is forbidden: {value}")


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Build an object only when every JSON member name is unique."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SessionContractError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _strict_json_loads(text: str, source: str) -> Any:
    """Parse a fixture without silently accepting duplicate keys or NaN values."""
    try:
        return json.loads(
            text,
            parse_constant=_reject_json_constant,
            object_pairs_hook=_reject_duplicate_json_keys,
        )
    except SessionContractError:
        raise
    except json.JSONDecodeError as exc:
        raise SessionContractError(f"cannot load {source}: {exc.msg}") from exc


def _event_digest(event: Mapping[str, Any]) -> str:  # 为“同 event_id 是否同内容”计算稳定、不可逆摘要
    try:  # 先把 event 规范化为唯一 JSON 字节序列
        encoded = json.dumps(  # JSON 序列化不会执行任何事件内容
            event,  # 传入已验证的事件映射
            ensure_ascii=False,  # 直接保留 Unicode，避免不同转义风格影响可读性
            sort_keys=True,  # 固定对象键顺序，保证同内容摘要相同
            separators=(",", ":"),  # 固定空白，避免格式差异影响摘要
            allow_nan=False,  # 禁止非标准数，保持跨实现一致
        ).encode("utf-8")  # 用 UTF-8 得到可哈希字节
    except (TypeError, ValueError) as exc:  # 不可 JSON 化的对象不能进入去重状态
        raise SessionContractError("event must contain JSON-compatible values") from exc  # 转为受控合同错误
    return hashlib.sha256(encoded).hexdigest()  # 返回十六进制 SHA-256 内容摘要


def validate_event(raw_event: object) -> dict[str, Any]:  # 将不可信输入事件转换为可安全交给状态机的严格对象
    """Return a validated event without accepting implicit coercions."""  # 不做字符串转数字、缺字段补默认等宽松处理

    event = dict(_exact_keys(raw_event, _EVENT_KEYS, "event"))  # 复制通过封闭 schema 检查的事件信封
    _require_text(event["event_id"], "event.event_id")  # event ID 既用于去重也用于审计，不能为空
    event_type = _require_text(event["type"], "event.type")  # 读取并校验事件类型文本
    if event_type not in _EVENT_TYPES:  # 仅允许该离线状态机明确实现的事件
        raise SessionContractError(f"unsupported event type: {event_type}")  # 未知事件不能被忽略后继续执行
    _require_int(event["at_ms"], "event.at_ms")  # 时间戳必须是非负整数毫秒
    payload = event["payload"]  # 之后按 event type 对载荷应用精确 schema

    if event_type == "audio.frame":
        data = _exact_keys(
            payload, {"turn_id", "sequence", "duration_ms", "speech"}, "payload"
        )
        _require_text(data["turn_id"], "payload.turn_id")
        _require_int(data["sequence"], "payload.sequence")
        duration = _require_int(data["duration_ms"], "payload.duration_ms", 1)
        if duration > _MAX_MEDIA_CHUNK_MS:
            raise SessionContractError(
                f"payload.duration_ms must be <= {_MAX_MEDIA_CHUNK_MS}"
            )
        _require_bool(data["speech"], "payload.speech")
    elif event_type in {"turn.commit", "response.completed"}:
        key = "turn_id" if event_type == "turn.commit" else "response_id"
        data = _exact_keys(payload, {key}, "payload")
        _require_text(data[key], f"payload.{key}")
    elif event_type == "response.started":
        data = _exact_keys(payload, {"response_id", "turn_id"}, "payload")
        _require_text(data["response_id"], "payload.response_id")
        _require_text(data["turn_id"], "payload.turn_id")
    elif event_type == "response.audio":
        data = _exact_keys(
            payload, {"response_id", "sequence", "duration_ms"}, "payload"
        )
        _require_text(data["response_id"], "payload.response_id")
        _require_int(data["sequence"], "payload.sequence")
        duration = _require_int(data["duration_ms"], "payload.duration_ms", 1)
        if duration > _MAX_MEDIA_CHUNK_MS:
            raise SessionContractError(
                f"payload.duration_ms must be <= {_MAX_MEDIA_CHUNK_MS}"
            )
    elif event_type == "user.interrupt":
        data = _exact_keys(
            payload, {"turn_id", "response_id", "reason"}, "payload"
        )
        _require_text(data["turn_id"], "payload.turn_id")
        _require_text(data["response_id"], "payload.response_id")
        _require_text(data["reason"], "payload.reason")
    elif event_type == "tool.call":
        data = _exact_keys(
            payload, {"call_id", "response_id", "name", "arguments"}, "payload"
        )
        _require_text(data["call_id"], "payload.call_id")
        _require_text(data["response_id"], "payload.response_id")
        name = _require_text(data["name"], "payload.name")
        if _TOOL_NAME.fullmatch(name) is None:
            raise SessionContractError("payload.name has unsupported characters")
        if not isinstance(data["arguments"], dict):
            raise SessionContractError("payload.arguments must be an object")
        _event_digest(data["arguments"])
    elif event_type == "tool.result":
        data = _exact_keys(
            payload, {"call_id", "response_id", "ok", "result"}, "payload"
        )
        _require_text(data["call_id"], "payload.call_id")
        _require_text(data["response_id"], "payload.response_id")
        _require_bool(data["ok"], "payload.ok")
        _require_text(data["result"], "payload.result")
    elif event_type in {
        "transport.disconnected",
        "session.timeout",
        "session.completed",
    }:
        data = _exact_keys(payload, {"reason"}, "payload")
        _require_text(data["reason"], "payload.reason")
    elif event_type == "transport.resumed":
        data = _exact_keys(payload, {"resume_token"}, "payload")
        _require_text(data["resume_token"], "payload.resume_token")

    return event  # 所有类型分支均通过后才返回可执行的事件


class RealtimeSession:  # 用确定性状态机模拟实时会话、打断、工具与恢复边界
    """Apply strict events to a deterministic, resumable session state."""  # 不采音、不联网、不调用模型或真实工具

    def __init__(self, session_id: str, resume_token: str) -> None:  # 创建一条尚未处理任何事件的会话状态
        self.session_id = _require_text(session_id, "session_id")  # 保存经验证的会话 ID，不把它当身份凭据
        self.resume_token = _require_text(resume_token, "resume_token")  # 保存 fixture 中的恢复令牌引用；真实系统需安全存储/校验
        self.status = "connected"  # 初始传输状态已连接
        self.phase = "listening"  # 初始业务阶段等待用户音频/轮次
        self.last_at_ms = -1  # 尚无事件时间；首条非负时间事件可通过单调检查
        self.processed_events = 0  # 记录唯一事件处理数量
        self.duplicate_events = 0  # 记录内容相同重放被安全忽略的次数
        self.checkpoint_version = 0  # 处理每条唯一事件后递增，供恢复/审计观察
        self.terminal_reason: str | None = None  # 终态前没有结束理由
        self.active_response_id: str | None = None  # 尚无正在播放/生成的 assistant 响应
        self.playback_queue_ms = 0  # 初始播放队列为空
        self.turns: dict[str, dict[str, Any]] = {}  # 按 turn ID 保存用户输入帧状态
        self.responses: dict[str, dict[str, Any]] = {}  # 按 response ID 保存 assistant 响应状态
        self.tool_calls: dict[str, dict[str, Any]] = {}  # 按 call ID 保存待回填/待对账工具调用
        self.effects: list[dict[str, Any]] = []  # 保存可观察事件效果，用于测试和摘要
        self._seen_events: dict[str, str] = {}  # event_id -> 内容摘要，检测重复 ID 是否被调包

    def apply(self, raw_event: object) -> dict[str, Any]:  # 原子应用一条事件：先验证，再检查时序/状态，最后记录效果
        """Apply one event atomically and return its observable effect."""  # 任一 gate 失败不会写入 seen-event 或推进状态

        event = validate_event(raw_event)  # 先把外部输入收紧为精确事件合同
        event_id = event["event_id"]  # 取稳定事件 ID 作为去重键
        digest = _event_digest(event)  # 对完整事件计算内容摘要，识别 ID 重用调包
        prior_digest = self._seen_events.get(event_id)  # 查看该 ID 是否已在本 session 处理过
        if prior_digest is not None:  # 已见事件属于重放/重复投递路径
            if prior_digest != digest:  # 相同 ID 却不同内容是严重协议冲突
                raise SessionContractError(  # 失败关闭，不能猜测使用哪一版本
                    f"event_id {event_id!r} was reused with different content"  # 输出具体冲突 ID 供审计
                )  # 结束异常构造
            self.duplicate_events += 1  # 内容相同的安全重放只计数，不重新改变状态
            return {"event_id": event_id, "effect": "duplicate_ignored"}  # 返回可观测的幂等效果

        at_ms = event["at_ms"]  # 读取当前事件的会话相对时间
        if at_ms < self.last_at_ms:  # 时间倒退会让播放、超时和恢复判断不可信
            raise SessionContractError("event.at_ms must not move backwards")  # 拒绝乱序事件而非静默重排
        if self.status in {"completed", "timed_out"}:  # 终态会话不可继续接受业务事件
            raise SessionContractError(f"session is terminal: {self.status}")  # 防止旧连接或重放重新打开会话

        event_type = event["type"]  # 使用已验证的事件类型选择状态机分支
        if self.status == "disconnected" and event_type not in {  # 断线期间只允许恢复或超时
            "transport.resumed",  # 恢复传输并进入对账/继续逻辑
            "session.timeout",  # 放弃未恢复的会话
        }:  # 其余输入在断线期间不能安全处理
            raise SessionContractError("only resume or timeout is valid while disconnected")  # 防止断线后继续产生副作用
        if self.status == "connected" and event_type == "transport.resumed":  # 已连接会话不能重复 resume
            raise SessionContractError("cannot resume an already connected session")  # 避免两次恢复造成状态分歧
        if self.phase == "reconciling" and event_type not in {  # 有未对账工具副作用时冻结新工作
            "tool.result",  # 允许回填已有工具调用的结果
            "transport.disconnected",  # 允许再次断线
            "session.timeout",  # 允许终止等待
        }:  # 任何新用户/模型工作都会绕过未解决副作用
            raise SessionContractError(  # 失败关闭直到 reconciliation 结束
                "reconciliation must finish before accepting new work"  # 给调用方明确恢复顺序
            )  # 结束异常构造
        if self.phase == "waiting_tool" and event_type not in {  # 工具等待期间只允许少量相关事件
            "tool.call",  # 允许同一响应发出已定义的工具调用
            "tool.result",  # 允许工具结果回填
            "user.interrupt",  # 用户可取消当前响应/工具等待
            "transport.disconnected",  # 传输可以断开
            "session.timeout",  # 会话可以超时终止
        }:  # 不允许直接产生新音频/完成事件跳过工具结果
            raise SessionContractError(  # 保持等待工具的状态机不变量
                "only tool events, interrupt, disconnect, or timeout are valid "  # 第一段稳定错误文本
                "while waiting for a tool"  # 补充当前 phase 的可接受事件范围
            )  # 结束异常构造

        handler_name = "_on_" + event_type.replace(".", "_")  # 将协议事件名映射到受控的内部 handler 名称
        handler = getattr(self, handler_name)  # 只从本类固定实现中取得 handler，不从外部文本执行代码
        effect = handler(event["payload"])  # handler 只在全部前置条件通过后更新相关子状态

        self._seen_events[event_id] = digest  # 成功处理后才登记 ID/摘要，保证失败事件可修正后重试
        self.last_at_ms = at_ms  # 推进单调时间基准
        self.processed_events += 1  # 计入唯一成功处理事件数
        record = {"event_id": event_id, "effect": effect}  # 生成对外可观察、非敏感的效果记录
        self.effects.append(record)  # 按顺序保留效果，便于测试和会话摘要
        return record  # 将本事件的确定性处理结果交回调用方

    def _turn(self, turn_id: str) -> dict[str, Any]:
        return self.turns.setdefault(
            turn_id,
            {"status": "receiving", "next_sequence": 0, "frames": 0, "speech": False},
        )

    def _cancel_active_response(self, reason: str) -> str | None:
        response_id = self.active_response_id
        if response_id is None:
            return None
        response = self.responses[response_id]
        response["status"] = "canceled"
        response["cancel_reason"] = reason
        for call in self.tool_calls.values():
            if call["response_id"] == response_id and call["status"] == "pending":
                call["status"] = "requires_reconciliation"
        self.active_response_id = None
        self.playback_queue_ms = 0
        return response_id

    def _has_unreconciled_calls(self) -> bool:
        """Return whether recovery must still query a prior side effect."""
        return any(
            call["status"] == "requires_reconciliation"
            for call in self.tool_calls.values()
        )

    def _has_unresolved_calls_for_response(self, response_id: str) -> bool:
        """Return whether this active response still waits on a tool outcome."""
        return any(
            call["response_id"] == response_id
            and call["status"] in {"pending", "requires_reconciliation"}
            for call in self.tool_calls.values()
        )

    def _on_audio_frame(self, payload: Mapping[str, Any]) -> str:
        turn = self.turns.get(payload["turn_id"])
        if turn is None:
            if payload["sequence"] != 0:
                raise SessionContractError("audio sequence must be contiguous from zero")
            turn = self._turn(payload["turn_id"])
        if turn["status"] != "receiving":
            raise SessionContractError("audio cannot be appended to a committed turn")
        if payload["sequence"] != turn["next_sequence"]:
            raise SessionContractError("audio sequence must be contiguous from zero")
        turn["next_sequence"] += 1
        turn["frames"] += 1
        turn["speech"] = turn["speech"] or payload["speech"]
        self.phase = "listening"
        return "audio_buffered"

    def _on_turn_commit(self, payload: Mapping[str, Any]) -> str:
        turn = self.turns.get(payload["turn_id"])
        if turn is None or turn["frames"] == 0:
            raise SessionContractError("turn must contain audio before commit")
        if turn["status"] != "receiving":
            raise SessionContractError("turn was already committed")
        if not turn["speech"]:
            raise SessionContractError("silence-only turn cannot be committed")
        turn["status"] = "committed"
        self.phase = "thinking"
        return "turn_committed"

    def _on_response_started(self, payload: Mapping[str, Any]) -> str:
        response_id = payload["response_id"]
        turn = self.turns.get(payload["turn_id"])
        if turn is None or turn["status"] != "committed":
            raise SessionContractError("response must correlate to a committed turn")
        if response_id in self.responses:
            raise SessionContractError("response_id must be unique")
        if self.active_response_id is not None:
            raise SessionContractError("only one response may be active")
        self.responses[response_id] = {
            "turn_id": payload["turn_id"],
            "status": "active",
            "next_audio_sequence": 0,
        }
        self.active_response_id = response_id
        self.phase = "thinking"
        return "response_started"

    def _on_response_audio(self, payload: Mapping[str, Any]) -> str:
        response_id = payload["response_id"]
        if response_id != self.active_response_id:
            raise SessionContractError("audio must correlate to the active response")
        response = self.responses[response_id]
        if payload["sequence"] != response["next_audio_sequence"]:
            raise SessionContractError("response audio sequence must be contiguous from zero")
        if self.playback_queue_ms + payload["duration_ms"] > _MAX_PLAYBACK_QUEUE_MS:
            raise SessionContractError(
                "playback queue must remain <= "
                f"{_MAX_PLAYBACK_QUEUE_MS}ms; apply backpressure or cancel"
            )
        response["next_audio_sequence"] += 1
        self.playback_queue_ms += payload["duration_ms"]
        self.phase = "speaking"
        return "output_audio_queued"

    def _on_user_interrupt(self, payload: Mapping[str, Any]) -> str:
        if self.active_response_id is None:
            raise SessionContractError("barge-in requires an active response")
        if payload["response_id"] != self.active_response_id:
            raise SessionContractError("interrupt must correlate to the active response")
        if payload["turn_id"] in self.turns:
            raise SessionContractError("interrupt turn_id must be new")
        canceled = self._cancel_active_response(payload["reason"])
        if canceled is None:  # Defensive: guarded above, retained for type clarity.
            raise SessionContractError("barge-in requires an active response")
        self._turn(payload["turn_id"])
        self.phase = "listening"
        return f"response_canceled:{canceled}"

    def _on_tool_call(self, payload: Mapping[str, Any]) -> str:
        response_id = payload["response_id"]
        if response_id != self.active_response_id:
            raise SessionContractError("tool call must correlate to the active response")
        response = self.responses[response_id]
        call_id = payload["call_id"]
        if call_id in self.tool_calls:
            raise SessionContractError("call_id must be unique")
        self.tool_calls[call_id] = {
            # Providers do not always repeat a turn ID on every tool event.  The
            # runtime must nevertheless persist the canonical relation so a
            # receipt is still attributable after a reconnect.
            "turn_id": response["turn_id"],
            "response_id": response_id,
            "name": payload["name"],
            "arguments": payload["arguments"],
            "status": "pending",
        }
        self.phase = "waiting_tool"
        return "tool_call_recorded"

    def _on_tool_result(self, payload: Mapping[str, Any]) -> str:
        call = self.tool_calls.get(payload["call_id"])
        if call is None:
            raise SessionContractError("tool result has no matching call_id")
        if call["response_id"] != payload["response_id"]:
            raise SessionContractError("tool result response_id does not match its call")
        if call["status"] not in {"pending", "requires_reconciliation"}:
            raise SessionContractError("tool call already has a terminal result")
        was_reconciliation_required = call["status"] == "requires_reconciliation"
        if self.phase == "reconciling" and not was_reconciliation_required:
            raise SessionContractError("tool result is not awaiting reconciliation")
        call["status"] = "succeeded" if payload["ok"] else "failed"
        call["result"] = payload["result"]
        if self.phase == "reconciling" and not self._has_unreconciled_calls():
            self.phase = "listening"
        elif self._has_unresolved_calls_for_response(payload["response_id"]):
            self.phase = "waiting_tool"
        elif self.active_response_id == payload["response_id"]:
            self.phase = "thinking"
        return "tool_result_correlated"

    def _on_response_completed(self, payload: Mapping[str, Any]) -> str:
        response_id = payload["response_id"]
        if response_id != self.active_response_id:
            raise SessionContractError("only the active response can complete")
        unresolved = [
            call_id
            for call_id, call in self.tool_calls.items()
            if call["response_id"] == response_id
            and call["status"] in {"pending", "requires_reconciliation"}
        ]
        if unresolved:
            raise SessionContractError(f"response has unresolved tool calls: {unresolved}")
        self.responses[response_id]["status"] = "completed"
        self.active_response_id = None
        self.playback_queue_ms = 0
        self.phase = "listening"
        return "response_completed"

    def _on_transport_disconnected(self, payload: Mapping[str, Any]) -> str:
        canceled = self._cancel_active_response("transport_disconnected")
        self.status = "disconnected"
        self.phase = "disconnected"
        self.checkpoint_version += 1
        suffix = f":canceled={canceled}" if canceled is not None else ""
        return f"checkpoint_saved{suffix}"

    def _on_transport_resumed(self, payload: Mapping[str, Any]) -> str:
        if payload["resume_token"] != self.resume_token:
            raise SessionContractError("resume token does not match the session")
        self.status = "connected"
        if self._has_unreconciled_calls():
            self.phase = "reconciling"
            return (
                f"session_resumed:checkpoint={self.checkpoint_version}"
                ":reconciliation_required"
            )
        self.phase = "listening"
        return f"session_resumed:checkpoint={self.checkpoint_version}"

    def _on_session_timeout(self, payload: Mapping[str, Any]) -> str:
        self._cancel_active_response("session_timeout")
        for call in self.tool_calls.values():
            if call["status"] == "pending":
                call["status"] = "requires_reconciliation"
        self.status = "timed_out"
        self.phase = "terminal"
        self.terminal_reason = payload["reason"]
        return "session_timed_out"

    def _on_session_completed(self, payload: Mapping[str, Any]) -> str:
        if self.active_response_id is not None:
            raise SessionContractError("cannot complete with an active response")
        unresolved = [
            call_id
            for call_id, call in self.tool_calls.items()
            if call["status"] in {"pending", "requires_reconciliation"}
        ]
        if unresolved:
            raise SessionContractError(f"cannot complete with unresolved calls: {unresolved}")
        self.status = "completed"
        self.phase = "terminal"
        self.terminal_reason = payload["reason"]
        return "session_completed"

    def summary(self) -> dict[str, Any]:
        """Return a stable, JSON-serializable snapshot for tests and review."""

        return {
            "session_id": self.session_id,
            "status": self.status,
            "phase": self.phase,
            "terminal_reason": self.terminal_reason,
            "processed_events": self.processed_events,
            "duplicate_events": self.duplicate_events,
            "checkpoint_version": self.checkpoint_version,
            "active_response_id": self.active_response_id,
            "playback_queue_ms": self.playback_queue_ms,
            "turns": self.turns,
            "responses": self.responses,
            "tool_calls": self.tool_calls,
        }


def run_fixture(path: Path) -> dict[str, Any]:  # 读取并运行一条严格 fixture，不创建任何输出文件或网络连接
    """Load and run one strict fixture without writing any output files."""  # 让初学者可重复观察同一事件序列的确定性结果

    try:  # 文件读取错误转换成统一 session 合同错误
        text = path.read_text(encoding="utf-8")  # 强制 UTF-8，避免终端/系统默认编码差异
    except OSError as exc:  # 路径不存在、权限不足等都属于用户可修复输入问题
        raise SessionContractError(f"cannot load fixture: {exc}") from exc  # 保留异常链，方便定位文件错误
    raw = _strict_json_loads(text, f"fixture {path}")  # 拒绝 duplicate key、NaN/Infinity 和普通 JSON 语法错误
    fixture = _exact_keys(raw, {"session", "events"}, "fixture")  # fixture 根只允许 session 与 events 两项
    session_data = _exact_keys(  # 对 session 子对象也使用封闭 schema
        fixture["session"], {"session_id", "resume_token"}, "fixture.session"  # 不接受隐藏 token/配置字段
    )  # 完成 session 数据校验
    if not isinstance(fixture["events"], list):  # 事件序列必须是数组，便于保持给定顺序
        raise SessionContractError("fixture.events must be an array")  # 不接受字典按键重排事件
    session = RealtimeSession(  # 用经校验的 session ID/resume token 创建确定性状态机
        session_id=session_data["session_id"], resume_token=session_data["resume_token"]  # 不从 event 载荷猜测会话身份
    )  # 完成会话初始化
    for event in fixture["events"]:  # 按 fixture 顺序逐条处理，时序错误会由 apply 拒绝
        session.apply(event)  # 每条事件独立经过 schema、去重、phase 与 handler gate
    return session.summary()  # 返回不含原始音频/秘密的可审计会话摘要


def main() -> int:  # CLI 入口：运行指定 fixture，并按需格式化打印 JSON 摘要
    parser = argparse.ArgumentParser(description=__doc__)  # --help 中展示本模拟器的明确能力边界
    parser.add_argument("fixture", type=Path, help="strict JSON event fixture")  # 接收严格 JSON fixture 文件位置
    parser.add_argument("--pretty", action="store_true", help="indent JSON output")  # 允许人读缩进，但不改变数据语义
    args = parser.parse_args()  # 解析用户命令行参数
    try:  # 只捕获可预期的合同错误，让未知程序错误可见
        result = run_fixture(args.fixture)  # 执行完整离线会话状态机
    except SessionContractError as exc:  # fixture/事件不符合合同
        parser.error(str(exc))  # argparse 以受控 usage error 输出并返回非零
    print(  # stdout 只输出成功的 JSON 摘要
        json.dumps(  # 序列化纯字典结果，不输出原始输入载荷
            result,  # summary 已由 session 控制字段组成
            ensure_ascii=False,  # 保留中文/Unicode 的可读形式
            sort_keys=True,  # 固定键顺序，方便测试和 diff
            indent=2 if args.pretty else None,  # --pretty 时启用缩进
            allow_nan=False,  # 成功输出同样禁止非标准 JSON 数值
        )  # 完成 JSON 文本生成
    )  # 写到标准输出
    return 0  # fixture 运行成功


if __name__ == "__main__":  # 直接运行脚本时启动 CLI；被测试导入时不自动执行
    raise SystemExit(main())  # 用 main 的整数结果作为进程退出码
