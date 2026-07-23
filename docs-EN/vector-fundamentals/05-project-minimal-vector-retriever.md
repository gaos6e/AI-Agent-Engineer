---
title: "Project: a minimal vector retriever"
tags: [ ai-agent-engineer, vectors, project ]
aliases: [ Vector retrieval project ]
source_checked: 2026-07-22
source_baseline:
  - Google Measuring Similarity from Embeddings
  - scikit-learn 1.9.0 pairwise metrics documentation
  - "Python 3.11.9 standard-library teaching implementation; nine unittest cases
    verified in normal and -O modes with -W error on 2026-07-22"
execution_verified: 2026-07-22
content_origin: original
content_status: validated
lang: en
translation_key: 向量基础/05-项目-最小向量检索器.md
translation_source_hash: 4962e3b1c2bd4898c341e5d84b908608f048f08c3667b80aa8c850a4bf15ecf3
translation_route: zh-CN/向量基础/05-项目-最小向量检索器
translation_default_route: zh-CN/向量基础/05-项目-最小向量检索器
---

# Project: a minimal vector retriever

## Project goal

Run [[vector-fundamentals/examples/vector_search.py|vector_search.py]] to implement dot product, L2 norm, unit normalization, cosine, Euclidean distance, exact top-*k*, and Recall@*k* using only the Python standard library. [[vector-fundamentals/examples/test_vector_search.py|test_vector_search.py]] fixes the mathematical relationships, ranking direction, invalid inputs, and command-line behavior with nine tests. The vectors are hand-constructed three-dimensional teaching data, not a real embedding model.

## Environment and execution

The project has no third-party dependency. To establish a stable habit, it is still recommended to use a separate `venv` on Windows 11 / PowerShell 7 and place it outside the vault:

```powershell
$exampleDir = (Resolve-Path '.\Knowledge\AI Agent Engineer\docs-EN\vector-fundamentals\examples').Path
$venv = Join-Path $env:LOCALAPPDATA 'Gao-venvs\vector-search'
$python = Join-Path $venv 'Scripts\python.exe'

py -3.11 -m venv $venv
& $python -m pip --version
& $python -B -W error (Join-Path $exampleDir 'vector_search.py')
& $python -B -O -W error (Join-Path $exampleDir 'vector_search.py')
& $python -B -W error -m unittest discover -s $exampleDir -p 'test_*.py' -v
& $python -B -O -W error -m unittest discover -s $exampleDir -p 'test_*.py' -v
```

No package installation is needed. `pip --version` only confirms that any future dependency would enter the intended environment. `-B` prevents bytecode caches, and `-O` removes ordinary `assert` statements. The script uses explicit exceptions for its important teaching checks, so normal and optimized modes retain the same acceptance behavior.

## Data, output, and interpretation

The query is `(1, 1, 0)`; the three document vectors represent a Python API, HTTP retries, and cat care. Under both cosine and Euclidean metrics, the script places the first two API documents in the top two:

| Metric | Rank 1 | Rank 2 | Ranking direction |
| --- | --- | --- | --- |
| cosine | `python-api`, approximately 0.9986 | `http-retry`, approximately 0.9948 | Larger is more similar |
| Euclidean | `python-api`, approximately 0.1000 | `http-retry`, approximately 0.2449 | Smaller is more similar |

The hand-authored relevance set is `{python-api, http-retry}`, so `Recall@2=2/2=1.0`. That proves only that this implementation agrees with the labels on three artificial records; it does not prove real semantic-model quality, ANN-index quality, or RAG answer quality.

## Questions to answer while reading the code

1. Why does `top_k` sort cosine/dot descending and Euclidean ascending?
2. Why does `cosine` check both norms?
3. Why are hand-authored relevance sets necessary for evaluation instead of being inferred from vector scores?
4. Why does exact-search complexity grow with both document count and dimension?
5. Why are equal scores secondarily sorted by document ID? How does that support reproducible tests?
6. Why must `_require` not be replaced by a bare `assert` as the sole runtime validation?

## Verification for this revision

> [!success] Verified on 2026-07-22
> Under Python 3.11.9, the script has identical output in normal and `-O` modes; all nine `unittest` cases pass in normal and `-O` modes with `-W error`. Acceptance uses only standard-library teaching data—no credentials, network, third-party dependencies, or real embedding data.

The tests cover known dot/norm/distance values; equivalence of normalized dot and cosine rankings; magnitude-induced metric ranking changes; ascending Euclidean order and stable tie breaking; Recall@*k*; empty/zero vectors, unequal dimensions, `NaN`, and infinity; invalid *k*, metric, and documents; and `main()` output.

## Required extensions

1. Multiply an irrelevant document by 100 and compare dot-product and cosine rankings.
2. Normalize every vector first and verify that dot and cosine rankings agree.
3. Add two queries with incomplete relevance sets, then explain the labeling bias in Recall.
4. Use the existing Euclidean top-*k* to verify the ranking relationship for unit vectors, and explain the condition under which “numeric values differ but ranking is equivalent.”
5. Record a fictitious model version for every vector; simulate mixing in another coordinate space and explain why the arithmetic still runs while the semantics are invalid.

## Common errors and troubleshooting

| Error | Consequence | Diagnosis and correction |
| --- | --- | --- |
| Sort cosine ascending | The least similar result is first | State “larger similarity is better; smaller distance is better” before coding. |
| Normalize only the query | Inner product is no longer equivalent to cosine | Apply the same normalization convention to query and documents. |
| Replace a zero vector with a tiny constant and continue | Hides an upstream data or model failure | Reject it explicitly, record its origin, and repair the generation path. |
| Compare floating-point results with `==` | Rounding makes tests fragile | Use absolute/relative tolerances and test rankings and boundaries. |
| Generate “relevance labels” from retrieval scores | Evaluation merely repeats model preference | Build ground truth from the task definition and human/authoritative data. |
| Extrapolate exact small-data results directly to ANN | Ignores index recall loss and filtering cost | Use exact top-*k* as the reference for ANN Recall@*k*, latency, and memory. |

## Mastery criteria

- [ ] I can implement and calculate the three measures without a library.
- [ ] I raise explicit errors for zero vectors and unequal dimensions.
- [ ] I can sort correctly for a metric's direction.
- [ ] I can calculate Recall@*k* and explain the limits of ground truth.
- [ ] I do not extrapolate teaching-vector results into claims about real model capability.
- [ ] I can run normal/`-O` scripts and both test groups, and explain why every exception check still applies.

Return to [[vector-fundamentals/00-index|Vector Fundamentals]].

## References

Sources verified on 2026-07-22.

- [Google: Measuring Similarity from Embeddings](https://developers.google.com/machine-learning/clustering/dnn-clustering/supervised-similarity)
- [scikit-learn 1.9.0: Pairwise metrics, affinities and kernels](https://scikit-learn.org/stable/modules/metrics.html)
