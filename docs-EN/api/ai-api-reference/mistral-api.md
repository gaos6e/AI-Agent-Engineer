---
title: "Mistral API Calls"
source: https://docs.mistral.ai/resources/sdks
source_checked: 2026-07-22
source_baseline:
  - Mistral SDK Clients, Chat, Vision, Function Calling, Embeddings, and OCR
content_origin: curated
content_status: dynamic
execution_verified: false
verification_note: "The current official Python SDK primary entry point and
  offline syntax were checked; no network call was made with real credentials."
tags: [ api, ai-api, mistral, python ]
aliases: [ Mistral AI API ]
lang: en
translation_key: API/AI API 调用/08-Mistral API.md
translation_source_hash: 860b0655810b9e8dc22246a2a9d9767b9f49f3ebeaf4d99d48b8aeeb76caed38
translation_route: zh-CN/API/AI-API-调用/08-Mistral-API
translation_default_route: zh-CN/API/AI-API-调用/08-Mistral-API
---

# Mistral API Calls

> [!source] Official sources
> This page is based on [Mistral SDK Clients](https://docs.mistral.ai/resources/sdks), Chat Completions, Vision, Function Calling, Embeddings, and OCR documentation. The official Python package is `mistralai`.

The current Python SDK documentation uses `from mistralai.client import Mistral` and `client.chat.complete(...)`. Other vendors may also use the phrase “chat completion,” but do not reuse their stream events, tool-result messages, OCR inputs, or JSON parameters here. These examples describe the current Mistral SDK shape only; validate the exact SDK version and API reference before production integration.

## Common entry points

| Python method | Purpose |
| --- | --- |
| `client.chat.complete()` | Text, multi-turn chat, images, JSON, and tool calls. |
| `client.chat.stream()` | Streaming chat. |
| `client.embeddings.create()` | Text vectors. |
| `client.files.upload()` | Upload a file. |
| `client.files.get_signed_url()` | Obtain a temporary access URL for an uploaded file. |
| `client.ocr.process()` | OCR and document parsing. |

## Install and set the API key

```powershell
python -m pip install --upgrade mistralai  # Install or update the official Mistral Python SDK.
$env:MISTRAL_API_KEY = Read-Host 'MISTRAL_API_KEY' -MaskInput  # Read the key into only this PowerShell process; do not write it into source.
```

## 1. Text generation

```python
import os  # Read environment variables so the API key is not hard-coded in source.
from mistralai.client import Mistral  # Import the synchronous client class from the current SDK.

client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])  # Create a client with the key from the process environment.

response = client.chat.complete(  # Start one Mistral Chat request.
    model="mistral-medium-latest",  # Use a convenient learning alias; production should assess whether to pin a snapshot.
    messages=[  # Supply context in role and chronological order.
        {"role": "system", "content": "You are a concise technical teacher."},  # Constrain answer style.
        {"role": "user", "content": "Explain an API call in three points."},  # Supply the current user question.
    ],
)

print(response.choices[0].message.content)  # Print the first candidate assistant message.
print(response.usage)  # Inspect actual service usage.
```

`*-latest` points to a newer version of a model family, which is convenient for learning but can change over time. Production projects should consult [Models](https://docs.mistral.ai/getting-started/models) and decide whether to pin a snapshot.

## 2. Multi-turn chat

```python
messages = [  # Keep complete history in the application; separate API calls do not remember automatically.
    {"role": "system", "content": "You are a Python teacher."},  # Fixed system instruction.
    {"role": "user", "content": "What is a dictionary?"},  # First user question.
]

first = client.chat.complete(  # Send the first message history and receive an answer.
    model="mistral-medium-latest",  # Use the model selected for this example.
    messages=messages,  # Supply current history.
)

messages.append({  # Append the first answer so the next turn can see it.
    "role": "assistant",  # Mark the message as assistant-authored.
    "content": first.choices[0].message.content,  # Preserve the first candidate's text.
})
messages.append({"role": "user", "content": "Show an example of reading a value by key."})  # Add a follow-up grounded in the preceding conversation.

second = client.chat.complete(  # Use the complete history to make the second request.
    model="mistral-medium-latest",  # Keep the model constant to avoid an unintended behaviour change.
    messages=messages,  # Include the first exchange and follow-up.
)

print(second.choices[0].message.content)  # Print the second answer.
```

## 3. Streaming output

```python
stream = client.chat.stream(  # Ask the service for content as Mistral event objects.
    model="mistral-medium-latest",  # Select the model for streaming generation.
    messages=[  # Supply this turn's user message.
        {"role": "user", "content": "Write Python API study advice."},  # The generation task.
    ],
)

for event in stream:  # Consume each Mistral stream event in arrival order.
    text = event.data.choices[0].delta.content  # Read the first candidate's text increment from the event's data layer.
    if text:  # Print only when this event contains visible text.
        print(text, end="", flush=True)  # Show incremental text immediately as a streaming UI would.
```

The outer streaming value is usually an event object; the actual increment is in `event.data`. That differs from an OpenAI SDK chunk structure.

## 4. Image understanding

```python
response = client.chat.complete(  # Start a vision request containing an image and text instruction.
    model="mistral-small-latest",  # Select a vision-capable model and verify current capability before use.
    messages=[  # Build one multimodal user message.
        {  # One user message object.
            "role": "user",  # Identify the message role.
            "content": [  # Combine task and image with content blocks.
                {"type": "text", "text": "Explain the chart trend and name its axes."},  # State the image-analysis task.
                {  # The second content block supplies an image.
                    "type": "image_url",  # Declare that the image is URL-referenced.
                    "image_url": "https://docs.mistral.ai/img/eiffel-tower-paris.jpg",  # Use Mistral's public example image URL.
                },
            ],
        }
    ],
)

print(response.choices[0].message.content)  # Print the vision-understanding text.
```

An image can be a public URL or Base64. Use Chat Completions for ordinary visual question answering; use OCR for document layout, tables, and scanned pages.

## 5. JSON output

```python
import json  # Use Python's standard JSON parser to validate returned content locally.

response = client.chat.complete(  # Ask the model for a study plan in JSON mode.
    model="mistral-medium-latest",  # Select a model that supports JSON output.
    messages=[{  # State the format requirement in the user message explicitly.
        "role": "user",  # Identify the message as user-authored.
        "content": "Return a study plan as JSON with topic, days, and tasks fields.",  # Specify JSON and expected fields together.
    }],
    response_format={"type": "json_object"},  # Request a JSON object from the API.
)

data = json.loads(response.choices[0].message.content)  # Parse returned text; invalid JSON raises immediately.
print(data["tasks"])  # Read the task field; production code must also validate type and ranges.
```

When the business requires fixed fields and types, add JSON Schema or the SDK's structured-output capability and keep local validation.

## 6. Function Calling

```python
import json  # Parse model function arguments and serialize local tool results.


def get_weather(city: str) -> dict:  # Define a side-effect-free teaching tool actually run by the host.
    return {"city": city, "temperature": 25, "unit": "celsius"}  # Return deterministic offline data instead of making a real network request.


tools = [{  # Declare a function tool the model can choose to call.
    "type": "function",  # Identify the tool category.
    "function": {  # Describe function name, purpose, and argument schema.
        "name": "get_weather",  # This name must match a host allowlisted function.
        "description": "Look up weather for a city.",  # Help the model decide when to invoke it.
        "parameters": {  # Constrain input using JSON Schema.
            "type": "object",  # Arguments must be an object.
            "properties": {"city": {"type": "string"}},  # Permit only a string city field.
            "required": ["city"],  # Require city for an invocation.
        },
    },
}]

messages = [{"role": "user", "content": "What is the temperature in Shanghai now?"}]  # Initialize history that persists across tool rounds.
first = client.chat.complete(  # Let the model decide first whether a tool is needed.
    model="mistral-medium-latest",  # Select a model that supports Function Calling.
    messages=messages,  # Send the current user question.
    tools=tools,  # Supply the permitted tool schema.
)

assistant_message = first.choices[0].message  # Obtain the model message and any possible tool_calls.
messages.append(assistant_message)  # Preserve the assistant message unchanged so a tool result can be correlated in context.

for tool_call in assistant_message.tool_calls or []:  # Process every tool call; safely skip if none was requested.
    arguments = json.loads(tool_call.function.arguments)  # Parse model JSON; production code must validate schema, authorization, and semantics first.
    result = get_weather(**arguments)  # Pass validated arguments to the local function.
    messages.append({  # Add a tool-result message for this call ID.
        "role": "tool",  # Identify this message as a tool execution result.
        "tool_call_id": tool_call.id,  # Match the original model call exactly.
        "name": tool_call.function.name,  # Return the tool name as required by this SDK's tool-message shape.
        "content": json.dumps(result),  # Encode the result as JSON.
    })

if assistant_message.tool_calls:  # Continue only after a tool actually ran.
    final = client.chat.complete(  # Let the model produce a final answer based on the tool results.
        model="mistral-medium-latest",  # Use the same model as the tool-decision turn.
        messages=messages,  # Supply the assistant tool calls and matching tool results.
        tools=tools,  # Continue with the same tool contract.
    )
    print(final.choices[0].message.content)  # Print the final answer.
```

Parameters originate from the model and must be validated before execution. One response can request several tools.

## 7. Embeddings

```python
response = client.embeddings.create(  # Convert a batch of text into numeric vectors through the Embeddings API.
    model="mistral-embed",  # Use the same embedding model for indexing and querying.
    inputs=[  # Note that the Mistral SDK uses inputs as its batch-input parameter name.
        "Python is suitable for rapid development.",  # First input text.
        "Rust emphasizes performance and memory safety.",  # Second input text.
    ],
)

vectors = [item.embedding for item in response.data]  # Extract one vector for each input in response order.
print(len(vectors), len(vectors[0]))  # Check vector count and one vector's dimensionality.
```

The parameter here is `inputs`, not `input` as in some compatible SDKs.

## 8. OCR: parse a local PDF

```python
from pathlib import Path  # Use Path to represent a local PDF path.

pdf_path = Path(r"D:\data\paper.pdf")  # Replace with a PDF you are authorized to upload and process.

with pdf_path.open("rb") as pdf_file:  # Open read-only binary content and close it automatically after the block.
    uploaded = client.files.upload(  # Upload the PDF and retain the returned file object.
        file={  # Provide file metadata and content in the object shape required by the SDK.
            "file_name": pdf_path.name,  # Pass the original file name.
            "content": pdf_file,  # Pass the open binary file object.
        },
        purpose="ocr",  # Declare that the upload is for OCR processing.
    )

signed_url = client.files.get_signed_url(file_id=uploaded.id)  # Request a temporary controlled-access URL for the uploaded file.

ocr_response = client.ocr.process(  # Submit the file URL to the OCR processing endpoint.
    model="mistral-ocr-latest",  # Select the OCR model; production must assess latest-alias drift.
    document={  # Build document input according to the OCR schema.
        "type": "document_url",  # State that document_url contains an accessible document address.
        "document_url": signed_url.url,  # Use the just-created temporary signed URL.
    },
)

for page in ocr_response.pages:  # Iterate through every page returned by OCR.
    print(page.markdown)  # Print the page's Markdown representation; production code should store or delete it according to its retention policy.
```

OCR is suitable for text, tables, and layout extraction from documents. A public PDF can be sent directly as `document_url` without an upload.

## Frequent errors

- `401`: API key is invalid or the environment variable did not take effect in a new terminal.
- `402`: account or payment-state issue.
- `429`: rate limiting.
- Reading `client.chat.stream()` events as ordinary completions.
- Passing the wrong Embeddings parameter name, `input`.
- Using ordinary visual QA instead of document OCR, producing unstable table or layout extraction.
- Letting `latest` move without regression tests.

## Official further reading

- [SDK Clients](https://docs.mistral.ai/resources/sdks)
- [Chat Completions](https://docs.mistral.ai/capabilities/completion)
- [Vision](https://docs.mistral.ai/studio-api/conversations/vision)
- [Function Calling](https://docs.mistral.ai/capabilities/function_calling)
- [Embeddings](https://docs.mistral.ai/capabilities/embeddings)
- [Document AI / OCR](https://docs.mistral.ai/capabilities/document_ai)

Return to [[api/ai-api-reference/00-index|Vendor AI API Reference Index]]; general HTTP contracts and reliability are in [[api/00-index|API Learning Path]].
