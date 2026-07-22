"""Validate a deliberately small A2A 1.0 teaching contract offline.

This module is not an implementation of the complete A2A specification and is
not a substitute for an official SDK, Inspector, TCK, or cross-vendor test.
"""

from __future__ import annotations  # 延迟求值类型注解，方便在教学代码中使用现代联合类型写法

import argparse  # 解析 --cases 离线 fixture 路径
import base64  # 校验 JSON 中 raw Part 的 base64 编码内容
import binascii  # 捕获 base64 解码器抛出的底层格式错误
import json  # 严格读取 A2A 教学场景并输出命令行结果
from pathlib import Path  # 安全、跨平台地表示 fixture 文件路径
from typing import Any  # JSON 解析后的值可能属于多种 Python 类型
from urllib.parse import urlparse  # 分解 URL，检查 Agent Card endpoint 是否为绝对地址


CORE_BINDINGS = {"JSONRPC", "GRPC", "HTTP+JSON"}  # 课程基线认可的核心 protocolBinding 名称
CONTENT_FIELDS = {"text", "raw", "url", "data"}  # A2A Part 在本课程中允许的四种互斥内容字段
TASK_STATES = {
    "TASK_STATE_UNSPECIFIED",  # 枚举占位值；本地执行基线会额外拒绝它
    "TASK_STATE_SUBMITTED",  # Task 已接受但尚未开始执行
    "TASK_STATE_WORKING",  # agent 正在处理该 Task
    "TASK_STATE_COMPLETED",  # Task 成功结束，通常需要 Artifact 证据
    "TASK_STATE_FAILED",  # Task 失败结束
    "TASK_STATE_CANCELED",  # 调用方或控制面取消 Task
    "TASK_STATE_INPUT_REQUIRED",  # agent 等待补充输入
    "TASK_STATE_REJECTED",  # agent/策略拒绝 Task
    "TASK_STATE_AUTH_REQUIRED",  # 继续执行前需要授权
}  # 结束支持的 A2A 1.0 状态集合
TERMINAL_STATES = {
    "TASK_STATE_COMPLETED",  # 成功终态不可再跳到 working
    "TASK_STATE_FAILED",  # 失败终态不可无证据重开
    "TASK_STATE_CANCELED",  # 取消终态不可被旧消息重放恢复
    "TASK_STATE_REJECTED",  # 拒绝终态不可被同一 snapshot 序列改写
}  # 结束本地不可逆终态集合


def _is_non_empty_string(value: Any) -> bool:  # 判断值是否为去掉空白后仍有内容的字符串
    return isinstance(value, str) and bool(value.strip())  # 同时拒绝 None、数字、空串和纯空白文本


def _is_absolute_url(value: Any, *, https_only: bool = False) -> bool:  # 判断 Agent Card/Part URL 是否为允许的绝对 HTTP 地址
    if not _is_non_empty_string(value):  # 空或非文本值没有可验证 URL 语义
        return False  # 交给上层添加字段级错误
    parsed = urlparse(value)  # 拆解 scheme、host、path 等组成部分
    if https_only:  # production baseline 的 endpoint 必须使用 HTTPS
        return parsed.scheme == "https" and bool(parsed.netloc)  # 同时要求存在非空网络位置
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)  # 普通内容 URL 允许 HTTP/HTTPS 两种 scheme


def _validate_string_list(value: Any, path: str, errors: list[str]) -> None:  # 对 MIME 类型、标签等字符串数组执行统一检查
    if not isinstance(value, list) or not value:  # 必须是至少含一项的列表
        errors.append(f"{path} must be a non-empty list")  # 把错误累积到当前对象，而非立刻中断全案例验证
        return  # 类型/空列表错误时不再遍历元素
    if any(not _is_non_empty_string(item) for item in value):  # 所有元素都必须有实际文本内容
        errors.append(f"{path} entries must be non-empty strings")  # 防止空标签或非文本 MIME 值进入协议层


