---
title: "Zero-Shot Prompting, Examples, and Counterexamples"
tags:
  - prompt-engineering
  - few-shot
aliases:
  - Few-shot prompting
source_checked: 2026-07-21
content_origin: original
content_status: dynamic
source_baseline:
  - OpenAI Prompt engineering guide
  - Anthropic Prompt engineering overview
  - Google Gemini Prompt design strategies
lang: en
translation_key: 提示词工程/02-零样本、示例与反例.md
translation_source_hash: f679dcc504269a6ceeb46465416a2a1eb580ab8dd98f78857927c73984ce310f
translation_route: zh-CN/提示词工程/02-零样本、示例与反例
translation_default_route: zh-CN/提示词工程/02-零样本、示例与反例
---

# Zero-Shot Prompting, Examples, and Counterexamples

## Goal of this lesson

Understand the trade-offs between zero-shot and few-shot prompting, choose examples that cover boundaries, and avoid leakage, ordering bias, and inconsistent formats.

## Treat zero-shot prompting as a comparable baseline

**Zero-shot prompting** supplies rules and input only. It is inexpensive and simple to maintain. **Few-shot prompting** provides several input-output pairs and is useful when label boundaries, tone, format, or exceptions are difficult to specify with prose alone. In practice, preserve one zero-shot version as a comparison point, then let evaluation results decide whether examples should be added. This is not a rule that every model must use zero-shot prompting first.

Provider guidance can differ and can change with model families. For example, documentation checked on **2026-07-21** emphasizes diverse examples in OpenAI guidance, while Google's Gemini prompt-design guidance explicitly recommends always including few-shot examples. Neither is a law across models. Fix the model configuration and compare zero-shot and few-shot versions on your own input distribution.

More examples are not always better. They consume context and can lead the model to imitate incidental features. Few-shot prompting is inference-time context; it does not train the model. Choose examples that cover:

- a typical positive case;
- a boundary case easily confused with a neighboring category;
- a case with missing information that should return **unknown**;
- a counterexample containing an untrusted command that must still be processed as data.

## Align format and labels

If the rules say **technical** but examples return **tech**, the model receives conflicting signals. Example fields, casing, null handling, and explanation length must match the output contract.

~~~text
Input: The payment is shown as successful, but the download button is disabled.
Output: {"label":"technical","reason":"The download feature is unavailable after payment.","evidence":"the download button is disabled"}

Input: The message only says, "Please help."
Output: {"label":"other","reason":"There is not enough information to determine the issue type.","evidence":null}
~~~

De-identify production data. Do not put real accounts, keys, or protected personal information in a prompt repository. Also separate training and evaluation examples so that repeatedly tuning a prompt against a test set is not mistaken for generalization.

A counterexample should show the expected behavior too: include input with an overreaching command or neighboring label and pair it with the correct output. Do not merely display a wrong answer and make the model guess what is wrong; it may imitate the wrong format or phrasing. Examples inside the prompt, the development set, and the held-out evaluation set must be distinct assets. Once a case is repeatedly used for tuning, it is no longer a reliable held-out case.

## Use a minimal controlled experiment to judge value

Fix the model configuration and evaluation set, then compare:

1. v1 with rules only;
2. v2 with typical cases;
3. v3 with boundary cases.

Record error categories in addition to overall accuracy, such as guessing when information is missing, unparsable JSON, or confusion at a category boundary. If v3 improves only training examples while harming new cases, revert it or choose different examples.

## Common pitfalls

- **Selecting only ideal examples:** this does not teach the model how to handle ambiguous input.
- **An imbalanced label distribution:** nine cases from one class out of ten can create unintended bias.
- **Treating long reasoning as the reference answer:** it can expose internal information, increase cost, and still fail to improve the task metric.
- **Examples drifting from the current business:** rules change while old examples do not. Version templates and examples together.

## Practice and self-check

Write four examples for three-way customer-support-message classification. Include at least one case of “insufficient information, classify as **other**” and one case containing prompt-injection text. Fields must match this course's [[prompt-engineering/examples/response.schema.json|response schema]]. Hide the expected outputs and ask a peer to annotate them. If people cannot agree, revise the label definitions before adding more examples.

## Mastery check

- [ ] I can explain the cost, benefit, and appropriate use of zero-shot and few-shot prompting.
- [ ] My examples cover typical, boundary, insufficient-information, and adversarial input rather than only attractive positive cases.
- [ ] Example fields, labels, nulls, and length limits fully match the production contract.
- [ ] I compare versions with the same model configuration and held-out cases, rather than following a provider slogan.

## Next step

Continue to [[prompt-engineering/03-structured-output-and-contracts|Structured output and contracts]] to turn the examples' conventions into a contract that a program can check.

## References

- [OpenAI: Prompt engineering](https://developers.openai.com/api/docs/guides/prompt-engineering) (accessed 2026-07-21)
- [Anthropic: Prompt engineering overview](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview) (accessed 2026-07-21)
- [Google: Prompt design strategies](https://ai.google.dev/gemini-api/docs/prompting-strategies) (accessed 2026-07-21)

