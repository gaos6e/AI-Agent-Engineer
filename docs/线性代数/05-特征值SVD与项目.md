---
title: 特征值、SVD 与最小二乘项目
tags: [ ai-agent-engineer, 线性代数, project ]
aliases: [ SVD 与降维 ]
source_checked: 2026-07-14
source_baseline:
  - MIT OpenCourseWare 18.06SC Linear Algebra
  - NumPy stable SVD and lstsq documentation
---

# 特征值、SVD 与最小二乘项目

## 本节目标

先用特征值和 SVD 建立“矩阵沿哪些方向缩放”的直觉，再完成一个不依赖第三方库、带输入契约和测试的最小二乘项目。重点是能解释方向、秩、残差和数值边界，而不是把分解函数当成黑箱。

## 特征向量：变换后方向不变

非零 $v$ 若满足：

$$Av=\lambda v$$

则 $v$ 是特征向量、$\lambda$ 是特征值。变换只沿该方向缩放或翻转。例：对角矩阵 `diag(3, 0.5)` 的坐标轴方向是特征向量。

用途：分析迭代系统的增长/衰减、协方差矩阵的主方向、某些优化问题的曲率。不是所有矩阵都有足够实特征向量，不能把特征分解当万能工具。

特征值只对方阵定义；同一个线性变换换基后矩阵写法会变，但特征值保持。对称实矩阵有一组正交实特征向量，这是协方差矩阵和 PCA 特别方便的原因。一般实矩阵可能有复特征值，也可能不可对角化。

## SVD：任意矩阵的方向分解

$$A=U\Sigma V^T$$

$U,V$ 的列是正交方向，$\Sigma$ 的非负奇异值表示各方向缩放强度。SVD 适用于非方阵；非零奇异值数量等于秩。

若 $A$ 为 $m\times n$，完整 SVD 的具体 shape 取决于 full/reduced 约定；工程上必须查库文档。右奇异向量位于输入空间，左奇异向量位于输出空间，不能只看到“方向”二字就互换。

保留前 $k$ 个最大奇异值可得低秩近似：

$$A_k=U_k\Sigma_kV_k^T$$

它可用于压缩、去噪和 PCA 的计算基础。选择 $k$ 是信息保留与成本的权衡；低方差方向也可能承载稀有但关键的安全信号。

按 Frobenius 范数或 2-范数，截断 SVD 给出给定秩 $k$ 的最佳低秩近似；“最佳”只针对该数学误差，不保证下游正确率、安全性或语义可解释性最佳。

## 在 ML/Embedding 中的用途

- PCA 寻找数据方差最大的正交方向，需先中心化；主成分不等于因果因素或“最有业务价值”。
- 权重矩阵低秩近似可减少参数和计算，但要实际评测任务损失。
- 检索向量降维可省内存并加速，但会改变近邻排序。
- 小奇异值意味着某些方向接近不可辨识，求解可能对噪声敏感。

## 项目：从零拟合线性模型

实现：[[线性代数/examples/least_squares.py|least_squares.py]]｜测试：[[线性代数/examples/test_least_squares.py|test_least_squares.py]]。

### 输入与输出契约

- `xs`、`ys` 是等长序列，至少两个观测；
- 每个值必须是有限实数，布尔值、字符串、`NaN` 和无穷值被拒绝；
- `x` 必须至少有两个不同值，否则斜率不可识别；
- 输出 `LineFit` 记录样本量、斜率、截距、MSE 和两条残差正交诊断；
- 本项目只拟合含截距的一元普通最小二乘，不声称因果或线上泛化。

实现先中心化 $x,y$，用 `math.fsum` 与 `statistics.fmean` 计算闭式解，再验证：

$$\sum_i r_i=0,\quad \sum_i(x_i-\bar x)r_i=0$$

### 运行与测试

从 vault 根目录运行：

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
python -B '.\Knowledge\AI Agent Engineer\docs\线性代数\examples\least_squares.py'
python -B -m unittest discover `
    -s '.\Knowledge\AI Agent Engineer\docs\线性代数\examples' `
    -p 'test_*.py' `
    -v
```

脚本预期输出：

```text
observations=5
weight=1.990000 bias=0.090000 mse=0.010200
residual-sum=-0.000000000000
centered-x-dot-residuals=0.000000000000
```

浮点零可能显示为 `-0.000...`；这不是负误差，只是舍入后的符号位。判断正交使用容差，不要求文本必须写成正零。

8 项测试覆盖：精确直线、两点直线、带噪样例与残差正交、行顺序不变性、大坐标偏移、常量 $x$、长度边界，以及非有限/非数值/布尔输入。

> [!success] 2026-07-14 实际验证
> 在 Python 3.11.9 下，脚本以普通模式和 `python -O` 模式运行结果一致；8 项 `unittest` 全部通过，两个 Python 文件也通过 `py_compile` 语法检查。验证生成的 `__pycache__` 已删除，未作为知识库内容保留。

> [!note] NumPy 扩展层
> 本机未安装 NumPy，因此核心项目只用标准库并已实际运行。以后进入科学计算环境，可用官方 `numpy.linalg.lstsq` 对照结果；它还返回秩与奇异值，并在多解时返回最小 2-范数解。使用前记录 NumPy 版本和 `rcond`，不要只复制一行调用。

## 必做扩展

1. 把所有 $x$ 改成相同值，观察脚本拒绝拟合；用秩解释。
2. 加入一个极端离群点，比较参数和 MSE。
3. 手算小数据，验证代码不是“黑箱”。
4. 将全部 $x$ 加上 $10^9$，观察中心化实现如何工作；再解释截距为何会改变。
5. 构造两个几乎相同的特征列，联系 [[线性代数/04A-数值稳定性与条件数|数值稳定性与条件数]]。
6. 若以后用 NumPy，比较 `linalg.lstsq`，不要显式求逆，并记录库版本、`rcond`、rank 和奇异值。

## 常见错误与排查

- 用 `assert` 承担生产输入检查；`python -O` 会移除 assert。本项目使用显式异常和退出状态。
- 只看 MSE，不检查残差、数据图、离群点和验证集。
- 把所有 $x$ 相同导致的不可识别误称为“样本太少”；即使复制更多相同 $x$，秩仍不增加。
- 把数值上能返回结果当作参数稳定；近常量 $x$ 仍可能非常敏感。
- 用显式逆实现最小二乘，却不检查秩、条件数和求解器契约。

## 掌握检查

- [ ] 能解释特征向量与奇异向量不是同一概念。
- [ ] 能用奇异值说明秩与近奇异。
- [ ] 能解释 PCA 保留高方差而非保证任务最优。
- [ ] 项目普通模式与 `-O` 模式输出一致，8 项测试通过。
- [ ] 我能解释输入契约、中心化公式和残差为何正交。
- [ ] 我能区分代数最优、数值稳定和统计泛化。

## 参考资料

核验日期：**2026-07-14**。

- [MIT OpenCourseWare：18.06SC Linear Algebra](https://ocw.mit.edu/courses/18-06sc-linear-algebra-fall-2011/)
- [MIT 18.06SC：Least Squares, Determinants and Eigenvalues](https://ocw.mit.edu/courses/18-06sc-linear-algebra-fall-2011/pages/least-squares-determinants-and-eigenvalues/)
- [NumPy：`linalg.svd`](https://numpy.org/doc/stable/reference/generated/numpy.linalg.svd.html)
- [NumPy：`linalg.lstsq`](https://numpy.org/doc/stable/reference/generated/numpy.linalg.lstsq.html)

返回 [[线性代数/00-目录|线性代数]]。
