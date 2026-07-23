---
title: "Zhipu GLM API Calls"
source: https://docs.bigmodel.cn/cn/guide/develop/python/introduction
source_checked: 2026-07-22
source_baseline:
  - Zhipu official Python SDK, model overview, streaming messages, tool calling,
    and thinking mode
content_origin: curated
content_status: dynamic
execution_verified: false
verification_note: "The current official Python SDK and model overview were
  checked with offline syntax review; no network call was made with real
  credentials."
tags: [ api, ai-api, glm, zhipu, python ]
aliases: [ Zhipu API, BigModel API, Z.AI API ]
lang: en
translation_key: API/AI API 调用/07-智谱 GLM API.md
translation_source_hash: 79ea5955c1ec69e80be7ec5fb0a17336296d295e85d4533c0579bf75d659bfd2
translation_route: zh-CN/API/AI-API-调用/07-智谱-GLM-API
translation_default_route: zh-CN/API/AI-API-调用/07-智谱-GLM-API
---

# Zhipu GLM API Calls

> [!source] Official sources
> This page is based on the [official Python SDK](https://docs.bigmodel.cn/cn/guide/develop/python/introduction), streaming-message, vision-understanding, and tool-calling documentation. Zhipu's China Open Platform uses `ZhipuAiClient`; the Python package is `zai-sdk`.

> [!important] The teaching defaults on this page follow an SDK upgrade
> The official Python SDK checked on 2026-07-22 uses `glm-5.2` for text, streaming, and tool-calling examples, and `glm-5v-turbo` for vision. Those are the current course baseline only: they do not guarantee access for every account, plan, or region, and they do not mean an existing regression or route using `glm-5.1` can be replaced without evaluation.

## Common entry points

| Python method | Purpose |
| --- | --- |
| `client.chat.completions.create()` | Text, multi-turn chat, streaming, vision, and tool calls. |
| `client.embeddings.create()` | Text vectors. |
| `client.images.generations()` | Image generation; verify the signature against the current SDK version. |
| `client.models.list()` | Inspect available models when the current SDK/account supports it. |

## Install and set the API key

```powershell
python -m pip install --upgrade zai-sdk  # Install or update the current official zai-sdk Python package.
$env:ZAI_API_KEY = Read-Host 'ZAI_API_KEY' -MaskInput  # Read the key into only this PowerShell process; do not put it in source.
```

> [!note]
> Historical code can use the `zhipuai` package or `ZHIPUAI_API_KEY`. This page uses the current `zai-sdk` and `ZAI_API_KEY`; do not mix examples from the two generations.

## 1. Text generation

```python
from zai import ZhipuAiClient  # Import the client class from the current official SDK.

client = ZhipuAiClient()  # Create a client from ZAI_API_KEY in the process environment; do not hard-code credentials.

response = client.chat.completions.create(  # Start one Chat Completions request.
    model="glm-5.2",  # Select the teaching model; verify the model page and account entitlement before deployment.
    messages=[  # Supply context in role and chronological order.
        {"role": "system", "content": "You are a concise technical teacher."},  # Constrain the answer style.
        {"role": "user", "content": "Explain an API call in three points."},  # Supply the current user question.
    ],
    temperature=0.6,  # Set moderate randomness; check current docs for model-supported ranges.
)

print(response.choices[0].message.content)  # Print the first candidate assistant message.
print(response.usage)  # Inspect actual service usage.
```

Model names change quickly; select them from the [model overview](https://docs.bigmodel.cn/cn/guide/start/model-overview). Text, vision, image generation, and video generation use different model families.

## 2. Multi-turn chat

```python
messages = [  # Keep full history in the client; the API does not remember a previous request automatically.
    {"role": "system", "content": "You are a Python teacher."},  # Fixed system instruction.
    {"role": "user", "content": "What is a dictionary?"},  # First user question.
]

first = client.chat.completions.create(model="glm-5.2", messages=messages)  # Send the first request.
messages.append({  # Append the first answer so the next turn receives it as context.
    "role": "assistant",  # Mark the message as assistant-authored.
    "content": first.choices[0].message.content,  # Keep the first candidate's answer text.
})
messages.append({"role": "user", "content": "Show an example of reading a value by key."})  # Add a follow-up based on the prior answer.

second = client.chat.completions.create(model="glm-5.2", messages=messages)  # Send complete history for the second turn.
print(second.choices[0].message.content)  # Print the second answer.
```

## 3. Streaming output

```python
stream = client.chat.completions.create(  # Request generated content as incremental chunks.
    model="glm-5.2",  # Select the model used for streaming.
    messages=[{"role": "user", "content": "Write Python API study advice."}],  # Provide this turn's task.
    stream=True,  # Enable streaming mode.
)

for chunk in stream:  # Consume chunks in arrival order.
    if not chunk.choices:  # Some chunks contain no candidate content.
        continue  # Avoid an invalid index access for empty choices.
    delta = chunk.choices[0].delta  # Read this candidate's incremental field.
    if delta.content:  # Print only when the increment contains visible text.
        print(delta.content, end="", flush=True)  # Display text immediately as a streaming UI would.
```

Thinking models can return reasoning increments through `delta.reasoning_content`; the final chunk can also include `finish_reason` and `usage`.

## 4. Image understanding

```python
response = client.chat.completions.create(  # Start a vision-understanding request with a public image URL.
    model="glm-5v-turbo",  # Select a vision model; never send image content blocks to a text-only model.
    messages=[  # Build one multimodal user message.
        {  # One user message object.
            "role": "user",  # Identify the message role.
            "content": [  # Combine a textual task and an image as content blocks.
                {"type": "text", "text": "Explain the chart trend and name its axes."},  # Describe the analysis task.
                {  # The second content block supplies an image URL.
                    "type": "image_url",  # Declare that the image is URL-referenced.
                    "image_url": {  # Wrap the actual image address.
                        "url": "https://api.nga.gov/iiif/a2e6da57-3cd1-4235-b20e-95dcaefed6c8/full/!800,800/0/default.jpg"  # Use a public example image; production use must respect access and copyright rules.
                    },
                },
            ],
        }
    ],
)

print(response.choices[0].message.content)  # Print the vision-analysis text.
```

You can encode a local image as `data:image/png;base64,...`. Check vision-model documentation for formats, size limits, and model capability.

## 5. Function Calling

```python
import json  # Parse model function arguments and serialize local tool results.


def get_weather(city: str) -> dict:  # Define a side-effect-free teaching tool that the host actually executes.
    return {"city": city, "temperature": 25, "unit": "celsius"}  # Return fixed offline data instead of accessing a live service.


tools = [{  # Declare a function tool that the model may choose to call.
    "type": "function",  # State the tool kind.
    "function": {  # Describe name, purpose, and argument schema.
        "name": "get_weather",  # Tool name must match the host allowlist.
        "description": "Look up weather for a city.",  # Help the model decide when to call it.
        "parameters": {  # Use JSON Schema to constrain argument shape.
            "type": "object",  # Arguments must be an object.
            "properties": {"city": {"type": "string"}},  # Permit only a string city field.
            "required": ["city"],  # Require city for every call.
        },
    },
}]

messages = [{"role": "user", "content": "What is the temperature in Shanghai now?"}]  # Initialize history retained across tool rounds.
first = client.chat.completions.create(  # Let the model decide whether to invoke a tool first.
    model="glm-5.2",  # Select a model that supports Function Calling.
    messages=messages,  # Send the current user question.
    tools=tools,  # Provide the permitted tool schema.
    tool_choice="auto",  # Allow the model to decide whether a tool is needed.
)

assistant_message = first.choices[0].message  # Obtain the model message and any possible tool_calls.
messages.append(assistant_message.model_dump())  # Serialize and preserve the complete assistant message, including tool-correlation fields.

for tool_call in assistant_message.tool_calls or []:  # Process all tool calls; safely skip when none was requested.
    arguments = json.loads(tool_call.function.arguments)  # Parse model JSON; production code must validate schema, authorization, and semantics first.
    result = get_weather(**arguments)  # Pass validated values to the local function.
    messages.append({  # Add a tool-result message correlated to this call ID.
        "role": "tool",  # Identify this message as a tool execution result.
        "tool_call_id": tool_call.id,  # Match the model's invocation ID exactly.
        "content": json.dumps(result),  # Encode the result as JSON.
    })

if assistant_message.tool_calls:  # Continue only after at least one tool was executed.
    final = client.chat.completions.create(  # Let the model form a final answer using tool results.
        model="glm-5.2",  # Keep the same model as the decision round.
        messages=messages,  # Include assistant tool calls and corresponding tool results.
        tools=tools,  # Continue with the same tool contract.
    )
    print(final.choices[0].message.content)  # Print the final answer.
```

When a response contains multiple `tool_calls`, execute and return all of them. High-impact functions require argument validation and human confirmation.

## 6. Built-in Web Search

```python
response = client.chat.completions.create(  # Permit the model to use the built-in Web Search tool.
    model="glm-5.2",  # Select a currently supporting model; verify capability and billing in official documentation.
    messages=[  # Supply a task that requires current information.
        {"role": "user", "content": "Find important updates in the official Python ecosystem today."},  # The current retrieval request.
    ],
    tools=[  # Explicitly declare built-in tools the model may use.
        {  # Define Web Search configuration.
            "type": "web_search",  # Identify the built-in network-retrieval tool type.
            "web_search": {  # Configure its query and requested result mode.
                "search_query": "official Python updates",  # Set the query the tool sends.
                "search_result": True,  # Ask for search-result information in the response.
            },
        }
    ],
)

print(response.choices[0].message.content)  # Print the model's synthesis; production code must also inspect citations and sources.
```

Tool support depends on model and plan. In production, inspect search results and citations instead of trusting only the final summary.

## 7. Embeddings

```python
response = client.embeddings.create(  # Convert a batch of text into numeric vectors through the Embeddings API.
    model="embedding-3",  # Use the same embedding model for indexing and querying.
    input=[  # Supply texts to vectorize in a batch.
        "Python is suitable for rapid development.",  # First input text.
        "Rust emphasizes performance and memory safety.",  # Second input text.
    ],
)

vectors = [item.embedding for item in response.data]  # Extract a vector for each input in response order.
print(len(vectors), len(vectors[0]))  # Check vector count and one vector's dimension.
```

Embeddings support semantic search, similarity, clustering, and RAG. Indexing and querying must use the same model and dimension.

## Error handling

```python
import zai  # Import the SDK module so its public exception classes can be caught.

try:  # Place one remote call inside a boundary that can classify actionable failures.
    response = client.chat.completions.create(  # Use a minimal request to demonstrate exception handling.
        model="glm-5.2",  # Verify that this model remains available before running it.
        messages=[{"role": "user", "content": "Hello"}],  # Supply a simple user input.
    )
except zai.core.APIStatusError as exc:  # The service returned a recognized API status error.
    print("API status error:", exc)  # Print a summary; production logs must redact and correlate a request ID.
except zai.core.APITimeoutError:  # The SDK timed out while waiting for the service.
    print("Request timed out.")  # Let the caller decide on a controlled retry within its overall budget.
```

Catch only public SDK errors for which this layer has a clear action. Preserve stacks for unknown failures and log them at the application boundary; do not swallow them with a broad `except Exception`.

## Frequent mistakes

- Mixing `zai-sdk` with the older `zhipuai` package.
- Mixing `ZAI_API_KEY` with historical environment-variable names.
- Mixing a general API endpoint with a Coding-plan endpoint.
- Passing images to a text model or reusing parameters across distinct vision models.
- Failing to return a `tool_call_id` after executing a tool.
- Not checking the current SDK signature for less-common methods such as image or video generation.

## Official further reading

- [Official Python SDK](https://docs.bigmodel.cn/cn/guide/develop/python/introduction)
- [Streaming messages](https://docs.bigmodel.cn/cn/guide/capabilities/streaming)
- [Tool calling](https://docs.bigmodel.cn/cn/guide/capabilities/function-calling)
- [Thinking mode](https://docs.bigmodel.cn/cn/guide/capabilities/thinking-mode)
- [Model overview](https://docs.bigmodel.cn/cn/guide/start/model-overview)

Return to [[api/ai-api-reference/00-index|Vendor AI API Reference Index]]; general HTTP contracts and reliability are in [[api/00-index|API Learning Path]].
