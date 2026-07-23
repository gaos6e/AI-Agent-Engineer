---
title: "Kimi API Calls"
source: https://platform.kimi.com/docs/guide/start-using-kimi-api
source_checked: 2026-07-22
source_baseline:
  - Kimi API overview, Kimi K2.6 quickstart, Chat Completion, and Tool Use
content_origin: curated
content_status: dynamic
execution_verified: false
verification_note: "The current official quickstart and model-capability
  boundary were checked with offline syntax review; no network call was made
  with real credentials."
tags: [ api, ai-api, kimi, moonshot, python ]
aliases: [ Moonshot API, Kimi API ]
lang: en
translation_key: API/AI API 调用/06-Kimi API.md
translation_source_hash: 4aa265c6c2942bae24aa4769e34a0f97f714d42f025dbb9233bd9dae98067d8f
translation_route: zh-CN/API/AI-API-调用/06-Kimi-API
translation_default_route: zh-CN/API/AI-API-调用/06-Kimi-API
---

# Kimi API Calls

> [!source] Official sources
> This page is based on the Kimi Open Platform quickstart, Chat Completion, Tool Use, and Files API documentation. Kimi uses an OpenAI-compatible shape, so Python clients commonly use the `openai` package.

## Common entry points

| Python method | Purpose |
| --- | --- |
| `client.chat.completions.create()` | Text, multi-turn chat, thinking, and tool calls. |
| `stream=True` | Stream output. |
| `client.files.create()` | Upload a file. |
| `client.files.content()` | Obtain Kimi's parsed file content. |
| `client.files.list()` / `delete()` | Manage uploaded files. |

> [!warning] Do not make Kimi `web_search` a new production dependency
> The K2.6 quickstart checked on 2026-07-22 states that this tool is being upgraded, that the existing documentation is outdated, and that it is not recommended for the near term. For network retrieval, choose a provider with a current stable contract and keep citation handling, freshness, access control, and failure fallback in the application layer. A model's ability to call a tool does not remove those responsibilities.

## Install and set the API key

```powershell
python -m pip install --upgrade "openai>=1.0"  # Install or update the OpenAI Python SDK used for the compatible interface.
$env:MOONSHOT_API_KEY = Read-Host 'MOONSHOT_API_KEY' -MaskInput  # Read the key only into this PowerShell process; never write it into code.
```

## 1. Endpoint and client

| Platform | `base_url` |
| --- | --- |
| China Open Platform | `https://api.moonshot.cn/v1` |
| International Open Platform | `https://api.moonshot.ai/v1` |

The key must match the platform region. This example uses the China Open Platform:

```python
import os  # Read credentials from environment variables instead of hard-coding a key.
from openai import OpenAI  # Import the client class for an OpenAI-compatible protocol.

client = OpenAI(  # Create a client directed at the China Kimi Open Platform endpoint.
    api_key=os.environ["MOONSHOT_API_KEY"],  # Fail early when the current process has no key.
    base_url="https://api.moonshot.cn/v1",  # Use the Chinese endpoint; an international key needs its corresponding endpoint.
)
```

## 2. Text generation

```python
response = client.chat.completions.create(  # Start one chat-generation request.
    model="kimi-k2.6",  # Select the teaching model; verify availability for the target region and plan.
    messages=[  # Pass messages in role and chronological order.
        {"role": "system", "content": "You are a concise technical teacher."},  # Define answer style with a system instruction.
        {"role": "user", "content": "Explain an API call in three points."},  # Supply the user's current question.
    ],
)

print(response.choices[0].message.content)  # Print the first candidate's assistant text.
print(response.usage)  # Inspect actual service usage.
```

Model IDs and capabilities can vary by region and plan. Check the current console or model list first.

## 3. Multi-turn chat

