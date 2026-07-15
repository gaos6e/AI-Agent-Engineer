---
title: 项目：结构化 OCR 结果审计
tags:
  - ai-agent-engineer
  - ocr
  - project
aliases:
  - OCR 审计项目
source_checked: 2026-07-14
---

# 项目：结构化 OCR 结果审计

## 项目目标

不安装 OCR 引擎、不读取真实图片，直接审计一个匿名结构化结果夹具。这样可以把“结果契约、阅读顺序、文本误差、低置信度复核和表格结构”做成稳定的回归门禁。

资产：

- [[OCR/03-项目与自测/examples/ocr_fixture.json|ocr_fixture.json]]：匿名、人工编写的输入与参考答案。
- [[OCR/03-项目与自测/examples/audit_ocr_fixture.py|audit_ocr_fixture.py]]：仅使用 Python 3 标准库。
- [[OCR/03-项目与自测/examples/test_contract_and_cli.py|test_contract_and_cli.py]]：严格 JSON、输入合同、指标、审计和 CLI 的回归测试。

## 运行

在 PowerShell 7 中：

```powershell
Set-Location 'X:\path\to\your-vault\Knowledge\AI Agent Engineer\docs\OCR\03-项目与自测\examples'
python -B .\audit_ocr_fixture.py .\ocr_fixture.json
python -B .\audit_ocr_fixture.py --self-test
python -B -m unittest discover -s . -p 'test_*.py'
python -B -O -m unittest discover -s . -p 'test_*.py'
python -B -W error -m unittest discover -s . -p 'test_*.py'
```

`-B` 禁止生成 `__pycache__`/`.pyc`。程序只读取夹具并把报告写到标准输出，不修改文件。当前回归集共 **73 项**；普通模式、`-O` 和 warnings-as-errors 三种运行都应通过。

## 输入与退出码合同

加载器要求 UTF-8 严格 JSON：重复键、`NaN`/`Infinity`、未知字段、越界坐标和错误类型都会被拒绝。顶层必须精确包含 `schema_version`、`document_id`、`review_threshold` 和 `pages`；页、块与表格也使用封闭字段集合。这是教学合同，不代表任一 OCR 产品的原生输出格式。

- 退出码 `0`：合同有效且没有审计级错误；低置信度或关键字段不一致可以进入复核队列，但不等于程序失败。
- 退出码 `1`：合同有效，但发现重复块 ID、同页顺序重复或倒序等审计错误。
- 退出码 `2`：文件、UTF-8、JSON 或输入合同错误。

## 你要读懂的报告

- `cer`/`wer`：基于参考文本的编辑错误率。
- `order_valid`：同页块顺序是否唯一且递增。
- `table_structure_match`：参考与预测的行列数是否一致。
- `review_queue`：低于阈值或关键字段校验失败的块。
- `errors`：合同通过后的审计级错误；存在时程序返回退出码 `1`。

## 扩展任务

1. 复制一个块，制造重复 `block_id`，确认脚本拒绝。
2. 将一个 `order` 改为已有序号，确认排序校验失败。
3. 新增匿名“竖排文字”切片和 `document_type` 字段，按类型汇总 CER。
4. 给关键金额加入格式校验，但必须保留 `raw_text`。

## 验收标准

- [ ] 能解释动态规划如何计算编辑距离。
- [ ] 能说出脚本没有验证哪些真实 OCR 能力：成像、检测框和模型推理均未执行。
- [ ] 能为新字段补 schema 校验和一个失败用例。
- [ ] 默认夹具退出码为 `0`，人为制造审计错误时为 `1`，破坏合同字段时为 `2`。
- [ ] 73 项测试在普通、`-O` 和 warnings-as-errors 三种模式均通过，且工作区没有缓存或输出文件。

## 常见问题

- **CER 很低但表格不可用**：查看结构匹配和单元格位置，而非只看文本。
- **WER 与预期不一致**：脚本按空白分词；中文等语言需换成明确 tokenizer。
- **置信度阈值难设**：夹具阈值只是演示，生产阈值需用代表性验证集校准。

完成后返回 [[OCR/00-目录|OCR 目录]]，并思考如何把审计报告接入 [[评测体系/00-目录|评测体系]]。
