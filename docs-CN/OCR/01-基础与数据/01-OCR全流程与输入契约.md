---
title: "OCR 全流程与输入契约"
tags:
  - ai-agent-engineer
  - ocr
aliases:
  - OCR pipeline
source_checked: 2026-07-22
lang: zh-CN
translation_key: OCR/01-基础与数据/01-OCR全流程与输入契约.md
translation_route: en/ocr/foundations-and-data/01-ocr-pipeline-and-input-contract
translation_default_route: zh-CN/OCR/01-基础与数据/01-OCR全流程与输入契约
---

# OCR 全流程与输入契约

## 本节目标

理解 OCR 为什么是一条数据流水线，并能先写结果契约、再选择模型。

## 从“看见”到“可用”

人看到一张发票会同时理解文字、位置、表格和层级；计算机收到的只是像素。一个可审计的 OCR 流程通常包含：

1. **采集与解码**：记录原文件、页码、尺寸、颜色空间和方向。
2. **预处理**：校正旋转或透视，抑制噪声，必要时调整对比度。
3. **版面分析**：找出标题、段落、表格、图片、页眉等区域。
4. **文字检测**：预测文字区域的边界框或多边形。
5. **文字识别**：把每个区域的像素转成字符序列。
6. **排序与后处理**：恢复阅读顺序、规范化字符并应用有限规则。
7. **质量控制**：计算指标，把不确定或高风险结果交给人工。

检测回答“文字在哪里”，识别回答“文字是什么”。对整页直接识别有时可行，但复杂版面一旦排序错误，文本本身全对也无法用于问答或抽取。

## 先定义输出契约

最小文本块可以设计为：

```json
{
  "document_id": "sample-001",
  "page": 1,
  "block_id": "p1-b03",
  "type": "text",
  "bbox": [120, 80, 620, 150],
  "order": 3,
  "text": "合计 128.00 元",
  "confidence": 0.93,
  "source": {
    "asset_id": "original-sample-001",
    "asset_sha256": "record-at-runtime",
    "coordinate_space": "page_pixels",
    "transform_id": "record-at-runtime",
    "engine": "record-at-runtime",
    "model": "record-at-runtime"
  }
}
```

`bbox` 只是坐标约定，必须同时记录它是像素还是归一化坐标，以及顺序为 `[left, top, right, bottom]` 还是别的格式。`asset_sha256`、`transform_id` 和坐标空间把文字框绑定到某个原始 revision 与派生图；裁剪、旋转或重跑 OCR 后不得复用旧框。`confidence` 是模型分数，不是“正确概率”；不同引擎的分数不可直接横比，阈值要在自己的验证集上校准。

## 失败边界

- 只保留纯文本会丢失证据位置，无法在原页高亮。
- 只保留平均置信度会掩盖金额、编号等关键字段错误。
- 预处理覆盖原图会让错误不可复现；原件应只读保存，衍生图记录参数。
- 把文件名当身份标识会在重名或移动后失效；应使用稳定文档 ID 和内容摘要。

## 进入 RAG 前的证据与权限边界

把块导出为 chunk 时，至少携带 `document_id`、page、block/table-cell ID、source revision、坐标/阅读顺序、分类与有效的对象级授权/ACL。chunk、Embedding、向量投影和检索缓存只是原文的派生物：来源撤权、到期或修订后应立即在在线候选中过滤，再按 [[知识库构建/03-版本删除与权限|版本、删除与权限]] 做撤权/删除传播。仅把 OCR `text` 写入向量库会丢失可引用证据，也可能让已撤权的内容继续被召回。

## 练习与自测

为“两页、第二页含表格”的匿名文档画数据流，并回答：

1. 哪些字段能定位到原图？
2. 表格的行列关系放在哪里？
3. 引擎升级后如何比较同一批文档？

若答案没有版本、坐标约定和原始来源，契约还不足以支持审计。

## 下一步与参考

下一步学习 [[OCR/01-基础与数据/02-成像原理与预处理|成像原理与预处理]]。参考 [Tesseract User Manual（当前 5.x 主线）](https://tesseract-ocr.github.io/tessdoc/) 与 [PaddleOCR PP-StructureV3 输出结构（latest/version3.x）](https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/PP-StructureV3.html)（获取日期：2026-07-22）。