```python
messages = [  # The application owns full history; separate requests do not remember automatically.
    {"role": "system", "content": "You are a Python teacher."},  # Fixed behavioural instruction.
    {"role": "user", "content": "What is a dictionary?"},  # First user question.
]

first = client.chat.completions.create(model="kimi-k2.6", messages=messages)  # Send the first history and receive an answer.
messages.append({  # Add the answer to history so the next request can see it.
    "role": "assistant",  # Mark this item as assistant-authored.
    "content": first.choices[0].message.content,  # Preserve the first candidate's text.
})
messages.append({"role": "user", "content": "Show an example of reading a value by key."})  # Add a follow-up based on the prior turn.

second = client.chat.completions.create(model="kimi-k2.6", messages=messages)  # Send complete ordered history for the second turn.
print(second.choices[0].message.content)  # Print the second answer.
```

Long conversations continually consume context. Control history length and summarize when necessary instead of appending forever.

## 4. Streaming output

```python
stream = client.chat.completions.create(  # Ask the server to return incremental chunks.
    model="kimi-k2.6",  # Select the target model for streaming.
    messages=[{"role": "user", "content": "Write Python API study advice."}],  # Supply this turn's task.
    stream=True,  # Enable streaming mode.
)

for chunk in stream:  # Consume stream chunks in arrival order.
    if not chunk.choices:  # Some chunks do not include candidate content.
        continue  # Skip empty choices to avoid an invalid index access.
    text = chunk.choices[0].delta.content or ""  # Read the first candidate's text delta, using an empty string if absent.
    print(text, end="", flush=True)  # Display text immediately as a streaming UI would.
```

Thinking models can also return `reasoning_content`. For multi-turn tool calling, consult the selected model's current official documentation to determine whether that field must be retained.

## 5. K2.6 thinking mode: explicitly disable it when required—do not invent a cross-vendor switch

The K2.6 quickstart presents extended thinking as a model capability and shows a **top-level request field** for disabling it. With the OpenAI SDK, pass this vendor extension through `extra_body`:

```python
response = client.chat.completions.create(  # Send a compatible request that explicitly disables thinking mode.
    model="kimi-k2.6",  # Use K2.6; verify the extension against current official documentation.
    messages=[{"role": "user", "content": "Compare two database migration approaches."}],  # State the comparison task.
    extra_body={"thinking": {"type": "disabled"}},  # Pass Kimi's model-specific setting through to the service.
)

print(response.choices[0].message.content)  # Print visible final text rather than assuming a reasoning field exists.
```

The current `kimi-k2.6` example does not require callers to provide `enabled`. Do not copy `reasoning_effort` from another vendor or invent unlisted `thinking` values. If cost, latency, or a tool trace depends on thinking configuration, first perform a non-sensitive integration check for the exact region, model, and SDK version, then record the result in routing or evaluation baselines.

## 6. Function Calling

```python
import json  # Parse model-supplied function arguments and serialize tool results.


def get_weather(city: str) -> dict:  # Define a side-effect-free teaching tool actually run by the host program.
    return {"city": city, "temperature": 25, "unit": "celsius"}  # Return deterministic offline data rather than querying a live weather service.


tools = [{  # Declare the function tool that the model may choose to call.
    "type": "function",  # Identify the tool kind.
    "function": {  # Describe the function's name, purpose, and input schema.
        "name": "get_weather",  # Must match the host's allowlist.
        "description": "Look up weather for a city.",  # Help the model choose the tool correctly.
        "parameters": {  # Use JSON Schema to constrain arguments.
            "type": "object",  # Arguments must be an object.
            "properties": {"city": {"type": "string"}},  # Permit only a string city field.
            "required": ["city"],  # Require city for each invocation.
        },
    },
}]

messages = [{"role": "user", "content": "What is the temperature in Shanghai now?"}]  # Initialize history that persists across tool rounds.
first = client.chat.completions.create(  # Let the model decide whether it needs the tool.
    model="kimi-k2.6",  # Select a model that supports tool calling.
    messages=messages,  # Send the current user question.
    tools=tools,  # Supply the permitted tool contract.
)

assistant_message = first.choices[0].message  # Obtain the model message and any possible tool_calls.
messages.append(assistant_message)  # Preserve the message unchanged, including extension fields and call correlation data.

for tool_call in assistant_message.tool_calls or []:  # Handle every tool call; safely skip when none was requested.
    arguments = json.loads(tool_call.function.arguments)  # Parse model JSON; production code must validate schema, authorization, and semantics first.
    result = get_weather(**arguments)  # Invoke the local function only with validated values.
    messages.append({  # Append a result associated with this exact call ID.
        "role": "tool",  # State that this is a host tool result.
        "tool_call_id": tool_call.id,  # Correlate the result with the model request precisely.
        "content": json.dumps(result),  # Serialize the result as JSON.
    })

if assistant_message.tool_calls:  # Continue only when at least one tool was actually executed.
    final = client.chat.completions.create(  # Ask the model for a final response based on tool results.
        model="kimi-k2.6",  # Keep the model the same as the decision round.
        messages=messages,  # Include the original assistant message and matching tool results.
        tools=tools,  # Continue to provide the same tool schema.
    )
    print(final.choices[0].message.content)  # Print the final assistant text.
```

