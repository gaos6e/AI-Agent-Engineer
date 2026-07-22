"""Validate the strict teaching profile used by the bundled Agent Skill.

This standard-library validator deliberately supports only the YAML subset used
by this example. It is not an Agent Skills conformance test and does not replace
the official ``skills-ref validate`` command.
"""

from __future__ import annotations  # 让所有类型注解延迟求值，避免前向引用问题

import argparse  # 解析要验证的 Skill 目录命令行参数
import json  # 读取本地 eval JSON 并输出验证摘要
import re  # 用正则从 Markdown 正文中识别资源链接
import sys  # 将用户可修正的验证错误写入 stderr
from pathlib import Path, PurePosixPath  # Path 操作真实文件；PurePosixPath 校验跨客户端资源路径语法
from typing import Any  # frontmatter/JSON 解析后的值可能属于多种类型


NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")  # 官方常用的 skill name：小写字母/数字，以单连字符分段
RESOURCE_PATTERN = re.compile(
    r"(?:`|\]\()((?:scripts|references|assets)/[^`\s)]+)(?=[`\s)])"  # 只捕获 Markdown 代码/链接中引用的三个约定资源目录
)  # 编译一次，避免每次验证正文都重新解析模式
ALLOWED_FIELDS = {
    "name",  # Skill 必填的稳定名称
    "description",  # 触发选择所依赖的简短能力描述
    "license",  # 可选的许可提示
    "compatibility",  # 可选的宿主环境兼容性说明
    "metadata",  # 本教学 profile 支持的一层字符串映射
    "allowed-tools",  # 实验性客户端能力声明，仍不等于最终授权
}  # 结束允许的顶层 frontmatter 字段集合
MIN_TRIGGER_CASES_PER_CLASS = 8  # 正/负触发语料各至少八条，避免只测“会触发”的单边情形


def require(condition: bool, message: str) -> None:  # 在整个离线 validator 中统一失败方式
    """Raise a stable, user-facing validation error."""  # 调用者得到清晰字段错误，而非随机下游异常
    if not condition:  # 条件未满足才构造错误
        raise ValueError(message)  # 使用 ValueError 表示用户可以修复的输入/Skill 形状问题


def _parse_scalar(raw: str, *, line_number: int) -> str:  # 解析本示例支持的简单 YAML 标量，而非实现完整 YAML
    value = raw.strip()  # 去掉键值分隔符后两侧的无意义空白
    require(value != "", f"frontmatter line {line_number} needs a scalar value")  # 空标量会使 metadata/描述语义不清
    if value[0] in {"'", '"'}:  # 单引号或双引号形式需要检查成对闭合
        require(  # 防止把未结束引号后的文本误当作配置
            len(value) >= 2 and value[-1] == value[0],  # 至少有一对相同边界引号
            f"frontmatter line {line_number} has an unterminated quoted scalar",  # 给出准确行号
        )  # 结束引号检查
        value = value[1:-1]  # 去掉外层引号，保留实际标量内容
    require("\n" not in value and "\r" not in value, "scalar values cannot contain newlines")  # 本 profile 不接受多行标量
    return value  # 返回已完成最小语法检查的文本值


