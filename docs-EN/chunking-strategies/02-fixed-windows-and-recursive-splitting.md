---
title: "Fixed Windows and Recursive Splitting"
tags:
  - ai-agent-engineer
  - chunking
  - testing
aliases:
  - Recursive Character Splitting
  - Fixed-Window Splitting
source_checked: 2026-07-22
source_baseline: LangChain Text Splitters and Unstructured Chunking official
  documentation checked through 2026-07-22
lang: en
translation_key: Chunking策略/02-固定窗口与递归切分.md
translation_source_hash: b30fd77f9e2de03a0a8fe9df9ec1092029ec15f2802487773672a8eb0d176668
translation_route: zh-CN/Chunking策略/02-固定窗口与递归切分
translation_default_route: zh-CN/Chunking策略/02-固定窗口与递归切分
---

# Fixed Windows and Recursive Splitting

## Learning objectives

You will start with fixed windows, which are the easiest strategy to verify, and understand stride, overlap, and termination conditions. You will then learn a recursive strategy that prioritizes natural boundaries and only cuts hard as a last resort. The goal is not to memorize a library class name; it is to verify that your own splitter never loses text, exceeds a bound, or loops forever.

## Fixed windows: establish a deterministic baseline first

Let the window limit be $S$ and let adjacent windows repeat $O$ units. The stride is:

$$
\text{stride}=S-O,\qquad 0\le O<S
$$

When length $L>S$, the number of windows is approximately:

$$
N=1+\left\lceil\frac{L-S}{S-O}\right\rceil
$$

For example, with $L=250,S=100,O=20$, the stride is 80 and the starts are 0, 80, and 160; the last chunk ends at the end of the input. If `O=S`, the stride is zero and the loop never advances, so configuration validation is not an optional optimization.

## A minimal runnable implementation

The following code splits a Python sequence by index. In production, `units` should come from the correct tokenizer or parsed elements; do not convert token IDs back into strings and concatenate them blindly.

```python
from collections.abc import Sequence  # Import the read-only sequence interface so both lists and tuples are valid inputs.
from typing import TypeVar  # Import the type-variable utility to retain the original type of input elements.

T = TypeVar("T")  # T represents any element type, such as a token, sentence, or parsed element.


def fixed_windows(  # Define a deterministic splitter that returns start, end, and window content.
    units: Sequence[T],  # The sequence of units to split; it is not assumed to be a string.
    *,  # Later parameters must be keywords, preventing size and overlap from being swapped positionally.
    size: int,  # The maximum number of units a window may contain: the hard max.
    overlap: int,  # The units repeated from the preceding window to preserve adjacent context.
) -> list[tuple[int, int, list[T]]]:  # Each result uses a half-open [start, end) range and carries its actual content.
    if isinstance(size, bool) or not isinstance(size, int) or size <= 0:  # bool is a subclass of int, so reject it separately.
        raise ValueError("size must be a positive integer")  # Fail immediately rather than entering a loop without a positive window.
    if (  # Then verify that overlap is an integer and guarantees a positive stride.
        isinstance(overlap, bool)  # Reject pseudo-integers such as True and False too.
        or not isinstance(overlap, int)  # Reject floats, strings, and other imprecise configurations.
        or not 0 <= overlap < size  # overlap equal to size would make size - overlap equal zero.
    ):
        raise ValueError("require 0 <= overlap < size")  # Make the non-advancing configuration explicit.

    result: list[tuple[int, int, list[T]]] = []  # Preserve every window in source order.
    start = 0  # The first window begins at unit 0.
    while start < len(units):  # Generate a window while its start is within the input.
        end = min(start + size, len(units))  # The final window may be short but never passes the input end.
        result.append((start, end, list(units[start:end])))  # Slice [start, end) and make an independent list.
        if end == len(units):  # Once the final unit is covered, do not create an overlap-only tail window.
            break  # End immediately so the output contains no redundant window.
        start += size - overlap  # Advance by a positive stride while retaining the requested overlap.
    return result  # Return all windows; an empty input naturally returns an empty list.
```

Returning `start/end` rather than text alone preserves verifiable source spans. Empty input returns an empty list; the splitter terminates immediately after the final window reaches the input end, avoiding an extra chunk that contains only overlap.

## What fixed windows can and cannot guarantee

They make it easy to guarantee:

- deterministic output;
- predictable hard maxima;
- complete coverage of source units;
- an exact overlap count;
- a baseline for cost and recall.

They cannot automatically guarantee:

- complete sentences, conditions, and pronoun references;
- headings that remain attached to their body;
- table headers that accompany data rows;
- intact functions or JSON objects;
- that neighboring chunks do not mix two topics.

Fixed windows are therefore a starting point for comparison, not a default production answer.

## The intuition behind recursive splitting

A recursive strategy prepares candidate boundaries from stronger to weaker, for example:

1. parsed sections or paragraphs;
2. blank lines;
3. line breaks;
4. language-specific sentence endings;
5. spaces;
6. a hard window when no boundary is available.

For an oversized fragment, try the stronger boundary first. If a resulting piece still exceeds the hard max, apply only a weaker boundary to that piece. Finally, merge adjacent small pieces in order until adding another would exceed the budget.

