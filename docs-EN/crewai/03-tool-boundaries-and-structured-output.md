---
title: "Tool Boundaries and Structured Output"
aliases:
  - CrewAI Tools and Structured Output
  - CrewAI Tool and Output Contracts
tags:
  - crewai
  - tools
  - structured-output
source_checked: 2026-07-21
lang: en
translation_key: CrewAI/03-Tools边界与结构化输出.md
translation_source_hash: 0999498320ced64623d7fc9556e14b896ade62313d8d419abdca46349e8f6c6d
translation_route: zh-CN/CrewAI/03-Tools边界与结构化输出
translation_default_route: zh-CN/CrewAI/03-Tools边界与结构化输出
---

# Tool Boundaries and Structured Output

## Learning objectives

You will define parameter, return, authority, side-effect, and error contracts for CrewAI tools; understand the current official <code>BaseTool</code>/<code>@tool</code> shape; and use Task Pydantic/JSON output and guardrails to establish contracts between Agents.

## A tool is first an authority interface

A tool turns a model suggestion into a data read or external action. Each Agent receives only tools needed by its current Task: a researcher can read local sources, a writer consumes structured research results, and a reviewer should not hold publication authority.

Every tool contract needs at least:

| Field | Question |
| --- | --- |
| Name/description | When may it be used, and when may it not? |
| Parameter schema | What are its types, ranges, normalization, and rejection conditions? |
| Return schema | How are success, empty result, and error distinguished? |
| Authority | Which identity is used and which resources are reachable? |
| Side effect | Read-only, reversible, or irreversible? |
| Timeout | Does timeout mean failure or unknown commit state? |
| Retry | Which categories are retryable, and with what budget? |
| Idempotency | How is one business action recognized? |
| Audit | Which digest is retained, and which secrets are never logged? |

Parameters produced by a model must pass execution-layer validation. A Tool description helps select a Tool; it grants no authority.

## Current official custom-Tool shape

The official Tools page presents two primary approaches: subclass <code>BaseTool</code> with Pydantic <code>args_schema</code>, or decorate a function with <code>@tool</code>. The following is a minimal shape for reading; it was not run in this course’s real installed environment:

~~~python
from typing import Type  # Declare a type for the args_schema class object.
from crewai.tools import BaseTool  # Import the CrewAI base class for custom tools.
from pydantic import BaseModel, Field  # Define and constrain tool input with Pydantic.

class LocalSearchInput(BaseModel):  # Accept only type-checked, length-checked parameters.
    topic: str = Field(min_length=1, max_length=120)  # Reject empty or unusually long topics.

class LocalSearchTool(BaseTool):  # Implement a read-only local-search tool with a narrow boundary.
    name: str = "search_approved_local_sources"  # Use one action name rather than an ambiguous general-purpose tool.
    description: str = "Search only the approved local source catalog."  # State the permitted data boundary for the model.
    args_schema: Type[BaseModel] = LocalSearchInput  # Bind the schema so runtime validates input first.

    def _run(self, topic: str) -> str:  # Define the synchronous execution entry; production also needs authorization and audit.
        return search_catalog(topic)  # Call only an application-controlled catalog search.
~~~

<code>search_catalog</code> is your controlled implementation. Define a schema before returning a JSON string, and do not leak filesystem paths, credentials, or server stacks through exceptions. The official page also shows synchronous/asynchronous tools and <code>cache_function</code>, but cache only known-reusable reads—not payments, sends, or other side-effecting results.

## Async tools do not change commit semantics

The current Tools page supports <code>async def</code> functions decorated by <code>@tool</code> and asynchronous <code>_run</code>. That prevents one coroutine from blocking while it waits for network or file I/O; it **does not** prove that a remote request did not complete after a timeout or cancellation. For a write action, cancellation, disconnection, or timeout means <code>unknown_commit</code>. Query the receipt by idempotency key before retrying rather than assuming a cancelled function is safe to resend.

Concurrency also amplifies shared quotas, contention for the same resource, and logging correlation problems. Every call should carry a stable operation ID, deadline, and audit correlation ID.

## Separate read and write tools

Split a high-risk action into:

1. <code>preview_publish</code>: read-only; produces the normalized action, target, and diff.
2. The Flow stores the action fingerprint and asks for approval.
3. <code>publish_report</code>: verifies trusted approval, target, and idempotency ID.
4. <code>get_publication_receipt</code>: queried during recovery to learn whether commitment occurred.

Do not let a Tool search Task text for the words “approved.” An approval record must come from controlled state or an authorization service.

## Structured Task output

The official Tasks documentation lists:

- <code>output_pydantic=Model</code>: <code>TaskOutput.pydantic</code> contains a model instance;
- <code>output_json=Model</code>: <code>TaskOutput.json_dict</code> contains JSON output;
- the default guarantees only <code>raw</code>;
- <code>guardrail</code> can validate a Task output before it enters a downstream step.

Conceptual example:

