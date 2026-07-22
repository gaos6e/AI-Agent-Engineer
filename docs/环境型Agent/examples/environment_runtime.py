"""Deterministic control-plane simulator for environment agents.

The example uses an in-memory adapter.  It demonstrates strict contracts,
authenticated checkpoints, bounded proposals, adapter-owned receipts, and
reconciliation without invoking a browser, desktop, shell, network, or model.
"""

from __future__ import annotations  # 延后解析类型，令本地教学脚本的类型引用保持轻量。

import copy  # 记录前深拷贝外部输入，避免调用方改写运行时证据。
import hashlib  # 计算内容、状态和意图摘要。
import hmac  # 校验审批、复核和检查点的真实性。
import json  # 严格解析合同，并输出可审阅的离线报告。
import secrets  # 生成不可预测的沙箱实例标识和演示密钥。
import sys  # 提供脚本直接运行的退出入口。
import time  # 默认可信时钟以毫秒表达审批的墙钟过期时间。
from dataclasses import asdict, dataclass, field  # 将可检查的运行状态明确建模为数据类。
from pathlib import Path, PurePosixPath  # 限制教学文件路径为 POSIX 相对路径。
from typing import Any, Callable  # 不可信 JSON 和可注入时钟都要在运行时验证。


SCHEMA_VERSION = 2  # fixture、检查点和恢复逻辑共享的显式合同版本。
PERMISSIONS = {"workspace.read", "workspace.write", "tests.run"}  # 最小权限白名单。
ACTION_KINDS = {"read_file", "write_file", "run_tests", "finish", "cancel"}  # 运行时只接受固定动作集合。
TERMINAL_PHASES = {"completed", "cancelled", "failed"}  # 终态禁止再次提案或执行。
ACTIVE_PHASES = {"running", "needs_review"}  # 复核冻结仍是活跃运行，而不是静默失败。
PRECONDITIONS = {"environment_version_matches"}  # 非取消动作必须携带的乐观并发条件。
RISK_FOR_KIND = {
    "read_file": "read_only",
    "write_file": "reversible_write",
    "run_tests": "verification",
    "finish": "control",
    "cancel": "control",
}
HEX_64 = set("0123456789abcdef")
APPROVAL_PAYLOAD_KEYS = {
    "approver_id",
    "task_id",
    "run_id",
    "policy_version",
    "action_id",
    "idempotency_key",
    "intent_digest",
    "environment_version",
    "environment_instance_id",
    "state_fingerprint",
    "environment_generation",
    "expires_at_proposal",
    "expires_at_unix_ms",
    "nonce",
}
RECONCILIATION_PAYLOAD_KEYS = {
    "reviewer_id",
    "task_id",
    "run_id",
    "policy_version",
    "action_id",
    "idempotency_key",
    "pending_intent_digest",
    "observed_intent_digest",
    "observed_receipt_fingerprint",
    "environment_version",
    "decision",
    "nonce",
}


class EnvironmentAgentError(RuntimeError):
    """Base class for explicit runtime failures."""


class ContractError(EnvironmentAgentError):
    """Input does not satisfy a declared contract."""


class PermissionDenied(EnvironmentAgentError):
    """The proposal is valid but not authorized."""


class ApprovalError(EnvironmentAgentError):
    """Required approval is absent, stale, expired, or mismatched."""


class ReviewRequired(EnvironmentAgentError):
    """A receipt conflict froze the run until a trusted reviewer resolves it."""


class StaleObservation(EnvironmentAgentError):
    """The proposal was built against an old environment version."""


class IdempotencyConflict(EnvironmentAgentError):
    """One idempotency key was reused for a different mutation intent."""


class CheckpointError(EnvironmentAgentError):
    """A checkpoint is malformed, unauthenticated, or inconsistent."""


class TerminalStateError(EnvironmentAgentError):
    """A proposal cannot proceed because the run is terminal."""


class VerificationError(EnvironmentAgentError):
    """Completion lacks current external evidence."""


class SimulatedCrash(EnvironmentAgentError):
    """The adapter committed, but the runtime receipt was not persisted."""


@dataclass
class CheckpointGenerationStore:
    """External high-water marks required to reject authenticated rollback."""

    high_water_marks: dict[str, int] = field(default_factory=dict)  # 存在运行时外部，才可抵抗已认证旧检查点回滚。

    @staticmethod
    def scope(task_id: str, run_id: str, environment_instance_id: str) -> str:
        return canonical_json(
            {
                "task_id": task_id,
                "run_id": run_id,
                "environment_instance_id": environment_instance_id,
            }
        )

    def issue(
        self,
        task_id: str,
        run_id: str,
        environment_instance_id: str,
        current_generation: int,
    ) -> int:
        scope = self.scope(task_id, run_id, environment_instance_id)  # 代际高水位按任务、运行与具体环境隔离。
        stored = self.high_water_marks.get(scope, 0)  # 当前状态必须与外部记录连续。
        require(
            current_generation == stored,
            "runtime checkpoint generation differs from external high-water mark",
            error_type=CheckpointError,
        )
        generation = stored + 1  # 发放单调增加的代次，而不是由检查点内容自行声明。
        self.high_water_marks[scope] = generation  # 先推进外部高水位，再允许序列化。
        return generation

    def verify(
        self,
        task_id: str,
        run_id: str,
        environment_instance_id: str,
        generation: int,
    ) -> None:
        scope = self.scope(task_id, run_id, environment_instance_id)  # 恢复时必须回到同一个外部作用域。
        require(
            is_int(generation) and generation >= 1,
            "checkpoint generation is invalid",
            error_type=CheckpointError,
        )
        require(
            self.high_water_marks.get(scope) == generation,
            "checkpoint is stale or the external high-water mark is unavailable",
            error_type=CheckpointError,
        )


def require(
    condition: bool,
    message: str,
    *,
    error_type: type[EnvironmentAgentError] = ContractError,
) -> None:
    """Enforce an invariant in normal and ``python -O`` execution."""
    if not condition:
        raise error_type(message)  # 不使用 assert，确保 python -O 下合同仍然生效。


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))  # 固定字节表示是摘要和 HMAC 的前提。


def sha256_json(value: Any) -> str:
    """Return a corruption checksum; this is not an authenticity proof."""
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()  # 校验和检测损坏，不证明来源身份。