```text
split(part, boundary_index):
  if units(part) <= hard_max:
    return [part]
  if no weaker boundary:
    return hard_windows(part)

  pieces = split_by_current_boundary(part)
  if boundary made no progress:
    return split(part, boundary_index + 1)

  recursively split oversized pieces with weaker boundaries
  merge adjacent complete pieces without crossing hard_max
```

Current LangChain documentation lists recursive character splitting as a common general-purpose starting point. That is a practical default, not experimental proof that it is optimal for every corpus. Its default character-counting separators are `['\n\n', '\n', ' ', '']`, which fit languages commonly tokenized by spaces more closely. For Chinese, Japanese, or Thai, add sentence-ending punctuation, full-width punctuation, zero-width spaces, or other boundaries that match the actual text, and use fixtures to verify that meaning is not damaged. Even when the length function is changed to tokenizer counting, separators still only define candidate boundaries; the target model’s real token limit must still accept the hard max. Unstructured instead combines parsed elements first and continues splitting only when a single element is oversized. The input abstractions differ, so comparing class names alone is not meaningful.

## Merging is easier to get wrong than splitting

Recursively splitting without merging again creates isolated headings and one-sentence fragments. A merger should:

- preserve source order;
- avoid silently removing separator meaning and creating concatenations such as `foobar`;
- merge only within the same source, revision, ACL, and permitted structural boundary;
- close the current chunk before a candidate would exceed the hard max;
- send an oversized element itself to a fallback window;
- avoid producing chunks for blank fragments, while still measuring source offsets against normalized text.

If you call `strip()` before calculating character offsets, positions drift. A safer order is to normalize line endings and Unicode, record each unit’s character range, and then slice from the original normalized text.

## Language, code, and structural boundaries

Natural-language sentence splitting is not simple:

- Chinese full stops, question marks, and quotation-mark combinations need tests;
- English abbreviations, decimals, and URLs can trigger period rules incorrectly;
- a long string with no spaces still needs a hard fallback;
- emoji, combining characters, and Unicode normalization affect character offsets.

For code, prioritize file → class/function → syntax-tree boundaries; a fenced Markdown code block should not be split by ordinary paragraph separators; split tables by complete rows and include the table header as retrieval context. These rules are developed further in [[chunking-strategies/03-structural-and-semantic-chunking|Structural and Semantic Chunking]].

## Properties that must be tested

Example tests prove only individual examples. A splitter is better checked through invariants:

| Property | What failure means |
| --- | --- |
| Every source unit is covered at least once | Content was lost |
| Each chunk has length `<= hard max` | A downstream system may truncate or reject it |
| Ordinals are contiguous and order is stable | Citations and incremental updates are unpredictable |
| Every loop iteration advances | Some configurations can loop forever |
| Overlap appears only in expected windows | Duplication cost is uncontrolled |
| No source, revision, or ACL boundary is crossed | Source or permission contamination occurred |
| The same input and version produce the same result | The result cannot be cached, compared, or replayed |
| The content hash matches the actual body | Vectors or citations may use stale text |

Boundary cases should at least include: empty text, one unit, exactly the hard max, hard max + 1, a long string with no separator, all whitespace, multilingual text, an oversized code block, and an oversized table row.

## Common mistakes and diagnosis

- **The separator disappears**: check whether neighboring words were joined after merging, or assign the separator to the preceding or following piece.
- **The short tail appears twice**: the splitter did not `break` immediately after reaching the input end.
- **The last units are missing**: the window-count formula or `end` calculation is wrong.
- **Recursion makes no progress**: the current separator is absent but the same input is recursively processed again.
- **Strings are split before token spans are guessed**: citation offsets and tokenizer lengths will not align.
- **An oversized single element is “allowed”**: the hard max is no longer hard.

## Exercises

1. Calculate every half-open interval `[start, end)` and the actual duplication for $L=250,S=100,O=20$.
2. Add six `unittest` cases to `fixed_windows` above: empty input, exactly one window, a tail window, overlap, invalid configuration, and determinism.
3. Design a separator priority that orders Markdown headings, code fences, paragraphs, and sentences from strong to weak; state how blank lines inside a code fence are handled.
4. Explain why “rejoining the split strings equals the original text” cannot be checked directly when overlap exists, and propose a deduplicated verification method.

## Mastery checklist

- [ ] I can derive stride and the number of windows.
- [ ] I can prove that the loop advances and terminates at the input end.
- [ ] I treat the hard max as an inviolable contract.
- [ ] I know recursive splitting means strong-boundary priority + oversized fallback + small-piece merging.
- [ ] I check coverage, order, boundary isolation, hashes, and determinism.
- [ ] I do not generalize one language’s sentence-splitting regex to every corpus.

## Summary and next step

Fixed windows provide a reproducible lower bound, while recursive splitting tries to retain natural boundaries; reliable production inputs usually also include parsed structure. Next: [[chunking-strategies/03-structural-and-semantic-chunking|Structural and Semantic Chunking]].

## References

- [LangChain Text Splitters](https://docs.langchain.com/oss/python/integrations/splitters)
- [Unstructured: Chunking](https://docs.unstructured.io/open-source/core-functionality/chunking)

Sources checked on 2026-07-22. Return to [[chunking-strategies/00-index|the Chunking Strategies course index]].
