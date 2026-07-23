---
title: "Task, Message, and Artifact Lifecycles"
aliases:
  - A2A Task lifecycle
  - A2A Message and Artifact lifecycle
tags:
  - a2a
  - task-state
  - lifecycle
source_checked: 2026-07-21
content_origin: original
content_status: dynamic
source_baseline: A2A Protocol 1.0.0 core data model
lang: en
translation_key: A2A/03-Task消息与工件生命周期.md
translation_source_hash: 1c985f17206b001de8a9daf8def87295ac64dc646d6746c91fd332538fcbf8de
translation_route: zh-CN/A2A/03-Task消息与工件生命周期
translation_default_route: zh-CN/A2A/03-Task消息与工件生命周期
---

# Task, Message, and Artifact Lifecycles

## Goals of this lesson

- Distinguish Message, Task, TaskStatus, Part, and Artifact.
- Handle terminal states, interrupted states, supplemental input, and authorization recovery.
- Design idempotency boundaries for retries, duplicate events, and incomplete history.

## The five objects have distinct responsibilities

| Object | Engineering responsibility | Common misuse |
| --- | --- | --- |
| Message | Starts a Task, clarifies, supplies input, or explains status | Put a critical final deliverable only in a Message |
| Task | A stateful work unit with a server-generated ID | Pass off a client-local ID as a server Task ID |
| TaskStatus | The current state, optional message, and time | Read only its text and ignore its enumerated state |
| Part | A text, byte, URL, or structured-data segment within a Message or Artifact | Set multiple content fields at the same time |
| Artifact | A formal output produced by a Task | Treat transient progress as the final result |

A2A 1.0 explicitly recommends using an Artifact to deliver a Task result; a Message is better suited to communication. A Task's \`history\` is not guaranteed to retain all messages, and a resumed stream is not guaranteed to fill in every previous transient message. Critical results therefore cannot rely only on temporary status text.

## Task state machine

\`\`\`mermaid
stateDiagram-v2
    [*] --> TASK_STATE_SUBMITTED
    TASK_STATE_SUBMITTED --> TASK_STATE_WORKING
    TASK_STATE_SUBMITTED --> TASK_STATE_REJECTED
    TASK_STATE_WORKING --> TASK_STATE_INPUT_REQUIRED
    TASK_STATE_WORKING --> TASK_STATE_AUTH_REQUIRED
    TASK_STATE_INPUT_REQUIRED --> TASK_STATE_WORKING
    TASK_STATE_AUTH_REQUIRED --> TASK_STATE_WORKING
    TASK_STATE_SUBMITTED --> TASK_STATE_COMPLETED
    TASK_STATE_WORKING --> TASK_STATE_COMPLETED
    TASK_STATE_SUBMITTED --> TASK_STATE_FAILED
    TASK_STATE_WORKING --> TASK_STATE_FAILED
    TASK_STATE_SUBMITTED --> TASK_STATE_CANCELED
    TASK_STATE_WORKING --> TASK_STATE_CANCELED
    TASK_STATE_COMPLETED --> [*]
    TASK_STATE_FAILED --> [*]
    TASK_STATE_CANCELED --> [*]
    TASK_STATE_REJECTED --> [*]
\`\`\`

The diagram is a teaching-oriented view of common transitions, not a mechanized copy of every behavior allowed by the specification. A real client must follow the specification, the target SDK, and the service contract.

The states are:

- In progress: \`SUBMITTED\`, \`WORKING\`.
- Interrupted and waiting for external action: \`INPUT_REQUIRED\`, \`AUTH_REQUIRED\`.
- Terminal: \`COMPLETED\`, \`FAILED\`, \`CANCELED\`, \`REJECTED\`.
- \`UNSPECIFIED\`: it cannot be treated as a default success or resumable state.

## Input interruption and authorization interruption differ

\`INPUT_REQUIRED\` means that business input is missing—for example, the user must select the scope of a report. \`AUTH_REQUIRED\` means that authorization needed to continue is not yet satisfied. The latter cannot be solved by asking the user to “send the token in chat.” The specification recommends supplying credentials directly to the original requester through a secure out-of-band channel, rather than forwarding them through each Agent in a chain.

At minimum, a recovery flow records:

1. Which Task and which action were interrupted.
2. Whether it needs business information, human approval, or machine credentials.
3. Who may satisfy the request, and the applicable scope and lifetime.
4. The idempotency point from which work resumes.
5. Whether the client obtains subsequent status through subscription, webhook, or polling.

## The one-of constraint for Part

A2A 1.0 unifies text, files, and data in one \`Part\`; the presence of a member distinguishes the content. Each Part must contain exactly one of \`text\`, \`raw\`, \`url\`, or \`data\`; JSON fields use camelCase and enums use the specification's \`SCREAMING_SNAKE_CASE\`.

This is incompatible with the \`kind\` discriminator and nested \`file\` structure in \`0.3\`. A parser that “liberally accepts everything” is likely to let malformed payloads silently reach downstream systems.

## Idempotency and duplicate delivery

Network retries, stream reconnections, and at-least-once webhook delivery can all create duplicates. Callers need to:

- Deduplicate using \`messageId\`, Task ID, Artifact ID, and an event digest.
- Separate side effects from protocol messages and execute them server-side by a business idempotency key.
- Reject illegal rollback after a terminal state, or explicitly create a new Task for new work.
- Validate Artifact chunks through the combination of ID, order, \`append\`, and \`lastChunk\`.
- Avoid storing data, sending email, or charging again merely because a duplicate \`COMPLETED\` arrives.

## Failure is not one string

At minimum, treat these separately:

- Protocol errors: incompatible fields, binding, version, or operation.
- Authentication/authorization errors: invalid identity or insufficient object scope.
- Task rejection: the server decides not to accept the work.
- Task failure: the server accepted the work but execution failed.
- Delivery failure: the Task may have succeeded, but streaming, webhook delivery, or client handling failed.
- An unacceptable business result: the protocol succeeded but the Artifact does not meet quality or security gates.

## Self-check

1. Why is \`AUTH_REQUIRED\` not a terminal state?
2. Why do both a completed state and an Artifact require validation?
3. Can Task history serve as a complete audit log? Why or why not?

## References

- [A2A 1.0 Core Objects](https://a2a-protocol.org/latest/specification/#41-core-objects)
- [A2A 1.0 Messages and Artifacts](https://a2a-protocol.org/latest/specification/#37-messages-and-artifacts)
- [A2A v1.0 migration notes](https://a2a-protocol.org/latest/whats-new-v1/)
