---
title: "Common OpenAI Responses API Patterns"
tags:
  - llm-api
  - openai
  - responses-api
  - python
aliases:
  - OpenAI Responses API Tutorial
  - OpenAI Responses API in Practice
source_checked: 2026-07-22
source_baseline:
  - OpenAI Responses API Reference and official guides
content_origin: original
content_status: dynamic
lang: en
translation_key: LLM API集成/09-OpenAI Responses API常见用法.md
translation_source_hash: 02b0264f9868ee83d27252198829a6fa194cd5f64f6c039b381ffaec2376312f
translation_route: zh-CN/LLM-API集成/09-OpenAI-Responses-API常见用法
translation_default_route: zh-CN/LLM-API集成/09-OpenAI-Responses-API常见用法
---

# Common OpenAI Responses API Patterns

> Source review date: 2026-07-22. Model identifiers, SDK types, tool parameters, data retention, and prices change. Before copying an example, follow the SDK version pinned by your project and the [Responses API Reference](https://developers.openai.com/api/docs/api-reference/responses). This page uses the Python SDK and puts the model name in an environment variable by default, rather than scattering a mutable model choice throughout business code.

The Responses API is OpenAI's recommended unified generation interface for new projects. A request can accept text or images, return text, structured results, or tool calls, and retain context through `previous_response_id`, manual history, or the Conversations API. It is not a framework that “executes business actions for you”: after a model proposes a function call, your server must still validate, authorize, execute, and return the result.

## Establish a global mental model first

One Responses call can be simplified as:

```text
model + instructions + input + optional tools / state
                    ↓
response: id, status, output[], output_text, usage
```

| Need | Request focus | Result to read |
| --- | --- | --- |
| Ordinary Q&A, rewriting, or summarization | `input` plus optional `instructions` | `response.output_text` |
| Multi-turn chat | `previous_response_id`, manual `history`, or `conversation` | the new response `id` and text |
| Real-time rendering of a long answer | `stream=True` | events such as `response.output_text.delta` |
| Fixed fields for a program | `responses.parse(..., text_format=...)` or `text.format` | a parsed object or JSON |
| Calling your database or order system | `tools=[{"type": "function", ...}]` | `function_call` in `response.output` |
| Looking up current web information | `tools=[{"type": "web_search"}]` | text and `url_citation` annotations |
| Searching uploaded private material | `tools=[{"type": "file_search", ...}]` | text and `file_citation` annotations |
| Image understanding, OCR, or screenshot analysis | an `input_image` content block | `response.output_text` |

`output_text` is a convenience property when you only want final text. When tools, reasoning Items, or other multimodal output are involved, iterate over `response.output` and handle every item's `type`; do not assume `output[0]` is always text.

## 0. Installation and secure configuration

Create an isolated environment in PowerShell 7. The environment variables below exist only for the current terminal session. Production should use the deployment platform's secret manager or controlled environment variables; never put a real key in a frontend, Markdown file, Git, or log.

```powershell
python -m venv .venv  # Create an isolated Python virtual environment in the current directory.
.\.venv\Scripts\Activate.ps1  # Activate the environment so later pip installs affect only this project.
python -m pip install --upgrade openai pydantic  # Install the OpenAI SDK; structured-output examples also use Pydantic.

$env:OPENAI_API_KEY = "<read from a secure secret manager>"  # Put it only in this terminal; never write a real value into code or Git.
$env:OPENAI_MODEL = "gpt-5.6"  # Centralize this tutorial's model choice; a business project should use its own configuration value.
```

All Python examples below share this initialization. If your project pins a model, region, proxy, or retry policy, inject it once through your adapter configuration layer rather than hard-coding it into individual calls.

```python
import os  # Read operating-system environment variables.

from openai import OpenAI  # Import the synchronous client from the OpenAI Python SDK.

client = OpenAI()  # Create a client; it reads the key from OPENAI_API_KEY by default.
MODEL = os.environ["OPENAI_MODEL"]  # Read the model name from centralized configuration and fail immediately if it is missing.
```

## 1. Minimal text generation

Put stable behavior constraints in `instructions` and the current task in `input`. A minimal call needs only `output_text`.

```python
response = client.responses.create(  # Send one non-streaming generation request to the Responses API.
    model=MODEL,  # Select the model supplied by centralized configuration.
    instructions="You are a patient Python tutor. Explain concepts step by step in clear English.",  # Supply stable behavior guidance for this turn.
    input="Explain list comprehensions with one short example.",  # Send the current user task.
)

print(response.output_text)  # Read the final text aggregated by the SDK.
print("response id:", response.id)  # Print the response ID for troubleshooting, continuation, or audit.
print("token usage:", response.usage)  # Print this call's token-usage object.
```

When a user message needs explicit representation, `input` can also be an Item list:

```python
response = client.responses.create(  # Send a request using a typed input Item.
    model=MODEL,  # Select the model for this call.
    instructions="Answer in at most three bullet points; state uncertainty explicitly.",  # Constrain answer style and uncertainty handling.
    input=[  # Explicitly describe an input Item; this can later expand to multiple messages or modalities.
        {  # Begin one user-message Item.
            "role": "user",  # Mark this content as coming from the user.
            "content": "Compare the two most important differences between lists and tuples.",  # Provide the user's concrete question.
        }
    ],
    max_output_tokens=300,  # Cap the maximum output tokens for this turn.
)

print(response.output_text)  # Print the final text answer.
```

`instructions` are top-level system/developer guidance for the current request. In particular, when using `previous_response_id`, the preceding turn's top-level `instructions` do not automatically inherit, so resend stable rules every turn.

## 2. Multi-turn conversation: choose a state strategy first

| Strategy | Best fit | What you must save |
| --- | --- | --- |
| `previous_response_id` | simple serial chat that may store responses server-side | the latest response ID |
| manual history | trimming, audit, or self-hosted context; `store=False` scenarios | input Items and complete `response.output` |
| `conversation` | persistent conversation across sessions, devices, or long-running work | Conversation ID |

### 2.1 Continue with `previous_response_id`

This is the shortest pattern for a chat prototype. `store=True` is written explicitly so the reader can see that the example depends on server-side response storage. Current default storage behavior and retention still need verification against project compliance requirements.

```python
BASE_INSTRUCTIONS = "You are an English learning assistant. Give the conclusion first, then one small verifiable example."  # Centralize stable instructions that must be resent every turn.

first = client.responses.create(  # Create the first response in the conversation.
    model=MODEL,  # Select the model.
    instructions=BASE_INSTRUCTIONS,  # Send stable behavior guidance for the first turn.
    input="Explain what a closure is.",  # Send the first user question.
    store=True,  # Explicitly allow the server to store this response for the next reference.
)

follow_up = client.responses.create(  # Create a second response that references the previous context.
    model=MODEL,  # Select the model.
    instructions=BASE_INSTRUCTIONS,  # Resend stable guidance because previous_response_id does not inherit it automatically.
    previous_response_id=first.id,  # Chain context through the first response ID.
    input="Turn the earlier example into a counter.",  # Supply the new question for this turn.
    store=True,  # Store this response too so a later turn can continue from it.
)

print(follow_up.output_text)  # Print the second answer with preceding context.
```

This retains prior context, but does not make prior tokens free. Earlier inputs in the chain still count as input tokens for later requests. When you need trimming, summarization, or sensitive-content removal, prefer manual history.

### 2.2 Maintain history manually (suitable for `store=False`)

The key is to append complete `response.output`, not only final text. This preserves function calls, reasoning Items, and assistant messages with their correct types for replay.

```python
history = [{"role": "user", "content": "Tell a joke about recursion."}]  # Begin caller-owned history with the first user message.

first = client.responses.create(  # Start the first turn with current history.
    model=MODEL,  # Select the model.
    input=history,  # Send the full context maintained by the caller.
    store=False,  # Do not store the Response object; the caller retains the required context.
)
print(first.output_text)  # Show the first generated joke.

history += first.output  # Append complete typed output rather than only text so continuation context is retained.
history.append({"role": "user", "content": "Explain the punchline."})  # Append the user's second-turn question.

second = client.responses.create(  # Send the manually maintained history to the model.
    model=MODEL,  # Select the model.
    input=history,  # Include first input, first output, and the second user question.
    store=False,  # Continue using caller-maintained state.
)
print(second.output_text)  # Show the model's explanation based on earlier content.
```

`store=False` controls only storage of the Response object. It must not be described as “the whole business chain retains no data.” Application logs, reverse proxies, databases, file storage, and third-party tools still need separate design and audit.

## 3. Streaming text: success only after a completion event

With `stream=True`, the SDK returns an iterable of semantic events. A frontend can render as `response.output_text.delta` arrives, but a server should mark a turn complete only after `response.completed`. An `error`, `response.failed`, broken connection, or missing terminal state must not count as success.

```python
stream = client.responses.create(  # Start a Responses request that returns a semantic event stream.
    model=MODEL,  # Select the model.
    input="Explain in plain language why HTTP requests need timeouts.",  # Set the question for this turn.
    stream=True,  # Enable SSE streaming; the return value is now an iterable event sequence.
)

completed = False  # Assume the request is incomplete first so a partial cannot be mistaken for success.

for event in stream:  # Consume SDK-decoded stream events one at a time.
    # `response.output_text.delta` means the model generated one additional text fragment.
    # `response.completed` means the entire Response has completed.
    if event.type == "response.output_text.delta":  # This event carries a small text increment.
        print(event.delta, end="", flush=True)  # Display the text increment immediately and flush the terminal buffer.
    elif event.type == "response.completed":  # Only this terminal proves the whole response completed.
        completed = True  # Record receipt of a valid completion signal.
    elif event.type in {"response.failed", "error"}:  # Handle both response failure and generic stream error.
        raise RuntimeError(f"Response stream failed: {event}")  # Stop the business flow rather than using an incomplete result.

print()  # Add a newline after streamed text to keep terminal output tidy.
if not completed:  # A connection ending without a terminal is still failure.
    raise RuntimeError("The stream ended before response.completed; the result is not complete.")  # Explicitly reject a partial result.
```

Function arguments can also arrive as incremental events. Do not execute a tool with partial JSON; wait for the corresponding function-call argument completion event, then parse, validate, and authorize it in the normal tool loop in the next section.

## 4. Structured output: give a program an object, not guessed JSON

When a program needs fixed fields (classification, a form, task decomposition), prefer Structured Outputs over asking in a prompt to “return JSON.” The Pydantic helper converts a type definition into a schema and puts a successfully parsed result in the output content's `parsed` field.

```python
from typing import Literal  # Declare a finite string set for the priority field.

from pydantic import BaseModel, Field  # Define and validate a structured-output type with Pydantic.


class SupportTicket(BaseModel):  # Define the ticket object the application expects from the model.
    title: str = Field(description="A title of no more than 40 characters")  # Title field and its instruction to the model.
    priority: Literal["low", "medium", "high"]  # Allow only three priorities rather than an arbitrary string.
    summary: str  # Retain a short summary for a later human reader.
    needs_human: bool  # Mark whether the ticket should go to a human.


response = client.responses.parse(  # Ask the SDK to send a Pydantic schema and parse a successful result.
    model=MODEL,  # Select the model.
    instructions="Extract a support ticket from the user message. State missing information honestly; do not invent order numbers.",  # Constrain factual behavior during extraction.
    input="My order has not arrived after two weeks, and customer-service email has not replied.",  # Supply the user text to extract.
    text_format=SupportTicket,  # Require the final output to match the Pydantic type.
)

ticket = None  # Keep an empty value until a parseable object is found.
for output_item in response.output:  # Iterate over every typed output Item rather than assuming a position.
    if output_item.type != "message":  # Look for final structured text only in a message Item.
        continue  # Skip Items such as tool calls.
    for content in output_item.content:  # Iterate over every content block in the message.
        if content.type == "refusal":  # A safety refusal need not obey the target schema.
            raise RuntimeError(f"Model refusal: {content.refusal}")  # Pass refusal to upper-layer UI or business policy.
        if content.type == "output_text" and content.parsed is not None:  # Accept only text successfully parsed by the SDK.
            ticket = content.parsed  # Extract the Pydantic SupportTicket object.

if ticket is None:  # Raw text must not be used as structured data when no parsed object exists.
    raise RuntimeError("No parseable structured result was returned.")  # Make the caller handle an incomplete or exceptional result explicitly.

print(ticket.model_dump())  # Convert to an ordinary dictionary and print it for inspection.
```

If a schema is shared by multiple languages or services, send JSON Schema directly through `text.format`:

```python
import json  # Parse final JSON text into a Python object.

ticket_schema = {  # Define JSON Schema reusable across services and languages.
    "type": "object",  # Require an object at the root.
    "properties": {  # List the fields the object permits.
        "category": {"type": "string", "enum": ["billing", "shipping", "other"]},  # Restrict category to the specified enum values.
        "needs_human": {"type": "boolean"},  # Require the human-handoff field to be Boolean.
    },
    "required": ["category", "needs_human"],  # Require both fields to appear.
    "additionalProperties": False,  # Reject fields not defined in this schema.
}

response = client.responses.create(  # Request structured output using raw JSON Schema.
    model=MODEL,  # Select the model.
    instructions="Return JSON that conforms to the supplied JSON Schema.",  # Tell the model that final content must be JSON.
    input="The parcel says delivered, but I did not receive it.",  # Provide the user description to classify.
    text={  # Configure the final-text format for the Responses API.
        "format": {  # Enter the concrete format-constraint object.
            "type": "json_schema",  # Select strict JSON Schema output mode.
            "name": "ticket_routing",  # Give the schema an auditable, recognizable name.
            "strict": True,  # Require strict conformance to supported schema constraints.
            "schema": ticket_schema,  # Supply the schema defined above.
        }
    },
)

data = json.loads(response.output_text)  # Convert completed JSON text to a Python dictionary.
print(data)  # Print the parsed structured result.
```

Schema compliance does not mean factual correctness, business-logic correctness, or an authorized action. Continue with domain validation: confirm that an order belongs to the current user, that an amount is in range, and that a write operation received explicit confirmation.

## 5. Function calling: the model proposes, the application executes

The complete function-calling loop is: define tools -> the model returns one or more `function_call`s -> the application validates and executes -> return `function_call_output` with the same `call_id` -> request the model again. A model can make zero, one, or multiple calls in a turn, so do not write an `if` that handles only the first Item.

```python
import json  # Parse function arguments returned by the model and serialize tool-execution results.


TOOLS = [  # Declare every custom tool available for model selection in this turn.
    {  # Begin the complete get_order_status tool contract.
        "type": "function",  # Identify a function tool defined with JSON Schema.
        "name": "get_order_status",  # Provide a stable tool name routable by the application.
        "description": "Look up an order status by order ID; use only for orders the current user is allowed to access.",  # Explain intended use and authorization boundary.
        "parameters": {  # Define the parameter schema the model may submit.
            "type": "object",  # Require parameters as one object.
            "properties": {  # Declare accepted argument fields.
                "order_id": {  # Define the order-ID field.
                    "type": "string",  # Require the order ID to be a string.
                    "description": "An order ID, for example ORD-2026-001",  # Explain the field format to the model.
                }
            },
            "required": ["order_id"],  # Require an order ID on every call.
            "additionalProperties": False,  # Reject parameters outside the schema.
        },
        "strict": True,  # Request that function arguments conform as strictly as possible to the schema.
    }
]


def get_order_status(order_id: str) -> dict:  # Simulate a read-only order lookup.
    # In a real project: obtain user_id from the login session, authorize it, then query the database.
    return {"order_id": order_id, "status": "shipping", "eta": "2026-07-25"}  # Return a lookup result that is safe to send back to the model.


def call_tool(name: str, args: dict) -> dict:  # Route a model-proposed tool name to a controlled application function.
    if name == "get_order_status":  # Permit only the registered read-only tool.
        order_id = args.get("order_id")  # Read the order ID from model-provided JSON arguments.
        if not isinstance(order_id, str) or not order_id.startswith("ORD-"):  # Revalidate type and business format server-side.
            raise ValueError("Invalid order ID format.")  # Reject malformed arguments rather than trusting the model to correct them.
        return get_order_status(order_id)  # Access order data only after local validation passes.
    raise ValueError(f"An unapproved tool was requested: {name}")  # Prevent access to capabilities that were not explicitly exposed.


def parse_tool_arguments(raw_arguments: str) -> dict:  # Limit model-returned JSON arguments to an object shape.
    arguments = json.loads(raw_arguments)  # Parse the raw argument string as JSON syntax first.
    if not isinstance(arguments, dict):  # Prevent arrays, strings, and other values from bypassing later field validation.
        raise ValueError("Tool arguments must be a JSON object.")  # Stop execution when the argument contract does not hold.
    return arguments  # Give only a controlled dictionary to the application router.


MAX_TOOL_ROUNDS = 4  # Bound consecutive tool rounds for one user request to avoid runaway loops and cost growth.


input_items = [  # Initialize the Responses input Item list that will keep growing.
    {"role": "user", "content": "Please check the status of order ORD-2026-001."}  # Supply the first user request.
]

for _ in range(MAX_TOOL_ROUNDS):  # Handle potentially multi-round tool calls within a bounded number of turns.
    response = client.responses.create(  # Ask the model to decide the next step with current context and tool definitions.
        model=MODEL,  # Select the model.
        instructions="Call the tool when you need order status; do not invent lookup results.",  # Require model answers to follow actual tool results.
        input=input_items,  # Send user message, prior output, and existing tool results.
        tools=TOOLS,  # Expose available function tools for this turn.
    )

    function_calls = [  # Filter every typed output Item that asks the application to execute a function.
        item for item in response.output if item.type == "function_call"  # Retain zero, one, or multiple function-call Items.
    ]
    if not function_calls:  # Without a tool call, the model has supplied a final text answer.
        print(response.output_text)  # Print the final natural-language answer.
        break  # Leave the tool loop.

    # Return all output from this turn, preserving function calls and any other typed Items.
    input_items += response.output  # Append complete output so call IDs and other context are not lost.

    for call in function_calls:  # Process every function call proposed in this turn.
        args = parse_tool_arguments(call.arguments)  # Accept only a JSON object before server-side business validation.
        result = call_tool(call.name, args)  # Route, authorize, and execute the real application tool.
        input_items.append(  # Return every tool result to the model as a new input Item.
            {  # Begin a function-output Item associated with the current call ID.
                "type": "function_call_output",  # Explicitly identify this as a function-call output.
                "call_id": call.call_id,  # Correlate the result precisely with the model's original call.
                "output": json.dumps(result, ensure_ascii=False, allow_nan=False),  # Encode the controlled result as standard JSON, preserving Unicode and rejecting non-finite values.
            }
        )
else:  # A pending call remains after the bound is reached.
    raise RuntimeError(f"Tool calling exceeded the {MAX_TOOL_ROUNDS}-round limit; execution stopped.")  # Hand controlled failure to higher-level logging, alerting, or user guidance.
```

`strict=True` constrains argument shape. It does not replace server-side authentication, semantic argument validation, idempotency, audit, or human confirmation for high-risk actions. The example deliberately limits consecutive tool rounds to four; production should also set a total deadline per request plus call-count, rate/cost thresholds, and idempotency protection per tool. For write actions such as refunds, deletion, or sending email, the tool itself must enforce least privilege and confirmation gates. A model calling a function must never immediately cause the side effect.

## 6. Web search: obtain current information and display citations

Use `web_search` for new projects, not legacy `web_search_preview`. `tool_choice="auto"` lets the model decide whether to search; when a requirement explicitly calls for research, use `"required"`. A web answer's `url_citation` must be clearly visible and clickable in a user-facing UI.

```python
response = client.responses.create(  # Start a turn that must use the web-search tool.
    model=MODEL,  # Select the model.
    input="Find the official OpenAI guidance for streaming Responses API output. Give two key points and sources.",  # State the research target and answer format.
    tools=[  # Configure hosted web-search tooling for this turn.
        {  # Begin web-search tool configuration.
            "type": "web_search",  # Use the web-search tool type intended for new projects.
            "search_context_size": "low",  # Choose a smaller search context for a simple factual query.
            "filters": {  # Restrict the allowed search-site scope.
                "allowed_domains": ["developers.openai.com"],  # Permit only the official developer-documentation domain.
            },
        }
    ],
    tool_choice="required",  # Require the model to actually search this turn rather than answer only from prior knowledge.
    include=["web_search_call.action.sources"],  # Request the complete source list used by the search action.
)

print(response.output_text)  # Display the model's synthesized text with inline citations first.

for output_item in response.output:  # Iterate over output Items to extract text citation annotations.
    if output_item.type != "message":  # Search final text only in a model message Item.
        continue  # Skip non-text Items such as web_search_call.
    for content in output_item.content:  # Iterate over message content blocks.
        if content.type != "output_text":  # Process only output-text blocks.
            continue  # Skip refusal or other content types.
        for annotation in content.annotations:  # Read each annotation attached to text.
            if annotation.type == "url_citation":  # Recognize a web URL citation annotation.
                print(f"- {annotation.title}: {annotation.url}")  # Print title and URL that a UI can render.
```

Write only hostnames, not `https://`, in domain filters. A filter narrows evidence sources but does not replace judgement of result quality. Real-time external access is allowed by default; when business rules allow only cached/indexed material, set `external_web_access=False` in the tool object. When you need every retrieved URL, retain the preceding `include`, while also evaluating cost, latency, and external-content exposure in logs.

## 7. File search: let the model retrieve your document library

File search is an OpenAI-hosted built-in tool. Upload files and create a vector store first; wait for indexing to complete, then put the vector-store ID in the `file_search` tool. Once the model decides to call it, the platform performs retrieval; unlike function calling, the application does not return tool output itself.

The initialization below usually occurs once. Store `vector_store.id` in a business database so every question does not re-upload files or recreate the knowledge base.

```python
from time import monotonic, sleep  # Use a monotonic clock to bound the wait window and sleep briefly between polls.


POLL_INTERVAL_SECONDS = 1.0  # Control index-status polling frequency and avoid a tight loop.
INDEX_TIMEOUT_SECONDS = 120  # Set an explicit maximum wait for this initialization.

with open("employee_handbook.pdf", "rb") as file_content:  # Open the local PDF for indexing in binary mode.
    uploaded_file = client.files.create(  # Upload the local file to the OpenAI Files API first.
        file=file_content,  # Supply the open binary file object.
        purpose="assistants",  # Declare use in a retrievable knowledge-base scenario.
    )

vector_store = client.vector_stores.create(name="employee_handbook")  # Create the vector store that will hold this knowledge base.
client.vector_stores.files.create(  # Associate the uploaded file and submit it for vector-store indexing.
    vector_store_id=vector_store.id,  # Identify the target knowledge-base ID.
    file_id=uploaded_file.id,  # Identify the uploaded file to add.
)

# Use the file for retrieval only after indexing completes.
indexing_deadline = monotonic() + INDEX_TIMEOUT_SECONDS  # Record the monotonic deadline for this polling operation.
while monotonic() < indexing_deadline:  # Query file-index status only within the bounded wait window.
    indexed_file = client.vector_stores.files.retrieve(  # Retrieve the latest state of the file association.
        vector_store_id=vector_store.id,  # Identify the vector store to query.
        file_id=uploaded_file.id,  # Identify the file just uploaded and associated.
    )
    if indexed_file.status == "completed":  # Enter the query phase only after indexing completes.
        break  # End polling.
    if indexed_file.status in {"failed", "cancelled"}:  # Recognize non-recoverable indexing terminals explicitly.
        raise RuntimeError(f"File indexing failed: {indexed_file.status}")  # Do not treat a failed file as retrievable material.
    sleep(POLL_INTERVAL_SECONDS)  # Wait at a fixed interval while incomplete to avoid tight polling.
else:  # The deadline passed without a completed or failed terminal.
    raise TimeoutError(f"File indexing did not complete within {INDEX_TIMEOUT_SECONDS} seconds.")  # Let an upper layer record state and decide whether controlled retry is appropriate.

print("Persist this ID for later questions:", vector_store.id)  # Print the knowledge-base ID that should be saved for reuse.
```

A timeout means only that this wait window ended; it does not mean indexing permanently failed. Record `vector_store.id`, file ID, and last status, then let a controlled retry job or human process choose the next action. Asking a question needs only the existing vector store:

```python
response = client.responses.create(  # Ask a question against the existing knowledge base with file_search.
    model=MODEL,  # Select the model.
    instructions="Answer only from the retrieved employee handbook. Say explicitly when supporting evidence is not found.",  # Prevent guesses from replacing document evidence.
    input="How far in advance must remote work be requested?",  # Supply the user's specific handbook question.
    tools=[  # Configure the hosted file-retrieval tool usable this turn.
        {  # Begin file_search tool configuration.
            "type": "file_search",  # Select vector-store file retrieval.
            "vector_store_ids": [vector_store.id],  # Limit the query to the knowledge base created above.
            "max_num_results": 5,  # Retrieve at most five results to balance quality, cost, and latency.
        }
    ],
    include=["file_search_call.results"],  # Include raw retrieval results for audit or debugging.
)

print(response.output_text)  # Print the answer generated from retrieved material.
```

Final text carries `file_citation` annotations. When presenting an answer to an end user, also show file name/citation location. A production system must additionally implement tenant isolation, file authorization, lifecycle, and deletion policy before upload.

## 8. Image input: URL, Data URL, or file ID

An image can use a public URL, Base64 Data URL, or Files API `file_id`. The following example turns a local file into a Data URL. `detail="low"` suits fast, lower-cost coarse understanding; for fine text, spatial relations, or complex charts, choose `high`, `original`, or image preprocessing according to model capability, cost, and accuracy.

```python
import base64  # Encode local image bytes as Base64 text.
import mimetypes  # Infer image MIME type from the filename.
from pathlib import Path  # Read a local image through an object-oriented path API.


def as_data_url(path: str) -> str:  # Convert a local image to a Data URL accepted by the Responses API.
    image_path = Path(path)  # Convert the string path to a Path object.
    mime_type = mimetypes.guess_type(image_path.name)[0] or "image/jpeg"  # Infer MIME type and use a common JPEG default when unknown.
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")  # Read bytes, Base64-encode them, and convert to text.
    return f"data:{mime_type};base64,{encoded}"  # Assemble a standard data: URL.


response = client.responses.create(  # Start a multimodal request containing both text and an image.
    model=MODEL,  # Select a model that supports image input.
    input=[  # Use a user-message Item to carry multiple modalities.
        {  # Begin one message containing text and image content.
            "role": "user",  # Identify the source as the user.
            "content": [  # Send textual instruction and image in sequence.
                {"type": "input_text", "text": "Extract the image title and its three main points."},  # State the task for the image.
                {  # Begin an image-content block.
                    "type": "input_image",  # Identify this block as image input.
                    "image_url": as_data_url("report_screenshot.png"),  # Convert the local screenshot to a Data URL before sending it.
                    "detail": "low",  # Request low-detail visual processing to reduce ordinary-case cost and latency.
                },
            ],
        }
    ],
)

print(response.output_text)  # Print the text result generated from the image.
```

Images also consume input tokens. Do not send CAPTCHAs to a model. Medical images, precise counting, complex spatial localization, and tiny low-resolution text have known limitations; add specialized validation or human review for critical conclusions.

## 9. Delivery checklist: turn “it runs” into “it is usable”

- [ ] API keys are read only on a server or controlled runtime; none entered a browser, repository, or log.
- [ ] The model name comes from centralized configuration and its availability has been verified with the project account.
- [ ] A turn is marked successful only after `response.status` completes or a stream receives `response.completed`.
- [ ] Structured output handles refusal, parse failure, and domain-semantic validation.
- [ ] Business code gates function-call arguments, identity, permission, idempotency, and high-risk confirmation.
- [ ] Web/file-search citations are traceable in the UI, and retrieval scope is isolated by tenant and data permission.
- [ ] Timeouts, bounded retries, and rate limits follow [[llm-api-integration/05-timeouts-errors-rate-limiting-and-retries|Timeouts, Errors, Rate Limits, and Retries]]; do not combine SDK defaults and application retries into unlimited retries.
- [ ] Record `response.id`, model, prompt version, duration, usage, and controlled error category; do not record unnecessary raw sensitive content. See [[llm-api-integration/06-usage-observability-and-provider-adapters|Usage, Observability, and Provider Adapters]].

## Next steps

- To systematically learn tool selection, arguments, authorization, and multi-turn loops, continue to [[tool-calling-function-calling/00-index|Tool Calling (including Function Calling)]].
- To turn this code into a reliable SDK adapter, complete [[llm-api-integration/07-project-reliable-client-and-self-tests|Reliable Client Project and Self-Tests]] and keep real API calls separate from offline contract tests.
- For a long-lived knowledge base, then read [[rag/00-index|RAG]]; do not treat file search as the entire retrieval-system design.

## References

- [OpenAI: Responses API Reference](https://developers.openai.com/api/docs/api-reference/responses) (accessed 2026-07-22)
- [OpenAI: Migrate to the Responses API](https://developers.openai.com/api/docs/guides/migrate-to-responses) (`input`/`output`, `output_text`, and state strategies; accessed 2026-07-22)
- [OpenAI: Conversation state](https://developers.openai.com/api/docs/guides/conversation-state) (`previous_response_id`, manual history, Conversations API, and retention boundaries; accessed 2026-07-22)
- [OpenAI: Streaming API responses](https://developers.openai.com/api/docs/guides/streaming-responses) (semantic events and terminal states; accessed 2026-07-22)
- [OpenAI: Structured model outputs](https://developers.openai.com/api/docs/guides/structured-outputs) (Pydantic/Zod helpers, `text.format`, and refusal; accessed 2026-07-22)
- [OpenAI: Function calling](https://developers.openai.com/api/docs/guides/function-calling) (function loops, `call_id`, and strict schema; accessed 2026-07-22)
- [OpenAI: Web search](https://developers.openai.com/api/docs/guides/tools-web-search) (`web_search`, citations, and domain filtering; accessed 2026-07-22)
- [OpenAI: File search](https://developers.openai.com/api/docs/guides/tools-file-search) (vector stores, indexing, and file citations; accessed 2026-07-22)
- [OpenAI: Images and vision](https://developers.openai.com/api/docs/guides/images-vision) (`input_image`, detail, and limitations; accessed 2026-07-22)
