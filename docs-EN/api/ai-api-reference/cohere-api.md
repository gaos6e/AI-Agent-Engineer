---
title: "Cohere API Calls"
source: https://docs.cohere.com/v2/cohere-documentation
source_checked: 2026-07-22
source_baseline:
  - Cohere v2 Chat, Embed, Rerank, Tool Use, and Structured Outputs
content_origin: curated
content_status: dynamic
execution_verified: false
verification_note: "The current v2 Chat reference plus model and combination
  limits were checked with offline syntax review; no network call was made with
  real credentials."
tags: [ api, ai-api, cohere, python ]
aliases: [ Cohere API ]
lang: en
translation_key: API/AI API 调用/09-Cohere API.md
translation_source_hash: 819c06d56ee15d59b8d49b1138a5d0b90e9ff7e670f5745dc8250338c03fbaeb
translation_route: zh-CN/API/AI-API-调用/09-Cohere-API
translation_default_route: zh-CN/API/AI-API-调用/09-Cohere-API
---

# Cohere API Calls

> [!source] Official sources
> This page is based on Cohere v2 Chat, Embed, Rerank, Tool Use, and Structured Outputs documentation. The current Python primary client is `cohere.ClientV2`.

## Common entry points

| Python method | Purpose |
| --- | --- |
| `co.chat()` | Text, multi-turn chat, RAG, JSON, and tool calls. |
| `co.chat_stream()` | Streaming chat. |
| `co.embed()` | Embed text, images, or mixed content. |
| `co.rerank()` | Reorder documents by relevance to a query. |

Cohere's generation, Embedding, and Rerank routes can be composed into a RAG workflow.

## Install and set the API key

```powershell
python -m pip install --upgrade cohere  # Install or update the official Cohere Python SDK.
$env:COHERE_API_KEY = Read-Host 'COHERE_API_KEY' -MaskInput  # Read the key into only this PowerShell process; do not put it in source.
```

## 1. Text generation

```python
import os  # Read environment variables so the API key is not hard-coded in source.
import cohere  # Import the Cohere SDK module.

co = cohere.ClientV2(api_key=os.environ["COHERE_API_KEY"])  # Create a v2 client using the process key.

response = co.chat(  # Start one v2 Chat request.
    model="command-a-plus-05-2026",  # Use the teaching model; verify availability on the current official Models page first.
    messages=[  # Supply context in role and chronological order.
        {"role": "system", "content": "You are a concise technical teacher."},  # Constrain answer style.
        {"role": "user", "content": "Explain an API call in three points."},  # Supply the current user question.
    ],
)

print(response.message.content[0].text)  # Print the first text content block.
print(response.usage)  # Inspect actual service usage.
```

