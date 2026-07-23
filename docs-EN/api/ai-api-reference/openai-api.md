---
title: "OpenAI API Calls"
source: https://developers.openai.com/api/docs/quickstart
source_checked: 2026-07-20
source_baseline:
  - OpenAI Responses, Conversation state, Your data, Function calling, and
    Streaming guides
  - openai-python v2.46.0 source and official examples
content_origin: curated
content_status: dynamic
execution_verified: false
verification_note: "Verified against official documentation and SDK source with
  offline syntax checks; no real credentials or network calls were used."
tags:
  - api
  - ai-api
  - openai
  - python
aliases:
  - OpenAI API
lang: en
translation_key: API/AI API 调用/01-OpenAI API.md
translation_source_hash: c3998c8f2ef1d2b37fae5ec34a123b59ded0a4b6fda8c1a5563cbe2794130936
translation_route: zh-CN/API/AI-API-调用/01-OpenAI-API
translation_default_route: zh-CN/API/AI-API-调用/01-OpenAI-API
---

# OpenAI API Calls

> [!source] Official source
> This Windows-and-Python note follows the `Responses API` recommended by the [Developer quickstart](https://developers.openai.com/api/docs/quickstart). Chat Completions remains supported, but OpenAI recommends Responses for new projects; see [Migrate to the Responses API](https://developers.openai.com/api/docs/guides/migrate-to-responses) for the migration boundary. The examples use the general alias `gpt-5.6` checked on 2026-07-20, which resolved to GPT-5.6 Sol that day. Aliases and available models change: production work must check [Models](https://developers.openai.com/api/docs/models), record the tested model, and rerun its regression evaluation before an upgrade.

## Common entry points

| Python method | Purpose | Learning priority |
| --- | --- | --- |
| `client.responses.create()` | Unified entry for text, multimodal input, and tool calling | Required |
| `client.responses.parse()` | Structured data returned against a Pydantic model | Common |
| `client.files.create()` | Upload PDFs, documents, images, and other files | Common |
| `client.embeddings.create()` | Produce vectors for semantic retrieval and RAG | Common |
| `client.audio.transcriptions.create()` | Speech-to-text | As needed |
| `client.images.generate()` | Generate images with the Images API directly | As needed |
| `client.models.list()` | Inspect models currently accessible to the project | Supporting |

> [!tip] Suggested sequence
> Master text generation, multi-turn conversation, and streaming first. Then learn images/files, structured output, and tool calling. Add embeddings, audio, and image generation as the project requires.

## Install and set the API key

```powershell
python -m pip install --upgrade openai  # Install or update the official Python SDK in the active virtual environment.
$env:OPENAI_API_KEY = Read-Host 'OPENAI_API_KEY' -MaskInput  # Read the key masked into this PowerShell process only.

try {
    python .\your_script.py  # Run your SDK example; replace with the actual filename.
} finally {
    Remove-Item Env:OPENAI_API_KEY -ErrorAction SilentlyContinue  # Remove the precise variable on every exit path.
}
```

`your_script.py` is your script name. Never put a key in notes, source, notebooks, logs, or a frontend. Clean up even a temporary environment variable when the command ends.

## 1. Text generation with `responses.create()`

```python
from openai import OpenAI

client = OpenAI()


def require_completed(response, *, context: str):
    if response.status != "completed":
        raise RuntimeError(f"{context} did not complete: status={response.status}")
    for item in getattr(response, "output", ()) or ():
        for content in getattr(item, "content", ()) or ():
            if getattr(content, "type", None) == "refusal":
                raise RuntimeError(f"{context} contains a refusal and cannot be committed")
    return response


def require_text(response, *, context: str) -> str:
    require_completed(response, context=context)
    text = response.output_text
    if not text:
        raise RuntimeError(f"{context} has no final text that can be committed")
    return text


response = client.responses.create(
    model="gpt-5.6",
    reasoning={"effort": "low"},
    instructions="You are a concise and accurate technical teacher.",
    input="Explain an API call in three points.",
    store=False,
)

text = require_text(response, context="text response")
print(text)
print(response.usage)
print(response._request_id)
```

`require_completed()` narrows a response to a committable terminal state and rejects every `refusal` item. `require_text()` additionally requires nonempty aggregated text. A response that contains partial text and a refusal must not be committed merely because `output_text` exists.

| Parameter | Purpose |
| --- | --- |
| `model` | Selects the model. |
| `input` | User input as a string or structured message list. |
| `instructions` | High-priority developer instruction for the current request. |
| `reasoning` | Configuration such as reasoning effort; supported values are model-specific. |
| `max_output_tokens` | Caps generated tokens for this request. |
| `tools` | Enables built-in tools, MCP, or custom functions. |
| `store` | Chooses whether to save Response application state; choose explicitly under data governance. |

> [!warning] Do not hard-code `response.output[0]`
> `output` can also contain reasoning and tool-call items. `response.output_text` is only a convenience aggregation. Commit it only after confirming a valid terminal state, no pending tool call or refusal, and that the business path actually needs text.

## 2. Structured messages and multi-turn conversation

### Message roles

```python
response = client.responses.create(
    model="gpt-5.6",
    store=False,
    input=[
        {
            "role": "developer",
            "content": "Answer with a definition, an example, and one common mistake.",
        },
        {
            "role": "user",
            "content": "Explain a Python virtual environment.",
        },
    ],
)

print(require_text(response, context="message response"))
```

- `developer`: application rules and output requirements, higher priority than user input.
- `user`: the end-user input.
- `assistant`: a prior model response when the application maintains history itself.

### Continue with `previous_response_id`

```python
first = client.responses.create(
    model="gpt-5.6",
    input="My project uses Python and FastAPI.",
    store=True,
)
require_completed(first, context="prior response")

second = client.responses.create(
    model="gpt-5.6",
    previous_response_id=first.id,
    input="Based on that, propose a directory layout.",
    store=False,
)

print(require_text(second, context="continued response"))
```

> [!note]
> `instructions` applies only to the current request. Supply it again when it must continue to govern a subsequent turn.

### Choose state and storage deliberately

| Approach | Suitable use | Boundary to understand |
| --- | --- | --- |
| `store=False` plus application-managed history | Data minimization, portable context, or an approved ZDR project | The app must replay full inputs and retained output items; `store=False` alone is not ZDR. |
| `previous_response_id` | Short chained server-side continuation | The prior Response must still be resolvable; declare `instructions` and `store` every turn. |
| Conversations API | Long-lived state across sessions, devices, or tasks | Conversation items do not share the ordinary Response 30-day lifecycle; set a separate deletion and retention policy. |

As of 2026-07-20, the [data-controls guide](https://developers.openai.com/api/docs/guides/your-data#v1responses) states that Responses application state is stored for 30 days by default. `store=False` changes only that state-storage layer; it does not automatically grant Zero Data Retention or disable abuse-monitoring logs. `previous_response_id` does not eliminate billing for history input tokens. Files API objects have an independent lifecycle and do not disappear merely because a request ends. Before processing sensitive data, check organizational retention eligibility, endpoint coverage, and local compliance requirements together.

## 3. Streaming output

Streaming suits chat interfaces and long answers. It yields events throughout generation:

```python
stream = client.responses.create(
    model="gpt-5.6",
    input="Write a 200-word recommendation for learning Python.",
    store=False,
    stream=True,
)

fragments = []
terminal_event = None
refusal_seen = False

for event in stream:
    if event.type == "response.output_text.delta":
        fragments.append(event.delta)
        print(event.delta, end="", flush=True)
    elif event.type in {"response.refusal.delta", "response.refusal.done"}:
        refusal_seen = True
    elif event.type in {
        "response.completed",
        "response.failed",
        "response.incomplete",
        "error",
    }:
        terminal_event = event.type
        break

if terminal_event != "response.completed" or refusal_seen:
    raise RuntimeError(
        f"stream did not complete legally: terminal={terminal_event}, refusal={refusal_seen}"
    )

committed_text = "".join(fragments)
print("\n\nGeneration complete; only now may text be committed")
```

Text deltas are provisional preview, not a business result. Iterator failure, top-level `error`, `response.failed`, `response.incomplete`, a refusal, or EOF without a valid terminal event fails the turn. See [[llm-api-integration/00-index|LLM API Integration]] for a cross-provider event state machine and offline negative tests.

## 4. Analyze images

An image can come from a public URL, Base64 data URL, or uploaded file `file_id`:

```python
response = client.responses.create(
    model="gpt-5.6",
    store=False,
    input=[
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": "Describe the image and extract visible text."},
                {
                    "type": "input_image",
                    "image_url": "https://api.nga.gov/iiif/a2e6da57-3cd1-4235-b20e-95dcaefed6c8/full/!800,800/0/default.jpg",
                },
            ],
        }
    ],
)

print(require_text(response, context="image analysis"))
```

Validate URL provenance, authorization, and data boundaries in a real project. To send a local image, encode it as Base64:

```python
import base64
from pathlib import Path

image_path = Path(r"D:\data\chart.png")
image_base64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")

response = client.responses.create(
    model="gpt-5.6",
    store=False,
    input=[{
        "role": "user",
        "content": [
            {"type": "input_text", "text": "Explain the trend in this chart."},
            {
                "type": "input_image",
                "image_url": f"data:image/png;base64,{image_base64}",
            },
        ],
    }],
)

print(require_text(response, context="local image analysis"))
```

Replace the path only with a file you are authorized to read and send.

## 5. Upload and analyze a file

This applies to PDFs, DOCX, PPTX, TXT, code files, and tables. On vision-capable models, a PDF can supply both extracted text and page images.

```python
from pathlib import Path

file_path = Path(r"D:\data\paper.pdf")

with file_path.open("rb") as file_handle:
    uploaded = client.files.create(
        file=file_handle,
        purpose="user_data",
        expires_after={"anchor": "created_at", "seconds": 86_400},
    )

try:
    response = client.responses.create(
        model="gpt-5.6",
        store=False,
        input=[{
            "role": "user",
            "content": [
                {"type": "input_file", "file_id": uploaded.id},
                {"type": "input_text", "text": "Summarize the document and list three key conclusions."},
            ],
        }],
    )
    print(require_text(response, context="file analysis"))
finally:
    client.files.delete(uploaded.id)
```

`expires_after` is a server-side backstop. `finally` closes this task's remote temporary-resource lifecycle. Production systems additionally need compensating cleanup for failed retries and files left by process crashes. Use `input_file` for a few one-off files; study [File search](https://developers.openai.com/api/docs/guides/tools-file-search) for larger repeated retrieval or knowledge-base workloads.

## 6. Built-in tools: Web Search

```python
response = client.responses.create(
    model="gpt-5.6",
    tools=[{"type": "web_search"}],
    input="Find important official Python updates today and cite sources.",
    store=False,
)

print(require_text(response, context="Web Search response"))
```

Tool output is not necessarily text only, so inspect item types during debugging:

```python
for item in response.output:
    print(item.type)
```

Other common built-in tools include `file_search`, `code_interpreter`, `image_generation`, and remote MCP. Their availability varies by model and account.

## 7. Custom function calling

The model decides which function to call and with which arguments; your Python program performs the function.

```python
import json


def get_weather(city: str) -> dict:
    return {"city": city, "temperature": 25, "unit": "celsius"}


def reject_non_finite(value: str) -> None:
    raise ValueError(f"JSON does not allow a non-finite constant: {value}")


def parse_weather_arguments(raw: str) -> dict:
    arguments = json.loads(raw, parse_constant=reject_non_finite)
    if not isinstance(arguments, dict) or set(arguments) != {"city"}:
        raise ValueError("arguments must contain exactly city")
    city = arguments["city"]
    if not isinstance(city, str) or not city.strip() or len(city) > 100:
        raise ValueError("city must be a nonempty string from 1 to 100 characters")
    return {"city": city.strip()}


tools = [
    {
        "type": "function",
        "name": "get_weather",
        "description": "Look up current weather for the specified city.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name"},
            },
            "required": ["city"],
            "additionalProperties": False,
        },
        "strict": True,
    }
]

MAX_TOOL_ROUNDS = 4
seen_call_ids = set()

response = client.responses.create(
    model="gpt-5.6",
    tools=tools,
    input="What is the temperature in Shanghai now?",
    store=True,
)

for _round in range(MAX_TOOL_ROUNDS):
    require_completed(response, context=f"tool round {_round + 1}")

    calls = [item for item in response.output if item.type == "function_call"]
    if not calls:
        print(require_text(response, context="final tool-call response"))
        break

    tool_outputs = []
    for item in calls:
        if item.name != "get_weather":
            raise ValueError(f"unknown tool: {item.name}")
        if item.call_id in seen_call_ids:
            raise RuntimeError(f"duplicate call_id: {item.call_id}")
        seen_call_ids.add(item.call_id)

        arguments = parse_weather_arguments(item.arguments)
        result = get_weather(**arguments)
        tool_outputs.append({
            "type": "function_call_output",
            "call_id": item.call_id,
            "output": json.dumps(result, ensure_ascii=False, allow_nan=False),
        })

    response = client.responses.create(
        model="gpt-5.6",
        tools=tools,
        previous_response_id=response.id,
        input=tool_outputs,
        store=True,
    )
else:
    raise RuntimeError("maximum tool-call rounds exceeded")
```

`strict: True` cannot replace business validation, identity authorization, or approval. `get_weather` is rea…9337 tokens truncated…
For [[rag/00-index|RAG]] or an extraction Agent, retain table JSON first: tables, rows, columns, cells, spans, header paths, and coordinates. Render relevant cells as text or Markdown for a question only afterward. Flattening the entire table into a paragraph before splitting can join row/column ownership, units, and headers incorrectly. Every retrieved fragment should still lead back to a page and cell ID.

## 8. Structured output with `responses.parse()`

Use a Pydantic model when the program needs stable fields rather than free-form prose:

```powershell
python -m pip install --upgrade pydantic  # Install or update the structured-output model library in the active virtual environment.
```

```python
from pydantic import BaseModel


class StudyPlan(BaseModel):
    topic: str
    days: int
    tasks: list[str]


response = client.responses.parse(
    model="gpt-5.6",
    input="Create a seven-day plan for learning Python APIs.",
    text_format=StudyPlan,
    store=False,
)

require_completed(response, context="structured response")
plan = response.output_parsed
if plan is None:
    raise RuntimeError("response completed without refusal but has no usable structured result")

print(plan.topic)
print(plan.tasks)
```

`output_parsed` remains a convenience property in openai-python v2.46.0 for a path expected to yield one structured text result. When multiple messages/content items must be retained or a refusal located, inspect `output[*].content[*].parsed` item by item. Structured output helps with database writes, subsequent functions, configuration generation, and data extraction, but still handle refusals, incomplete output, `None`, and validation failure first.

## 9. Embeddings with `embeddings.create()`

```python
response = client.embeddings.create(
    model="text-embedding-3-small",
    input=[
        "Python is suitable for rapid development.",
        "Rust emphasizes performance and memory safety.",
    ],
)

vectors = [item.embedding for item in response.data]
print(len(vectors), len(vectors[0]))
```

An embedding does not answer a question itself. It turns text into vectors for semantic search, clustering, recommendation, and RAG. Indexing and query must use the same model and dimension.

## 10. Speech-to-text

```python
from pathlib import Path

audio_path = Path(r"D:\data\meeting.mp3")

with audio_path.open("rb") as audio_file:
    transcription = client.audio.transcriptions.create(
        model="gpt-4o-transcribe",
        file=audio_file,
    )

print(transcription.text)
```

Replace the path only with audio you are authorized to upload. Live microphone transcription and voice conversation do not use this file-upload example; study the Realtime API instead.

## 11. Generate images

Responses can use image generation as a built-in tool:

```python
import base64
from pathlib import Path

response = client.responses.create(
    model="gpt-5.6",
    input="Generate a minimalist learning roadmap for Python APIs.",
    tools=[{"type": "image_generation"}],
    store=False,
)

require_completed(response, context="image generation")
images = [item for item in response.output if item.type == "image_generation_call"]
if not images:
    raise RuntimeError("response completed but contains no image result")

for index, item in enumerate(images, start=1):
    image_bytes = base64.b64decode(item.result, validate=True)
    Path(f"api-roadmap-{index}.png").write_bytes(image_bytes)
```

For image-only generation and editing, also study `client.images.generate()` and `client.images.edit()`.

## Error handling and retry

```python
import openai

try:
    response = client.responses.create(
        model="gpt-5.6",
        input="Hello",
        store=False,
        timeout=60,
    )
    require_completed(response, context="request")
    print("request_id:", response._request_id)
except openai.AuthenticationError:
    print("The API key is invalid or lacks permission.")
except openai.RateLimitError:
    print("A rate limit or quota was reached; retry later and check the account.")
except openai.APITimeoutError:
    print("The request timed out.")
except openai.APIConnectionError:
    print("The network connection failed.")
except openai.APIStatusError as exc:
    print("API error:", exc.status_code, exc.request_id)
```

At client level, set a per-attempt timeout and finite SDK retry count explicitly:

```python
client = OpenAI(timeout=60.0, max_retries=2)
```

openai-python currently retries connection errors, 408, 409, 429, and 5xx twice by default. `max_retries=2` makes that default an explicit contract rather than adding another retry layer. `timeout=60` bounds one SDK attempt, not a business deadline across attempts, queuing, and downstream work. Production systems need one retry owner: set SDK `max_retries=0` when an outer workflow owns the budget; if the SDK owns it, do not add unbounded outer retry. Do not assume Responses supplies a generic exactly-once or HTTP-idempotency contract for payment, database write, or other side effect. The business system still needs its operation key, ledger, and outbox.

Record `_request_id` from a success and `request_id` on an API status error for diagnosis. They are not a business idempotency key and must not be recorded without bounds alongside user input, credentials, or complete sensitive body text.

## Common errors

- `401`: bad API key, environment variable not available in a new terminal, or insufficient project permission.
- `429`: a rate limit, or possibly quota or billing condition.
- Model unavailable: the project lacks access or its name changed; check the model page or `client.models.list()`.
- Treating a ChatGPT subscription as API quota: ChatGPT and API billing/permission are separate.
- Writing a key into `.py`, a notebook, or Git: use environment variables, and revoke/recreate immediately after a leak.
- Concatenating only streaming text: tool calls and failure events need separate handling.

> [!info] Verification boundary for this page
> On 2026-07-20, all 16 Python fenced blocks passed `ast.parse`; principal method shapes were checked against official documentation, openai-python v2.46.0 source, and official examples. No real API key or network request was used and no cost was incurred. This proves syntax and documentation contract, not your account permission, model availability, remote response shape, or end-to-end latency. [[llm-api-integration/00-index|LLM API Integration]] carries offline contracts for strict terminal state, duplicate `call_id`, unknown tools, invalid JSON, and multi-round tool calling.

## Official further reading

- [Developer quickstart](https://developers.openai.com/api/docs/quickstart)
- [Migrate to the Responses API](https://developers.openai.com/api/docs/guides/migrate-to-responses)
- [Text generation](https://developers.openai.com/api/docs/guides/text)
- [Conversation state](https://developers.openai.com/api/docs/guides/conversation-state)
- [Your data / data controls](https://developers.openai.com/api/docs/guides/your-data)
- [Images and vision](https://developers.openai.com/api/docs/guides/images-vision)
- [File inputs](https://developers.openai.com/api/docs/guides/file-inputs)
- [Using tools](https://developers.openai.com/api/docs/guides/tools)
- [Function calling](https://developers.openai.com/api/docs/guides/function-calling)
- [Streaming API responses](https://developers.openai.com/api/docs/guides/streaming-responses)
- [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [openai-python retries and timeouts](https://github.com/openai/openai-python#retries)
- [openai-python v2.46.0 parsed Responses source](https://github.com/openai/openai-python/blob/v2.46.0/src/openai/types/responses/parsed_response.py)

Return to [[api/ai-api-reference/00-index|Vendor AI API Reference Index]]. For general HTTP contract and reliability, see [[api/00-index|API Learning Path]].
