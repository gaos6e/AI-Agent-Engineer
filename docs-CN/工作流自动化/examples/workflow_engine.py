"""A bounded, offline workflow engine for teaching reliability contracts.

The implementation is intentionally single-process. It demonstrates strict
definition and event validation, deduplication, finite retries, idempotent side
effects, approval binding, checkpoint integrity, and compensation. It is not a
production transaction system or an exactly-once guarantee.
"""

from __future__ import annotations  # 允许注解延后解析，保持示例在不同 Python 环境中稳定。

import argparse  # 为“仅校验”和“运行演示”提供同一个命令行入口。
import hashlib  # 对定义、事件、意图和检查点生成可比较的摘要。
import json  # 严格读取 JSON 合同并输出可复查的演示报告。
import re  # 先用正则筛除本示例不支持的时间戳形式。
import tempfile  # 演示检查点恢复时使用不污染工作区的临时目录。
from dataclasses import asdict, dataclass, field  # 将运行时状态明确序列化为合同数据。
from datetime import datetime  # 验证可被标准库可靠解析的 RFC 3339 时间子集。
from pathlib import Path  # 用路径对象定位同目录的工作流定义。
from typing import Any, Callable  # 外部 JSON 与可注入时钟均需运行时约束。


ALLOWED_DEFINITION_FIELDS = {"name", "version", "max_total_attempts", "steps"}  # 拒绝拼写错误或未知配置。
ALLOWED_STEP_FIELDS = {
    "name",
    "needs",
    "handler",
    "approval",
    "max_attempts",
    "retryable_errors",
    "compensate",
}
HANDLERS = {"validate", "reserve_inventory", "risk_check", "charge", "notify"}  # 本教学引擎支持的动作白名单。
COMPENSATIONS = {"release_inventory", "refund"}  # 可逆副作用对应的补偿动作白名单。
RETRYABLE_ERROR_CODES = {"TRANSIENT", "UNKNOWN_RESULT"}  # 重试由错误语义决定，不由异常文本决定。
EVENT_FIELDS = {"id", "source", "specversion", "type", "time", "data"}  # CloudEvents 子集的允许字段。
RFC3339_TIMESTAMP = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
CHECKPOINT_FIELDS = {"schema_version", "definition_fingerprint", "payload", "sha256"}
STATE_FIELDS = {
    "instance_id",
    "event_key",
    "event_fingerprint",
    "definition_name",
    "definition_version",
    "definition_fingerprint",
    "status",
    "data",
    "steps",
    "attempts",
    "approved_steps",
    "compensations",
    "approval_request",
    "state_version",
    "ready_batches",
    "events",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)  # 所有合同违例统一在边界处失败，避免带病运行。


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))  # 固定编码供摘要与幂等比较使用。


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()  # 摘要不是签名，只用于一致性检测。


def event_identity_key(*, source: str, event_id: str) -> str:
    """Encode the CloudEvents identity as structured data, never a delimiter join."""

    return canonical_json([source, event_id])  # 结构化编码避免 source/id 用分隔符拼接时碰撞。


def is_supported_rfc3339_timestamp(value: str) -> bool:
    """Accept the timestamp subset this offline profile can parse reliably.

    CloudEvents permits RFC 3339 timestamps.  This standard-library example
    deliberately requires an explicit UTC offset and does not model leap
    seconds; a general-purpose CloudEvents gateway should use its protocol
    library's full parser instead.
    """

    if RFC3339_TIMESTAMP.fullmatch(value) is None:
        return False
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value  # 适配 fromisoformat 的 UTC 表示法。
    try:
        datetime.fromisoformat(normalized)
    except ValueError:
        return False
    return True


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")  # 禁止解析器静默采用“最后一个键”。
        result[key] = value
    return result


def read_json_object(path: Path) -> dict[str, Any]:
    data = json.loads(  # 读取定义/检查点时把重复键视为协议歧义。
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_keys,
    )
    require(isinstance(data, dict), f"{path.name} root must be an object")
    return data