When a Kimi thinking model makes multi-step tool calls, usually retain all extension fields in the assistant message. The safest approach is to append the SDK-returned assistant message directly rather than copying just its text.

## 7. Upload and parse a file

```python
from pathlib import Path  # Use Path for local file paths instead of manually joining separators.

file_path = Path(r"D:\data\paper.pdf")  # Replace with a PDF you are authorized to upload and process.

with file_path.open("rb") as file_handle:  # Open the file read-only in binary mode and close it automatically afterwards.
    uploaded = client.files.create(  # Upload the file and retain the returned file object.
        file=file_handle,  # Send the open binary handle as the upload content.
        purpose="file-extract",  # Declare that the server should extract the file's content.
    )

file_content = client.files.content(file_id=uploaded.id).text  # Obtain service-parsed text; production code must enforce size and sensitive-data boundaries.

response = client.chat.completions.create(  # Ask for a summary using the extracted document text.
    model="kimi-k2.6",  # Select the text model used in this example.
    messages=[  # Put extracted content and user task into conversation context.
        {"role": "system", "content": file_content},  # Treat file text as context; real applications need chunking, permissions, and length control.
        {"role": "user", "content": "Summarize the document and list three key conclusions."},  # State the document-analysis task.
    ],
)

print(response.choices[0].message.content)  # Print the document summary.
```

Newer Kimi APIs may also support a message reference such as `ms://<file_id>`. Do not mix the two routes; choose one based on the current Chat API file-reference documentation.

Manage files explicitly:

```python
for item in client.files.list().data:  # Iterate over files visible to the current account.
    print(item.id, item.filename)  # Show ID and name without printing unnecessary file content.

client.files.delete(uploaded.id)  # Delete the file uploaded in this example; production code must verify retention policy and target ID.
```

## 8. List models

```python
models = client.models.list()  # Query the models visible to the current account.
for model in models.data:  # Iterate over each returned model object.
    print(model.id)  # Print its API model ID for validation against the official capability table.
```

This is more reliable than copying a model name from an old blog post, but you must still check the official model documentation for capabilities, context, and pricing.

## Frequent mistakes

- Mixing China and international endpoints or API keys.
- Forgetting `base_url`, which sends a request to OpenAI instead of Kimi.
- Omitting Kimi-specific fields from `extra_body`.
- Retaining only text from thinking/tool calls and dropping `reasoning_content` or `tool_calls`.
- Treating `web_search`, which current documentation says not to use near term, as a production retrieval contract.
- Uploading a file without reading parsed content or referencing it in the API-supported way.
- Appending history indefinitely until context is exceeded or cost becomes excessive.

## Official further reading

- [Kimi API documentation](https://platform.kimi.com/docs)
- [International API overview](https://platform.kimi.ai/docs/api/overview)
- [Create Chat Completion](https://platform.kimi.ai/docs/api/chat)
- [Tool Use](https://platform.kimi.ai/docs/guide/use-kimi-k2-model)
- [Upload File](https://platform.kimi.ai/docs/api/files-upload)

Return to [[api/ai-api-reference/00-index|Vendor AI API Reference Index]]; general HTTP contracts and reliability are in [[api/00-index|API Learning Path]].