def validate_agent_card(card: Any) -> list[str]:  # 校验本课程支持的 A2A 1.0 Agent Card 子集与额外生产基线
    """Validate the documented A2A 1.0 subset plus local production policy."""  # 不是完整规范/TCK 实现

    errors: list[str] = []  # 收集全部发现的问题，方便一个 fixture 同时展示多个边界
    if not isinstance(card, dict):  # Card 根必须是对象，不能是数组或文本
        return ["agentCard must be an object"]  # 根类型错误时没有可继续读取的字段

    for field in ("name", "description", "version"):  # 三个基础身份/说明字段都需有意义
        if not _is_non_empty_string(card.get(field)):  # 缺失、空串或非文本均为无效
            errors.append(f"agentCard.{field} must be a non-empty string")  # 使用稳定路径帮助作者定位

    interfaces = card.get("supportedInterfaces")  # agent 对外提供的 transport endpoint 列表
    if not isinstance(interfaces, list) or not interfaces:  # 至少需声明一个可调用接口
        errors.append("agentCard.supportedInterfaces must be a non-empty list")  # 无接口的 Card 无法被安全调用
    else:  # 列表存在时逐项检查 endpoint 合同
        for index, interface in enumerate(interfaces):  # 保留数组下标用于精确错误路径
            path = f"agentCard.supportedInterfaces[{index}]"  # 构造人读/机器可搜索的字段路径
            if not isinstance(interface, dict):  # 单条接口声明必须是对象
                errors.append(f"{path} must be an object")  # 记录错误后继续检查下一条接口
                continue  # 不在非对象上调用 get
            if not _is_absolute_url(interface.get("url"), https_only=True):  # 课程 production baseline 只接受 HTTPS endpoint
                errors.append(f"{path}.url must be an absolute HTTPS URL for this production baseline")  # 防止相对 URL 或明文 HTTP 被误当可信 endpoint

            binding = interface.get("protocolBinding")  # 获取协议绑定名称或自定义 binding URL
            is_custom_binding = _is_absolute_url(binding)  # 自定义 binding 必须本身是绝对 HTTP(S) URI
            if binding not in CORE_BINDINGS and not is_custom_binding:  # 既非标准 binding 也非可验证 URI 时拒绝
                errors.append(  # 将 binding 错误加入同一 Card 报告
                    f"{path}.protocolBinding must be a core binding or an absolute HTTP(S) URI"  # 指出两种可接受形式
                )  # 结束错误追加

            if interface.get("protocolVersion") != "1.0":  # 本教程明确以 1.0 作为互操作基线
                errors.append(f"{path}.protocolVersion must equal the course baseline '1.0'")  # 不静默把其他版本当兼容

    if not isinstance(card.get("capabilities"), dict):  # capabilities 应是结构化协商声明
        errors.append("agentCard.capabilities must be an object")  # 不能由自由文本代替能力形状

    _validate_string_list(card.get("defaultInputModes"), "agentCard.defaultInputModes", errors)  # 检查默认输入 MIME 类型列表
    _validate_string_list(card.get("defaultOutputModes"), "agentCard.defaultOutputModes", errors)  # 检查默认输出 MIME 类型列表

    skills = card.get("skills")  # 读取细粒度可发现任务能力列表
    if not isinstance(skills, list) or not skills:  # 至少一个 Skill 才能说明 agent 提供什么能力
        errors.append("agentCard.skills must be a non-empty list")  # 记录缺失/空列表错误
    else:  # 逐项验证 skill metadata
        seen_ids: set[str] = set()  # 用集合保证同一 Card 内 skill ID 唯一
        for index, skill in enumerate(skills):  # 遍历每一项技能声明
            path = f"agentCard.skills[{index}]"  # 生成当前 skill 的错误路径前缀
            if not isinstance(skill, dict):  # skill 声明必须是对象
                errors.append(f"{path} must be an object")  # 记录错误
                continue  # 避免在非对象上取字段
            for field in ("id", "name", "description"):  # 三个最小发现字段均不可为空
                if not _is_non_empty_string(skill.get(field)):  # 检查该字段是否是有效文本
                    errors.append(f"{path}.{field} must be a non-empty string")  # 标注具体缺失字段
            skill_id = skill.get("id")  # 取 ID 供唯一性检查
            if _is_non_empty_string(skill_id):  # 只有基本类型正确时才进入集合比较
                if skill_id in seen_ids:  # 重复 ID 会让调用/审计路由模糊
                    errors.append(f"{path}.id must be unique within the Agent Card")  # 提醒作者去重
                seen_ids.add(skill_id)  # 记录本条 ID，即使已重复也保留后续检测语义
            _validate_string_list(skill.get("tags"), f"{path}.tags", errors)  # 检查用于发现/过滤的标签数组

    return errors  # 返回全部验证错误；空列表表示 Card 通过该教学 profile