@dataclass(frozen=True)
class StepDefinition:
    name: str
    needs: tuple[str, ...]
    handler: str
    approval: bool
    max_attempts: int
    retryable_errors: tuple[str, ...]
    compensate: str | None


@dataclass(frozen=True)
class WorkflowDefinition:
    name: str
    version: str
    max_total_attempts: int
    steps: tuple[StepDefinition, ...]
    fingerprint: str

    @property
    def registry(self) -> dict[str, StepDefinition]:
        return {step.name: step for step in self.steps}


def load_definition(path: Path) -> WorkflowDefinition:
    raw = read_json_object(path)  # 先验证外部配置，再把它收窄为不可变定义对象。
    require(set(raw) == ALLOWED_DEFINITION_FIELDS, "definition has missing or unknown top-level fields")
    require(isinstance(raw["name"], str) and raw["name"].strip(), "definition name must be non-empty")
    require(isinstance(raw["version"], str) and raw["version"].strip(), "definition version must be non-empty")
    require(
        isinstance(raw["max_total_attempts"], int)
        and not isinstance(raw["max_total_attempts"], bool)
        and raw["max_total_attempts"] >= 1,
        "max_total_attempts must be a positive integer",
    )
    raw_steps = raw["steps"]
    require(isinstance(raw_steps, list) and raw_steps, "steps must be a non-empty array")

    steps: list[StepDefinition] = []
    names: set[str] = set()
    for index, item in enumerate(raw_steps, start=1):
        require(isinstance(item, dict), f"step {index} must be an object")
        require(set(item) == ALLOWED_STEP_FIELDS, f"step {index} has missing or unknown fields")
        name = item["name"]
        require(isinstance(name, str) and name.strip(), f"step {index} name must be non-empty")
        require(name not in names, f"duplicate step name: {name}")
        names.add(name)
        needs = item["needs"]
        require(
            isinstance(needs, list) and all(isinstance(value, str) and value for value in needs),
            f"step {name} needs must be an array of names",
        )
        require(len(needs) == len(set(needs)), f"step {name} has duplicate dependencies")
        handler = item["handler"]
        require(handler in HANDLERS, f"unknown handler for {name}: {handler}")
        require(isinstance(item["approval"], bool), f"step {name} approval must be boolean")
        max_attempts = item["max_attempts"]
        require(
            isinstance(max_attempts, int) and not isinstance(max_attempts, bool) and max_attempts >= 1,
            f"step {name} max_attempts must be a positive integer",
        )
        retryable = item["retryable_errors"]
        require(
            isinstance(retryable, list) and all(isinstance(value, str) for value in retryable),
            f"step {name} retryable_errors must be an array of strings",
        )
        require(len(retryable) == len(set(retryable)), f"step {name} has duplicate retryable errors")
        unknown_errors = set(retryable) - RETRYABLE_ERROR_CODES
        require(not unknown_errors, f"step {name} has unknown retryable errors: {sorted(unknown_errors)}")
        compensate = item["compensate"]
        require(
            compensate is None or compensate in COMPENSATIONS,
            f"unknown compensation for {name}: {compensate}",
        )
        steps.append(  # 列表顺序保留，用于可复现的 ready batch 和执行轨迹。
            StepDefinition(
                name=name,
                needs=tuple(needs),
                handler=handler,
                approval=item["approval"],
                max_attempts=max_attempts,
                retryable_errors=tuple(retryable),
                compensate=compensate,
            )
        )

    registry = {step.name: step for step in steps}  # 统一用名称解析依赖，避免索引与定义顺序耦合。
    for step in steps:
        unknown = set(step.needs) - set(registry)
        require(not unknown, f"unknown dependencies for {step.name}: {sorted(unknown)}")
        require(step.name not in step.needs, f"step {step.name} cannot depend on itself")
    _assert_acyclic(registry)  # 在启动前拒绝循环依赖，而非运行到一半才死锁。
    require(any(not step.needs for step in steps), "definition needs at least one root step")
    require(
        raw["max_total_attempts"] >= sum(1 for _ in steps),
        "max_total_attempts must allow every step one attempt",
    )
    return WorkflowDefinition(
        name=raw["name"],
        version=raw["version"],
        max_total_attempts=raw["max_total_attempts"],
        steps=tuple(steps),
        fingerprint=fingerprint(raw),  # 检查点只能恢复到完全一致的定义版本。
    )