def parse_frontmatter_subset(text: str) -> tuple[dict[str, Any], str]:  # 分离本课程可验证的 frontmatter 子集与 Markdown 正文
    """Parse flat scalars plus a one-level string-to-string metadata mapping."""  # 刻意不处理 YAML 的锚点、数组、多行值等完整特性
    lines = text.splitlines()  # 先按逻辑行读取，便于给出稳定行号
    require(lines and lines[0] == "---", "SKILL.md must start with ---")  # Frontmatter 必须从首行界定符开始
    try:  # 在第一行之后找对应的关闭界定符
        closing = lines.index("---", 1)  # 返回关闭行索引，允许空 frontmatter 但后续字段会各自校验
    except ValueError as exc:  # 缺少关闭界定符会让正文和配置边界不可靠
        raise ValueError("SKILL.md frontmatter has no closing ---") from exc  # 转换为学习者可修复的错误

    fields: dict[str, Any] = {}  # 累积已解析的顶层字段
    index = 1  # 跳过 opening ---，从第一行配置开始
    while index < closing:  # 只处理界定符之间的行
        line_number = index + 1  # 对用户显示的行号从 1 开始
        line = lines[index]  # 取当前原始配置行
        require(line and not line[0].isspace(), f"unexpected indentation on line {line_number}")  # 顶层键不允许缩进
        require(":" in line, f"frontmatter line {line_number} must contain ':'")  # 标量或映射键都需冒号分隔
        key, raw_value = line.split(":", 1)  # 只在首个冒号切分，保留值中可能存在的 URL 冒号
        key = key.strip()  # 去掉键名周围空白，得到规范字段名
        require(key in ALLOWED_FIELDS, f"unsupported top-level field in teaching profile: {key}")  # profile 不静默接受未知字段
        require(key not in fields, f"duplicate frontmatter field: {key}")  # 重复字段会导致不同 YAML 解析器语义不同

        if key != "metadata":  # 除 metadata 外，本 profile 的字段都只能是单行标量
            fields[key] = _parse_scalar(raw_value, line_number=line_number)  # 解析并保存当前标量
            index += 1  # 继续读取下一顶层行
            continue  # 不进入 metadata 专用分支

        require(raw_value.strip() == "", "metadata must be a one-level mapping in this teaching profile")  # metadata: 后不能再混入标量值
        metadata: dict[str, str] = {}  # 为一层键值映射初始化临时字典
        index += 1  # 移到第一条可能的二空格缩进 metadata 行
        while index < closing and lines[index].startswith("  "):  # 只读取恰好属于 metadata 的缩进行
            nested_number = index + 1  # 生成用户可读的行号
            nested = lines[index][2:]  # 移除两空格缩进，取得子键文本
            require(nested and not nested[0].isspace(), f"metadata line {nested_number} is too deeply nested")  # 禁止二级以上嵌套
            require(":" in nested, f"metadata line {nested_number} must contain ':'")  # 子项也必须是 key: value
            nested_key, nested_raw = nested.split(":", 1)  # 仍只按第一个冒号切分
            nested_key = nested_key.strip()  # 规范化子键两侧空白
            require(nested_key != "", f"metadata line {nested_number} needs a key")  # 空键没有可用语义
            require(nested_key not in metadata, f"duplicate metadata key: {nested_key}")  # 禁止同一 metadata 键重复
            metadata[nested_key] = _parse_scalar(nested_raw, line_number=nested_number)  # 保存经过标量校验的字符串值
            index += 1  # 继续到下一个缩进行或下一个顶层字段
        require(metadata, "metadata mapping must not be empty")  # 防止空 metadata: 留下误导性配置
        fields[key] = metadata  # 将已验证的嵌套映射写入顶层字段

    return fields, "\n".join(lines[closing + 1 :]).strip()  # 返回配置与去掉前后空白的 Markdown 正文


def require_canonical_resource_relative(relative: str) -> None:  # 在接触宿主文件系统前拒绝歧义/越界资源写法
    """Reject ambiguous resource spellings before resolving them on the host OS."""  # 统一使用 POSIX 分隔符，避免 Windows 特例绕过检查
    path = PurePosixPath(relative)  # 只按逻辑 POSIX 路径解析，不根据当前 OS 改写含义
    parts = path.parts  # 获取各级路径段，便于判断根目录和 traversal
    require(  # 所有 canonical 约束必须同时成立
        not path.is_absolute()  # 资源不允许是绝对路径
        and "\\" not in relative  # 禁止 Windows 反斜杠造成跨平台解释差异
        and str(path) == relative  # 禁止重复分隔符或其他会被规范化的歧义写法
        and len(parts) >= 2  # 必须至少为“资源目录/文件”两段
        and parts[0] in {"scripts", "references", "assets"}  # 只允许 Skill 约定的三个资源根
        and all(part not in {".", ".."} for part in parts),  # 显式阻断当前目录/父目录 traversal
        f"resource reference must be a canonical relative POSIX path: {relative}",  # 告诉用户应修正的资源引用
    )  # 结束资源路径合同校验


