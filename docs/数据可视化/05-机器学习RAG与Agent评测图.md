---
title: 机器学习、RAG 与 Agent 评测图
tags:
  - ai-agent-engineer
  - data-visualization
aliases:
  - AI Evaluation Visualization
source_checked: 2026-07-14
source_baseline:
  - scikit-learn 1.9.0 official model-evaluation and visualization documentation
  - Matplotlib 3.11.0 official documentation
---

# 机器学习、RAG 与 Agent 评测图

## 本节目标

为分类器、检索链和 Agent 系统选择能定位失败来源的图，把质量、代价、尾延迟、超时与安全风险分开呈现，而不是压成一个总分。

## 分类器

- **混淆矩阵**：行列分别是真实/预测标签；必须标方向和是否按行归一化。
- **PR 曲线**：类别不平衡、关注正类时展示 precision—recall 随阈值变化。
- **ROC 曲线**：展示 TPR—FPR 权衡，但正类极少时需同时看 PR 与实际数量。
- **校准图**：预测概率分桶后比较预测与实际频率。
- **学习曲线**：训练样本数与训练/验证分数，帮助判断是否继续收集数据。

混淆矩阵必须明确“行是真实、列是预测”还是相反。绝对数回答事故规模，按行归一化回答各真实类的召回模式；两者最好在格子里同时显示为 `count / row %`。归一化不能替代分母：一个 50% 的格子可能来自 1/2，也可能来自 500/1000。

PR/ROC 都是阈值扫描，不代表已选定生产阈值的实际成本。最终报告还应标出部署阈值、该点的精确率/召回率、正类基率和绝对错误数。校准图的分箱也会改变外观，应报告分箱方法与每箱样本数。

## RAG

至少分开检索与生成：

- 检索：Recall@k、MRR/nDCG 等随 `k` 变化，并按查询类型拆分。
- 生成：有证据支持、答案正确、引用准确、拒答合理等维度。
- 系统：端到端成功率、延迟、token、费用和无结果率。

若只画回答总分，无法判断失败来自解析、chunking、retrieval、reranking 还是生成。

把查询作为观察单元并保留切片：头部/长尾查询、语言、文档新旧、是否有答案。`Recall@k` 随 `k` 上升并不免费——上下文长度、延迟和噪声也可能上升，因此质量曲线应与成本/延迟放在共享实验版本下解读。

## Agent

推荐一个“结果—代价—风险”组合：

1. 各任务类成功率及样本数/区间。
2. p50/p95 延迟与超时比例。
3. 工具调用错误类型的堆叠或小倍图。
4. 单任务成本与成功率散点图，标出 Pareto 候选。
5. 安全失败按严重度单独报告，不用总体成功率稀释。

成本—成功率散点图中，“Pareto 候选”指不存在另一个版本同时成本不高且成功率不低、并至少一项严格更好的点。它只表示在当前两个指标和当前评测集上不被支配，不表示自动成为最佳版本；安全门槛、p95 延迟和置信区间仍需单独审查。

## 消融与版本比较

消融图每次只移除一个组件，并在同一评测集、配置和随机性设计下比较。若多个因素同时变化，只能称版本对比，不能归因于某一个组件。

## 练习

为 RAG 回答“引用错误率上升”设计三张诊断图，分别检查数据来源、检索排名和生成引用。每张图写清分母与切片。

一种可验收答案：① 按数据源版本/文档年龄画引用错误数与查询数；② 按 gold 文档排名画 ECDF 或 Recall@k 曲线并按查询类型分层；③ 画“已检索到支持证据但引用错误/未检索到支持证据”的堆叠计数。三张图都固定同一查询快照，保留无答案与超时，并报告绝对数。

## 掌握检查

- [ ] 我能同时解释混淆矩阵的绝对数、行百分比和轴方向。
- [ ] 我知道 PR/ROC 曲线不能替代部署阈值处的实际错误数。
- [ ] 我会把 RAG 的解析、检索、重排、生成与端到端失败分开画。
- [ ] 我能解释 Pareto 候选的定义与局限，不把它当自动决策。
- [ ] 我会把安全失败、超时和关键子群从总体均值中单独暴露。

下一步：[[数据可视化/06-误导风险与可访问性|误导风险与可访问性]]。

## 参考资料

资料核验日期：2026-07-14；scikit-learn `stable` 当前为 1.9.0，后续版本的展示类接口应重新核对。

- [scikit-learn: Visualizations](https://scikit-learn.org/stable/visualizations.html)
- [scikit-learn: Model evaluation](https://scikit-learn.org/stable/modules/model_evaluation.html)
- [scikit-learn: Confusion matrix](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.confusion_matrix.html)
- [scikit-learn: Precision-Recall](https://scikit-learn.org/stable/auto_examples/model_selection/plot_precision_recall.html)
- [scikit-learn: Calibration curves](https://scikit-learn.org/stable/modules/calibration.html)