def _hmac_json(value: Any, signing_key: bytes) -> str:
    _validate_signing_key(signing_key)  # 检查点密钥与审批权威密钥具有不同的验证边界。
    return hmac.new(
        signing_key,
        canonical_json(value).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _validate_authority_key(signing_key: bytes) -> None:
    require(
        isinstance(signing_key, bytes) and len(signing_key) >= 32,
        "authority signing_key must contain at least 32 bytes",
        error_type=ApprovalError,
    )


def _authority_hmac(value: Any, signing_key: bytes) -> str:
    _validate_authority_key(signing_key)  # 低熵或过短权威密钥不能签发控制面证据。
    return hmac.new(
        signing_key,
        canonical_json(value).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def signed_approval(
    *,
    approver_id: str,
    task_id: str,
    run_id: str,
    policy_version: str,
    action_id: str,
    idempotency_key: str | None,
    intent_digest: str,
    environment_version: int,
    environment_instance_id: str,
    state_fingerprint: str,
    environment_generation: int,
    expires_at_proposal: int,
    expires_at_unix_ms: int,
    nonce: str,
    signing_key: bytes,
) -> dict[str, Any]:
    """Create a signed control-plane approval outside the model action schema."""
    payload = {
        "approver_id": nonempty_text(approver_id, "approver_id"),
        "task_id": nonempty_text(task_id, "approval task_id"),
        "run_id": nonempty_text(run_id, "approval run_id"),
        "policy_version": nonempty_text(
            policy_version, "approval policy_version"
        ),
        "action_id": nonempty_text(action_id, "approval action_id"),
        "idempotency_key": idempotency_key,
        "intent_digest": intent_digest,
        "environment_version": environment_version,
        "environment_instance_id": nonempty_text(
            environment_instance_id, "approval environment_instance_id"
        ),
        "state_fingerprint": state_fingerprint,
        "environment_generation": environment_generation,
        "expires_at_proposal": expires_at_proposal,
        "expires_at_unix_ms": expires_at_unix_ms,
        "nonce": nonempty_text(nonce, "approval nonce"),
    }
    require(
        idempotency_key is None
        or isinstance(idempotency_key, str) and bool(idempotency_key.strip()),
        "invalid approval idempotency_key",
        error_type=ApprovalError,
    )
    require(_is_hex64(intent_digest), "invalid approval intent_digest", error_type=ApprovalError)
    require(_is_hex64(state_fingerprint), "invalid approval state_fingerprint", error_type=ApprovalError)
    require(
        is_int(environment_version) and environment_version >= 0,
        "invalid approval environment_version",
        error_type=ApprovalError,
    )
    require(
        is_int(expires_at_proposal) and expires_at_proposal >= 1,
        "invalid approval expiry",
        error_type=ApprovalError,
    )
    require(
        is_int(environment_generation) and environment_generation >= 0,
        "invalid approval environment_generation",
        error_type=ApprovalError,
    )
    require(
        is_int(expires_at_unix_ms) and expires_at_unix_ms >= 1,
        "invalid approval wall-clock expiry",
        error_type=ApprovalError,
    )
    return {"payload": payload, "hmac_sha256": _authority_hmac(payload, signing_key)}


def signed_reconciliation(
    *,
    reviewer_id: str,
    task_id: str,
    run_id: str,
    policy_version: str,
    action_id: str,
    idempotency_key: str,
    pending_intent_digest: str,
    observed_intent_digest: str,
    observed_receipt_fingerprint: str,
    environment_version: int,
    decision: str,
    nonce: str,
    signing_key: bytes,
) -> dict[str, Any]:
    """Sign a human decision for one frozen receipt-conflict case."""
    require(decision in {"replan", "abort"}, "invalid reconciliation decision", error_type=ApprovalError)
    payload = {
        "reviewer_id": nonempty_text(reviewer_id, "reviewer_id"),
        "task_id": nonempty_text(task_id, "reconciliation task_id"),
        "run_id": nonempty_text(run_id, "reconciliation run_id"),
        "policy_version": nonempty_text(
            policy_version, "reconciliation policy_version"
        ),
        "action_id": nonempty_text(action_id, "reconciliation action_id"),
        "idempotency_key": nonempty_text(
            idempotency_key, "reconciliation idempotency_key"
        ),
        "pending_intent_digest": pending_intent_digest,
        "observed_intent_digest": observed_intent_digest,
        "observed_receipt_fingerprint": observed_receipt_fingerprint,
        "environment_version": environment_version,
        "decision": decision,
        "nonce": nonempty_text(nonce, "reconciliation nonce"),
    }
    require(
        _is_hex64(pending_intent_digest) and _is_hex64(observed_intent_digest),
        "invalid reconciliation intent digest",
        error_type=ApprovalError,
    )
    require(
        _is_hex64(observed_receipt_fingerprint),
        "invalid observed receipt fingerprint",
        error_type=ApprovalError,
    )
    require(
        is_int(environment_version) and environment_version >= 0,
        "invalid reconciliation environment_version",
        error_type=ApprovalError,
    )
    return {"payload": payload, "hmac_sha256": _authority_hmac(payload, signing_key)}


def _validate_signing_key(signing_key: bytes) -> None:
    require(
        isinstance(signing_key, bytes) and len(signing_key) >= 32,
        "checkpoint signing_key must contain at least 32 bytes",
        error_type=CheckpointError,
    )


def _is_hex64(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and set(value) <= HEX_64
    )


def _reject_constant(value: str) -> None:
    raise ContractError(f"non-finite JSON number is forbidden: {value}")


def _object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_loads(raw: str) -> Any:
    try:
        return json.loads(
            raw,
            object_pairs_hook=_object_without_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise ContractError(
            f"invalid JSON at line {exc.lineno}: {exc.msg}"
        ) from exc


def exact_keys(value: dict[str, Any], required: set[str], label: str) -> None:
    missing = required - set(value)
    unknown = set(value) - required
    require(not missing, f"{label} missing keys: {sorted(missing)}")
    require(not unknown, f"{label} has unknown keys: {sorted(unknown)}")


def is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def nonempty_text(value: Any, label: str, maximum: int = 200) -> str:
    require(isinstance(value, str) and bool(value.strip()), f"{label} must be non-empty")
    require(len(value) <= maximum, f"{label} exceeds {maximum} characters")
    return value


def _validate_signed_envelope(
    value: Any,
    *,
    label: str,
    payload_keys: set[str],
) -> dict[str, Any]:
    require(isinstance(value, dict), f"{label} must be an object", error_type=ApprovalError)
    exact_keys(value, {"payload", "hmac_sha256"}, label)
    payload = value["payload"]
    require(isinstance(payload, dict), f"{label} payload must be an object", error_type=ApprovalError)
    exact_keys(payload, payload_keys, f"{label} payload")
    require(_is_hex64(value["hmac_sha256"]), f"invalid {label} HMAC", error_type=ApprovalError)
    return payload


def validate_path(value: Any) -> str:
    path_text = nonempty_text(value, "path", maximum=300)
    require("\\" not in path_text and "\x00" not in path_text, "path must be safe POSIX text")
    path = PurePosixPath(path_text)
    require(not path.is_absolute(), "absolute paths are forbidden")
    require(".." not in path.parts and "." not in path.parts, "path traversal is forbidden")
    require(str(path) == path_text, "path must use a canonical relative form")
    return path_text


def validate_string_map(value: Any, label: str) -> dict[str, str]:
    require(isinstance(value, dict), f"{label} must be an object")
    result: dict[str, str] = {}
    for raw_path, content in value.items():
        path = validate_path(raw_path)
        require(isinstance(content, str), f"{label}[{path}] must be a string")
        result[path] = content
    return result


def validate_unique_text_list(
    value: Any,
    label: str,
    *,
    allowed: set[str] | None = None,
    allow_empty: bool = False,
) -> list[str]:
    require(isinstance(value, list), f"{label} must be an array")
    require(allow_empty or bool(value), f"{label} must be non-empty")
    items = [nonempty_text(item, f"{label} item") for item in value]
    require(len(set(items)) == len(items), f"{label} values must be unique")
    if allowed is not None:
        require(set(items) <= allowed, f"{label} contains an unsupported value")
    return items


@dataclass(frozen=True)
class Scenario:
    task_id: str
    task_version: str
    policy_version: str
    initial_files: dict[str, str]
    expected_files: dict[str, str]
    permissions: frozenset[str]
    allowed_paths: frozenset[str]
    allowed_test_targets: frozenset[str]
    approval_required_actions: frozenset[str]
    max_steps: int
    max_proposals: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,  # fixture 反序列化时拒绝不兼容结构。
            "task_id": self.task_id,
            "task_version": self.task_version,
            "policy_version": self.policy_version,
            "initial_files": dict(self.initial_files),
            "expected_files": dict(self.expected_files),
            "permissions": sorted(self.permissions),
            "allowed_paths": sorted(self.allowed_paths),
            "allowed_test_targets": sorted(self.allowed_test_targets),
            "approval_required_actions": sorted(self.approval_required_actions),
            "max_steps": self.max_steps,
            "max_proposals": self.max_proposals,
        }

    def fingerprint(self) -> str:
        return sha256_json(self.to_dict())  # 场景/策略变更会使旧检查点不能恢复。

    @classmethod
    def from_dict(cls, value: Any) -> "Scenario":
        require(isinstance(value, dict), "fixture must be a JSON object")  # 把 fixture 当作不可信合同输入。
        exact_keys(
            value,
            {
                "schema_version",
                "task_id",
                "task_version",
                "policy_version",
                "initial_files",
                "expected_files",
                "permissions",
                "allowed_paths",
                "allowed_test_targets",
                "approval_required_actions",
                "max_steps",
                "max_proposals",
            },
            "fixture",
        )
        require(value["schema_version"] == SCHEMA_VERSION, "unsupported fixture schema")
        task_id = nonempty_text(value["task_id"], "task_id")
        task_version = nonempty_text(value["task_version"], "task_version")
        policy_version = nonempty_text(value["policy_version"], "policy_version")
        initial = validate_string_map(value["initial_files"], "initial_files")
        expected = validate_string_map(value["expected_files"], "expected_files")
        permissions = validate_unique_text_list(
            value["permissions"], "permissions", allowed=PERMISSIONS, allow_empty=True
        )
        allowed_paths = [validate_path(item) for item in validate_unique_text_list(
            value["allowed_paths"], "allowed_paths"
        )]
        allowed = set(allowed_paths)
        require(set(initial) <= allowed, "initial_files escaped allowed_paths")  # 初始状态也不能越出策略边界。
        require(set(expected) <= allowed, "expected_files escaped allowed_paths")  # 验证目标同样只能声明允许路径。
        test_targets = validate_unique_text_list(
            value["allowed_test_targets"], "allowed_test_targets"
        )
        approval_actions = validate_unique_text_list(
            value["approval_required_actions"],
            "approval_required_actions",
            allowed=ACTION_KINDS,
            allow_empty=True,
        )
        max_steps = value["max_steps"]
        max_proposals = value["max_proposals"]
        require(is_int(max_steps) and 1 <= max_steps <= 100, "invalid max_steps")
        require(
            is_int(max_proposals) and 1 <= max_proposals <= 500,
            "invalid max_proposals",
        )
        require(max_proposals >= max_steps, "max_proposals must be at least max_steps")  # 每个执行步骤至少需要一次提案。
        return cls(
            task_id,
            task_version,
            policy_version,
            initial,
            expected,
            frozenset(permissions),
            frozenset(allowed),
            frozenset(test_targets),
            frozenset(approval_actions),
            max_steps,
            max_proposals,
        )


def load_scenario(path: Path) -> Scenario:
    return Scenario.from_dict(strict_loads(path.read_text(encoding="utf-8")))  # 先拒绝重复键/非标准常量，再构造不可变场景。


@dataclass(frozen=True)
class Action:
    action_id: str
    kind: str
    arguments: dict[str, Any]
    idempotency_key: str | None
    environment_version: int
    preconditions: tuple[str, ...]
    risk: str
    deadline_proposal: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "kind": self.kind,
            "arguments": copy.deepcopy(self.arguments),  # 动作快照不与调用方共享可变字典。
            "idempotency_key": self.idempotency_key,
            "environment_version": self.environment_version,
            "preconditions": list(self.preconditions),
            "risk": self.risk,
            "deadline_proposal": self.deadline_proposal,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "Action":
        require(isinstance(value, dict), "action must be an object")  # Agent 产出的动作在此处接受逐字段审计。
        exact_keys(
            value,
            {
                "action_id",
                "kind",
                "arguments",
                "idempotency_key",
                "environment_version",
                "preconditions",
                "risk",
                "deadline_proposal",
            },
            "action",
        )
        action_id = nonempty_text(value["action_id"], "action_id")
        kind = value["kind"]
        require(isinstance(kind, str) and kind in ACTION_KINDS, "unknown action kind")
        arguments = value["arguments"]
        require(isinstance(arguments, dict), "arguments must be an object")
        required_arguments = {
            "read_file": {"path"},
            "write_file": {"path", "content"},
            "run_tests": {"target"},
            "finish": set(),
            "cancel": {"reason"},
        }
        exact_keys(arguments, required_arguments[kind], f"{kind}.arguments")
        if "path" in arguments:
            validate_path(arguments["path"])
        if kind == "write_file":
            require(isinstance(arguments["content"], str), "write content must be text")
        if kind == "run_tests":
            nonempty_text(arguments["target"], "run_tests target")
        if kind == "cancel":
            nonempty_text(arguments["reason"], "cancel reason")
        key = value["idempotency_key"]
        require(key is None or isinstance(key, str) and bool(key.strip()), "invalid idempotency_key")
        require((kind == "write_file") == (key is not None), "only write_file requires idempotency_key")  # 可变操作必须有幂等意图键。
        environment_version = value["environment_version"]
        require(is_int(environment_version) and environment_version >= 0, "invalid environment_version")
        preconditions = validate_unique_text_list(
            value["preconditions"],
            "preconditions",
            allowed=PRECONDITIONS,
            allow_empty=kind == "cancel",
        )
        if kind != "cancel":
            require(set(preconditions) == PRECONDITIONS, "environment version precondition is required")  # 避免把过期观察直接变成执行。
        risk = value["risk"]
        require(risk == RISK_FOR_KIND[kind], "risk does not match action kind")
        deadline = value["deadline_proposal"]
        require(is_int(deadline) and 1 <= deadline <= 10000, "invalid deadline_proposal")
        return cls(
            action_id,
            kind,
            copy.deepcopy(arguments),
            key,
            environment_version,
            tuple(preconditions),
            risk,
            deadline,
        )

    def intent_digest(self) -> str:
        return sha256_json(
            {"kind": self.kind, "arguments": self.arguments, "risk": self.risk}  # 幂等比较绑定意图与风险，不只绑定动作名。
        )


def _validate_receipt_map(value: Any, label: str) -> dict[str, dict[str, Any]]:
    require(isinstance(value, dict), f"{label} must be an object")
    result: dict[str, dict[str, Any]] = {}
    for key, receipt in value.items():
        nonempty_text(key, f"{label} key")
        require(isinstance(receipt, dict), f"{label}[{key}] must be an object")
        exact_keys(
            receipt,
            {
                "adapter_namespace",
                "receipt_version",
                "receipt_id",
                "intent_digest",
                "result",
            },
            f"{label}[{key}]",
        )
        nonempty_text(receipt["adapter_namespace"], "receipt adapter_namespace")
        require(receipt["receipt_version"] == 1, "unsupported receipt version")
        require(_is_hex64(receipt["receipt_id"]), "invalid receipt id")
        require(_is_hex64(receipt["intent_digest"]), "invalid receipt intent_digest")
        payload = receipt["result"]
        require(isinstance(payload, dict), "receipt result must be an object")
        exact_keys(payload, {"path", "version", "content_sha256"}, "receipt result")
        validate_path(payload["path"])
        require(is_int(payload["version"]) and payload["version"] >= 1, "invalid receipt version")
        require(_is_hex64(payload["content_sha256"]), "invalid receipt content hash")
        result[key] = copy.deepcopy(receipt)
    return result


def receipt_fingerprint(idempotency_key: str, receipt: dict[str, Any]) -> str:
    """Bind the key and complete canonical adapter receipt."""
    return sha256_json(
        {"idempotency_key": idempotency_key, "receipt": receipt}
    )


@dataclass
class Sandbox:
    files: dict[str, str]
    expected_files: dict[str, str]
    version: int = 0
    write_count: int = 0
    adapter_receipts: dict[str, dict[str, Any]] = field(default_factory=dict)  # 权威适配器拥有副作用回执。
    instance_id: str = field(default_factory=lambda: f"sandbox-{secrets.token_hex(16)}")  # 防止跨环境混用审批或检查点。
    generation: int = 0

    def state_fingerprint(self) -> str:
        """Fingerprint authoritative mutable state, excluding instance identity."""
        return sha256_json(  # 与审批/待执行意图绑定的完整可变环境快照。
            {
                "files": self.files,
                "version": self.version,
                "write_count": self.write_count,
                "adapter_receipts": self.adapter_receipts,
                "generation": self.generation,
            }
        )

    def read_file(self, path: str) -> dict[str, Any]:
        require(path in self.files, f"file does not exist: {path}")  # 读取不存在文件是可说明的合同错误。
        content = self.files[path]
        return {
            "path": path,
            "content": content,
            "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),  # 内容摘要而非原文可进入审计事件。
            "version": self.version,  # 观察结果必须携带其对应的环境版本。
        }

    def write_file(
        self,
        path: str,
        content: str,
        idempotency_key: str,
        intent_digest: str,
    ) -> tuple[dict[str, Any], bool]:
        cached = self.adapter_receipts.get(idempotency_key)  # 先查询权威适配器，再决定是否真正写入。
        if cached is not None:
            require(
                cached["intent_digest"] == intent_digest,
                "adapter idempotency key conflicts with another intent",
                error_type=IdempotencyConflict,
            )
            return copy.deepcopy(cached["result"]), True  # 同意图重放返回旧回执，绝不重复写。
        self.files[path] = content  # 模拟适配器提交副作用的唯一位置。
        self.version += 1  # 每次真实写入推进乐观并发版本。
        self.write_count += 1  # 计数可证明示例没有重复提交。
        self.generation += 1  # 状态代次配合指纹防止审批绑定到陈旧沙箱。
        result = {
            "path": path,
            "version": self.version,
            "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        }
        receipt = {
            "adapter_namespace": "memory-file-adapter/v1",
            "receipt_version": 1,
            "receipt_id": sha256_json(
                {
                    "instance_id": self.instance_id,
                    "generation": self.generation,
                    "idempotency_key": idempotency_key,
                    "intent_digest": intent_digest,
                }
            ),
            "intent_digest": intent_digest,
            "result": copy.deepcopy(result),
        }
        self.adapter_receipts[idempotency_key] = receipt  # 回执先由适配器持有，运行时随后才镜像它。
        return result, False

    def query_receipt(self, key: str, intent_digest: str) -> dict[str, Any] | None:
        cached = self.adapter_receipts.get(key)  # 崩溃恢复先问副作用系统“是否已经提交”。
        if cached is None:
            return None
        require(
            cached["intent_digest"] == intent_digest,
            "adapter receipt conflicts with pending intent",
            error_type=IdempotencyConflict,
        )
        return copy.deepcopy(cached["result"])  # 返回副本，避免协调器篡改权威证据。

    def run_tests(self, target: str) -> dict[str, Any]:
        mismatches = sorted(  # 此离线测试器只比较期望文件，真实系统应调用受限验证器。
            path
            for path, expected in self.expected_files.items()
            if self.files.get(path) != expected
        )
        return {
            "target": target,
            "passed": not mismatches,  # 通过结果与当前环境版本一起记录，不能跨写入复用。
            "mismatches": mismatches,
            "environment_version": self.version,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "files": dict(self.files),
            "expected_files": dict(self.expected_files),
            "version": self.version,
            "write_count": self.write_count,
            "adapter_receipts": copy.deepcopy(self.adapter_receipts),
            "instance_id": self.instance_id,
            "generation": self.generation,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "Sandbox":
        require(isinstance(value, dict), "sandbox must be an object", error_type=CheckpointError)
        try:
            exact_keys(
                value,
                {
                    "files",
                    "expected_files",
                    "version",
                    "write_count",
                    "adapter_receipts",
                    "instance_id",
                    "generation",
                },
                "sandbox",
            )
            files = validate_string_map(value["files"], "sandbox.files")
            expected = validate_string_map(value["expected_files"], "sandbox.expected_files")
            require(is_int(value["version"]) and value["version"] >= 0, "invalid sandbox version")
            require(is_int(value["write_count"]) and value["write_count"] >= 0, "invalid write_count")
            nonempty_text(value["instance_id"], "sandbox instance_id")
            require(is_int(value["generation"]) and value["generation"] >= 0, "invalid sandbox generation")
            receipts = _validate_receipt_map(value["adapter_receipts"], "adapter_receipts")
            require(value["write_count"] == len(receipts), "write_count must match adapter receipts")
            require(value["version"] == value["write_count"], "sandbox version must match write_count")
            require(value["generation"] == value["write_count"], "sandbox generation must match write_count")
        except ContractError as exc:
            raise CheckpointError(str(exc)) from exc
        return cls(
            files,
            expected,
            value["version"],
            value["write_count"],
            receipts,
            value["instance_id"],
            value["generation"],
        )


@dataclass
class RunState:
    run_id: str
    task_id: str
    phase: str = "running"
    proposal_count: int = 0
    step_count: int = 0
    verified_version: int = -1
    terminal_reason: str | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    idempotency_receipts: dict[str, dict[str, Any]] = field(default_factory=dict)
    pending_intents: dict[str, dict[str, Any]] = field(default_factory=dict)  # 已接受但尚未确认的写入意图。
    approval_records: dict[str, dict[str, Any]] = field(default_factory=dict)
    consumed_approval_nonces: list[str] = field(default_factory=list)
    review_cases: dict[str, dict[str, Any]] = field(default_factory=dict)
    consumed_review_nonces: list[str] = field(default_factory=list)
    quarantined_idempotency_keys: list[str] = field(default_factory=list)  # 人工复核过的冲突键不能再次自动使用。
    checkpoint_generation: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Any) -> "RunState":
        require(isinstance(value, dict), "state must be an object", error_type=CheckpointError)  # 恢复的内部状态也绝不默认可信。
        try:
            exact_keys(
                value,
                {
                    "run_id",
                    "task_id",
                    "phase",
                    "proposal_count",
                    "step_count",
                    "verified_version",
                    "terminal_reason",
                    "events",
                    "idempotency_receipts",
                    "pending_intents",
                    "approval_records",
                    "consumed_approval_nonces",
                    "review_cases",
                    "consumed_review_nonces",
                    "quarantined_idempotency_keys",
                    "checkpoint_generation",
                },
                "state",
            )
            nonempty_text(value["run_id"], "run_id")
            nonempty_text(value["task_id"], "task_id")
            require(value["phase"] in ACTIVE_PHASES | TERMINAL_PHASES, "invalid phase")
            require(is_int(value["proposal_count"]) and value["proposal_count"] >= 0, "invalid proposal_count")
            require(is_int(value["step_count"]) and value["step_count"] >= 0, "invalid step_count")
            require(is_int(value["verified_version"]) and value["verified_version"] >= -1, "invalid verified_version")
            require(value["terminal_reason"] is None or isinstance(value["terminal_reason"], str), "invalid terminal_reason")
            require(isinstance(value["events"], list), "events must be an array")
            events: list[dict[str, Any]] = []
            for index, event in enumerate(value["events"], start=1):
                require(isinstance(event, dict), "event must be an object")
                exact_keys(
                    event,
                    {"sequence", "proposal_count", "action_id", "kind", "outcome", "environment_version", "detail"},
                    "event",
                )
                require(event["sequence"] == index, "event sequence must be contiguous")  # 检查点不允许悄悄删掉审计事件。
                require(is_int(event["proposal_count"]) and event["proposal_count"] >= 0, "invalid event proposal_count")
                require(event["action_id"] is None or isinstance(event["action_id"], str), "invalid event action_id")
                require(event["kind"] is None or isinstance(event["kind"], str), "invalid event kind")
                nonempty_text(event["outcome"], "event outcome")
                require(is_int(event["environment_version"]) and event["environment_version"] >= 0, "invalid event version")
                require(isinstance(event["detail"], dict), "event detail must be an object")
                events.append(copy.deepcopy(event))
            receipts = _validate_receipt_map(value["idempotency_receipts"], "runtime receipts")
            require(isinstance(value["pending_intents"], dict), "pending_intents must be an object")
            pending: dict[str, dict[str, Any]] = {}
            for action_id, item in value["pending_intents"].items():
                nonempty_text(action_id, "pending action id")
                require(isinstance(item, dict), "pending intent must be an object")
                exact_keys(
                    item,
                    {
                        "action",
                        "intent_digest",
                        "approval_evidence",
                        "environment_instance_id",
                        "state_fingerprint",
                        "environment_generation",
                        "expected_post_state_fingerprint",
                    },
                    "pending intent",
                )
                pending_action = Action.from_dict(item["action"])
                require(pending_action.action_id == action_id, "pending action id mismatch")
                require(pending_action.kind == "write_file", "only writes may be pending")  # 只有副作用写入需要两阶段确认。
                require(item["intent_digest"] == pending_action.intent_digest(), "pending digest mismatch")
                approval_evidence = item["approval_evidence"]
                if approval_evidence is not None:
                    require(isinstance(approval_evidence, dict), "pending approval evidence must be an object")
                    exact_keys(approval_evidence, {"payload", "hmac_sha256"}, "pending approval evidence")
                    require(isinstance(approval_evidence["payload"], dict), "pending approval payload must be an object")
                    exact_keys(approval_evidence["payload"], APPROVAL_PAYLOAD_KEYS, "pending approval payload")
                    require(_is_hex64(approval_evidence["hmac_sha256"]), "invalid pending approval HMAC")
                nonempty_text(item["environment_instance_id"], "pending environment_instance_id")
                require(_is_hex64(item["state_fingerprint"]), "invalid pending state fingerprint")
                require(
                    is_int(item["environment_generation"])
                    and item["environment_generation"] >= 0,
                    "invalid pending environment generation",
                )
                require(
                    _is_hex64(item["expected_post_state_fingerprint"]),
                    "invalid pending expected post-state fingerprint",
                )
                pending[action_id] = copy.deepcopy(item)
            require(isinstance(value["approval_records"], dict), "approval_records must be an object")
            approvals: dict[str, dict[str, Any]] = {}
            for nonce, envelope in value["approval_records"].items():
                nonempty_text(nonce, "approval record nonce")
                require(isinstance(envelope, dict), "approval record must be an object")
                exact_keys(envelope, {"payload", "hmac_sha256"}, "approval record")
                payload = envelope["payload"]
                require(isinstance(payload, dict), "approval payload must be an object")
                exact_keys(payload, APPROVAL_PAYLOAD_KEYS, "approval payload")
                require(payload["nonce"] == nonce, "approval nonce key mismatch")
                require(_is_hex64(envelope["hmac_sha256"]), "invalid approval HMAC")
                approvals[nonce] = copy.deepcopy(envelope)
            consumed_approvals = validate_unique_text_list(
                value["consumed_approval_nonces"],
                "consumed_approval_nonces",
                allow_empty=True,
            )
            require(
                not (set(approvals) & set(consumed_approvals)),
                "approval nonce cannot be both registered and consumed",
            )
            require(isinstance(value["review_cases"], dict), "review_cases must be an object")
            review_cases: dict[str, dict[str, Any]] = {}
            for action_id, case in value["review_cases"].items():
                nonempty_text(action_id, "review case action id")
                require(isinstance(case, dict), "review case must be an object")
                exact_keys(
                    case,
                    {
                        "status",
                        "pending_intent",
                        "observed_receipt",
                        "observed_receipt_fingerprint",
                        "resolution",
                    },
                    "review case",
                )
                require(case["status"] in {"open", "resolved"}, "invalid review case status")
                pending_item = case["pending_intent"]
                require(isinstance(pending_item, dict), "review pending intent must be an object")
                exact_keys(
                    pending_item,
                    {
                        "action",
                        "intent_digest",
                        "approval_evidence",
                        "environment_instance_id",
                        "state_fingerprint",
                        "environment_generation",
                        "expected_post_state_fingerprint",
                    },
                    "review pending intent",
                )
                review_action = Action.from_dict(pending_item["action"])
                require(review_action.action_id == action_id, "review action id mismatch")
                require(
                    pending_item["intent_digest"] == review_action.intent_digest(),
                    "review pending digest mismatch",
                )
                key = review_action.idempotency_key
                require(key is not None, "review write lacks idempotency key")
                _validate_receipt_map({key: case["observed_receipt"]}, "review receipt")
                require(
                    case["observed_receipt_fingerprint"]
                    == receipt_fingerprint(key, case["observed_receipt"]),
                    "review receipt fingerprint mismatch",
                )
                resolution = case["resolution"]
                if case["status"] == "open":
                    require(resolution is None, "open review case has resolution")
                else:
                    require(isinstance(resolution, dict), "resolved review case lacks evidence")
                    exact_keys(resolution, {"payload", "hmac_sha256"}, "review resolution")
                    require(isinstance(resolution["payload"], dict), "review resolution payload must be an object")
                    exact_keys(
                        resolution["payload"],
                        RECONCILIATION_PAYLOAD_KEYS,
                        "review resolution payload",
                    )
                    require(_is_hex64(resolution["hmac_sha256"]), "invalid review resolution HMAC")
                review_cases[action_id] = copy.deepcopy(case)
            consumed_reviews = validate_unique_text_list(
                value["consumed_review_nonces"],
                "consumed_review_nonces",
                allow_empty=True,
            )
            quarantined_keys = validate_unique_text_list(
                value["quarantined_idempotency_keys"],
                "quarantined_idempotency_keys",
                allow_empty=True,
            )
            require(
                is_int(value["checkpoint_generation"])
                and value["checkpoint_generation"] >= 0,
                "invalid checkpoint_generation",
            )
        except ContractError as exc:
            raise CheckpointError(str(exc)) from exc
        return cls(
            value["run_id"],
            value["task_id"],
            value["phase"],
            value["proposal_count"],
            value["step_count"],
            value["verified_version"],
            value["terminal_reason"],
            events,
            receipts,
            pending,
            approvals,
            consumed_approvals,
            review_cases,
            consumed_reviews,
            quarantined_keys,
            value["checkpoint_generation"],
        )


@dataclass(frozen=True)
class Proposal:
    action: Action
    outcome: str
    result: dict[str, Any] | None = None


class EnvironmentRuntime:
    """Validate, authorize, execute, record, verify, and recover actions."""

    def __init__(
        self,
        scenario: Scenario,
        *,
        run_id: str = "run-demo",
        sandbox: Sandbox | None = None,
        state: RunState | None = None,
        trusted_approval_keys: dict[str, bytes] | None = None,
        trusted_reviewer_keys: dict[str, bytes] | None = None,
        generation_store: CheckpointGenerationStore | None = None,
        clock: Callable[[], int] | None = None,
        _pending_precondition_sandbox: Sandbox | None = None,
    ) -> None:
        self.scenario = scenario  # 场景固定权限、目标和预算；运行中不可由 Agent 改写。
        self.sandbox = sandbox or Sandbox(
            files=dict(scenario.initial_files),
            expected_files=dict(scenario.expected_files),
        )
        self.state = state or RunState(run_id=run_id, task_id=scenario.task_id)  # 恢复时传入已验证状态，新运行则创建空状态。
        self.generation_store = generation_store or CheckpointGenerationStore()  # 外部高水位是恢复安全的一部分。
        self._clock = clock or (lambda: time.time_ns() // 1_000_000)  # 测试可注入确定时钟。
        self.trusted_approval_keys = self._validate_key_map(
            trusted_approval_keys or {}, "approval"
        )
        self.trusted_reviewer_keys = self._validate_key_map(
            trusted_reviewer_keys
            if trusted_reviewer_keys is not None
            else self.trusted_approval_keys,
            "reviewer",
        )
        self._validate_cross_state(  # 任何构造/恢复路径都在可执行前校验跨对象不变量。
            pending_precondition_sandbox=_pending_precondition_sandbox
        )

    def now_ms(self) -> int:
        value = self._clock()  # 控制面时间与 Agent 自报时间分离。
        require(is_int(value) and value >= 0, "trusted clock returned an invalid time")
        return value

    @staticmethod
    def _validate_key_map(value: dict[str, bytes], label: str) -> dict[str, bytes]:
        require(isinstance(value, dict), f"trusted {label} keys must be an object")
        result: dict[str, bytes] = {}
        for authority_id, key in value.items():
            nonempty_text(authority_id, f"trusted {label} id")
            _validate_authority_key(key)
            result[authority_id] = key  # 仅显式配置的权威才可签发控制面记录。
        return result

    @staticmethod
    def _validate_pending_precondition(
        item: dict[str, Any],
        sandbox: Sandbox,
        *,
        error_type: type[EnvironmentAgentError],
    ) -> None:
        """Require the exact environment against which a pending write was built."""
        action_value = Action.from_dict(item["action"])  # 再解析保存的动作，避免检查点绕开当前合同。
        require(
            item["environment_instance_id"] == sandbox.instance_id,
            "pending environment instance mismatch",
            error_type=error_type,
        )
        require(
            item["state_fingerprint"] == sandbox.state_fingerprint(),  # 版本相等不足以排除未计数的环境漂移。
            "pending state fingerprint mismatch",
            error_type=error_type,
        )
        require(
            item["environment_generation"] == sandbox.generation,
            "pending environment generation mismatch",
            error_type=error_type,
        )
        require(
            action_value.environment_version == sandbox.version,
            "pending action version differs from current environment",
            error_type=error_type,
        )

    @staticmethod
    def _validate_pending_reconciliation_state(
        item: dict[str, Any],
        sandbox: Sandbox,
    ) -> None:
        """Accept only the saved pre-state or one adapter-owned write transition."""
        action_value = Action.from_dict(item["action"])
        key = action_value.idempotency_key
        require(key is not None, "pending write lacks idempotency key")
        require(
            item["environment_instance_id"] == sandbox.instance_id,
            "pending environment instance mismatch",
            error_type=StaleObservation,
        )
        if (
            item["state_fingerprint"] == sandbox.state_fingerprint()
            and item["environment_generation"] == sandbox.generation
            and action_value.environment_version == sandbox.version
        ):
            return
        receipt = sandbox.adapter_receipts.get(key)  # 只有适配器回执能证明“崩溃前已提交”。
        require(
            receipt is not None
            and sandbox.generation == item["environment_generation"] + 1
            and sandbox.version == action_value.environment_version + 1,
            "environment no longer matches the pending write transition",
            error_type=StaleObservation,
        )
        if receipt["intent_digest"] == item["intent_digest"]:
            require(
                sandbox.state_fingerprint()
                == item["expected_post_state_fingerprint"],
                "committed pending write has unexpected post-state drift",
                error_type=StaleObservation,
            )

    def _validate_pending_approval(
        self,
        item: dict[str, Any],
        expected_sandbox: Sandbox,
        *,
        require_fresh: bool,
        validate_environment_state: bool = True,
        error_type: type[EnvironmentAgentError] = CheckpointError,
    ) -> None:
        action_value = Action.from_dict(item["action"])
        evidence = item["approval_evidence"]
        required = action_value.kind in self.scenario.approval_required_actions  # 当前策略决定是否必须保留审批证据。
        require(
            (evidence is not None) == required,
            "pending approval evidence does not match current policy",
            error_type=error_type,
        )
        if validate_environment_state:
            self._validate_pending_precondition(
                item,
                expected_sandbox,
                error_type=error_type,
            )
        else:
            require(
                item["environment_instance_id"] == expected_sandbox.instance_id,
                "pending environment instance mismatch",
                error_type=error_type,
            )
        if evidence is None:
            return
        payload = evidence["payload"]
        approver_id = payload["approver_id"]
        key = self.trusted_approval_keys.get(approver_id)  # 信任从本地配置的权威根开始，而非 payload 自称。
        require(
            key is not None,
            "pending approval signer trust root is unavailable",
            error_type=error_type,
        )
        require(
            hmac.compare_digest(
                evidence["hmac_sha256"], _authority_hmac(payload, key)
            ),
            "pending approval signature is invalid",
            error_type=error_type,
        )
        bindings = {  # 授权不是泛用令牌，必须绑定任务、意图和当时环境。
            "task_id": self.scenario.task_id,
            "run_id": self.state.run_id,
            "policy_version": self.scenario.policy_version,
            "action_id": action_value.action_id,
            "idempotency_key": action_value.idempotency_key,
            "intent_digest": item["intent_digest"],
            "environment_version": action_value.environment_version,
            "environment_instance_id": item["environment_instance_id"],
            "state_fingerprint": item["state_fingerprint"],
            "environment_generation": item["environment_generation"],
        }
        require(
            all(payload[name] == value for name, value in bindings.items()),
            "pending approval binding mismatch",
            error_type=error_type,
        )
        require(
            payload["nonce"] in self.state.consumed_approval_nonces,
            "pending approval nonce was not consumed",
            error_type=error_type,
        )
        require(
            payload["nonce"] not in self.state.approval_records,
            "pending approval nonce is still registered",
            error_type=error_type,
        )
        require(
            payload["expires_at_proposal"] >= self.state.proposal_count,
            "pending approval proposal expiry has passed",
            error_type=error_type,
        )
        if require_fresh:
            require(
                payload["expires_at_unix_ms"] > self.now_ms(),
                "pending approval wall-clock expiry has passed",
                error_type=error_type,
            )

    def _validate_cross_state(
        self, *, pending_precondition_sandbox: Sandbox | None = None
    ) -> None:
        approved_sandbox = pending_precondition_sandbox or self.sandbox
        require(self.state.task_id == self.scenario.task_id, "checkpoint task mismatch", error_type=CheckpointError)
        require(self.sandbox.expected_files == self.scenario.expected_files, "checkpoint verifier mismatch", error_type=CheckpointError)
        require(set(self.sandbox.files) <= self.scenario.allowed_paths, "sandbox escaped allowed_paths", error_type=CheckpointError)
        require(self.state.proposal_count <= self.scenario.max_proposals, "proposal count exceeds policy", error_type=CheckpointError)
        require(self.state.step_count <= self.scenario.max_steps, "step count exceeds policy", error_type=CheckpointError)
        require(self.state.verified_version <= self.sandbox.version, "verified version is in the future", error_type=CheckpointError)
        require(
            all(event["environment_version"] <= self.sandbox.version for event in self.state.events),
            "trace refers to a future environment version",
            error_type=CheckpointError,
        )
        require(
            all(event["proposal_count"] <= self.state.proposal_count for event in self.state.events),
            "trace refers to a future proposal",
            error_type=CheckpointError,
        )
        if self.state.verified_version >= 0:
            require(
                any(
                    event["kind"] == "run_tests"
                    and event["outcome"] == "executed"
                    and event["environment_version"] == self.state.verified_version
                    and event["detail"].get("passed") is True
                    and event["detail"].get("environment_version")
                    == self.state.verified_version
                    for event in self.state.events
                ),
                "verified state lacks passing trace evidence",
                error_type=CheckpointError,
            )
        open_cases = {
            action_id
            for action_id, case in self.state.review_cases.items()
            if case["status"] == "open"
        }
        resolution_nonces: set[str] = set()
        resolved_keys: set[str] = set()
        for action_id, case in self.state.review_cases.items():
            pending_evidence = case["pending_intent"]
            reviewed_action = Action.from_dict(pending_evidence["action"])
            reviewed_key = reviewed_action.idempotency_key
            require(reviewed_key is not None, "review case lacks idempotency key", error_type=CheckpointError)
            if case["status"] == "resolved":
                resolved_keys.add(reviewed_key)
            observed = case["observed_receipt"]
            require(
                self.sandbox.adapter_receipts.get(reviewed_key) == observed,
                "authoritative adapter receipt drifted from review evidence",
                error_type=CheckpointError,
            )
            require(
                case["observed_receipt_fingerprint"]
                == receipt_fingerprint(reviewed_key, observed),
                "review receipt fingerprint is invalid",
                error_type=CheckpointError,
            )
            require(
                observed["intent_digest"] != pending_evidence["intent_digest"],
                "review case does not contain a receipt intent conflict",
                error_type=CheckpointError,
            )
            if case["status"] == "resolved":
                resolution = case["resolution"]
                require(resolution is not None, "resolved case lacks evidence", error_type=CheckpointError)
                payload = resolution["payload"]
                reviewer_id = payload["reviewer_id"]
                reviewer_key = self.trusted_reviewer_keys.get(reviewer_id)
                require(reviewer_key is not None, "checkpoint reviewer is not trusted", error_type=CheckpointError)
                require(
                    hmac.compare_digest(
                        resolution["hmac_sha256"],
                        _authority_hmac(payload, reviewer_key),
                    ),
                    "checkpoint reconciliation signature is invalid",
                    error_type=CheckpointError,
                )
                require(payload["task_id"] == self.scenario.task_id, "checkpoint reconciliation task mismatch", error_type=CheckpointError)
                require(payload["run_id"] == self.state.run_id, "checkpoint reconciliation run mismatch", error_type=CheckpointError)
                require(payload["policy_version"] == self.scenario.policy_version, "checkpoint reconciliation policy mismatch", error_type=CheckpointError)
                require(payload["action_id"] == action_id, "checkpoint reconciliation action mismatch", error_type=CheckpointError)
                require(payload["idempotency_key"] == reviewed_key, "checkpoint reconciliation key mismatch", error_type=CheckpointError)
                require(payload["pending_intent_digest"] == pending_evidence["intent_digest"], "checkpoint pending digest mismatch", error_type=CheckpointError)
                require(payload["observed_intent_digest"] == observed["intent_digest"], "checkpoint observed digest mismatch", error_type=CheckpointError)
                require(
                    payload["observed_receipt_fingerprint"]
                    == case["observed_receipt_fingerprint"],
                    "checkpoint observed receipt fingerprint mismatch",
                    error_type=CheckpointError,
                )
                require(payload["environment_version"] <= self.sandbox.version, "checkpoint reconciliation version is in the future", error_type=CheckpointError)
                resolution_nonces.add(payload["nonce"])
                require(action_id not in self.state.pending_intents, "resolved review case is still pending", error_type=CheckpointError)
                if payload["decision"] == "abort":
                    require(self.state.phase == "failed", "aborted review did not fail closed", error_type=CheckpointError)
                    require(self.state.terminal_reason == "receipt_conflict_reviewed", "aborted review reason mismatch", error_type=CheckpointError)
        require(
            resolution_nonces == set(self.state.consumed_review_nonces),
            "consumed review nonces do not match resolution evidence",
            error_type=CheckpointError,
        )
        require(
            resolved_keys == set(self.state.quarantined_idempotency_keys),
            "quarantined keys do not match resolved review cases",
            error_type=CheckpointError,
        )
        require(
            open_cases <= set(self.state.pending_intents),
            "open review case lacks pending intent",
            error_type=CheckpointError,
        )
        for action_id in open_cases:
            require(
                self.state.review_cases[action_id]["pending_intent"]
                == self.state.pending_intents[action_id],
                "review evidence differs from pending intent",
                error_type=CheckpointError,
            )
        if self.state.phase == "running":
            require(self.state.terminal_reason is None, "running state has terminal reason", error_type=CheckpointError)
            require(not open_cases, "running state has an open review case", error_type=CheckpointError)
        elif self.state.phase == "needs_review":
            require(
                self.state.terminal_reason == "receipt_intent_conflict",
                "review state has an invalid reason",
                error_type=CheckpointError,
            )
            require(bool(open_cases), "review state lacks an open case", error_type=CheckpointError)
        else:
            require(bool(self.state.terminal_reason), "terminal state lacks reason", error_type=CheckpointError)
            require(not self.state.pending_intents, "terminal state has pending intent", error_type=CheckpointError)
            require(not open_cases, "terminal state has an open review case", error_type=CheckpointError)
        if self.state.phase == "completed":
            require(self.state.terminal_reason == "verified_outcome", "invalid completed reason", error_type=CheckpointError)
            require(self.state.verified_version == self.sandbox.version, "completed state lacks current verification", error_type=CheckpointError)
            require(self.sandbox.files == self.scenario.expected_files, "completed state has wrong outcome", error_type=CheckpointError)
            require(
                bool(self.state.events)
                and self.state.events[-1]["outcome"] == "completed"
                and self.state.events[-1]["kind"] == "finish",
                "completed state lacks a terminal trace event",
                error_type=CheckpointError,
            )
        for key, receipt in self.state.idempotency_receipts.items():
            require(self.sandbox.adapter_receipts.get(key) == receipt, "runtime receipt lacks adapter evidence", error_type=CheckpointError)
        for action_id, item in self.state.pending_intents.items():
            self._validate_pending_approval(
                item,
                approved_sandbox,
                # Expired evidence remains authenticated historical evidence.
                # The execution gate rechecks freshness and keeps it frozen.
                require_fresh=False,
                validate_environment_state=action_id not in open_cases,
                error_type=CheckpointError,
            )
        for nonce, envelope in self.state.approval_records.items():
            payload = envelope["payload"]
            approver_id = payload["approver_id"]
            key = self.trusted_approval_keys.get(approver_id)
            require(key is not None, "checkpoint approval signer is not trusted", error_type=CheckpointError)
            require(
                hmac.compare_digest(
                    envelope["hmac_sha256"], _authority_hmac(payload, key)
                ),
                "checkpoint approval signature is invalid",
                error_type=CheckpointError,
            )
            require(payload["nonce"] == nonce, "checkpoint approval nonce mismatch", error_type=CheckpointError)
            require(payload["task_id"] == self.scenario.task_id, "checkpoint approval task mismatch", error_type=CheckpointError)
            require(payload["run_id"] == self.state.run_id, "checkpoint approval run mismatch", error_type=CheckpointError)
            require(payload["policy_version"] == self.scenario.policy_version, "checkpoint approval policy mismatch", error_type=CheckpointError)

    def _record(
        self,
        outcome: str,
        *,
        action_id: str | None = None,
        kind: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self.state.events.append(  # 统一写入不可变式审计轨迹；detail 先深拷贝。
            {
                "sequence": len(self.state.events) + 1,
                "proposal_count": self.state.proposal_count,
                "action_id": action_id,
                "kind": kind,
                "outcome": outcome,
                "environment_version": self.sandbox.version,
                "detail": copy.deepcopy(detail or {}),
            }
        )

    def _fail(self, reason: str) -> None:
        if self.state.phase in TERMINAL_PHASES:
            return
        require(not self.state.pending_intents, "cannot fail while an intent is pending")
        self.state.phase = "failed"  # 失败只在不存在悬而未决写入时才可最终化。
        self.state.terminal_reason = reason
        self._record(reason)

    def _close_if_proposal_budget_spent(self) -> None:
        if (
            self.state.phase == "running"
            and not self.state.pending_intents
            and self.state.proposal_count >= self.scenario.max_proposals
        ):
            self._fail("proposal_budget_exhausted")

    def _ensure_can_propose(self) -> None:
        require(
            self.state.phase != "needs_review",
            "run is frozen for receipt-conflict review",
            error_type=ReviewRequired,
        )
        require(
            self.state.phase not in TERMINAL_PHASES,
            f"run is terminal: {self.state.phase}",
            error_type=TerminalStateError,
        )
        if self.state.proposal_count >= self.scenario.max_proposals:  # 拒绝无限思考或反复试探。
            self._fail("proposal_budget_exhausted")
            raise TerminalStateError("proposal budget exhausted")

    @staticmethod
    def _raw_identity(raw_action: Any) -> tuple[str | None, str | None]:
        if not isinstance(raw_action, dict):
            return None, None
        action_id = raw_action.get("action_id")
        kind = raw_action.get("kind")
        return (
            action_id if isinstance(action_id, str) else None,
            kind if isinstance(kind, str) else None,
        )

    def _authorize(self, action: Action) -> None:
        permission_for = {
            "read_file": "workspace.read",
            "write_file": "workspace.write",
            "run_tests": "tests.run",
        }
        permission = permission_for.get(action.kind)  # 每种动作映射到最小所需能力。
        if permission is not None:
            require(permission in self.scenario.permissions, f"permission denied: {permission}", error_type=PermissionDenied)
        path = action.arguments.get("path")
        if path is not None:
            require(path in self.scenario.allowed_paths, f"path is outside scope: {path}", error_type=PermissionDenied)
        if action.kind == "run_tests":  # 验证入口也属于策略面，不能让 Agent 任意执行。
            require(action.arguments["target"] in self.scenario.allowed_test_targets, "test target is outside scope", error_type=PermissionDenied)

    def register_approval(self, envelope: dict[str, Any]) -> None:
        """Accept an approval only through the trusted control-plane seam."""
        payload = _validate_signed_envelope(  # 先校验信封形状，再读取其中任何控制字段。
            envelope,
            label="approval",
            payload_keys=APPROVAL_PAYLOAD_KEYS,
        )
        approver_id = nonempty_text(payload["approver_id"], "approver_id")
        key = self.trusted_approval_keys.get(approver_id)  # 只接受当前运行配置的可信审批人。
        require(key is not None, "approval signer is not trusted", error_type=ApprovalError)
        require(
            hmac.compare_digest(
                envelope["hmac_sha256"], _authority_hmac(payload, key)
            ),
            "approval signature is invalid",
            error_type=ApprovalError,
        )
        require(payload["task_id"] == self.scenario.task_id, "approval task mismatch", error_type=ApprovalError)
        require(payload["run_id"] == self.state.run_id, "approval run mismatch", error_type=ApprovalError)
        require(payload["policy_version"] == self.scenario.policy_version, "approval policy mismatch", error_type=ApprovalError)
        nonempty_text(payload["action_id"], "approval action_id")
        approval_key = payload["idempotency_key"]
        require(
            approval_key is None
            or isinstance(approval_key, str) and bool(approval_key.strip()),
            "invalid approval idempotency_key",
            error_type=ApprovalError,
        )
        require(_is_hex64(payload["intent_digest"]), "invalid approval intent_digest", error_type=ApprovalError)
        require(
            is_int(payload["environment_version"])
            and payload["environment_version"] >= 0,
            "invalid approval environment_version",
            error_type=ApprovalError,
        )
        nonempty_text(
            payload["environment_instance_id"],
            "approval environment_instance_id",
        )
        require(
            _is_hex64(payload["state_fingerprint"]),
            "invalid approval state_fingerprint",
            error_type=ApprovalError,
        )
        require(
            is_int(payload["environment_generation"])
            and payload["environment_generation"] >= 0,
            "invalid approval environment_generation",
            error_type=ApprovalError,
        )
        require(
            is_int(payload["expires_at_proposal"])
            and payload["expires_at_proposal"] >= 1,
            "invalid approval expiry",
            error_type=ApprovalError,
        )
        require(
            is_int(payload["expires_at_unix_ms"])
            and payload["expires_at_unix_ms"] > self.now_ms(),
            "approval wall-clock expiry has passed",
            error_type=ApprovalError,
        )
        nonce = nonempty_text(payload["nonce"], "approval nonce")
        require(
            nonce not in self.state.approval_records
            and nonce not in self.state.consumed_approval_nonces,
            "approval nonce was already registered or consumed",
            error_type=ApprovalError,
        )
        self.state.approval_records[nonce] = copy.deepcopy(envelope)  # 登记后由具体动作消费一次。

    def _validate_approval(
        self,
        action: Action,
        *,
        expected_nonce: str | None = None,
    ) -> dict[str, Any] | None:
        if action.kind not in self.scenario.approval_required_actions:  # 不需要审批的动作不应假装携带授权。
            return None
        candidates = [
            (nonce, envelope)
            for nonce, envelope in self.state.approval_records.items()
            if envelope["payload"]["action_id"] == action.action_id
            and (expected_nonce is None or nonce == expected_nonce)
        ]
        require(bool(candidates), "action requires a registered approval", error_type=ApprovalError)
        nonce, envelope = candidates[0]
        approval = envelope["payload"]
        require(
            approval["idempotency_key"] == action.idempotency_key,
            "approval idempotency key mismatch",
            error_type=ApprovalError,
        )
        require(
            approval["intent_digest"] == action.intent_digest(),
            "approval intent mismatch",
            error_type=ApprovalError,
        )
        require(
            approval["environment_version"] == action.environment_version
            == self.sandbox.version,
            "approval state version is stale",
            error_type=ApprovalError,
        )
        require(
            approval["environment_instance_id"] == self.sandbox.instance_id,
            "approval environment instance mismatch",
            error_type=ApprovalError,
        )
        require(
            approval["state_fingerprint"] == self.sandbox.state_fingerprint(),
            "approval state fingerprint is stale",
            error_type=ApprovalError,
        )
        require(
            approval["environment_generation"] == self.sandbox.generation,
            "approval environment generation is stale",
            error_type=ApprovalError,
        )
        require(
            approval["expires_at_proposal"] >= self.state.proposal_count,
            "approval expired",
            error_type=ApprovalError,
        )
        require(
            approval["expires_at_unix_ms"] > self.now_ms(),
            "approval wall-clock expiry has passed",
            error_type=ApprovalError,
        )
        self.state.approval_records.pop(nonce)  # 授权一次性消费，禁止对多次写入重放。
        self.state.consumed_approval_nonces.append(nonce)  # 保留已消费 nonce，拒绝之后重新登记。
        return copy.deepcopy(envelope)

    def refresh_pending_approval(
        self,
        action_id: str,
        envelope: dict[str, Any],
    ) -> None:
        """Replace frozen approval evidence with one fresh, exactly bound record."""
        require(
            self.state.phase == "running",
            "approval refresh requires a running task",
            error_type=ApprovalError,
        )
        item = self.state.pending_intents.get(action_id)
        require(item is not None, "unknown pending action", error_type=ApprovalError)
        action_value = Action.from_dict(item["action"])
        require(
            action_value.kind in self.scenario.approval_required_actions
            and item["approval_evidence"] is not None,
            "pending action does not require refreshed approval",
            error_type=ApprovalError,
        )
        self._validate_pending_precondition(
            item,
            self.sandbox,
            error_type=ApprovalError,
        )
        self.register_approval(envelope)  # 新凭据先经过同一受信控制面入口。
        nonce = envelope["payload"]["nonce"]
        try:
            fresh_evidence = self._validate_approval(
                action_value,
                expected_nonce=nonce,
            )
        except EnvironmentAgentError:
            self.state.approval_records.pop(nonce, None)
            raise
        require(fresh_evidence is not None, "approval refresh produced no evidence")
        superseded = copy.deepcopy(item["approval_evidence"])
        item["approval_evidence"] = fresh_evidence
        self._validate_pending_approval(
            item,
            self.sandbox,
            require_fresh=True,
            error_type=ApprovalError,
        )
        self._record(
            "approval_refreshed",
            action_id=action_id,
            kind=action_value.kind,
            detail={
                "approver_id": fresh_evidence["payload"]["approver_id"],
                "superseded_approval_evidence": superseded,
            },
        )

    def propose(self, raw_action: dict[str, Any]) -> Proposal:
        self._ensure_can_propose()  # 在解析 Agent 输出前先检查终态、复核冻结和提案预算。
        self.state.proposal_count += 1  # 被拒动作也消耗提案预算，避免恶意/失控循环。
        raw_id, raw_kind = self._raw_identity(raw_action)
        try:
            require(
                not self.state.pending_intents,
                "resolve the pending intent before proposing another action",
            )
            action_value = Action.from_dict(raw_action)  # 严格契约将自由文本决策收窄为可执行动作。
            require(
                action_value.deadline_proposal >= self.state.proposal_count,
                "proposal deadline expired",
            )
            require(
                all(event["action_id"] != action_value.action_id for event in self.state.events if event["action_id"]),
                "action_id must be unique",
            )
            self._authorize(action_value)  # 语法合法不等同于拥有执行权限。

            digest = action_value.intent_digest()  # 后续授权、回执和冲突检测均绑定同一语义摘要。
            if action_value.kind != "cancel":
                require(
                    action_value.environment_version == self.sandbox.version,
                    "proposal was built from a stale environment version",
                    error_type=StaleObservation,
                )
            approval_evidence = self._validate_approval(action_value)  # 提案阶段消耗精确匹配的授权。
            if action_value.kind == "write_file":
                key = action_value.idempotency_key
                require(key is not None, "write requires idempotency")
                require(
                    key not in self.state.quarantined_idempotency_keys,
                    "idempotency key was quarantined after human review",
                    error_type=IdempotencyConflict,
                )
                known = self.state.idempotency_receipts.get(key)  # 运行时镜像只作为缓存证据。
                adapter_known = self.sandbox.adapter_receipts.get(key)  # 适配器回执才是权威事实。
                if known is not None:
                    require(
                        adapter_known is not None,
                        "runtime receipt lacks authoritative adapter evidence",
                        error_type=IdempotencyConflict,
                    )
                    require(
                        known == adapter_known,
                        "runtime receipt differs from authoritative adapter receipt",
                        error_type=IdempotencyConflict,
                    )
                if adapter_known is not None:
                    require(
                        adapter_known["intent_digest"] == digest,
                        "idempotency key conflicts with another intent",
                        error_type=IdempotencyConflict,
                    )
                    self.state.idempotency_receipts[key] = copy.deepcopy(adapter_known)  # 用权威数据修复运行时镜像。
                    result = copy.deepcopy(adapter_known["result"])
                    result["replayed"] = True
                    self._record("replayed", action_id=action_value.action_id, kind=action_value.kind, detail=result)
                    self._close_if_proposal_budget_spent()
                    return Proposal(action_value, "replayed", result)

            if self.state.step_count >= self.scenario.max_steps:
                self._fail("step_budget_exhausted")
                raise TerminalStateError("step budget exhausted")

            if action_value.kind == "write_file":
                expected_post_sandbox = Sandbox.from_dict(self.sandbox.to_dict())  # 预演唯一允许的写入后状态。
                expected_post_sandbox.write_file(
                    action_value.arguments["path"],
                    action_value.arguments["content"],
                    key,
                    digest,
                )
                self.state.pending_intents[action_value.action_id] = {  # 写入先冻结意图，等待适配器提交/确认。
                    "action": action_value.to_dict(),
                    "intent_digest": digest,
                    "approval_evidence": approval_evidence,
                    "environment_instance_id": self.sandbox.instance_id,
                    "state_fingerprint": self.sandbox.state_fingerprint(),
                    "environment_generation": self.sandbox.generation,
                    "expected_post_state_fingerprint": (
                        expected_post_sandbox.state_fingerprint()
                    ),
                }
                self._record("accepted_pending", action_id=action_value.action_id, kind=action_value.kind)  # 崩溃恢复可从此证据开始对账。
                return Proposal(action_value, "pending")
            return Proposal(action_value, "ready")
        except TerminalStateError:
            raise
        except EnvironmentAgentError as exc:
            outcome = {
                PermissionDenied: "permission_denied",
                ApprovalError: "approval_rejected",
                StaleObservation: "stale_observation",
                IdempotencyConflict: "idempotency_conflict",
            }.get(type(exc), "contract_rejected")
            self._record(
                outcome,
                action_id=raw_id,
                kind=raw_kind,
                detail={"error_type": type(exc).__name__},
            )
            self._close_if_proposal_budget_spent()
            raise

    def _consume_step(self) -> None:
        if self.state.step_count >= self.scenario.max_steps:
            require(not self.state.pending_intents, "pending action reached step budget")
            self._fail("step_budget_exhausted")
            raise TerminalStateError("step budget exhausted")
        self.state.step_count += 1  # 只在真正尝试执行前消耗外部动作预算。

    def execute_pending(
        self,
        action_id: str,
        *,
        crash_after_commit: bool = False,
    ) -> dict[str, Any]:
        require(
            self.state.phase != "needs_review",
            "pending action is frozen for review",
            error_type=ReviewRequired,
        )
        require(
            self.state.phase not in TERMINAL_PHASES,
            f"run is terminal: {self.state.phase}",
            error_type=TerminalStateError,
        )
        item = self.state.pending_intents.get(action_id)  # 只能执行已冻结、未被其他动作覆盖的意图。
        require(item is not None, "unknown pending action")
        action_value = Action.from_dict(item["action"])
        try:
            self._validate_pending_precondition(
                item,
                self.sandbox,
                error_type=StaleObservation,
            )
        except StaleObservation as exc:
            self._record(
                "stale_observation",
                action_id=action_id,
                kind=action_value.kind,
                detail={"error_type": type(exc).__name__},
            )
            self.state.pending_intents.pop(action_id, None)  # 环境已变，丢弃陈旧计划而不是强行写入。
            self._close_if_proposal_budget_spent()
            raise
        if item["approval_evidence"] is not None:
            try:
                self._validate_pending_approval(
                    item,
                    self.sandbox,
                    require_fresh=True,
                    validate_environment_state=False,
                    error_type=ApprovalError,
                )
            except ApprovalError as exc:
                self._record(
                    "approval_rejected",
                    action_id=action_id,
                    kind=action_value.kind,
                    detail={
                        "error_type": type(exc).__name__,
                        "pending_frozen": True,
                    },
                )
                # Retain the authenticated evidence so a fresh, exactly bound
                # control-plane approval can replace it without losing history.
                raise
        self._consume_step()  # 审批和前置条件仍新鲜后，才允许触发副作用。
        key = action_value.idempotency_key
        require(key is not None, "pending write lacks idempotency key")
        try:
            result, replayed = self.sandbox.write_file(  # 真实提交/重放判定由适配器执行。
                action_value.arguments["path"],
                action_value.arguments["content"],
                key,
                item["intent_digest"],
            )
        except IdempotencyConflict as exc:
            observed = self.sandbox.adapter_receipts.get(key)
            require(observed is not None, "receipt conflict lacks adapter evidence")
            self._enter_receipt_review(action_id, item, observed, exc)
            raise
        if crash_after_commit:  # 模拟最关键故障窗：外部已提交，运行时尚未持久化回执。
            raise SimulatedCrash("adapter committed before runtime receipt persistence")
        receipt = copy.deepcopy(self.sandbox.adapter_receipts[key])
        self.state.idempotency_receipts[key] = receipt  # 只镜像适配器实际给出的回执。
        self.state.pending_intents.pop(action_id, None)  # 有了权威回执后才能清除未决意图。
        returned = copy.deepcopy(result)
        returned["replayed"] = replayed
        self._record("replayed" if replayed else "executed", action_id=action_id, kind=action_value.kind, detail=returned)
        self._close_if_proposal_budget_spent()
        return returned

    def reconcile_pending(self, action_id: str) -> dict[str, Any]:
        require(
            self.state.phase != "needs_review",
            "pending action is frozen for review",
            error_type=ReviewRequired,
        )
        require(
            self.state.phase not in TERMINAL_PHASES,
            f"run is terminal: {self.state.phase}",
            error_type=TerminalStateError,
        )
        item = self.state.pending_intents.get(action_id)
        require(item is not None, "unknown pending action")
        action_value = Action.from_dict(item["action"])
        key = action_value.idempotency_key
        require(key is not None, "pending write lacks idempotency key")
        try:
            self._validate_pending_reconciliation_state(item, self.sandbox)
        except StaleObservation as exc:
            self._record(
                "stale_observation",
                action_id=action_id,
                kind=action_value.kind,
                detail={"error_type": type(exc).__name__},
            )
            self.state.pending_intents.pop(action_id, None)
            self._close_if_proposal_budget_spent()
            raise
        try:
            receipt = self.sandbox.query_receipt(key, item["intent_digest"])  # 从权威端查询，而非猜测崩溃前结果。
        except IdempotencyConflict as exc:
            observed = self.sandbox.adapter_receipts.get(key)
            require(observed is not None, "receipt conflict lacks adapter evidence")
            self._enter_receipt_review(action_id, item, observed, exc)
            raise
        if receipt is None:  # 未提交才可安全重走同一冻结意图。
            return self.execute_pending(action_id)
        self._consume_step()
        self.state.idempotency_receipts[key] = copy.deepcopy(self.sandbox.adapter_receipts[key])
        self.state.pending_intents.pop(action_id, None)
        returned = copy.deepcopy(receipt)
        returned["replayed"] = True
        self._record("reconciled", action_id=action_id, kind=action_value.kind, detail=returned)
        self._close_if_proposal_budget_spent()
        return returned

    def _enter_receipt_review(
        self,
        action_id: str,
        pending_intent: dict[str, Any],
        observed_receipt: dict[str, Any],
        error: IdempotencyConflict,
    ) -> None:
        """Freeze an ambiguous write while retaining both competing claims."""
        pending_action = Action.from_dict(pending_intent["action"])
        idempotency_key = pending_action.idempotency_key
        require(idempotency_key is not None, "reviewed write lacks idempotency key")
        self.state.review_cases[action_id] = {  # 同时保存待执行意图与观察到的回执，供人工举证。
            "status": "open",
            "pending_intent": copy.deepcopy(pending_intent),
            "observed_receipt": copy.deepcopy(observed_receipt),
            "observed_receipt_fingerprint": receipt_fingerprint(
                idempotency_key,
                observed_receipt,
            ),
            "resolution": None,
        }
        self.state.phase = "needs_review"  # 冲突时冻结运行；不能偏向先到或后到的结果。
        self.state.terminal_reason = "receipt_intent_conflict"
        self._record(
            "idempotency_conflict",
            action_id=action_id,
            kind="write_file",
            detail={
                "error_type": type(error).__name__,
                "expected_intent_digest": pending_intent["intent_digest"],
                "observed_intent_digest": observed_receipt["intent_digest"],
                "review_required": True,
            },
        )

    def resolve_receipt_conflict(
        self, envelope: dict[str, Any]
    ) -> dict[str, Any]:
        """Apply one authenticated human decision to an open conflict case."""
        require(
            self.state.phase == "needs_review",
            "run does not have an open receipt-conflict review",
            error_type=ReviewRequired,
        )
        payload = _validate_signed_envelope(  # 复核决定同样必须是已认证控制面消息。
            envelope,
            label="reconciliation",
            payload_keys=RECONCILIATION_PAYLOAD_KEYS,
        )
        reviewer_id = nonempty_text(payload["reviewer_id"], "reviewer_id")
        key = self.trusted_reviewer_keys.get(reviewer_id)  # 审批人与冲突复核人可以采用不同的信任根。
        require(key is not None, "reconciliation signer is not trusted", error_type=ApprovalError)
        require(
            hmac.compare_digest(
                envelope["hmac_sha256"], _authority_hmac(payload, key)
            ),
            "reconciliation signature is invalid",
            error_type=ApprovalError,
        )
        require(payload["task_id"] == self.scenario.task_id, "reconciliation task mismatch", error_type=ApprovalError)
        require(payload["run_id"] == self.state.run_id, "reconciliation run mismatch", error_type=ApprovalError)
        require(payload["policy_version"] == self.scenario.policy_version, "reconciliation policy mismatch", error_type=ApprovalError)
        nonce = nonempty_text(payload["nonce"], "reconciliation nonce")
        require(
            nonce not in self.state.consumed_review_nonces,
            "reconciliation nonce was already consumed",
            error_type=ApprovalError,
        )
        action_id = nonempty_text(payload["action_id"], "reconciliation action_id")
        case = self.state.review_cases.get(action_id)
        require(
            case is not None and case["status"] == "open",
            "reconciliation case is not open",
            error_type=ApprovalError,
        )
        pending = self.state.pending_intents.get(action_id)
        require(
            pending is not None and pending == case["pending_intent"],
            "pending reconciliation evidence changed",
            error_type=ApprovalError,
        )
        action_value = Action.from_dict(pending["action"])
        idempotency_key = action_value.idempotency_key
        require(idempotency_key is not None, "reviewed write lacks idempotency key")
        observed = case["observed_receipt"]
        current_receipt = self.sandbox.adapter_receipts.get(idempotency_key)
        require(
            current_receipt == observed,
            "authoritative receipt drifted after review began",
            error_type=ApprovalError,
        )
        require(
            case["observed_receipt_fingerprint"]
            == receipt_fingerprint(idempotency_key, current_receipt),
            "authoritative receipt fingerprint changed",
            error_type=ApprovalError,
        )
        require(payload["idempotency_key"] == idempotency_key, "reconciliation key mismatch", error_type=ApprovalError)
        require(payload["pending_intent_digest"] == pending["intent_digest"], "reconciliation pending digest mismatch", error_type=ApprovalError)
        require(payload["observed_intent_digest"] == observed["intent_digest"], "reconciliation observed digest mismatch", error_type=ApprovalError)
        require(
            payload["observed_receipt_fingerprint"]
            == case["observed_receipt_fingerprint"],
            "reconciliation receipt fingerprint mismatch",
            error_type=ApprovalError,
        )
        require(payload["environment_version"] == self.sandbox.version, "reconciliation environment changed", error_type=ApprovalError)
        require(payload["decision"] in {"replan", "abort"}, "invalid reconciliation decision", error_type=ApprovalError)

        self.state.consumed_review_nonces.append(nonce)  # 复核决定一次性消费，防止重放改变终态。
        case["status"] = "resolved"
        case["resolution"] = copy.deepcopy(envelope)
        self.state.pending_intents.pop(action_id)
        if idempotency_key not in self.state.quarantined_idempotency_keys:
            self.state.quarantined_idempotency_keys.append(idempotency_key)

        if payload["decision"] == "replan":
            self.state.phase = "running"  # replan 只允许生成新意图；旧幂等键已被隔离。
            self.state.terminal_reason = None
            outcome = "review_replanned"
        else:
            self.state.phase = "failed"  # abort 将冲突作为明确、可审计的终止原因。
            self.state.terminal_reason = "receipt_conflict_reviewed"
            outcome = "review_aborted"
        result = {
            "phase": self.state.phase,
            "decision": payload["decision"],
            "action_id": action_id,
            "quarantined_idempotency_key": idempotency_key,
        }
        self._record(
            outcome,
            action_id=action_id,
            kind="write_file",
            detail={**result, "reviewer_id": reviewer_id},
        )
        return copy.deepcopy(result)

    def _execute_ready(self, action_value: Action) -> dict[str, Any]:
        self._consume_step()  # 无需两阶段确认的动作也受同一执行预算限制。
        try:
            if action_value.kind == "read_file":
                result = self.sandbox.read_file(action_value.arguments["path"])
                detail = {key: value for key, value in result.items() if key != "content"}
                self._record("executed", action_id=action_value.action_id, kind=action_value.kind, detail=detail)
            elif action_value.kind == "run_tests":
                result = self.sandbox.run_tests(action_value.arguments["target"])
                if result["passed"]:
                    self.state.verified_version = self.sandbox.version
                self._record("executed", action_id=action_value.action_id, kind=action_value.kind, detail=result)
            elif action_value.kind == "finish":
                require(self.state.verified_version == self.sandbox.version, "current version lacks passing verification", error_type=VerificationError)  # 旧测试结果不能证明新版本。
                require(self.sandbox.files == self.scenario.expected_files, "final environment does not match expected outcome", error_type=VerificationError)  # 通过测试也须满足任务后置条件。
                self.state.phase = "completed"
                self.state.terminal_reason = "verified_outcome"
                result = {"phase": "completed", "reason": "verified_outcome", "environment_version": self.sandbox.version}
                self._record("completed", action_id=action_value.action_id, kind=action_value.kind, detail=result)
            else:
                require(action_value.kind == "cancel", "unhandled action kind")
                self.state.phase = "cancelled"
                self.state.terminal_reason = action_value.arguments["reason"]
                result = {"phase": "cancelled", "reason": self.state.terminal_reason}
                self._record("cancelled", action_id=action_value.action_id, kind=action_value.kind, detail=result)
        except EnvironmentAgentError as exc:
            self._record("execution_error", action_id=action_value.action_id, kind=action_value.kind, detail={"error_type": type(exc).__name__})
            self._close_if_proposal_budget_spent()
            raise
        self._close_if_proposal_budget_spent()
        return copy.deepcopy(result)

    def apply(self, raw_action: dict[str, Any]) -> dict[str, Any]:
        proposal = self.propose(raw_action)  # 为教学便利封装“提案—确认/执行”完整路径。
        if proposal.outcome == "replayed":
            require(proposal.result is not None, "replay lacks result")
            return copy.deepcopy(proposal.result)
        if proposal.outcome == "pending":
            return self.execute_pending(proposal.action.action_id)  # 写入经过冻结意图和适配器确认。
        return self._execute_ready(proposal.action)

    def checkpoint(self, signing_key: bytes) -> str:
        _validate_signing_key(signing_key)  # 校验检查点签名密钥，不与审批签名混用。
        # Validate both the public schema and cross-object invariants before an
        # external monotonic mark is advanced.  The final payload differs only
        # by the next integer generation, so post-issue serialization is
        # deterministic in this teaching runtime.
        Sandbox.from_dict(self.sandbox.to_dict())  # 序列化前再次验证公共沙箱合同。
        RunState.from_dict(self.state.to_dict())  # 序列化前再次验证运行状态合同。
        self._validate_cross_state()  # 字段各自合法仍不足以保证组合状态可恢复。
        preflight_payload = {
            "schema_version": SCHEMA_VERSION,
            "scenario_fingerprint": self.scenario.fingerprint(),
            "sandbox": self.sandbox.to_dict(),
            "state": self.state.to_dict(),
        }
        try:
            canonical_json(preflight_payload)
        except (TypeError, ValueError) as exc:
            raise CheckpointError("checkpoint payload is not serializable") from exc
        self.state.checkpoint_generation = self.generation_store.issue(  # 外部高水位先原子推进，抵抗合法旧快照回滚。
            self.scenario.task_id,
            self.state.run_id,
            self.sandbox.instance_id,
            self.state.checkpoint_generation,
        )
        payload = {
            "schema_version": SCHEMA_VERSION,
            "scenario_fingerprint": self.scenario.fingerprint(),
            "sandbox": self.sandbox.to_dict(),
            "state": self.state.to_dict(),
        }
        return canonical_json(
            {
                "payload": payload,
                "checksum_sha256": sha256_json(payload),  # 快速检测传输或存储损坏。
                "hmac_sha256": _hmac_json(payload, signing_key),  # 认证 payload 来源并防止未授权篡改。
            }
        )

    @staticmethod
    def _validate_external_sandbox_transition(
        checkpoint_sandbox: Sandbox,
        external_sandbox: Sandbox,
        state: RunState,
        scenario: Scenario,
    ) -> None:
        Sandbox.from_dict(external_sandbox.to_dict())
        require(
            external_sandbox.instance_id == checkpoint_sandbox.instance_id,
            "external environment instance differs from checkpoint",
            error_type=CheckpointError,
        )
        require(
            external_sandbox.expected_files == scenario.expected_files,
            "external verifier mismatch",
            error_type=CheckpointError,
        )
        if external_sandbox.to_dict() == checkpoint_sandbox.to_dict():  # 外部环境未改变时可直接恢复。
            return
        require(
            len(state.pending_intents) == 1,
            "external state drift is not one provable pending transition",
            error_type=CheckpointError,
        )
        item = next(iter(state.pending_intents.values()))
        action_value = Action.from_dict(item["action"])
        key = action_value.idempotency_key
        require(
            action_value.kind == "write_file" and key is not None,
            "external transition is not a pending write",
            error_type=CheckpointError,
        )
        expected = Sandbox.from_dict(checkpoint_sandbox.to_dict())  # 仅在检查点副本上重演唯一允许的未决写入。
        expected.write_file(
            action_value.arguments["path"],
            action_value.arguments["content"],
            key,
            item["intent_digest"],
        )
        require(
            external_sandbox.to_dict() == expected.to_dict(),
            "external state does not match the single authorized pending write",
            error_type=CheckpointError,
        )

    @classmethod
    def restore(
        cls,
        raw_checkpoint: str,
        scenario: Scenario,
        signing_key: bytes,
        *,
        external_sandbox: Sandbox | None = None,
        trusted_approval_keys: dict[str, bytes] | None = None,
        trusted_reviewer_keys: dict[str, bytes] | None = None,
        generation_store: CheckpointGenerationStore | None = None,
        clock: Callable[[], int] | None = None,
    ) -> "EnvironmentRuntime":
        _validate_signing_key(signing_key)  # 首先确保验证者拥有正确形态的检查点密钥。
        try:
            envelope = strict_loads(raw_checkpoint)  # 解析时拒绝重复键与非标准 JSON 常量。
            require(isinstance(envelope, dict), "checkpoint must be an object")
            exact_keys(envelope, {"payload", "checksum_sha256", "hmac_sha256"}, "checkpoint")
            payload = envelope["payload"]
            require(isinstance(payload, dict), "checkpoint payload must be an object")
            require(_is_hex64(envelope["checksum_sha256"]), "invalid checkpoint checksum")
            require(_is_hex64(envelope["hmac_sha256"]), "invalid checkpoint HMAC")
            require(envelope["checksum_sha256"] == sha256_json(payload), "checkpoint corruption detected")  # 先排除意外损坏。
            require(hmac.compare_digest(envelope["hmac_sha256"], _hmac_json(payload, signing_key)), "checkpoint authentication failed")  # 再确认来源与完整性。
            exact_keys(payload, {"schema_version", "scenario_fingerprint", "sandbox", "state"}, "payload")
            require(payload["schema_version"] == SCHEMA_VERSION, "unsupported checkpoint schema")
            require(payload["scenario_fingerprint"] == scenario.fingerprint(), "external scenario/task/policy version mismatch")  # 不能把旧权限/任务状态带入新场景。
            checkpoint_sandbox = Sandbox.from_dict(payload["sandbox"])
            state = RunState.from_dict(payload["state"])
            require(
                generation_store is not None,
                "restore requires an external checkpoint generation store",
                error_type=CheckpointError,
            )
            generation_store.verify(  # 恢复必须询问外部高水位，而不是只相信 checkpoint 内数字。
                scenario.task_id,
                state.run_id,
                checkpoint_sandbox.instance_id,
                state.checkpoint_generation,
            )
            sandbox = external_sandbox or checkpoint_sandbox  # 有真实外部环境时，以它为权威事实。
            if external_sandbox is not None:
                cls._validate_external_sandbox_transition(
                    checkpoint_sandbox,
                    external_sandbox,
                    state,
                    scenario,
                )
            return cls(
                scenario,
                sandbox=sandbox,
                state=state,
                trusted_approval_keys=trusted_approval_keys,
                trusted_reviewer_keys=trusted_reviewer_keys,
                generation_store=generation_store,
                clock=clock,
                _pending_precondition_sandbox=checkpoint_sandbox,
            )
        except CheckpointError:
            raise
        except ContractError as exc:
            raise CheckpointError(str(exc)) from exc


def action(
    action_id: str,
    kind: str,
    arguments: dict[str, Any],
    idempotency_key: str | None = None,
    *,
    environment_version: int = 0,
    deadline_proposal: int = 100,
) -> dict[str, Any]:
    return {  # 为 fixture/演示构造合同对象；生产端仍应由 Agent 显式生成并接受校验。
        "action_id": action_id,
        "kind": kind,
        "arguments": arguments,
        "idempotency_key": idempotency_key,
        "environment_version": environment_version,
        "preconditions": [] if kind == "cancel" else ["environment_version_matches"],
        "risk": RISK_FOR_KIND.get(kind, "unknown"),
        "deadline_proposal": deadline_proposal,
    }


def run_demo() -> dict[str, Any]:
    fixture = Path(__file__).with_name("environment_fixture.json")  # 不依赖调用者当前工作目录。
    scenario = load_scenario(fixture)  # fixture 同时提供权限、目标状态和预算。
    signing_key = secrets.token_bytes(32)  # 演示每次生成临时检查点密钥，不输出其内容。
    runtime = EnvironmentRuntime(scenario)  # 从受限初始沙箱启动。
    runtime.apply(action("a-1", "read_file", {"path": "app.py"}))
    runtime.apply(
        action(
            "a-2",
            "write_file",
            {"path": "app.py", "content": "print('ready')\n"},
            "write-app-ready",
        )
    )
    restored = EnvironmentRuntime.restore(  # 在写入后模拟进程替换与受认证恢复。
        runtime.checkpoint(signing_key),
        scenario,
        signing_key,
        generation_store=runtime.generation_store,
    )
    restored.apply(  # 测试证据绑定到写入后的环境版本。
        action("a-3", "run_tests", {"target": "unit"}, environment_version=1)
    )
    restored.apply(action("a-4", "finish", {}, environment_version=1))  # finish 会重新验证当前版本与预期后置条件。
    return {
        "phase": restored.state.phase,
        "terminal_reason": restored.state.terminal_reason,
        "environment_version": restored.sandbox.version,
        "write_count": restored.sandbox.write_count,
        "proposal_count": restored.state.proposal_count,
        "event_count": len(restored.state.events),
    }


def main() -> int:
    print(json.dumps(run_demo(), ensure_ascii=False, indent=2))  # 输出不含密钥的可复查终态摘要。
    return 0


if __name__ == "__main__":
    sys.exit(main())