def validate_part(part: Any, path: str) -> list[str]:  # 校验课程采用的 A2A v1.0 member-based Part 区分方式
    """Validate the v1.0 member-based Part discrimination used in the course."""  # 旧 v0.3 的 kind discriminator 在此基线中无效

    if not isinstance(part, dict):  # Part 根必须是对象
        return [f"{path} must be an object"]  # 类型错时立即返回，防止后续集合操作异常

    present = CONTENT_FIELDS.intersection(part)  # 找到四种内容字段中实际出现的成员
    errors: list[str] = []  # 累积单个 Part 的所有合同错误
    if len(present) != 1:  # A2A Part 在本 profile 中必须恰好选一种内容表示
        errors.append(f"{path} must contain exactly one of text/raw/url/data")  # 同时存在或全部缺失都不可解释
    if "kind" in part:  # 迁移时常见的旧协议字段
        errors.append(f"{path}.kind is a v0.3 discriminator and is not valid in the v1.0 baseline")  # 明确拒绝旧式 discriminator
    if "url" in part and not _is_absolute_url(part.get("url")):  # URL content 必须为绝对 HTTP(S) 地址
        errors.append(f"{path}.url must be an absolute HTTP(S) URL")  # 防止相对 URL 在不同宿主下解释不一致
    if "text" in part and not isinstance(part.get("text"), str):  # text content 必须是字符串
        errors.append(f"{path}.text must be a string")  # 不接受对象/数组伪装为文本
    if "raw" in part and not _is_non_empty_string(part.get("raw")):  # raw fixture 先必须为非空文本
        errors.append(f"{path}.raw must be a non-empty base64 string in JSON fixtures")  # 给出 JSON fixture 中 raw 的编码约定
    elif "raw" in part:  # 只有文本形状通过后才验证 base64 字节语法
        try:  # base64 decoder 可在不执行内容的情况下检查格式
            base64.b64decode(part["raw"], validate=True)  # validate=True 拒绝非 base64 字符和错误 padding
        except (binascii.Error, ValueError):  # 捕获格式/填充问题
            errors.append(f"{path}.raw must be valid base64 in JSON fixtures")  # 将底层异常改为稳定合同错误
    return errors  # 返回该 Part 的所有问题；空列表代表通过


def _validate_artifacts(artifacts: Any, path: str) -> list[str]:  # 校验一个 Task snapshot 中的 Artifact 数组与其内容 Part
    if not isinstance(artifacts, list) or not artifacts:  # completed Task 至少需一个可交付 Artifact
        return [f"{path} must be a non-empty list"]  # 根形状错误时无需继续遍历

    errors: list[str] = []  # 收集该数组中每个 Artifact 的错误
    seen_ids: set[str] = set()  # Artifact ID 在同一 snapshot 内必须唯一
    for index, artifact in enumerate(artifacts):  # 逐项验证交付物
        artifact_path = f"{path}[{index}]"  # 构造可定位到数组下标的错误路径
        if not isinstance(artifact, dict):  # Artifact 必须为对象
            errors.append(f"{artifact_path} must be an object")  # 记录类型问题
            continue  # 跳过无法读取字段的项目
        artifact_id = artifact.get("artifactId")  # 读取可用于下载/引用的稳定 ID
        if not _is_non_empty_string(artifact_id):  # ID 缺失或空白不能可靠关联交付物
            errors.append(f"{artifact_path}.artifactId must be a non-empty string")  # 明确指出缺失的标识字段
        elif artifact_id in seen_ids:  # 同一 snapshot 重复 ID 会让覆盖/重试语义含糊
            errors.append(f"{artifact_path}.artifactId must be unique within the snapshot")  # 禁止重复 artifact
        else:  # 仅新的有效 ID 才写入集合
            seen_ids.add(artifact_id)  # 记录该 ID，供后续项目检测

        parts = artifact.get("parts")  # Artifact 内容由一个或多个 Part 表达
        if not isinstance(parts, list) or not parts:  # 空 artifact 不能作为完成证据
            errors.append(f"{artifact_path}.parts must be a non-empty list")  # 提醒补充实际内容
            continue  # 不对缺失/错类型 parts 遍历
        for part_index, part in enumerate(parts):  # 逐一应用 v1.0 Part 合同
            errors.extend(validate_part(part, f"{artifact_path}.parts[{part_index}]"))  # 合并内容字段的错误到同一报告
    return errors  # 返回所有 Artifact/Part 错误


