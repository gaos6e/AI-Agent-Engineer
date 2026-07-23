---
title: "Anthropic Claude API Calls"
source: https://platform.claude.com/docs/en/claude_api_primer
source_checked: 2026-07-22
source_baseline:
  - Anthropic API usage primer, Python SDK, Messages tool handling, Model IDs
    and versioning
content_origin: curated
content_status: dynamic
execution_verified: false
verification_note: "The current Messages entry point, model-ID semantics, and
  offline syntax were checked; no real credentials or network calls were used."
tags: [ api, ai-api, anthropic, claude, python ]
aliases: [ Claude API, Anthropic API ]
lang: en
translation_key: API/AI API 调用/02-Anthropic Claude API.md
translation_source_hash: 74b4cdbdc5c214c4525f18663065bfe43b3651a2ffa5d4669e10164d8387a9dc
translation_route: zh-CN/API/AI-API-调用/02-Anthropic-Claude-API
translation_default_route: zh-CN/API/AI-API-调用/02-Anthropic-Claude-API
---

# Anthropic Claude API Calls

> [!source] Official source
> This note follows the [API usage primer](https://platform.claude.com/docs/en/claude_api_primer), [Python SDK](https://platform.claude.com/docs/en/cli-sdks-libraries/sdks/python), [Handle tool calls](https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls), and Messages API documentation. Claude's main entry point is the `Messages API`; the Python package is `anthropic`.

## Common entry points

| Method | Purpose |
| --- | --- |
| `client.messages.create()` | One turn, multi-turn, image, and tool calls. |
| `client.messages.stream()` | Stream output and obtain an aggregated final message. |
| `client.messages.count_tokens()` | Estimate input tokens before a request. |
| `client.models.list()` | Inspect available models. |
| `client.beta.files.upload()` | Upload reusable files; beta capability, so recheck documentation before use. |

Examples use `claude-sonnet-5` as a general learning model. Check [Models overview](https://platform.claude.com/docs/en/about-claude/models/overview) before production.

> [!note] Dateless 4.6-and-later IDs are not “always latest”
> The 2026-07-22 version documentation says that a dateless 4.6-and-later ID such as `claude-sonnet-5` is the canonical pinned snapshot for that release, not an evergreen alias that moves to the next generation. Upgrade by changing IDs explicitly, recording retirement plans, and rerunning tool, structured-output, and safety regression tests.

## Install and configure the key

```powershell
python -m pip install --upgrade anthropic
$env:ANTHROPIC_API_KEY = Read-Host 'ANTHROPIC_API_KEY' -MaskInput
```

The key belongs only in the current process environment, never in source or a script.

## Text and multi-turn Messages calls

```python
from anthropic import Anthropic

client = Anthropic()

message = client.messages.create(
    model="claude-sonnet-5",
    max_tokens=1024,
    system="You are a concise and accurate technical teacher.",
    messages=[{"role": "user", "content": "Explain an API call in three points."}],
)

for block in message.content:
    if block.type == "text":
        print(block.text)
print(message.usage)
```

For `claude-sonnet-5` and broadly compatible default implementations, pass `system` as the top-level parameter and set `max_tokens` explicitly. Do not infer that Messages API never supports a system role: mid-conversation system messages exist only for specifically verified models with strict placement rules. As of 2026-07-19, the documented support list includes Fable 5, Mythos 5, and Opus 4.8—not Sonnet 5—and a mid-conversation system message cannot interrupt a tool-use turn that still needs a client result.

Messages API is stateless. Preserve and resend history in time order:

```python
history = [
    {"role": "user", "content": "What is a Python list?"},
    {"role": "assistant", "content": "A list is a mutable ordered container."},
    {"role": "user", "content": "Show one append example."},
]

message = client.messages.create(
    model="claude-sonnet-5",
    max_tokens=512,
    messages=history,
)
```

Do not assume `content[0]` is text when a response can contain tool use or other blocks. Top-level `system` accepts a string or text-block array. A production adapter must allow mid-conversation system messages explicitly by model capability, not merely because a role field exists.

## Streaming and vision

```python
with client.messages.stream(
    model="claude-sonnet-5",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Write a study plan for Python APIs."}],
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
    final_message = stream.get_final_message()

print("\nUsage:", final_message.usage)
```

`text_stream` is a convenience for text. For tools, thinking, or stream errors, process typed events/content blocks and verify final `stop_reason` and `message_stop`; seeing text does not prove a completed turn. Use `client.messages.create(..., stream=True)` for raw event processing without the SDK's final-message aggregation.

```python
import base64
from pathlib import Path

image_path = Path(r"D:\data\chart.png")
image_data = base64.b64encode(image_path.read_bytes()).decode("utf-8")

message = client.messages.create(
    model="claude-sonnet-5",
    max_tokens=1024,
    messages=[{
        "role": "user",
        "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image_data}},
            {"type": "text", "text": "Explain the chart trend and name its axes."},
        ],
    }],
)
```

Use only an image you are authorized to upload. URL images are also possible; recheck [Vision](https://platform.claude.com/docs/en/build-with-claude/vision) for supported formats, size, and count limits.

## Tool calling

The model selects a tool; the host validates and executes it. Only a `tool_use` terminal state permits host execution. A `max_tokens` stop, refusal, or other terminal state needs an explicit recovery path even if one content block resembles tool use.

```python
import json


def get_weather(city: str) -> dict:
    return {"city": city, "temperature": 25, "unit": "celsius"}


tools = [{
    "name": "get_weather",
    "description": "Look up weather for a city.",
    "input_schema": {
        "type": "object",
        "properties": {"city": {"type": "string"}},
        "required": ["city"],
        "additionalProperties": False,
    },
}]
messages = [{"role": "user", "content": "What is the temperature in Shanghai now?"}]

first = client.messages.create(
    model="claude-sonnet-5", max_tokens=1024, tools=tools, messages=messages
)
if first.stop_reason != "tool_use":
    raise RuntimeError(f"tool turn is not executable: {first.stop_reason}")

messages.append({"role": "assistant", "content": first.content})
tool_results = []
for block in first.content:
    if block.type != "tool_use":
        continue
    is_error = False
    if block.name != "get_weather":
        result, is_error = {"error": "unsupported_tool"}, True
    elif (not isinstance(block.input, dict) or set(block.input) != {"city"}
          or not isinstance(block.input["city"], str) or not block.input["city"].strip()
          or len(block.input["city"]) > 100):
        result, is_error = {"error": "invalid_tool_input"}, True
    else:
        try:
            result = get_weather(block.input["city"].strip())
        except Exception:
            result, is_error = {"error": "tool_execution_failed"}, True
    tool_result = {
        "type": "tool_result",
        "tool_use_id": block.id,
        "content": json.dumps(result, ensure_ascii=False),
    }
    if is_error:
        tool_result["is_error"] = True
    tool_results.append(tool_result)

if tool_results:
    messages.append({"role": "user", "content": tool_results})
    final = client.messages.create(
        model="claude-sonnet-5", max_tokens=1024, tools=tools, messages=messages
    )
    for block in final.content:
        if block.type == "text":
            print(block.text)
        elif block.type == "tool_use":
            raise RuntimeError("model requested another tool turn; loop with a bound")
```

Every `tool_use` requires exactly one matching `tool_result`. Unknown tools, invalid arguments, and execution failures return a stable `is_error=true` result; retain internal exception detail only in protected logs. A production loop needs a maximum round count, total deadline, repeated-call detection, and approval state.

For streaming tools, parse `input_json_delta.partial_json` only after its corresponding content block ends. Fine-grained/eager tool-input streaming can end with incomplete JSON; return an error result only, never execute partial arguments. Preserve thinking, redacted thinking, signatures, regular text, and server-tool blocks in original assistant-content order. `server_tool_use` is executed by Anthropic and must not be renamed and dispatched as a local function. Practice the state machine with offline negative tests in [[llm-api-integration/00-index|LLM API Integration]].

## Token count, async, and error handling

```python
count = client.messages.count_tokens(
    model="claude-sonnet-5",
    system="You are a technical teacher.",
    messages=[{"role": "user", "content": "Explain Python decorators in detail."}],
)
print(count.input_tokens)
```

Token count helps decide whether to truncate, chunk, or reject a long input; actual billing follows `usage` on the real response.

```python
import asyncio
from anthropic import AsyncAnthropic


async def main() -> None:
    client = AsyncAnthropic()
    message = await client.messages.create(
        model="claude-sonnet-5",
        max_tokens=512,
        messages=[{"role": "user", "content": "Explain async/await."}],
    )
    print(message.content[0].text)


asyncio.run(main())
```

Use async when a web service or many independent calls need concurrency. A synchronous client is easier to debug for one script.

```python
import anthropic

try:
    message = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=512,
        messages=[{"role": "user", "content": "Hello"}],
    )
except anthropic.AuthenticationError:
    print("The API key is invalid or lacks permission.")
except anthropic.RateLimitError:
    print("A rate limit was reached; retry later within a budget.")
except anthropic.APITimeoutError:
    print("The request timed out.")
except anthropic.APIConnectionError:
    print("The network connection failed.")
except anthropic.APIStatusError as exc:
    print(exc.status_code, exc.request_id)
```

## Common mistakes and further reading

- Put `system` inside `messages` without checking model capability and placement; this course's Sonnet 5 path uses the top-level parameter.
- Omit `max_tokens`.
- Send only the latest question in a multi-turn conversation.
- Read only the first content block and miss `tool_use` or another type.
- Return no `tool_result` matching a `tool_use_id`.
- Use a retired model ID without checking the official model page and retirement date.

- [API usage primer](https://platform.claude.com/docs/en/claude_api_primer)
- [Python SDK](https://platform.claude.com/docs/en/cli-sdks-libraries/sdks/python)
- [Streaming Messages](https://platform.claude.com/docs/en/build-with-claude/streaming)
- [Vision](https://platform.claude.com/docs/en/build-with-claude/vision)
- [Tool use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview)
- [Handle tool calls](https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls)
- [Fine-grained tool streaming](https://platform.claude.com/docs/en/agents-and-tools/tool-use/fine-grained-tool-streaming)
- [Mid-conversation system messages](https://platform.claude.com/docs/en/build-with-claude/mid-conversation-system-messages)
- [Token counting](https://platform.claude.com/docs/en/build-with-claude/token-counting)

Return to [[api/ai-api-reference/00-index|Vendor AI API Reference Index]]; general HTTP contract and reliability remain in [[api/00-index|API Learning Path]].