~~~python
from pydantic import BaseModel  # Import the base model for structured output.
from crewai import Task  # Import Task, which declares an output contract.

class Claim(BaseModel):  # Represent a research statement that requires traceable evidence.
    text: str  # Store the statement text; factual correctness still needs external checking.
    source_ids: list[str]  # Store stable identifiers for sources supporting the statement.

class ResearchResult(BaseModel):  # Define the complete structured result of a research Task.
    claims: list[Claim]  # Collect all sourced statement objects.
    unknowns: list[str]  # Preserve evidence gaps explicitly instead of letting the model invent conclusions.

task = Task(  # Create a research Task accepted through a Pydantic model.
    description="Extract claims only from approved sources.",  # Bound the allowed evidence.
    expected_output="Claims with source IDs plus explicit unknowns.",  # Add natural-language requirements for the model.
    output_pydantic=ResearchResult,  # Ask the framework to parse the result into the model above.
)
~~~

Whether a real version permits omitted <code>agent</code>, the exact <code>guardrail</code> signature, and retry behavior must be verified against the pinned version. Structural validity does not prove factual correctness: still check that every <code>source_id</code> exists and that source text supports the claim.

## What a guardrail should do

Good deterministic guardrails include:

- JSON/Pydantic types;
- required fields, lengths, and enumerations;
- existence of cited IDs;
- prohibited tools or targets;
- whether a file path stays under an allowed root;
- iteration or cost-budget exhaustion.

Style and argument quality may use a model grader, but fix its rubric and calibrate it against human samples. A review Agent that lacks the same source as the producing Agent is not inherently more trustworthy.

## Tool error categories

Return stable categories such as <code>invalid_input</code>, <code>not_found</code>, <code>permission_denied</code>, <code>transient</code>, <code>permanent</code>, and <code>unknown_commit</code>. Retry only transient failure within a finite budget. A permission or policy rejection must not be bypassed by swapping Agents. For unknown commitment, query the receipt first.

~~~json
{
  "ok": false,
  "error": {
    "category": "permission_denied",
    "retryable": false,
    "message": "caller cannot publish to this target"
  }
}
~~~

- <code>ok</code> is the machine-readable success switch; downstream code must not treat a failed call as normal output.
- <code>error.category</code> is the stable class that determines retry or human escalation.
- <code>error.retryable</code> avoids guessing policy from a natural-language error message.
- <code>error.message</code> explains the failure to a caller; production must omit credentials, paths, and internal stacks.

## External content is untrusted data

Web pages, documents, MCP responses, and Knowledge fragments can contain prompt injection. The Tool layer must constrain paths, network targets, SQL/command parameters, and identity; a model cannot use instructions found in a document to expand its allowlist. When Shell or code execution is necessary, use an isolated service and disposable environment rather than directly executing model-generated strings on the host.

## Common mistakes and diagnosis

- **All Agents share one Tool set:** build a least-privilege allowlist per Task.
- **Only checking that JSON parses:** also check field semantics, sources, and business constraints.
- **Giving natural-language errors to a retryer:** adapt them into finite categories.
- **Automatically caching/retrying a write:** use a business idempotency ID and receipt.
- **Letting a model choose any output path:** normalize it and ensure it lies under the allowed root.
- **Copying credential-placeholder conventions from an official example:** real values come only from the environment or a secret service.

## Exercise

For a research Crew, design <code>search_local_sources</code>, <code>read_source</code>, <code>preview_publish</code>, and <code>publish_report</code>:

1. write parameter and return schemas;
2. identify each Agent’s Tool allowlist;
3. design approval, action fingerprint, and idempotency receipt for publication;
4. write eight failure samples, including path escape, unknown source, permission denial, and commit timeout;
5. explain which checks belong to a Task guardrail and which must execute in the Tool service.

## Mastery check

- [ ] Explain the difference between a Tool description and execution authorization.
- [ ] Recognize the current official <code>BaseTool</code>, <code>args_schema</code>, and <code>@tool</code> shapes.
- [ ] Constrain Task artifacts with <code>output_pydantic</code>/<code>output_json</code>.
- [ ] Validate schema, sources, and business semantics together.
- [ ] Design preview, approval, idempotency, and receipts for a write Tool.

## Next step

Continue to [[crewai/04-memory-knowledge-and-context|Memory, Knowledge, and Context]] to decide which information belongs to which lifecycle layer.

## References

- [CrewAI Tools](https://docs.crewai.com/en/concepts/tools) (dynamic documentation; synchronous/asynchronous Tool and cache boundaries checked 2026-07-21).
- [CrewAI Tasks](https://docs.crewai.com/en/concepts/tasks) (page label <code>v1.12.1</code>; checked 2026-07-14).
- [CrewAI Agents](https://docs.crewai.com/en/concepts/agents) (page label <code>v1.14.6</code>; checked 2026-07-14).
- [[agentic-design-patterns/00-index|Agentic Design Patterns]].