def validate_task_snapshots(snapshots: Any) -> list[str]:  # 校验同一 A2A Task 的一系列状态快照是否保持身份与终态不变量
    """Validate a local sequence policy over snapshots of one A2A Task."""  # 这是本地教学序列规则，不是完整远程同步协议

    if not isinstance(snapshots, list) or not snapshots:  # 至少要有一个 snapshot 才有可验证的生命周期
        return ["taskSnapshots must be a non-empty list"]  # 空序列没有任务身份、状态或证据

    errors: list[str] = []  # 累积整个 snapshot 序列中的问题
    expected_task_id: str | None = None  # 第一个快照确定后续必须保持的 Task ID
    expected_context_id: str | None = None  # 第一个快照确定后续必须保持的 Context ID
    previous_state: str | None = None  # 记录上一个合法状态，用来阻止从终态跳走

    for index, task in enumerate(snapshots):  # 按给定顺序检查状态演进
        path = f"taskSnapshots[{index}]"  # 生成当前快照的错误路径
        if not isinstance(task, dict):  # 快照必须为对象
            errors.append(f"{path} must be an object")  # 记录类型错误
            continue  # 无法读取身份或 status 时跳到下一快照

        task_id = task.get("id")  # 读取该快照的 Task 标识
        context_id = task.get("contextId")  # 读取用于关联会话/任务上下文的标识
        if not _is_non_empty_string(task_id):  # ID 不能为空或非文本
            errors.append(f"{path}.id must be a non-empty string")  # 提示补充稳定任务 ID
        if not _is_non_empty_string(context_id):  # Context ID 也必须稳定可用
            errors.append(f"{path}.contextId must be a non-empty string")  # 提示补充上下文关联 ID

        if index == 0:  # 第一条快照定义本序列应保持的身份
            expected_task_id = task_id if _is_non_empty_string(task_id) else None  # 只有基本格式正确才作为比较基准
            expected_context_id = context_id if _is_non_empty_string(context_id) else None  # 同理保存合法 context ID
        else:  # 后续任何快照均不可切换到另一 Task/Context
            if expected_task_id is not None and task_id != expected_task_id:  # 比较当前 Task ID 与首条基准
                errors.append(f"{path}.id changed within one task snapshot sequence")  # 防止拼接不同任务的更新
            if expected_context_id is not None and context_id != expected_context_id:  # 比较当前 Context ID 与首条基准
                errors.append(f"{path}.contextId changed within one task snapshot sequence")  # 防止跨上下文重放

        status = task.get("status")  # 读取嵌套状态对象
        if not isinstance(status, dict):  # 没有结构化 status 时不能判定生命周期
            errors.append(f"{path}.status must be an object")  # 报告 status 根类型错误
            previous_state = None  # 断开状态链，避免以错误值推导下一条
            continue  # 跳过后续 state/Artifact 规则
        state = status.get("state")  # 获取 A2A 枚举状态值
        if state not in TASK_STATES:  # 只接受本版本的 TASK_STATE_* 枚举
            errors.append(f"{path}.status.state must use an A2A 1.0 TASK_STATE_* enum")  # 旧值或拼写错误不能悄悄兼容
            previous_state = None  # 无效状态不能作为下一个转移的前态
        else:  # 枚举值语法合法后应用本地执行基线限制
            if state == "TASK_STATE_UNSPECIFIED":  # 占位枚举没有运行时含义
                errors.append(f"{path}.status.state cannot be UNSPECIFIED in this local execution baseline")  # 不能用它掩盖未知状态

            if previous_state in TERMINAL_STATES and state != previous_state:  # 不允许从 completed/failed 等终态跳回其他状态
                errors.append(f"{path}.status.state cannot transition away from terminal state {previous_state}")  # 防止旧消息重放重开 Task

        artifacts = task.get("artifacts")  # 读取可选交付物字段
        if state == "TASK_STATE_COMPLETED":  # 完成状态必须提供可验证的工作产物
            errors.extend(_validate_artifacts(artifacts, f"{path}.artifacts"))  # 缺少/畸形 artifact 会使 completed 失败
        elif artifacts is not None:  # 非完成状态若已有 artifact，也必须符合结构合同
            errors.extend(_validate_artifacts(artifacts, f"{path}.artifacts"))  # 不允许在中间态塞入畸形内容

        previous_state = state if state in TASK_STATES else None  # 保存合法状态供下一条快照检查终态不变量

    return errors  # 返回整个序列的全部错误；空列表表示通过本地生命周期规则