def resolve_within(root: Path, relative: str) -> Path:  # 将逻辑资源路径解析成真实文件，但不允许逃出 Skill 根目录
    """Resolve a canonical resource reference without allowing Skill-root escape."""  # symlink 等真实路径变化也需在 resolve 后检查
    require_canonical_resource_relative(relative)  # 先检查文本形式，避免 normalize 前隐藏 traversal
    target = (root / relative).resolve()  # 解析符号链接和 . 等真实文件系统路径
    try:  # 用 relative_to 验证解析后的目标仍位于 Skill 根内
        target.relative_to(root.resolve())  # 若不在根下会抛 ValueError
    except ValueError as exc:  # 包括 symlink 指向根外的情形
        raise ValueError(f"resource escapes skill root: {relative}") from exc  # 失败关闭，不跟随到外部文件
    return target  # 返回已同时通过逻辑和真实路径检查的资源路径


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:  # 给 json.loads 的 object_pairs_hook，用于检测重复键
    result: dict[str, Any] = {}  # 逐项重建字典，保留 parser 提供的所有原始键值对
    for key, value in pairs:  # 同名键不会在此处被静默覆盖
        require(key not in result, f"duplicate JSON key: {key}")  # 发现重复就拒绝，避免不同实现取前/后值
        result[key] = value  # 仅保存首次出现的合法唯一键
    return result  # 交回严格、无重复键的对象


def load_json_object(path: Path) -> dict[str, Any]:  # 读取需要“根为对象且无重复键”的本地 JSON 文件
    data = json.loads(  # 使用标准 JSON parser，而不是容忍 JSONC/宽松变体
        path.read_text(encoding="utf-8"),  # 显式 UTF-8，避免依赖本机默认编码
        object_pairs_hook=_reject_duplicate_json_keys,  # 解析每个对象时执行重复键 gate
    )  # 得到 Python JSON 值
    require(isinstance(data, dict), f"{path.name} root must be an object")  # eval 文件根不能是数组或字符串
    return data  # 返回后续 schema 校验所需的对象


def validate_evals(skill_root: Path, skill_name: str) -> dict[str, int]:  # 验证本地触发语料是否足以覆盖“该触发/不该触发”两类案例
    """Validate the local trigger-corpus profile, not a universal eval schema."""  # 这不是对所有评测格式通用的 schema 声明
    eval_path = skill_root / "evals" / "evals.json"  # 按本课程示例的固定相对位置查找语料
    if not eval_path.exists():  # evals 是可选教学资源，缺失时不使基本 Skill 无法验证
        return {"total": 0, "positive": 0, "negative": 0}  # 返回明确的零覆盖摘要，而不是假称通过过评测

    data = load_json_object(eval_path)  # 严格读取 JSON 根对象并拒绝重复键
    require(data.get("skill_name") == skill_name, "eval skill_name must match name")  # 防止把另一 Skill 的语料误复用
    cases = data.get("evals")  # 取出触发案例数组
    require(isinstance(cases, list) and cases, "evals must be a non-empty array")  # 有 eval 文件时至少应有一条有效案例

    ids: set[str] = set()  # 用集合检测案例 ID 是否重复
    positives = 0  # 统计 should_trigger=True 的正例数量
    negatives = 0  # 统计 should_trigger=False 的负例数量
    for index, case in enumerate(cases, start=1):  # 从 1 编号，便于向学习者报告具体案例
        require(isinstance(case, dict), f"eval {index} must be an object")  # 单条案例必须结构化
        case_id = case.get("id")  # 取稳定案例 ID
        require(isinstance(case_id, str) and case_id.strip(), f"eval {index} needs a string id")  # ID 必须为非空文本
        require(case_id not in ids, f"duplicate eval id: {case_id}")  # 不允许一条 ID 覆盖另一条测试意图
        ids.add(case_id)  # 将已验证 ID 记录到集合
        require(  # prompt 是模型/客户端真实要判断的输入，因此不能为空
            isinstance(case.get("prompt"), str) and case["prompt"].strip(),  # 必须为含非空白内容的字符串
            f"eval {index} needs a non-empty prompt",  # 明确缺失的字段
        )  # 结束 prompt 校验
        trigger = case.get("should_trigger")  # 提取期望的布尔触发决策
        require(isinstance(trigger, bool), f"eval {index} needs boolean should_trigger")  # 禁止 "yes"/1 等歧义真值
        require(  # reason 让评测案例可人工审阅，而非只有标签
            isinstance(case.get("reason"), str) and case["reason"].strip(),  # 说明为何应/不应选择 Skill
            f"eval {index} needs a non-empty reason",  # 给出可修复提示
        )  # 结束 reason 校验
        require(  # expected_output 记录选择后应有的最小行为结果
            isinstance(case.get("expected_output"), str) and case["expected_output"].strip(),  # 输出期望需可读
            f"eval {index} needs a non-empty expected_output",  # 报告缺失字段
        )  # 结束 expected_output 校验
        positives += int(trigger)  # True 转为 1，累计正例
        negatives += int(not trigger)  # False 转为 1，累计负例

    require(  # 正例过少会让描述看似会触发但缺少覆盖
        positives >= MIN_TRIGGER_CASES_PER_CLASS,  # 达到教学 profile 的最小正例数
        f"teaching profile needs at least {MIN_TRIGGER_CASES_PER_CLASS} positive trigger cases",  # 说明缺口
    )  # 结束正例数量检查
    require(  # 负例过少无法发现过度触发/范围漂移
        negatives >= MIN_TRIGGER_CASES_PER_CLASS,  # 达到教学 profile 的最小负例数
        f"teaching profile needs at least {MIN_TRIGGER_CASES_PER_CLASS} negative trigger cases",  # 说明缺口
    )  # 结束负例数量检查
    return {"total": len(cases), "positive": positives, "negative": negatives}  # 返回可展示、可回归比较的覆盖摘要


