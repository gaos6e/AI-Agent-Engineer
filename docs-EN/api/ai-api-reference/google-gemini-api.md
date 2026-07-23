---
title: "Google Gemini API Calls (Interactions and GenerateContent)"
source: https://ai.google.dev/gemini-api/docs/get-started
source_checked: 2026-07-22
source_baseline:
  - Gemini API Getting started, Interactions overview, Interactions migration,
    and Gemini 3.5 GenerateContent migration
content_origin: curated
content_status: dynamic
execution_verified: false
verification_note: "The current Interactions/GenerateContent boundary was
  checked and examples received offline syntax review; no network call was made
  with real credentials."
tags: [ api, ai-api, gemini, google, python ]
aliases: [ Gemini API, Google GenAI API ]
lang: en
translation_key: API/AI API 调用/03-Google Gemini API.md
translation_source_hash: 78104b4ade5230892525ed9f560504038490746ce1f65bc2f3f4ce886756d61a
translation_route: zh-CN/API/AI-API-调用/03-Google-Gemini-API
translation_default_route: zh-CN/API/AI-API-调用/03-Google-Gemini-API
---

# Google Gemini API Calls (Interactions and GenerateContent)

> [!source] Official sources
> This page consolidates the [Gemini API getting-started guide](https://ai.google.dev/gemini-api/docs/get-started), the [Interactions API overview](https://ai.google.dev/gemini-api/docs/interactions-overview), and the [Gemini 3.5 migration guidance](https://ai.google.dev/gemini-api/docs/generate-content/whats-new-gemini-3.5). It was checked on **2026-07-22**. The older `google-generativeai` package is not the primary path in this note.

> [!important] Choose the API family first
> The **Interactions API became generally available in June 2026**. Google recommends it for new projects and places new models and capabilities on that path. The original `generateContent` API is now labelled legacy but remains fully supported. The latter half of this page keeps it for maintaining existing integrations, understanding `contents`/`candidates`/`parts`, and carrying out a migration—not as the default for a new project. Do not mix the two families' history, stream events, tool results, or structured-output contracts.

## Prepare the environment

```powershell
python -m pip install --upgrade google-genai  # Install or update the current Google Gen AI Python SDK in the active environment.
$env:GEMINI_API_KEY = Read-Host 'GEMINI_API_KEY' -MaskInput  # Read the key only into this PowerShell process without recording it in source or history.
```

`genai.Client()` reads `GEMINI_API_KEY` from the current process. Never put a real key in notes, source code, command history, or screenshots.

## Recommended path: the Interactions API

### Minimal text request

```python
from google import genai  # Import the primary module from the current Google Gen AI Python SDK.

client = genai.Client()  # Create a client using GEMINI_API_KEY from the process environment.
interaction = client.interactions.create(  # Create one Interactions API request.
    model="gemini-3.5-flash",  # Use the teaching model; verify availability before production use.
    input="Explain an API call in three points.",  # Supply this turn's user input.
)

print(interaction.output_text)  # Print the SDK's convenient text property.
print(interaction.usage)  # Inspect actual usage for cost and context diagnostics.
```

### Streaming and stateful continuation

```python
from google import genai  # This example is self-contained and can run independently.

client = genai.Client()  # Create a client that obtains credentials from the environment.
stream = client.interactions.create(  # Ask for generation as a sequence of stream events.
    model="gemini-3.5-flash",  # Select a model that supports this example.
    input="Explain REST APIs in 200 words.",  # Define the task for this request.
    stream=True,  # Stream rather than waiting for one complete Interaction object.
)
for event in stream:  # Consume each event in the order it arrives.
    print(event)  # Print raw events for learning; production code should branch by event type and log safely.

first = client.interactions.create(  # Create a stored interaction that the next turn can reference.
    model="gemini-3.5-flash",  # Keep the teaching model consistent across the two turns.
    input="I have two dogs at home.",  # Establish a fact for the following question.
)
second = client.interactions.create(  # Create a second interaction.
    model="gemini-3.5-flash",  # Use the same model for the continuation.
    input="How many paws do they have?",  # Ask a follow-up grounded in the earlier turn.
    previous_interaction_id=first.id,  # Reference the prior stored interaction to continue its history.
)
print(second.output_text)  # Print the continued answer.
```

`previous_interaction_id` carries only stored history. It does not inherit this request's `tools`, `system_instruction`, or `generation_config`, so resend those explicitly when needed. Interactions default to `store=true`: the free tier defaults to one day of retention and paid tiers to 55 days, with shorter 7/14/28-day options. With `store=false`, a previous ID cannot be reused and background execution is unavailable. In stateless mode, persist and replay every model-generated step unchanged—including thoughts and function calls/results—not only visible text. A `create` response primarily contains steps generated in the current turn; check a retrievable Interaction snapshot for complete history.

### Boundary with GenerateContent

Interactions is the preferred entrance for new capabilities, but that does not make the two families' fields interchangeable. Before migration, compare tools, structured output, thinking configuration, files/media, and state semantics one by one. For example, Gemini 3.x should not change `temperature`, `top_p`, or `top_k` in requests; use `thinking_level` (`minimal`, `low`, `medium`, or `high`) to express a reasoning budget. Existing code that depends on a GenerateContent-only or not-yet-migrated capability should remain in a clearly labelled compatibility layer with an explicit model and API version.

## Compatibility path: GenerateContent (legacy but fully supported)

The examples below support existing `client.models.*` / `client.chats.*` integrations. For a new project, start with the Interactions section above.

### Common entry points

| Python method | Purpose |
| --- | --- |
| `client.models.generate_content()` | Text and multimodal generation. |
| `client.models.generate_content_stream()` | Streaming generation. |
| `client.chats.create()` / `chat.send_message()` | SDK-managed multi-turn chat history. |
| `client.files.upload()` | Upload images, audio, video, and documents. |
| `client.models.embed_content()` | Generate text vectors. |
| `client.models.get()` / `client.models.list()` | Inspect model information. |

The teaching examples use the stable `gemini-3.5-flash` model. A `latest` alias can move automatically; production systems should pin a stable model.

### 1. Minimal text generation

```python
from google import genai  # Import the module used by the GenerateContent compatibility path.

client = genai.Client()  # Create a client; credentials come from the current process.

response = client.models.generate_content(  # Call the legacy-compatible generation method.
    model="gemini-3.5-flash",  # Pick the example model; pin and verify models in production.
    contents="Explain an API call in three points.",  # Provide one text content item.
)

print(response.text)  # Print the SDK's convenient text property.
print(response.usage_metadata)  # Inspect usage metadata for cost and quota investigation.
```

`response.text` is a convenience property. Inspect `response.candidates` when you need candidate results, finish reasons, or safety information.

### 2. System instruction and generation configuration

```python
from google.genai import types  # Import strongly typed SDK configuration classes.

response = client.models.generate_content(  # Use the compatibility text-generation method.
    model="gemini-3.5-flash",  # Select the stable model ID used in this example.
    contents="Explain Python virtual environments.",  # State the topic to explain.
    config=types.GenerateContentConfig(  # Keep system guidance and generation settings explicit.
        system_instruction="You are a concise, accurate technical teacher.",  # Constrain role and writing style.
        thinking_config=types.ThinkingConfig(thinking_level="medium"),  # Choose a medium reasoning budget where supported.
        max_output_tokens=800,  # Cap the number of tokens returned by this turn.
    ),
)

print(response.text)  # Print the generated text.
```

Common settings include `system_instruction`, `thinking_config`, `max_output_tokens`, safety settings, tools, and structured output. Do not set `temperature`, `top_p`, or `top_k` for Gemini 3.x; check the selected model's documentation for parameters available on other models. Model support is not uniform.

### 3. Multi-turn chat

```python
chat = client.chats.create(model="gemini-3.5-flash")  # Create a chat object whose history is maintained locally by the SDK.

first = chat.send_message("What is a Python dictionary?")  # Send the first turn and update local chat history.
print(first.text)  # Print the first text response.

second = chat.send_message("Show an example of reading a value by key.")  # Continue the same chat; the SDK carries preceding turns.
print(second.text)  # Print the second text response.
```

The `chat` object is useful for learning and simple sessions because it maintains history in the client. An application that needs durable sessions must save and restore history itself.

### 4. Streaming output

```python
for chunk in client.models.generate_content_stream(  # Use the compatibility streaming method.
    model="gemini-3.5-flash",  # Select the model for this stream.
    contents="Write a seven-day Python API study plan.",  # Supply the task for this generation.
):  # Iterate in the service's arrival order.
    if chunk.text:  # Some events have no text, so test before reading the convenience property.
        print(chunk.text, end="", flush=True)  # Display each text increment immediately.
```

Chat objects can also stream a message:

```python
chat = client.chats.create(model="gemini-3.5-flash")  # Create a chat with SDK-managed local history.

for chunk in chat.send_message_stream("Explain REST APIs in 200 words."):  # Send one message and receive a streamed answer.
    if chunk.text:  # Skip stream events that do not contain text.
        print(chunk.text, end="", flush=True)  # Show the text fragment immediately.
```

### 5. Image understanding

```python
from PIL import Image  # Import Pillow's image-loading interface.

image = Image.open(r"D:\data\chart.png")  # Open a local image that you are authorized to upload; production code must handle missing files and format errors.

response = client.models.generate_content(  # Send a multimodal request containing text and an image.
    model="gemini-3.5-flash",  # Select a vision-capable model and verify its limits before use.
    contents=["Explain the chart trend and name its axes.", image],  # Submit the instruction together with the Pillow image object.
)

print(response.text)  # Print the image-analysis text.
```

Install Pillow when needed:

```powershell
python -m pip install --upgrade pillow  # Install or update Pillow, which is used to read local image files.
```

Small images and short audio can be passed directly. Upload larger or repeatedly used files first.

### 6. Upload and analyse a file

```python
uploaded = client.files.upload(file=r"D:\data\paper.pdf")  # Upload a file that you are authorized to process and retain the returned file reference.

response = client.models.generate_content(  # Request document analysis using the uploaded reference.
    model="gemini-3.5-flash",  # Select a model that supports this file-input route.
    contents=[uploaded, "Summarize this document and list three key conclusions."],  # Provide the file reference and the analysis instruction.
)

print(response.text)  # Print the document summary.
```

Videos and long audio can require processing time after upload. Check file state before generation. See [File input methods](https://ai.google.dev/gemini-api/docs/file-input-methods) for supported formats, retention, and size limits.

### 7. Structured JSON output

```powershell
python -m pip install --upgrade pydantic  # Install or update Pydantic for Python-side response-schema definitions.
```

```python
from pydantic import BaseModel  # Import Pydantic's base class for defining the expected JSON shape.
from google.genai import types  # Import typed GenerateContent configuration classes.


class StudyPlan(BaseModel):  # Define a study-plan schema that the model must follow and the client can validate.
    topic: str  # Name of the study topic.
    days: int  # Number of days covered by the plan.
    tasks: list[str]  # Task text for each day or phase.


response = client.models.generate_content(  # Ask the model for a schema-constrained structured response.
    model="gemini-3.5-flash",  # Select a target model that supports structured output.
    contents="Create a seven-day study plan for learning Python APIs.",  # State the task that needs a structured answer.
    config=types.GenerateContentConfig(  # Declare response format and schema explicitly.
        response_mime_type="application/json",  # Require an application/json response media type.
        response_schema=StudyPlan,  # Use the Pydantic model as the response-field constraint.
    ),
)

plan = StudyPlan.model_validate_json(response.text)  # Parse and validate the returned JSON locally; invalid data raises a validation error.
print(plan.tasks)  # Print the validated task list.
```

Structured output is appropriate for extraction, database writes, and downstream program processing. Do not rely only on a prompt saying “return JSON”; supply a schema as well.

### 8. Function calling

The Python SDK can derive a tool declaration from a function signature and automatically invoke ordinary Python functions:

```python
from google.genai import types  # Import SDK types used to configure tools.


def get_weather(city: str) -> dict:  # Define a local teaching tool that is safe and side-effect free.
    """Look up the current weather for a city."""  # Describe purpose so the model can decide when to call it.
    return {"city": city, "temperature": 25, "unit": "celsius"}  # Return fixed offline data rather than contacting a real weather service.


response = client.models.generate_content(  # Run generation with automatic function calling enabled.
    model="gemini-3.5-flash",  # Choose a model that supports function calling.
    contents="What is the temperature in Shanghai now?",  # Provide a question that can trigger the tool.
    config=types.GenerateContentConfig(tools=[get_weather]),  # Expose only this side-effect-free local function.
)

print(response.text)  # Print the answer after SDK-managed tool invocation and continuation.
```

> [!warning]
> Automatic function calling is suitable for side-effect-free learning examples. For deletion, payments, sending messages, or other high-impact actions, disable automatic execution or enforce strict validation and human approval inside the function.

You can instead declare a `FunctionDeclaration`, inspect the model's returned call, execute it yourself, and return a result. A manual loop is usually safer for complex agents.

### 9. Google Search tool

```python
from google.genai import types  # Import the type used to declare the built-in Google Search tool.

response = client.models.generate_content(  # Allow a controlled built-in search tool during generation.
    model="gemini-3.5-flash",  # Pick a currently supported model; verify capability and pricing with official documentation.
    contents="Find important updates in the official Python ecosystem today and cite the sources.",  # Ask for time-sensitive information.
    config=types.GenerateContentConfig(  # Open the built-in tool explicitly in configuration.
        tools=[types.Tool(google_search=types.GoogleSearch())],  # Enable Google Search only; do not grant arbitrary network access.
    ),
)

print(response.text)  # Print the model's combined result; production code should also inspect grounding metadata.
```

Tool support, billing, and returned grounding metadata depend on the model and account. Check [Grounding with Google Search](https://ai.google.dev/gemini-api/docs/google-search).

### 10. Embeddings

```python
response = client.models.embed_content(  # Convert a batch of texts into numeric vectors.
    model="gemini-embedding-001",  # Use the same embedding model for indexing and querying.
    contents=[  # Supply the texts to vectorize in one batch.
        "Python is suitable for rapid development.",  # First input text.
        "Rust emphasizes performance and memory safety.",  # Second input text.
    ],
)

vectors = [item.values for item in response.embeddings]  # Extract the vector values for each input in response order.
print(len(vectors), len(vectors[0]))  # Check vector count and dimensionality to catch configuration drift.
```

Vectors support semantic retrieval, clustering, classification, and RAG. Indexing and queries must use the same model with consistent task-type and dimensionality configuration.

### 11. Asynchronous request

```python
import asyncio  # Import Python's standard asynchronous event-loop utilities.
from google import genai  # Import the SDK so the async interface is available via client.aio.


async def main() -> None:  # Define an asynchronous script entry point.
    client = genai.Client()  # Create a client using credentials from the process environment.
    response = await client.aio.models.generate_content(  # Await an asynchronous GenerateContent request.
        model="gemini-3.5-flash",  # Select the model used by this example.
        contents="Explain async/await.",  # Supply the user's question for this turn.
    )
    print(response.text)  # Print the generated text response.


asyncio.run(main())  # Run the event loop until main completes in a normal Python script.
```

## Frequent mistakes

- Installing the old `google-generativeai` package while following current `google-genai` examples.
- Using a product name as a model ID instead of copying the ID from the official Models page.
- Depending on a `latest` alias and then observing changed model behaviour; pin a stable version in production.
- Calling generation immediately after uploading a large file without waiting for processing.
- Reading only `response.text` and ignoring finish reasons, safety feedback, or function calls.
- Applying automatic function calling to high-risk side effects.

## Official further reading

- [Gemini API getting started (Interactions path)](https://ai.google.dev/gemini-api/docs/get-started)
- [Interactions API overview](https://ai.google.dev/gemini-api/docs/interactions-overview)
- [Migrate from GenerateContent to Interactions](https://ai.google.dev/gemini-api/docs/migrate-to-interactions)
- [Gemini 3.5 Flash: GenerateContent compatibility and parameter migration](https://ai.google.dev/gemini-api/docs/generate-content/whats-new-gemini-3.5)
- [Gemini API quickstart (legacy GenerateContent switch page)](https://ai.google.dev/gemini-api/docs/quickstart)
- [Text generation](https://ai.google.dev/gemini-api/docs/text-generation)
- [File input methods](https://ai.google.dev/gemini-api/docs/file-input-methods)
- [Function calling](https://ai.google.dev/gemini-api/docs/function-calling)
- [Structured outputs](https://ai.google.dev/gemini-api/docs/structured-output)
- [Embeddings](https://ai.google.dev/gemini-api/docs/embeddings)
- [Models](https://ai.google.dev/gemini-api/docs/models)

Return to [[api/ai-api-reference/00-index|Vendor AI API Reference Index]]; general HTTP contracts and reliability are in [[api/00-index|API Learning Path]].
