"""Return deterministic text statistics without network or file writes."""

from __future__ import annotations  # 允许类型注解引用稍后定义的对象，保持新旧 Python 注解行为稳定

import argparse  # 解析 --text 与 --input 两种命令行输入方式
import json  # 将统计结果输出为便于机器读取的 JSON
import re  # 用正则识别英文/数字词块与单个汉字
import sys  # 将可预期的用户输入错误写到 stderr
from pathlib import Path  # 安全、跨平台地表示输入文件路径


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+|[\u3400-\u4dbf\u4e00-\u9fff]")  # 一个英文/数字连续段算一个词，每个汉字算一个词样 token
MAX_INPUT_BYTES = 1024 * 1024  # 统一限制输入为 1 MiB，避免示例被超大文本拖垮


def logical_line_count(text: str) -> int:  # 统计用户理解的“行”，而不受 Windows/Linux 换行差异影响
    """Count logical lines after normalizing common newline sequences."""  # \r\n、\r 与 \n 都按同一种换行处理
    if text == "":  # 空文本没有任何逻辑行
        return 0  # 直接返回，避免把空字符串误计为一行
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")  # 先统一三种常见换行表示
    return normalized.count("\n") + 1  # 换行符个数加一即为非空文本的逻辑行数


def calculate(text: str) -> dict[str, int]:  # 汇总三个稳定、无网络依赖的文本指标
    """Count Latin/numeric runs and individual Han characters as word-like tokens."""  # 这不是自然语言分词器，只是教学用近似计数
    return {  # 返回 JSON 可直接序列化的纯整数对象
        "words": len(TOKEN_PATTERN.findall(text)),  # 正则匹配次数代表词样 token 数量
        "characters": len(text),  # Python str 的 Unicode 码点数量，不等同于 UTF-8 字节数
        "lines": logical_line_count(text),  # 复用上面的跨平台逻辑行统计
    }  # 结束统计结果对象


def require_bounded_utf8_text(text: str, *, source: str) -> str:  # 让 --text 与文件输入共享同一 UTF-8 字节上限
    """Reject text that cannot fit the shared 1 MiB UTF-8 input contract."""  # 限制的是编码后的字节数，不是字符数
    try:  # 编码时也可能因孤立代理项等异常 Unicode 值失败
        size = len(text.encode("utf-8"))  # 得到真实将进入系统的 UTF-8 字节长度
    except UnicodeEncodeError as exc:  # 无法编码时不能假装为有效文本继续统计
        raise ValueError(f"{source} must be valid UTF-8 text") from exc  # 转为清晰、可预期的用户错误
    if size > MAX_INPUT_BYTES:  # 超过共享 1 MiB 合同时立即拒绝
        raise ValueError(f"{source} exceeds {MAX_INPUT_BYTES} UTF-8 bytes (1 MiB): {size}")  # 告知限制与实际长度
    return text  # 校验成功后原样返回，供调用链继续使用


def read_utf8_file(path: Path) -> str:  # 以有上限的二进制读取方式加载用户指定文件
    """Read at most 1 MiB of UTF-8 input without trusting a pre-read file size."""  # 避免先 stat 再读时文件大小发生变化
    if not path.is_file():  # 目录、快捷方式目标异常或不存在路径都不当作输入文件
        raise ValueError(f"input path is not a file: {path}")  # 返回清楚的参数错误
    with path.open("rb") as stream:  # 以字节读取，才能精确执行 UTF-8 字节上限
        raw = stream.read(MAX_INPUT_BYTES + 1)  # 多读一个字节即可检测是否超过限制，而不加载整个大文件
    if len(raw) > MAX_INPUT_BYTES:  # 读到了第 1 MiB 之后的字节，说明输入超限
        raise ValueError(f"input exceeds {MAX_INPUT_BYTES} UTF-8 bytes (1 MiB): at least {len(raw)}")  # 不继续解码或统计超大数据
    try:  # 只有通过大小检查的字节才进入 Unicode 解码
        return require_bounded_utf8_text(raw.decode("utf-8"), source="input")  # 解码后再走共享文本合同，防止逻辑分叉
    except UnicodeDecodeError as exc:  # 无效 UTF-8 不应被替换字符悄悄掩盖
        raise ValueError("input file must be valid UTF-8") from exc  # 告知学习者编码而非统计逻辑出了问题


def build_parser() -> argparse.ArgumentParser:  # 构造可复用的 CLI 参数解析器，便于单元测试传入 argv
    parser = argparse.ArgumentParser(  # 创建标准 argparse 解析器
        description="Count word-like tokens, Unicode code points, and logical lines."  # 在 --help 中解释本工具统计什么
    )  # 完成解析器创建
    source = parser.add_mutually_exclusive_group(required=True)  # 强制用户只选文本或文件其中一种来源
    source.add_argument("--text", help="Literal UTF-8 text (maximum 1 MiB); avoid this option for secrets")  # 直接输入文本；命令行历史可能泄露秘密
    source.add_argument("--input", type=Path, help="Path to a UTF-8 text file (maximum 1 MiB)")  # 让 argparse 自动把路径文本转为 Path
    return parser  # 交给 main() 调用 parse_args


def main(argv: list[str] | None = None) -> int:  # 执行一次 CLI 调用，并用退出码表达成功或用户输入错误
    args = build_parser().parse_args(argv)  # 解析真实 sys.argv 或测试传入的参数列表
    try:  # 将文件 I/O、编码和边界错误统一转换成友好 CLI 结果
        text = (  # 根据互斥参数选择唯一的输入来源
            require_bounded_utf8_text(args.text, source="--text")  # --text 已是 str，但仍需检查 UTF-8 编码长度
            if args.text is not None  # 用户显式提供 --text 时走此分支
            else read_utf8_file(args.input)  # 否则读取已由 argparse 转成 Path 的 --input 文件
        )  # 得到通过大小和 UTF-8 合同的文本
    except (OSError, ValueError) as exc:  # 只捕获预期用户错误，不隐藏编程错误
        print(f"error: {exc}", file=sys.stderr)  # 错误写 stderr，保持 stdout 只承载成功 JSON
        return 2  # 使用常见的“命令行使用/输入错误”非零退出码
    print(json.dumps(calculate(text), ensure_ascii=False, sort_keys=True))  # 计算并输出键排序的稳定 JSON 结果
    return 0  # 正常完成


if __name__ == "__main__":  # 直接运行脚本时才启动 CLI；导入测试时不会自动执行
    raise SystemExit(main())  # 将 main 的整数返回值交给操作系统作为退出码