def validate_python_scripts(skill_root: Path) -> list[str]:  # 只做 Python 语法编译检查，不执行 Skill 脚本
    """Compile Python source in memory so validation creates no bytecode cache."""  # 这样不会创建 __pycache__ 或触发副作用
    scripts_root = skill_root / "scripts"  # 按 Skill 约定定位可执行脚本目录
    if not scripts_root.exists():  # 无脚本的 Skill 是允许的
        return []  # 返回空列表，清晰表示没有需要编译的文件
    require(scripts_root.is_dir(), "scripts must be a directory")  # 同名普通文件不能冒充脚本目录
    checked: list[str] = []  # 收集成功通过语法检查的相对路径
    for path in sorted(scripts_root.rglob("*.py")):  # 递归、稳定排序检查全部 Python 脚本
        relative = path.relative_to(skill_root).as_posix()  # 用 Skill 内 POSIX 相对路径呈现结果
        try:  # compile 只解析和编译，不会运行脚本内容
            compile(path.read_text(encoding="utf-8"), relative, "exec")  # 显式 UTF-8 读取，并以 exec 模式验证完整模块
        except (SyntaxError, UnicodeError) as exc:  # 捕获语法和解码异常，避免 CLI 打出大 traceback
            raise ValueError(f"invalid Python script {relative}: {exc}") from exc  # 报告具体脚本路径，保留异常链
        checked.append(relative)  # 仅在无异常后列为已检查脚本
    return checked  # 交给主验证结果显示