def validate_case(case: Any) -> list[str]:  # 校验一个 fixture case 中声明的 Card、Task 快照或两者
    if not isinstance(case, dict):  # case 根必须为对象，才能含 named fields
        return ["case must be an object"]  # 类型错误时立即返回

    errors: list[str] = []  # 汇总 Card 与 Task 两个独立验证器的结果
    if "agentCard" in case:  # fixture 可只测试发现合同
        errors.extend(validate_agent_card(case["agentCard"]))  # 合并 Agent Card 字段错误
    if "taskSnapshots" in case:  # fixture 可只测试 Task 生命周期合同
        errors.extend(validate_task_snapshots(case["taskSnapshots"]))  # 合并快照序列错误
    if "agentCard" not in case and "taskSnapshots" not in case:  # 两类被测对象都缺失时 case 没有意义
        errors.append("case must contain agentCard and/or taskSnapshots")  # 给出最小案例形状要求
    return errors  # 返回累积错误，供 expectedErrors 匹配


def load_cases(path: Path) -> list[dict[str, Any]]:  # 以严格 JSON 规则读取离线 A2A 测试场景
    def reject_nonstandard_number(value: str) -> None:  # json.loads 遇到 NaN/Infinity 时调用此 hook
        raise ValueError(f"fixture contains a non-standard JSON number: {value}")  # 非标准数会造成跨实现语义漂移

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:  # object_pairs_hook 可发现普通 dict 会覆盖掉的重复键
        result: dict[str, Any] = {}  # 从原始键值对逐项构造对象
        for key, value in pairs:  # 保留输入中每次同名字段出现机会
            if key in result:  # 同一 JSON object 出现重复键时语义不可靠
                raise ValueError(f"fixture contains a duplicate JSON field: {key}")  # 失败关闭，避免 parser 选前/后值差异
            result[key] = value  # 仅保存唯一键
        return result  # 将无重复键对象交还 json parser

    payload = json.loads(  # 解析 fixture 根 JSON 值
        path.read_text(encoding="utf-8"),  # 显式 UTF-8 读取，避免宿主默认编码差异
        parse_constant=reject_nonstandard_number,  # 拒绝 NaN/Infinity 等宽松常量
        object_pairs_hook=reject_duplicate_keys,  # 拒绝重复字段
    )  # 完成严格解析
    cases = payload.get("cases") if isinstance(payload, dict) else None  # 仅当根为对象时取得 cases 数组
    if not isinstance(cases, list) or not cases:  # 必须至少有一个要验证的案例
        raise ValueError("fixture must contain a non-empty 'cases' list")  # 向 CLI 返回用户可修复的 fixture 错误
    return cases  # 返回场景数组给运行器