def _assert_acyclic(steps: dict[str, StepDefinition]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(name: str) -> None:
        require(name not in visiting, "workflow contains a cycle")
        if name in visited:
            return
        visiting.add(name)  # 深度优先遍历中的灰色节点表示当前递归路径。
        for dependency in steps[name].needs:
            visit(dependency)
        visiting.remove(name)
        visited.add(name)

    for step_name in steps:
        visit(step_name)


class StepError(RuntimeError):
    code = "STEP_ERROR"


class TransientStepError(StepError):
    code = "TRANSIENT"


class UnknownResultError(StepError):
    code = "UNKNOWN_RESULT"


class PermanentStepError(StepError):
    code = "PERMANENT"


@dataclass(frozen=True)
class EffectRecord:
    key: str
    action: str
    intent_fingerprint: str
    result: dict[str, Any]


class EffectStore:
    """In-memory idempotency ledger; deliberately not a production boundary."""

    def __init__(
        self,
        *,
        unknown_once: set[str] | None = None,
        transient_failures: dict[str, int] | None = None,
        permanent_failures: set[str] | None = None,
    ) -> None:
        self.records: dict[str, EffectRecord] = {}  # 以幂等键保存已提交副作用的回执。
        self.counts: dict[str, int] = {}  # 演示断言实际提交次数，而非仅看工作流状态。
        self.unknown_once = set(unknown_once or set())
        self.unknown_emitted: set[str] = set()
        self.transient_failures = dict(transient_failures or {})
        self.permanent_failures = set(permanent_failures or set())

    def perform(self, *, key: str, action: str, intent: dict[str, Any]) -> dict[str, Any]:
        intent_fingerprint = fingerprint(intent)  # 相同键必须绑定到相同业务意图。
        existing = self.records.get(key)  # 重放先查账本，避免再次提交外部副作用。
        if existing is not None:
            require(existing.intent_fingerprint == intent_fingerprint, f"idempotency conflict for {key}")
            require(existing.action == action, f"idempotency action conflict for {key}")
            return dict(existing.result)  # 返回副本，调用方不能改写账本中的历史回执。

        remaining = self.transient_failures.get(action, 0)
        if remaining > 0:
            self.transient_failures[action] = remaining - 1
            raise TransientStepError(f"{action} temporarily unavailable")
        if action in self.permanent_failures:
            raise PermanentStepError(f"{action} permanently failed")

        result = {"action": action, "receipt": fingerprint({"key": key, "intent": intent})[:16]}
        self.records[key] = EffectRecord(key, action, intent_fingerprint, result)  # 在模拟提交后持久化幂等证据。
        self.counts[action] = self.counts.get(action, 0) + 1  # 用于验证恢复没有重复扣款或预留。
        if action in self.unknown_once and action not in self.unknown_emitted:
            self.unknown_emitted.add(action)
            raise UnknownResultError(f"{action} committed but acknowledgement was lost")  # 已提交但未知结果时必须以同键重试查询。
        return dict(result)


@dataclass(frozen=True)
class CompensationRecord:
    original_step: str
    action: str
    intent: dict[str, Any]
    status: str = "pending"


@dataclass(frozen=True)
class ApprovalRequest:
    request_id: str
    instance_id: str
    step: str
    payload_fingerprint: str
    definition_version: str
    state_version: int
    expires_at: int


@dataclass(frozen=True)
class ApprovalGrant:
    request_id: str
    instance_id: str
    step: str
    payload_fingerprint: str
    definition_version: str
    state_version: int
    expires_at: int
    decision: str


@dataclass
class WorkflowState:
    instance_id: str
    event_key: str
    event_fingerprint: str
    definition_name: str
    definition_version: str
    definition_fingerprint: str
    status: str
    data: dict[str, Any]
    steps: dict[str, str]
    attempts: dict[str, int]
    approved_steps: list[str] = field(default_factory=list)
    compensations: list[CompensationRecord] = field(default_factory=list)
    approval_request: ApprovalRequest | None = None
    state_version: int = 0
    ready_batches: list[list[str]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)


def validate_event(event: dict[str, Any]) -> dict[str, Any]:
    require(isinstance(event, dict), "event must be an object")  # 事件是启动实例的唯一不可信边界。
    require(set(event) <= EVENT_FIELDS, "event has unknown fields")
    for field_name in ("id", "source", "specversion", "type", "data"):
        require(field_name in event, f"event missing required field: {field_name}")
    for field_name in ("id", "source", "specversion", "type"):
        require(
            isinstance(event[field_name], str) and event[field_name].strip(),
            f"event {field_name} must be a non-empty string",
        )
    require(event["specversion"] == "1.0", "this example accepts CloudEvents specversion 1.0")
    require(event["type"] == "com.example.order.submitted.v1", "unsupported event type")
    if "time" in event:
        require(
            isinstance(event["time"], str) and is_supported_rfc3339_timestamp(event["time"]),
            "event time must be a supported RFC 3339 timestamp with an explicit offset",
        )
    data = event["data"]
    require(isinstance(data, dict), "event data must be an object")
    require(set(data) == {"order_id", "amount_cents"}, "event data has missing or unknown fields")
    require(isinstance(data["order_id"], str) and data["order_id"].strip(), "order_id must be non-empty")
    require(
        isinstance(data["amount_cents"], int)
        and not isinstance(data["amount_cents"], bool)
        and data["amount_cents"] > 0,
        "amount_cents must be a positive integer",
    )
    return {"order_id": data["order_id"], "amount_cents": data["amount_cents"]}  # 只把已验证的业务字段带入状态。


class WorkflowCoordinator:
    def __init__(
        self,
        definition: WorkflowDefinition,
        effects: EffectStore,
        *,
        now: Callable[[], int] | None = None,
        approval_ttl: int = 3600,
    ) -> None:
        require(approval_ttl > 0, "approval_ttl must be positive")
        self.definition = definition  # 协调器在整个实例生命周期中绑定一个不可变定义。
        self.effects = effects  # 注入副作用账本，使重试语义可测试。
        self.now = now or (lambda: 0)  # 注入时钟，令审批过期测试无需依赖真实时间。
        self.approval_ttl = approval_ttl
        self.events: dict[str, tuple[str, WorkflowState]] = {}

    def start(self, event: dict[str, Any]) -> WorkflowState:
        data = validate_event(event)  # 先收窄外部 CloudEvent，再创建工作流状态。
        event_key = event_identity_key(source=event["source"], event_id=event["id"])  # source + id 是事件身份。
        event_fingerprint = fingerprint(event)  # 同身份不同内容必须被视为冲突。
        existing = self.events.get(event_key)
        if existing is not None:
            require(existing[0] == event_fingerprint, "same event key has a different payload")
            return existing[1]  # 合法重放返回同一实例，不会再开一个订单流程。
        instance_id = "wf-" + fingerprint({"event_key": event_key})[:16]
        state = WorkflowState(
            instance_id=instance_id,
            event_key=event_key,
            event_fingerprint=event_fingerprint,
            definition_name=self.definition.name,
            definition_version=self.definition.version,
            definition_fingerprint=self.definition.fingerprint,
            status="running",
            data=data,
            steps={step.name: "pending" for step in self.definition.steps},
            attempts={step.name: 0 for step in self.definition.steps},
        )
        self._record(state, "instance_started")  # 启动也写入事件证据，便于回放。
        self.events[event_key] = (event_fingerprint, state)  # 注册去重映射必须发生在返回前。
        return state

    def run_until_blocked(self, state: WorkflowState) -> WorkflowState:
        self._validate_state_identity(state)  # 恢复的检查点不能冒充另一个定义。
        require(state.status == "running", f"state must be running, got {state.status}")
        registry = self.definition.registry
        while state.status == "running":
            ready = [  # 一个批次的所有任务都只依赖已成功的前置步骤。
                step.name
                for step in self.definition.steps
                if state.steps[step.name] == "pending"
                and all(state.steps[dependency] == "succeeded" for dependency in step.needs)
            ]
            if not ready:
                if all(value == "succeeded" for value in state.steps.values()):
                    state.status = "completed"  # 只有所有定义步骤成功，实例才完成。
                    self._bump(state, "instance_completed")
                    return state
                raise ValueError("workflow is blocked without a waiting or terminal state")
            state.ready_batches.append(list(ready))  # 保留可并行集合，即使本示例顺序执行它们。
            self._record(state, "ready_batch", count=len(ready))
            for step_name in ready:
                step = registry[step_name]
                if step.approval and step_name not in state.approved_steps:
                    self._wait_for_approval(state, step)  # 审批是暂停点，绝不先执行后补签。
                    return state
                if not self._execute_with_retries(state, step):
                    return state
        return state

    def approve(self, state: WorkflowState, grant: ApprovalGrant) -> WorkflowState:
        self._validate_state_identity(state)
        require(state.status == "waiting_approval", "workflow is not waiting for approval")
        request = state.approval_request
        require(request is not None, "approval request is missing")
        expected = asdict(request)  # 请求中的实例、版本、载荷与状态版本都属于审批绑定。
        actual = {key: value for key, value in asdict(grant).items() if key != "decision"}  # 决策是唯一允许新增的字段。
        require(actual == expected, "approval grant does not match the bound request")
        require(grant.decision in {"approve", "reject"}, "approval decision must be approve or reject")
        require(self.now() <= grant.expires_at, "approval has expired")
        if grant.decision == "reject":
            state.steps[grant.step] = "rejected"
            state.status = "business_rejected"
            state.approval_request = None
            self._bump(state, "approval_rejected", step=grant.step)
            self._compensate(state)  # 业务拒绝也要撤销先前成功的可逆副作用。
            return state
        state.approved_steps.append(grant.step)  # 已批准的步骤避免恢复后再次请求同一审批。
        state.steps[grant.step] = "pending"
        state.status = "running"
        state.approval_request = None
        self._bump(state, "approval_accepted", step=grant.step)
        return state

    def _execute_with_retries(self, state: WorkflowState, step: StepDefinition) -> bool:
        while state.attempts[step.name] < step.max_attempts:
            if sum(state.attempts.values()) >= self.definition.max_total_attempts:  # 全局上限先于单步重试上限生效。
                state.steps[step.name] = "failed"
                state.status = "failed"
                self._bump(state, "attempt_budget_exhausted", step=step.name)
                self._compensate(state)
                return False
            state.attempts[step.name] += 1  # 每个实际执行尝试都要计数并记录。
            state.steps[step.name] = "running"  # 先改状态，再调用可能产生副作用的处理器。
            self._bump(state, "step_started", step=step.name, attempt=state.attempts[step.name])
            try:
                self._execute_step(state, step)
            except StepError as exc:
                self._record(state, "step_error", step=step.name, error_code=exc.code)
                can_retry = exc.code in step.retryable_errors and state.attempts[step.name] < step.max_attempts  # 重试策略显式绑定错误码和次数。
                if can_retry:
                    state.steps[step.name] = "pending"
                    self._bump(state, "retry_scheduled", step=step.name, attempt=state.attempts[step.name])
                    continue
                state.steps[step.name] = "failed"
                state.status = "failed"
                self._bump(state, "step_failed", step=step.name, error_code=exc.code)
                self._compensate(state)  # 不可恢复失败后按反向顺序补偿既有副作用。
                return False
            state.steps[step.name] = "succeeded"
            if step.compensate is not None:  # 仅成功的、声明可逆的步骤才进入补偿栈。
                state.compensations.append(
                    CompensationRecord(
                        original_step=step.name,
                        action=step.compensate,
                        intent=self._effect_intent(state, step.name),
                    )
                )
            self._bump(state, "step_succeeded", step=step.name)
            return True
        return False

    def _execute_step(self, state: WorkflowState, step: StepDefinition) -> None:
        if step.handler in {"validate", "risk_check"}:
            return  # 纯计算步骤没有外部副作用，也无需幂等账本。
        intent = self._effect_intent(state, step.name)  # 同一业务意图在重试/恢复时保持不变。
        key = f"{state.instance_id}:{step.name}:v1"  # 幂等键包含实例、步骤与意图版本。
        self.effects.perform(key=key, action=step.handler, intent=intent)

    def _effect_intent(self, state: WorkflowState, step_name: str) -> dict[str, Any]:
        return {
            "instance_id": state.instance_id,
            "step": step_name,
            "order_id": state.data["order_id"],
            "amount_cents": state.data["amount_cents"],
            "intent_version": "v1",
        }

    def _wait_for_approval(self, state: WorkflowState, step: StepDefinition) -> None:
        state.steps[step.name] = "waiting_approval"  # 该步骤不可被调度，直到匹配的授权返回。
        state.status = "waiting_approval"  # 整个实例在审批边界暂停。
        state.state_version += 1  # 请求将绑定这个版本，拒绝过期或陈旧授权。
        payload_fingerprint = fingerprint(self._effect_intent(state, step.name))  # 授权与即将产生的副作用绑定。
        expires_at = self.now() + self.approval_ttl
        request_id = "approval-" + fingerprint(
            {
                "instance_id": state.instance_id,
                "step": step.name,
                "payload_fingerprint": payload_fingerprint,
                "definition_version": state.definition_version,
                "state_version": state.state_version,
                "expires_at": expires_at,
            }
        )[:16]
        state.approval_request = ApprovalRequest(  # 保存原请求，稍后做字段级完全匹配。
            request_id=request_id,
            instance_id=state.instance_id,
            step=step.name,
            payload_fingerprint=payload_fingerprint,
            definition_version=state.definition_version,
            state_version=state.state_version,
            expires_at=expires_at,
        )
        self._record(state, "approval_requested", step=step.name)

    def _compensate(self, state: WorkflowState) -> None:
        rejected = state.status == "business_rejected"  # 区分业务拒绝与技术失败，保留最终语义。
        if not state.compensations:
            if state.status == "failed":
                state.status = "failed_uncompensated"
            return
        state.status = "compensating"  # 显示中间状态，不能把补偿过程误报为最终失败。
        self._bump(state, "compensation_started")
        updated = list(state.compensations)
        for index in range(len(updated) - 1, -1, -1):  # Saga 补偿必须按成功副作用的反向顺序执行。
            record = updated[index]
            if record.status == "succeeded":
                continue
            key = f"{state.instance_id}:compensate:{record.original_step}:{record.action}:v1"  # 补偿本身也必须幂等。
            try:
                self.effects.perform(key=key, action=record.action, intent=record.intent)
            except StepError as exc:
                updated[index] = CompensationRecord(
                    record.original_step,
                    record.action,
                    record.intent,
                    "failed",
                )
                state.compensations = updated
                state.status = "compensation_failed"  # 失败保留证据并停止，交给人工或后续恢复处理。
                self._bump(state, "compensation_failed", step=record.original_step, error_code=exc.code)
                return
            updated[index] = CompensationRecord(
                record.original_step,
                record.action,
                record.intent,
                "succeeded",
            )
            self._bump(state, "compensation_succeeded", step=record.original_step)
        state.compensations = updated
        state.status = "business_rejected_compensated" if rejected else "failed_compensated"  # 完成后表达原始终因和补偿结果。
        self._bump(
            state,
            "instance_business_rejected_compensated" if rejected else "instance_failed_compensated",
        )

    def _validate_state_identity(self, state: WorkflowState) -> None:
        require(state.definition_name == self.definition.name, "checkpoint definition name mismatch")  # 防止把旧状态恢复到名称不同的流程。
        require(state.definition_version == self.definition.version, "checkpoint definition version mismatch")
        require(
            state.definition_fingerprint == self.definition.fingerprint,
            "checkpoint definition fingerprint mismatch",
        )
        require(set(state.steps) == set(self.definition.registry), "checkpoint step set mismatch")
        require(set(state.attempts) == set(self.definition.registry), "checkpoint attempt set mismatch")

    def _record(self, state: WorkflowState, event_type: str, **fields: Any) -> None:
        event = {"type": event_type, "state_version": state.state_version}  # 每条审计事件锚定到产生它的版本。
        event.update(fields)
        state.events.append(event)

    def _bump(self, state: WorkflowState, event_type: str, **fields: Any) -> None:
        state.state_version += 1  # 所有持久状态变化必须令版本单调递增。
        self._record(state, event_type, **fields)


def encode_checkpoint(state: WorkflowState) -> str:
    payload = asdict(state)  # dataclass 转为纯数据，便于存储和跨进程恢复。
    envelope = {
        "schema_version": 1,
        "definition_fingerprint": state.definition_fingerprint,
        "payload": payload,
        "sha256": fingerprint(payload),  # 仅防意外/未授权改写检测，不替代签名或访问控制。
    }
    return canonical_json(envelope)


def decode_checkpoint(raw: str, definition: WorkflowDefinition) -> WorkflowState:
    envelope = json.loads(raw, object_pairs_hook=_reject_duplicate_keys)  # 在恢复边界同样拒绝重复键。
    require(isinstance(envelope, dict), "checkpoint root must be an object")
    require(set(envelope) == CHECKPOINT_FIELDS, "checkpoint has missing or unknown fields")
    require(envelope["schema_version"] == 1, "unsupported checkpoint schema_version")
    require(
        envelope["definition_fingerprint"] == definition.fingerprint,
        "checkpoint definition fingerprint mismatch",
    )
    payload = envelope["payload"]
    require(isinstance(payload, dict) and set(payload) == STATE_FIELDS, "checkpoint payload shape is invalid")
    require(envelope["sha256"] == fingerprint(payload), "checkpoint integrity check failed")  # 先验完整性，再反序列化状态。
    require(isinstance(payload["compensations"], list), "checkpoint compensations must be an array")
    require(
        payload["approval_request"] is None or isinstance(payload["approval_request"], dict),
        "checkpoint approval_request is invalid",
    )
    try:
        compensations = [CompensationRecord(**item) for item in payload["compensations"]]
        approval = (
            ApprovalRequest(**payload["approval_request"])
            if payload["approval_request"] is not None
            else None
        )
        state = WorkflowState(
            **{
                **payload,
                "compensations": compensations,
                "approval_request": approval,
            }
        )
    except (TypeError, KeyError) as exc:
        raise ValueError(f"checkpoint payload values are invalid: {exc}") from exc
    validator = WorkflowCoordinator(definition, EffectStore())  # 复用运行时身份约束验证恢复状态。
    validator._validate_state_identity(state)
    require(state.status in {
        "running",
        "waiting_approval",
        "completed",
        "business_rejected",
        "business_rejected_compensated",
        "failed_uncompensated",
        "failed_compensated",
        "compensation_failed",
    }, "checkpoint status is invalid")
    require(all(isinstance(value, int) and value >= 0 for value in state.attempts.values()), "invalid attempts")
    return state


def make_event(event_id: str, order_id: str, amount_cents: int) -> dict[str, Any]:
    return {
        "id": event_id,
        "source": "/offline-demo/orders",
        "specversion": "1.0",
        "type": "com.example.order.submitted.v1",
        "data": {"order_id": order_id, "amount_cents": amount_cents},
    }


def grant_for(request: ApprovalRequest, decision: str = "approve") -> ApprovalGrant:
    return ApprovalGrant(**asdict(request), decision=decision)


def run_demo(definition: WorkflowDefinition) -> dict[str, Any]:
    clock = [1_000]  # 可控时钟让审批/恢复路径完全确定。
    success_effects = EffectStore(unknown_once={"reserve_inventory"})  # 模拟“已提交但确认丢失”的关键故障。
    first = WorkflowCoordinator(definition, success_effects, now=lambda: clock[0])
    state = first.start(make_event("event-success", "order-7", 2599))
    first.run_until_blocked(state)
    require(state.status == "waiting_approval", "demo should pause for approval")
    require(state.approval_request is not None, "demo approval request missing")
    request = state.approval_request

    with tempfile.TemporaryDirectory() as temp_directory:
        checkpoint_path = Path(temp_directory) / "checkpoint.json"
        checkpoint_path.write_text(encode_checkpoint(state), encoding="utf-8")  # 暂停点只保存可验证的检查点信封。
        restored = decode_checkpoint(checkpoint_path.read_text(encoding="utf-8"), definition)  # 恢复时重验定义与完整性。

    resumed = WorkflowCoordinator(definition, success_effects, now=lambda: clock[0])
    resumed.approve(restored, grant_for(request))  # 授权必须匹配暂停前绑定的请求。
    resumed.run_until_blocked(restored)
    require(restored.status == "completed", "demo success workflow did not complete")
    require(success_effects.counts.get("reserve_inventory") == 1, "reservation was duplicated")

    failure_effects = EffectStore(permanent_failures={"notify"})  # 模拟末端不可恢复失败，检查 Saga 补偿。
    failure = WorkflowCoordinator(definition, failure_effects, now=lambda: clock[0])
    failed_state = failure.start(make_event("event-failure", "order-8", 4999))
    failure.run_until_blocked(failed_state)
    require(failed_state.approval_request is not None, "failure demo approval request missing")
    failure.approve(failed_state, grant_for(failed_state.approval_request))
    failure.run_until_blocked(failed_state)
    require(failed_state.status == "failed_compensated", "failure demo was not compensated")
    require(failure_effects.counts.get("refund") == 1, "charge refund missing")
    require(failure_effects.counts.get("release_inventory") == 1, "inventory release missing")

    return {
        "status": "ok",
        "definition": definition.name,
        "version": definition.version,
        "definition_fingerprint": definition.fingerprint,
        "success": {
            "final_status": restored.status,
            "reserve_commits": success_effects.counts.get("reserve_inventory", 0),
            "charge_commits": success_effects.counts.get("charge", 0),
            "ready_parallel_batch": ["reserve_inventory", "risk_check"] in restored.ready_batches,
        },
        "failure": {
            "final_status": failed_state.status,
            "refund_commits": failure_effects.counts.get("refund", 0),
            "release_commits": failure_effects.counts.get("release_inventory", 0),
        },
        "note": "single-process teaching evidence; not production exactly-once",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run or validate the offline workflow teaching project.")  # 最小 CLI 不接触真实外部系统。
    parser.add_argument("--validate", action="store_true", help="Validate the workflow definition only")
    args = parser.parse_args(argv)
    definition = load_definition(Path(__file__).with_name("workflow.json"))  # 课程 fixture 与脚本同目录，避免依赖当前 cwd。
    if args.validate:
        print(
            json.dumps(
                {
                    "status": "ok",
                    "name": definition.name,
                    "version": definition.version,
                    "steps": len(definition.steps),
                    "fingerprint": definition.fingerprint,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    print(json.dumps(run_demo(definition), ensure_ascii=False, indent=2, sort_keys=True))  # 输出可被测试或学习者逐项核对的证据。
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        raise SystemExit(1) from exc
