---
title: "xAI Grok API Calls"
source: https://docs.x.ai/developers/quickstart
source_checked: 2026-07-22
source_baseline:
  - xAI Quickstart, Grok 4.5, Responses API, Function Calling, and Web Search
content_origin: curated
content_status: dynamic
execution_verified: false
verification_note: "The current Grok 4.5 and Responses API documentation were
  checked with offline syntax review; no network call was made with real
  credentials."
tags: [ api, ai-api, xai, grok, python ]
aliases: [ Grok API, xAI API ]
lang: en
translation_key: API/AI API 调用/10-xAI Grok API.md
translation_source_hash: 4a9cd3c20408c832c6b5dcf23383972530b26fd438954379e83ca2a1a464a6cb
translation_route: zh-CN/API/AI-API-调用/10-xAI-Grok-API
translation_default_route: zh-CN/API/AI-API-调用/10-xAI-Grok-API
---

# xAI Grok API Calls

> [!source] Official sources
> This page is based on the [xAI Quickstart](https://docs.x.ai/developers/quickstart), official Python SDK, Responses API, Function Calling, and Agent Tools documentation. xAI provides both its native `xai-sdk` and an OpenAI-compatible interface.

## Two call styles

| Style | Appropriate use |
| --- | --- |
| `xai-sdk` | Multi-turn chat, xAI-native search/code tools, images, video, and other native capabilities. |
| OpenAI-compatible `openai` interface | Projects already familiar with Responses API or migrating from OpenAI code. |

New learners can choose one primary path first. This page introduces the native SDK and then the OpenAI-compatible style.

## Install and set the API key

```powershell
python -m pip install --upgrade xai-sdk openai  # Install or update the native xAI SDK and OpenAI-compatible client dependency.
$env:XAI_API_KEY = Read-Host 'XAI_API_KEY' -MaskInput  # Read the key into only this PowerShell process; do not write it into source.
```

## 1. xAI SDK text generation

```python
from xai_sdk import Client  # Import the native xAI SDK client class.
from xai_sdk.chat import system, user  # Import helpers that construct system and user chat messages.

client = Client()  # Create a native client using XAI_API_KEY from the process environment; do not hard-code credentials.

chat = client.chat.create(model="grok-4.5")  # Create a chat object whose history is maintained locally by the SDK.
chat.append(system("You are a concise, accurate technical teacher."))  # Append a system instruction that constrains answer style.
chat.append(user("Explain an API call in three points."))  # Append the current user question.

response = chat.sample()  # Ask the model to generate one answer from the current chat history.
print(response.content)  # Print the model's visible content.
```

Model IDs change quickly. Copy the current ID from [Models](https://docs.x.ai/developers/models); do not treat a product name shown in a web UI as an API model ID.

## 2. xAI SDK multi-turn chat

```python
chat = client.chat.create(model="grok-4.5")  # Create a separate session object to hold this example's history.

chat.append(user("What is a Python dictionary?"))  # Append the first user question.
first = chat.sample()  # Generate the first answer.
print(first.content)  # Print the first text response.
chat.append(first)  # Append the complete model response rather than copying only visible text.

chat.append(user("Show an example of reading a value by key."))  # Append a follow-up in the same session.
second = chat.sample()  # Generate the second answer with preceding context.
print(second.content)  # Print the second text response.
```

The underlying API is still stateless: the `chat` object merely helps the client maintain history. Persist a session yourself if it must survive across processes.

## 3. xAI SDK streaming output

```python
chat = client.chat.create(model="grok-4.5")  # Create a chat object for streaming generation.
chat.append(user("Write Python API study advice."))  # Append this streaming task.

final_response = None  # Reserve a variable for the full response accumulated by the stream.
for response, chunk in chat.stream():  # Native SDK yields both cumulative response and current incremental chunk.
    final_response = response  # Keep updating the full response for history after the stream ends.
    print(chunk.content, end="", flush=True)  # Display current text increment immediately.

if final_response is not None:  # Update session history only after at least one stream event was received.
    chat.append(final_response)  # Preserve full response structure for the next turn.
```

`chat.stream()` returns a cumulative `response` and current `chunk` together, which differs from OpenAI SDK stream events.

## 4. OpenAI-compatible Responses API

```python
import os  # Read environment variables so the API key is not stored in source.
from openai import OpenAI  # Import the client class for xAI's OpenAI-compatible Responses interface.

openai_client = OpenAI(  # Create a client pointed at xAI's compatible endpoint.
    api_key=os.environ["XAI_API_KEY"],  # Read the key from the current process environment.
    base_url="https://api.x.ai/v1",  # Override the default endpoint with xAI's compatible API.
)

response = openai_client.responses.create(  # Start one Responses API request.
    model="grok-4.5",  # Select the teaching model; check the official Models page before deployment.
    instructions="You are a concise, accurate technical teacher.",  # Set high-level behavioural guidance for this turn.
    input="Explain an API call in three points.",  # Provide the current user input.
)

print(response.output_text)  # Print the SDK's aggregated text convenience property.
```

`responses.create()` remains the common entry point. Old Chat Completions examples are mainly for compatibility; consult Responses documentation for new capabilities.

Current Grok 4.5 documentation recommends setting `prompt_cache_key` for continuing sessions to increase the chance of hitting the same cache server. It affects vendor cache routing/cost behaviour only; it is **not** a user, tenant, or session authorization mechanism, and it is not an application idempotency key. Applications still need trustworthy actor identity, object-level ACLs, and their own `operation_id`; never place raw sensitive prompts in a logged cache key.

## 5. Compatible streaming output

```python
stream = openai_client.responses.create(  # Request a Responses API stream that can be consumed event by event.
    model="grok-4.5",  # Select the target model for streaming generation.
    input="Write Python API study advice.",  # Supply this turn's task.
    stream=True,  # Enable the event stream.
)

for event in stream:  # Consume Responses events in arrival order.
    if event.type == "response.output_text.delta":  # Handle only text-delta events; other events have different meanings.
        print(event.delta, end="", flush=True)  # Show this text increment immediately.
```

Tool calls, failure, and completion also produce events; branch on `event.type` for each one.

## 6. Image understanding

```python
response = openai_client.responses.create(  # Start a multimodal Responses request containing a public image URL.
    model="grok-4.5",  # Select a vision-capable model and verify current documentation for capability.
    input=[  # Send a structured input array containing a multimodal user message.
        {  # One user-message object.
            "role": "user",  # Identify the message role.
            "content": [  # Combine text task and image with content blocks.
                {"type": "input_text", "text": "Explain the chart trend and name its axes."},  # Describe the image-analysis task.
                {  # The second block provides an image.
                    "type": "input_image",  # Identify this as image input.
                    "image_url": "https://api.nga.gov/iiif/a2e6da57-3cd1-4235-b20e-95dcaefed6c8/full/!800,800/0/default.jpg",  # Use a public example image; production use must respect access and copyright rules.
                },
            ],
        }
    ],
)

print(response.output_text)  # Print the SDK's combined vision-analysis text.
```

Use a model that supports visual input. Check the current Image Understanding documentation for image formats, size limits, and token accounting.

## 7. Server-side search tools

The native xAI SDK can let Grok use server-side tools such as Web Search and X Search:

```python
from xai_sdk.chat import user  # Import the helper used to construct a user chat message.
from xai_sdk.tools import web_search, x_search  # Import native server-side search tool factories.

chat = client.chat.create(  # Create a session that permits controlled server-side search tools.
    model="grok-4.5",  # Select a currently supporting model; verify capability and pricing in official documentation.
    tools=[web_search(), x_search()],  # Explicitly enable Web and X Search rather than granting arbitrary network access.
)
chat.append(user("Find important updates in the official Python ecosystem today and cite sources."))  # Add a time-sensitive retrieval task.

response = chat.sample()  # Let the model complete one turn under the tool contract.
print(response.content)  # Print final text; production code must also inspect citations and tool-call details.
```

Available tools and citation structures vary by SDK and account. For verifiable results, inspect tool calls and citations instead of retaining only final text.

## 8. Custom function calling

This example uses the OpenAI-compatible Responses format:

```python
import json  # Parse model function arguments and serialize local tool results.


def get_weather(city: str) -> dict:  # Define a side-effect-free teaching tool actually executed by the host program.
    return {"city": city, "temperature": 25, "unit": "celsius"}  # Return fixed offline data instead of making a real network call.


tools = [{  # Declare a callable Responses function tool to the model.
    "type": "function",  # Identify the tool category.
    "name": "get_weather",  # The tool name must match the host allowlist.
    "description": "Look up weather for a city.",  # Help the model decide when to call it.
    "parameters": {  # Use JSON Schema to constrain argument shape.
        "type": "object",  # Arguments must be an object.
        "properties": {"city": {"type": "string"}},  # Permit only a string city field.
        "required": ["city"],  # Require city for every invocation.
        "additionalProperties": False,  # Reject undeclared fields to reduce executable input surface.
    },
}]

response = openai_client.responses.create(  # Let the model decide first whether this function is needed.
    model="grok-4.5",  # Select a model that supports Function Calling.
    input="What is the temperature in Shanghai now?",  # Supply a question that can trigger the tool.
    tools=tools,  # Send the permitted tool schema.
)

tool_outputs = []  # Collect one function_call_output for every function_call.
for item in response.output:  # Inspect every output item from this model turn.
    if item.type == "function_call" and item.name == "get_weather":  # Process only an allowlisted function call.
        arguments = json.loads(item.arguments)  # Parse model JSON; production code must validate schema, authorization, and semantics first.
        result = get_weather(**arguments)  # Pass validated arguments to the local function.
        tool_outputs.append({  # Append a result bound precisely to this function invocation.
            "type": "function_call_output",  # State that the item is a tool execution result.
            "call_id": item.call_id,  # Correlate it with the model's function-call ID.
            "output": json.dumps(result),  # Encode the result as JSON.
        })

if tool_outputs:  # Continue only after at least one function was actually executed.
    final = openai_client.responses.create(  # Ask the model for a final answer based on all tool results.
        model="grok-4.5",  # Keep the same model as the tool-decision turn.
        input=tool_outputs,  # Return every tool output together.
        tools=tools,  # Continue with the same tool contract.
        previous_response_id=response.id,  # Reference the preceding Response to keep the tool-call context.
    )
    print(final.output_text)  # Print the final text answer based on tool results.
```

xAI can request several functions in parallel by default. Process all calls, validate parameters, then continue the conversation.

## 9. Common native SDK capabilities

The official xAI SDK also provides these learn-as-needed entry points:

| Capability | Typical entry point |
| --- | --- |
| Image generation | `client.image` methods. |
| Video generation | `client.video.generate()`. |
| Model information | `client.models` methods. |
| Tokenization | `client.tokenize` methods. |
| Delayed work | Deferred chat / polling. |

Models, parameters, and return objects for these capabilities move quickly. Open current SDK examples directly before use; do not copy a complete snippet from an old tutorial.

## Frequent mistakes

- Mixing response objects from native `xai-sdk` and the OpenAI-compatible SDK.
- Forgetting `base_url="https://api.x.ai/v1"` on compatible calls.
- Mixing the tuple from `chat.stream()` with Responses events in streaming code.
- Using old Chat Completions examples to learn new tool features.
- Reading only final text from a search tool without retaining citations.
- Processing only the first of parallel function calls.
- Taking a model name from a chat-product UI rather than the API Models page.

## Official further reading

- [xAI Quickstart](https://docs.x.ai/developers/quickstart)
- [Official Python SDK](https://github.com/xai-org/xai-sdk-python)
- [Responses API](https://docs.x.ai/developers/api-reference#responses)
- [Function Calling](https://docs.x.ai/developers/tools/function-calling)
- [Web Search](https://docs.x.ai/developers/tools/web-search)
- [Image Understanding](https://docs.x.ai/developers/image-understanding)
- [Models](https://docs.x.ai/developers/models)

Return to [[api/ai-api-reference/00-index|Vendor AI API Reference Index]]; general HTTP contracts and reliability are in [[api/00-index|API Learning Path]].