def run_cases(cases: list[dict[str, Any]]) -> tuple[list[str], list[str]]:  # 执行每个正/负向场景，并比较实际错误与 fixture 期望
    passed: list[str] = []  # 保存期望与实际完全一致的 case 名称
    failed: list[str] = []  # 保存 fixture 自身或 validator 行为不一致的详细诊断

    for index, case in enumerate(cases):  # 按 fixture 固定顺序运行，输出保持稳定
        name = case.get("name", f"case-{index}")  # 优先使用作者提供的场景名称
        if not _is_non_empty_string(name):  # 无效名称退回确定性的默认名称
            name = f"case-{index}"  # 仍让失败报告可以精确定位数组位置
        errors = validate_case(case)  # 运行 Card/Task 合同验证，得到实际错误列表
        expected_valid = case.get("expectedValid")  # fixture 声明该 case 预期是否通过
        expected_errors = case.get("expectedErrors", [])  # fixture 声明负例必须包含的错误文本片段

        mismatch: list[str] = []  # 单独收集“测试期望写错”或“实现回归”的差异
        if not isinstance(expected_valid, bool):  # expectedValid 必须是明确布尔值
            mismatch.append("expectedValid must be a boolean")  # 拒绝用字符串/数字表示期望
        elif expected_valid != (not errors):  # 实际有效性由错误列表是否为空决定
            mismatch.append(f"expectedValid={expected_valid}, actualValid={not errors}")  # 报告期望与实际的差异

        if not isinstance(expected_errors, list) or any(  # expectedErrors 必须是文本片段列表
            not _is_non_empty_string(item) for item in expected_errors  # 每个片段都需要可读内容
        ):  # 类型/元素不合法时不能可靠进行包含匹配
            mismatch.append("expectedErrors must be a list of non-empty strings")  # 提醒修复 fixture 自身
        else:  # 期望格式正确时逐一确认实际错误涵盖该风险
            for fragment in expected_errors:  # 每个片段代表一个应被 validator 拦住的边界
                if not any(fragment in error for error in errors):  # 允许实际错误包含更多上下文，但必须包含期望片段
                    mismatch.append(f"missing expected error fragment: {fragment}")  # 说明哪个负向断言失效

        if mismatch:  # 任一期望不匹配都让该场景失败
            detail = "; ".join(mismatch)  # 将多项差异拼成单行 CLI 诊断
            failed.append(f"{name}: {detail}; errors={errors}")  # 同时输出实际 errors，帮助判断是实现还是 fixture 漂移
        else:  # 所有期望均与实际一致
            passed.append(name)  # 记录通过的场景名称

    return passed, failed  # 由 CLI 分别打印通过与失败，并用失败列表决定退出码


def main() -> int:  # CLI 入口：读取 fixture、运行验证并用退出码表达测试结果
    parser = argparse.ArgumentParser(description=__doc__)  # 将模块 docstring 显示在 --help 中，说明教学边界
    parser.add_argument("--cases", type=Path, required=True, help="Path to the JSON fixture")  # 强制用户显式指定场景文件
    args = parser.parse_args()  # 解析命令行参数

    try:  # 把可预期的文件/JSON/合同输入问题转换成受控 CLI 错误
        cases = load_cases(args.cases)  # 严格解析并取得 fixture case 列表
        passed, failed = run_cases(cases)  # 执行所有场景，保留通过与失败明细
    except (OSError, ValueError, json.JSONDecodeError) as exc:  # 不吞掉未知程序 bug，便于开发时看见 traceback
        print(f"ERROR: {exc}")  # 输出可读错误，不泄漏完整异常堆栈
        return 2  # 输入/使用错误使用独立非零退出码

    for name in passed:  # 逐行输出通过的 fixture 名称
        print(f"PASS {name}")  # 便于 CI 与学习者定位覆盖范围
    for detail in failed:  # 逐行输出不匹配场景与实际错误
        print(f"FAIL {detail}")  # 失败包含期望差异，方便修正合同或 fixture
    print(f"SUMMARY passed={len(passed)} failed={len(failed)}")  # 输出稳定汇总供脚本/人工检查
    return 1 if failed else 0  # 有回归时返回 1；全部通过返回 0


if __name__ == "__main__":  # 仅直接执行文件时启动 CLI，导入测试时不会产生输出
    raise SystemExit(main())  # 将 main 返回的测试退出码交给操作系统