def validate_skill(skill_root: Path) -> dict[str, Any]:  # 执行本课程的离线严格 profile 验证，并返回机器可读摘要
    require(skill_root.is_dir(), f"skill directory not found: {skill_root}")  # 根路径必须是一个实际目录
    skill_file = skill_root / "SKILL.md"  # Skill 的入口文件有固定名称
    require(skill_file.is_file(), "SKILL.md not found")  # 没有入口就无法作为 Skill 使用
    skill_text = skill_file.read_text(encoding="utf-8")  # 用显式 UTF-8 读取 Markdown
    fields, body = parse_frontmatter_subset(skill_text)  # 分离并验证受支持的 frontmatter 结构

    name = fields.get("name", "")  # 获取必填名称，缺失时用空值触发下一行清晰错误
    description = fields.get("description", "")  # 获取触发描述，缺失时同样进入明确校验
    require(isinstance(name, str) and 1 <= len(name) <= 64, "name must contain 1-64 characters")  # 约束名称长度，避免空或极端长标识
    require(bool(NAME_PATTERN.fullmatch(name)), "name must use lowercase letters, digits, and single hyphens")  # 强制跨客户端可移植的 name 形式
    require(name == skill_root.name, "name must match the parent directory")  # 目录名与名称不一致会让资源定位混乱
    require(  # description 既是用户说明，也是客户端选择 Skill 的重要信号
        isinstance(description, str) and 1 <= len(description) <= 1024,  # 允许足够具体但受限的文本长度
        "description must contain 1-1024 characters",  # 说明描述字段合同
    )  # 结束 description 校验
    require(body, "SKILL.md body must not be empty")  # metadata 本身不能取代给 agent 的步骤正文
    compatibility = fields.get("compatibility")  # 可选读取宿主兼容性说明
    if compatibility is not None:  # 写了该字段时才检查长度和类型
        require(  # 不允许嵌套对象或过长平台文本
            isinstance(compatibility, str) and 1 <= len(compatibility) <= 500,  # 保持为简短人读约束
            "compatibility must contain 1-500 characters",  # 输出可修复错误
        )  # 结束 compatibility 校验
    metadata = fields.get("metadata")  # 可选读取一层 metadata 映射
    if metadata is not None:  # 只在字段出现时强制 profile 的类型限制
        require(  # 所有键和值必须保持为纯字符串
            isinstance(metadata, dict)  # 元数据必须是对象
            and all(isinstance(key, str) and isinstance(value, str) for key, value in metadata.items()),  # 不允许深层或非文本值
            "metadata must be a string-to-string mapping",  # 说明 profile 的故意范围
        )  # 结束 metadata 校验
    allowed_tools = fields.get("allowed-tools")  # 可选读取客户端的实验性建议字段
    if allowed_tools is not None:  # 写了该字段时不允许空字符串
        require(isinstance(allowed_tools, str) and bool(allowed_tools.strip()), "allowed-tools must be a string")  # 这只是声明，不替代 runtime 授权

    references = sorted(set(RESOURCE_PATTERN.findall(body)))  # 去重并稳定排序正文提到的资源
    for relative in references:  # 每个引用都要证明位于根内并实际存在
        require(resolve_within(skill_root, relative).is_file(), f"missing resource: {relative}")  # 缺资源会导致 Skill 在执行时失效

    warnings: list[str] = []  # 将非致命、但值得学习者注意的问题与错误分开
    if len(skill_text.splitlines()) >= 500:  # 文件过长会削弱渐进披露与可发现性
        warnings.append("official guidance recommends keeping SKILL.md under 500 lines")  # 不阻塞验证，但提示重构方向
    for relative in references:  # 深层路径并非非法，但可能使 agent 更难正确定位
        if len(Path(relative).parts) > 2:  # 例如 scripts/helpers/x.py 有三层以上
            warnings.append(f"deep resource reference may be harder to discover: {relative}")  # 保留具体路径给作者判断

    eval_summary = validate_evals(skill_root, name)  # 检查触发/不触发语料并获取数量摘要
    scripts = validate_python_scripts(skill_root)  # 编译本地脚本但不执行它们
    return {  # 输出稳定、可供测试和文档展示的验证结果
        "status": "ok",  # 所有硬性 gate 已通过
        "profile": "strict-offline-teaching-profile-v1",  # 明确这是本库教学 profile，不是假冒官方 conformance
        "name": name,  # 回显已经验证的 Skill 名称
        "referenced_files": references,  # 列出正文实际依赖的文件
        "python_scripts": scripts,  # 列出语法检查过的脚本
        "trigger_cases": eval_summary,  # 报告正/负触发覆盖数量
        "warnings": sorted(set(warnings)),  # 去重并排序非致命提醒，保持输出稳定
        "note": "not an official conformance result; use skills-ref for official validation",  # 防止学习者把本脚本误当规范认证器
    }  # 结束结果对象


def main() -> int:  # 命令行入口：读取一个 Skill 目录并打印验证 JSON
    parser = argparse.ArgumentParser(description="Validate the offline teaching Agent Skill profile.")  # 创建带 --help 文本的标准 parser
    parser.add_argument("skill_directory", type=Path, help="Path containing SKILL.md")  # 将位置参数自动转为 Path
    args = parser.parse_args()  # 从命令行读取用户输入
    result = validate_skill(args.skill_directory.resolve())  # 先解析为真实绝对路径，再按根边界验证
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))  # 以稳定排序、保留中文的格式输出成功摘要
    return 0  # 返回成功退出码


if __name__ == "__main__":  # 仅直接运行时启动 CLI，不影响导入到测试模块
    try:  # 将预期的文件、编码、验证与 JSON 错误转换成统一输出
        raise SystemExit(main())  # main 成功时将 0 交给操作系统
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:  # 不吞掉未知编程异常，便于开发时发现 bug
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)  # 错误 JSON 写 stderr，stdout 保持成功协议
        raise SystemExit(1) from exc  # 非零退出并保留异常链