Models change quickly. Verify current IDs in [Models](https://docs.cohere.com/v2/docs/models), and do not keep using v1-era `command` aliases.

## 2. Multi-turn chat

```python
messages = [  # Keep complete history in the application; API requests do not remember automatically.
    {"role": "system", "content": "You are a Python teacher."},  # Fixed system instruction.
    {"role": "user", "content": "What is a dictionary?"},  # First user question.
]

first = co.chat(model="command-a-plus-05-2026", messages=messages)  # Send first history and receive an answer.
assistant_text = first.message.content[0].text  # Extract the first text content block.

messages.append({"role": "assistant", "content": assistant_text})  # Write the first answer back into history.
messages.append({"role": "user", "content": "Show an example of reading a value by key."})  # Add a follow-up based on the prior turn.

second = co.chat(model="command-a-plus-05-2026", messages=messages)  # Start the second turn with complete history.
print(second.message.content[0].text)  # Print the second answer.
```

v2 combines the current message and history in `messages`; do not copy v1's `message=` and `chat_history=` pattern.

## 3. Streaming output

```python
stream = co.chat_stream(  # Ask v2 Chat to return content as an event stream.
    model="command-a-plus-05-2026",  # Select the target model for streaming generation.
    messages=[  # Supply this turn's user message.
        {"role": "user", "content": "Write Python API study advice."},  # The generation task.
    ],
)

for event in stream:  # Consume Cohere stream events in arrival order.
    if event.type == "content-delta":  # Handle only textual delta events; other types have different shapes.
        print(event.delta.message.content.text, end="", flush=True)  # Display the text increment immediately.
```

Tool calling and streamed responses also produce other event types. Complex applications should branch by `event.type` rather than assuming every event has text.

## 4. Structured JSON output

```python
import json  # Use Python's standard JSON parser to validate a structured result locally.

response = co.chat(  # Ask the model for a study plan that conforms to JSON Schema.
    model="command-a-plus-05-2026",  # Select a model that supports structured output.
    messages=[{  # State task and JSON requirement clearly in the user message.
        "role": "user",  # Identify the message as user-authored.
        "content": "Create a seven-day Python API study plan and return JSON.",  # Specify content objective and output format.
    }],
    response_format={  # Declare the response's JSON format and field constraints.
        "type": "json_object",  # Require the response body to be a JSON object.
        "json_schema": {  # Use Cohere v2's json_schema field for the schema.
            "type": "object",  # The top-level value must be an object.
            "properties": {  # Define permitted fields and their types.
                "topic": {"type": "string"},  # Study topic.
                "days": {"type": "integer"},  # Number of days.
                "tasks": {"type": "array", "items": {"type": "string"}},  # Array of task strings.
            },
            "required": ["topic", "days", "tasks"],  # Require all three key fields.
        },
    },
)

data = json.loads(response.message.content[0].text)  # Parse text into a Python object; call boundaries should handle exceptions.
print(data["tasks"])  # Read the task list; production code must also validate ranges and business constraints.
```

When JSON output is enabled, the prompt should explicitly mention JSON too. In the v2 Chat reference, the schema field is `json_schema`, not generic `schema`. Also, `response_format` currently **cannot** be combined with `documents` or `tools`. If retrieval/tool execution and stable structure are both needed, split work into auditable stages—retrieve or execute and validate first, then let a structured-generation stage consume the minimum required facts—instead of assuming one request can safely do all of it.

## 5. Provide retrieval documents to Chat

```python
documents = [  # Simulate a small set of relevant documents selected by upstream retrieval.
    "venv isolates project dependencies.",  # A fact directly relevant to the question.
    "pip installs Python packages.",  # Another candidate fact the model may cite.
]

response = co.chat(  # Ask the model to answer from an explicit document collection.
    model="command-a-plus-05-2026",  # Select the chat model used in this example.
    messages=[{"role": "user", "content": "What is venv used for?"}],  # Ask a question that should be answered from the documents.
    documents=documents,  # Pass retrieval-selected texts; this does not replace retrieval or access control.
)

print(response.message.content[0].text)  # Print the first textual answer block.
print(response.message.citations)  # Print citations so evidence can be displayed or audited.
```

This works well when a small set of relevant documents has already been retrieved. Large-scale RAG commonly retrieves with Embed, reranks, then calls Chat.

## 6. Embeddings

```python
response = co.embed(  # Convert a batch of document text into vectors through the Embed API.
    model="embed-v4.0",  # Use an embedding model that stays consistent between indexing and querying.
    texts=[  # Supply document text in a batch.
        "Python is suitable for rapid development.",  # First candidate document.
        "Rust emphasizes performance and memory safety.",  # Second candidate document.
    ],
    input_type="search_document",  # Mark these vectors as retrieval-corpus documents, not user queries.
    output_dimension=1024,  # Specify output dimension; the vector-store schema must match it.
    embedding_types=["float"],  # Request floating-point vectors.
)

vectors = response.embeddings.float  # Retrieve the SDK's float-vector list.
print(len(vectors), len(vectors[0]))  # Check vector count and one vector's dimension.
```

Semantic search must distinguish input type:

- Documents for indexing: `input_type="search_document"`
- User queries: `input_type="search_query"`
- Classification: `classification`
- Clustering: `clustering`

Example query vector:

```python
query_response = co.embed(  # Produce a query vector that can be compared with document vectors.
    model="embed-v4.0",  # Use the same embedding model as indexed documents.
    texts=["Which language is suitable for rapid development?"],  # Supply one user query.
    input_type="search_query",  # Mark this as a query-side input with semantics distinct from document-side input.
    output_dimension=1024,  # Keep dimension equal to indexed vectors.
    embedding_types=["float"],  # Request float vectors.
)

query_vector = query_response.embeddings.float[0]  # Extract the first query vector.
```

Keep model, output dimension, and embedding type identical for indexing and querying.

## 7. Rerank

Rerank takes one query and candidate documents, then returns them reordered by relevance:

```python
documents = [  # Simulate candidate documents returned by upstream vector retrieval.
    "venv isolates dependencies for a Python project.",  # Highly relevant to dependency isolation.
    "Git is used for version control.",  # A lower-relevance distractor.
    "pip installs Python packages.",  # Related to Python dependency management.
]

response = co.rerank(  # Reorder candidate texts by semantic relevance to the query.
    model="rerank-v4.0-pro",  # Select the quality-oriented Rerank model; evaluate latency and cost for actual selection.
    query="How can I prevent dependency conflicts between two Python projects?",  # State the user's retrieval intent.
    documents=documents,  # Supply candidates to rerank.
    top_n=2,  # Request only the two highest-ranked results.
)

for result in response.results:  # Iterate through service-ranked results.
    print(result.index, result.relevance_score, documents[result.index])  # Print original index, relevance score, and matching document text.
```

`rerank-v4.0-pro` is quality oriented, while `rerank-v4.0-fast` favours lower latency and higher throughput. Rerank does not generate an answer; it only returns ranking and relevance scores.

## 8. Function Calling

```python
tools = [{  # Declare a function tool that the model may choose to use.
    "type": "function",  # Identify the tool category as a function.
    "function": {  # Describe tool name, purpose, and input schema.
        "name": "get_weather",  # The name must match a host-authorized executable tool.
        "description": "Look up weather for a city.",  # Help the model choose the tool.
        "parameters": {  # Use JSON Schema to constrain parameters.
            "type": "object",  # Arguments must be an object.
            "properties": {"city": {"type": "string"}},  # Permit only a string city field.
            "required": ["city"],  # Require city for an invocation.
        },
    },
}]

response = co.chat(  # Ask the model whether the declared function is needed for the user question.
    model="command-a-plus-05-2026",  # Select a model that supports tool calling.
    messages=[{"role": "user", "content": "What is the temperature in Shanghai now?"}],  # Supply the current user question.
    tools=tools,  # Send the allowable tool schema to the model.
)

for tool_call in response.message.tool_calls or []:  # Iterate through model calls; safely skip when none were made.
    print(tool_call.function.name, tool_call.function.arguments)  # Display only name and raw arguments; validate and authorize before any execution.
```

The complete flow still needs Python to execute the function and return a `tool` message with the matching `tool_call_id`. Validate arguments before execution.

## Frequent mistakes

- Using `Client` or v1's `message=` shape while reading a response as v2.
- Not branching on `event.type` for stream events.
- Combining `response_format` with `documents` or `tools`, which the current v2 Chat reference does not support.
- Giving indexed documents and user queries the same Embedding `input_type`.
- Mixing vector dimension or model, making vectors incomparable.
- Treating Rerank as a generative model; it only returns ordering and relevance scores.
- Using an obsolete Command model ID.

## Official further reading

- [Cohere Documentation](https://docs.cohere.com/v2/cohere-documentation)
- [Chat API](https://docs.cohere.com/v2/docs/chat-api)
- [Chat Streaming](https://docs.cohere.com/v2/reference/chat-stream)
- [Embeddings](https://docs.cohere.com/v2/docs/embeddings)
- [Rerank](https://docs.cohere.com/v2/docs/rerank)
- [Tool Use](https://docs.cohere.com/v2/docs/tool-use-overview)

Return to [[api/ai-api-reference/00-index|Vendor AI API Reference Index]]; general HTTP contracts and reliability are in [[api/00-index|API Learning Path]].
