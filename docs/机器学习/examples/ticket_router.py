"""Train and evaluate a tiny offline Chinese ticket-intent classifier."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Sequence

from sklearn import __version__ as sklearn_version
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline


Sample = tuple[str, str]

SAMPLES: tuple[Sample, ...] = (
    ("登录时一直提示密码错误", "账号"),
    ("手机换了以后收不到验证码", "账号"),
    ("怎样修改绑定邮箱", "账号"),
    ("账号突然被锁定了", "账号"),
    ("忘记密码如何找回", "账号"),
    ("无法完成双重验证", "账号"),
    ("请帮我注销旧账号", "账号"),
    ("用户名能不能修改", "账号"),
    ("重复扣款需要退款", "退款"),
    ("购买后不想要了怎么退", "退款"),
    ("会员取消后钱没有到账", "退款"),
    ("误付了一笔订单", "退款"),
    ("订单已经取消请退钱", "退款"),
    ("退款申请显示审核中", "退款"),
    ("试用期扣费希望退回", "退款"),
    ("发票金额不对想撤销付款", "退款"),
    ("页面打开后一直是空白", "技术"),
    ("上传文件总是失败", "技术"),
    ("接口请求返回服务器错误", "技术"),
    ("应用启动后立刻闪退", "技术"),
    ("搜索结果加载不出来", "技术"),
    ("更新版本以后按钮失效", "技术"),
    ("网络正常但是无法同步", "技术"),
    ("导出文件出现乱码", "技术"),
)


@dataclass(frozen=True)
class DatasetSplit:
    train_texts: tuple[str, ...]
    test_texts: tuple[str, ...]
    train_labels: tuple[str, ...]
    test_labels: tuple[str, ...]
    random_state: int


@dataclass(frozen=True)
class PredictionError:
    text: str
    expected: str
    predicted: str
    confidence: float


@dataclass(frozen=True)
class EvaluationResult:
    split: DatasetSplit
    labels: tuple[str, ...]
    baseline_accuracy: float
    accuracy: float
    macro_f1: float
    confusion: tuple[tuple[int, ...], ...]
    report_text: str
    errors: tuple[PredictionError, ...]


def validate_samples(samples: Sequence[Sample]) -> tuple[Sample, ...]:
    """Validate the teaching dataset and return normalized immutable rows."""

    try:
        rows = list(samples)
    except TypeError:
        raise ValueError("samples 必须是 (text, label) 序列") from None
    if not rows:
        raise ValueError("samples 不能为空")

    normalized: list[Sample] = []
    seen_texts: set[str] = set()
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, (tuple, list)) or len(row) != 2:
            raise ValueError(f"sample {index} 必须包含 text 和 label")
        text, label = row
        if not isinstance(text, str) or not isinstance(label, str):
            raise ValueError(f"sample {index} 的 text/label 必须是字符串")
        clean_text = text.strip()
        clean_label = label.strip()
        if not clean_text or not clean_label:
            raise ValueError(f"sample {index} 的 text/label 不能为空")
        if clean_text in seen_texts:
            raise ValueError(f"发现重复文本：{clean_text!r}")
        seen_texts.add(clean_text)
        normalized.append((clean_text, clean_label))

    counts = Counter(label for _, label in normalized)
    if len(counts) < 2:
        raise ValueError("分类至少需要两个类别")
    if min(counts.values()) < 4:
        raise ValueError("每类至少需要 4 条样本以支持分层切分")
    return tuple(normalized)


def split_dataset(
    samples: Sequence[Sample],
    *,
    test_size: float | int = 0.25,
    random_state: int = 42,
) -> DatasetSplit:
    """Create a deterministic stratified split over unique teaching rows."""

    rows = validate_samples(samples)
    if isinstance(random_state, bool) or not isinstance(random_state, int):
        raise ValueError("random_state 必须是整数")
    if isinstance(test_size, bool) or not isinstance(test_size, (int, float)):
        raise ValueError("test_size 必须是比例或正整数")
    if isinstance(test_size, float) and not 0.0 < test_size < 1.0:
        raise ValueError("浮点 test_size 必须位于 (0, 1)")
    if isinstance(test_size, int) and not 0 < test_size < len(rows):
        raise ValueError("整数 test_size 必须介于 1 与样本总数之间")

    indices = list(range(len(rows)))
    labels = [label for _, label in rows]
    try:
        train_indices, test_indices = train_test_split(
            indices,
            test_size=test_size,
            stratify=labels,
            random_state=random_state,
        )
    except ValueError as exc:
        raise ValueError(f"当前类别数量无法完成分层切分：{exc}") from exc

    return DatasetSplit(
        train_texts=tuple(rows[index][0] for index in train_indices),
        test_texts=tuple(rows[index][0] for index in test_indices),
        train_labels=tuple(rows[index][1] for index in train_indices),
        test_labels=tuple(rows[index][1] for index in test_indices),
        random_state=random_state,
    )


def build_model() -> Pipeline:
    """Build a leakage-resistant text preprocessing and classifier pipeline."""

    return Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(analyzer="char", ngram_range=(2, 4)),
            ),
            (
                "classifier",
                LogisticRegression(
                    l1_ratio=0.0,
                    solver="lbfgs",
                    max_iter=1_000,
                    random_state=42,
                ),
            ),
        ]
    )


def evaluate(
    samples: Sequence[Sample] = SAMPLES,
    *,
    test_size: float | int = 0.25,
    random_state: int = 42,
) -> EvaluationResult:
    """Fit the baseline and pipeline, then return auditable test metrics."""

    split = split_dataset(
        samples,
        test_size=test_size,
        random_state=random_state,
    )
    labels = tuple(sorted(set(split.train_labels) | set(split.test_labels)))

    baseline = DummyClassifier(strategy="most_frequent")
    baseline_features = [[0.0] for _ in split.train_labels]
    baseline.fit(baseline_features, split.train_labels)
    baseline_predictions = baseline.predict(
        [[0.0] for _ in split.test_labels]
    )

    model = build_model()
    model.fit(split.train_texts, split.train_labels)
    predictions = model.predict(split.test_texts)
    probabilities = model.predict_proba(split.test_texts)

    errors: list[PredictionError] = []
    for text, expected, predicted, row_probabilities in zip(
        split.test_texts,
        split.test_labels,
        predictions,
        probabilities,
    ):
        if expected != predicted:
            errors.append(
                PredictionError(
                    text=text,
                    expected=expected,
                    predicted=str(predicted),
                    confidence=float(max(row_probabilities)),
                )
            )

    matrix = confusion_matrix(split.test_labels, predictions, labels=labels)
    return EvaluationResult(
        split=split,
        labels=labels,
        baseline_accuracy=float(
            accuracy_score(split.test_labels, baseline_predictions)
        ),
        accuracy=float(accuracy_score(split.test_labels, predictions)),
        macro_f1=float(
            f1_score(
                split.test_labels,
                predictions,
                labels=labels,
                average="macro",
                zero_division=0,
            )
        ),
        confusion=tuple(tuple(int(value) for value in row) for row in matrix),
        report_text=classification_report(
            split.test_labels,
            predictions,
            labels=labels,
            zero_division=0,
        ),
        errors=tuple(errors),
    )


def main() -> int:
    result = evaluate()
    print(f"scikit-learn={sklearn_version}")
    print(
        f"train={len(result.split.train_texts)} "
        f"test={len(result.split.test_texts)} "
        f"random_state={result.split.random_state}"
    )
    print(f"labels={','.join(result.labels)}")
    print(f"baseline-accuracy={result.baseline_accuracy:.3f}")
    print(
        f"accuracy={result.accuracy:.3f} "
        f"macro-f1={result.macro_f1:.3f}"
    )
    print("confusion-matrix rows=true columns=predicted")
    for label, row in zip(result.labels, result.confusion):
        print(f"- {label}: {row}")
    print(result.report_text.rstrip())
    print("errors:")
    if not result.errors:
        print("- 本次切分没有误分类；请勿据此推断已能上线。")
    for error in result.errors:
        print(
            f"- text={error.text!r} expected={error.expected} "
            f"predicted={error.predicted} confidence={error.confidence:.3f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
