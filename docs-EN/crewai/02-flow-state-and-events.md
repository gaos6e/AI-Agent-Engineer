---
title: "Flow, State, and Events"
aliases:
  - CrewAI Flows State Events
  - CrewAI Flow Introduction
tags:
  - crewai
  - flow
  - state
  - events
source_checked: 2026-07-21
content_origin: original
content_status: dynamic
lang: en
translation_key: CrewAI/02-Flow State与事件.md
translation_source_hash: fd274fce70300581c72de95436ae7a6ffb5ae317063185ca7b275155cb77d477
translation_route: zh-CN/CrewAI/02-Flow-State与事件
translation_default_route: zh-CN/CrewAI/02-Flow-State与事件
---

# Flow, State, and Events

## Learning objectives

You will use <code>@start</code>, <code>@listen</code>, and <code>@router</code> to understand a Flow event graph, choose structured state, design bounded loops and terminal states, and distinguish the current official documentation’s <code>@persist</code> from checkpointing.

## What a Flow solves

A Crew suits one or more Agents performing cognitive Tasks with clear boundaries. A Flow connects Python code, external services, human feedback, routing, and one or more Crews into a business lifecycle. A common layering is:

~~~text
Flow: receive input -> validate -> call Crew -> review route -> approval -> write
                                           └-> revise (bounded) ->┘

Crew: research Task -> writing Task -> review Task
~~~

Payment, file writing, approval, retry budgets, and final publication must not be controlled only by role prompts. A Flow is not an automatic security boundary either: ordinary code must still protect tool implementations and service authority.

## Intuition for three decorators

The current official Flows page presents:

- <code>@start()</code> to mark an entry point. Every satisfied start runs; the documentation says they can usually run in parallel.
- <code>@listen(method_or_label)</code> to listen for a method output or a route label.
- <code>@router(method)</code> to return a finite label that determines which later listener runs.

The following minimal shape uses a separate namespace for route labels, so a label cannot accidentally equal a handler name and self-listen. This shape was validated with <code>crewai==1.15.4</code>:

~~~python
from crewai.flow.flow import Flow, FlowState, listen, router, start  # Import the Flow base class, state base class, and event-routing decorators.

ROUTE_PUBLISH = "route_publish"  # Keep the publishable route label as one finite, central constant.
ROUTE_REVISE = "route_revise"  # Keep the revision route label as one finite, central constant.

class ReviewState(FlowState):  # Declare recoverable, verifiable review-workflow state.
    attempts: int = 0  # Record attempts for budget and stopping conditions.
    passed: bool = False  # Store a trusted validation result, not free-form model text.

class ReviewFlow(Flow[ReviewState]):  # Bind this Flow to the structured state type above.
    @start()  # Mark the step executed when the Flow starts.
    def draft(self):  # Illustrative step that produces a draft for review.
        self.state.attempts += 1  # Explicitly increment the retry count each time this step is entered.
        return {"draft": "..."}  # Return the smallest draft payload needed by the routing step.

    @router(draft)  # Route from the result returned by draft.
    def review(self, result):  # Receive the preceding result and choose a finite branch.
        self.state.passed = validate(result)  # Write an application-supplied trusted boolean validation result.
        return ROUTE_PUBLISH if self.state.passed else ROUTE_REVISE  # Return only predefined route labels.

    @listen(ROUTE_PUBLISH)  # Run only when the passed-review route label is emitted.
    def handle_publish(self):  # Perform deterministic pre-publication work.
        return "ready"  # Signal a business terminal state; real publication still needs separate authorization and execution.
~~~

The application must provide <code>validate</code>. Route labels should come from a finite set; an unknown label must fail closed. Never treat model free text as a method name.

## Prefer structured state

The official documentation supports both dictionary state and structured state based on Pydantic <code>BaseModel</code>, and automatically maintains a unique ID for Flow state. Structured state is usually more suitable for production because its fields, types, and migrations are explicit.

State should contain only facts needed by later steps:

~~~json
{
  "schema_version": 1,
  "topic": "Agent reliability",
  "stage": "review",
  "attempt": 1,
  "max_attempts": 2,
  "artifact_ref": "sha256:...",
  "approval": null
}
~~~

- <code>schema_version</code> determines whether the state can be safely read or migrated.
- <code>topic</code> freezes the business input for this run; recovery must not let a model rewrite it.
- <code>stage</code> is a controlled routing stage from a finite enumeration.
- <code>attempt</code> and <code>max_attempts</code> make a verifiable retry budget.
- <code>artifact_ref</code> points to a stable digest or identifier for an external artifact rather than embedding a large text block.
- <code>approval</code> remains <code>null</code> until trusted approval is obtained; model text cannot replace it.

Long model text is an artifact, not a routing field. Validate <code>passed</code>, error categories, and approval state in trusted code. When a schema changes, migrate explicitly or reject it; never silently guess at old fields.

## Events are contract-bound business messages

Whether or not you use the official event bus, each event should carry a run ID, contiguous sequence number, type, source, relevant versions, and minimal payload. Event handlers must tolerate duplicate invocation; a side-effecting handler needs a stable action ID and receipt.

~~~json
{
  "sequence": 4,
  "type": "review_completed",
  "payload": {"attempt": 1, "passed": false}
}
~~~

- <code>sequence</code> lets consumers detect omissions, reordering, or duplicates.
- <code>type</code> is a fixed business-event name; a handler must not treat free text as its type.
- <code>payload</code> carries only facts needed for this event—in this example, review count and result.

Do not place API keys, full private user data, or unnecessary model context in events.

## Loops and stopping conditions

“Rewrite when review fails” must also define a maximum attempt count, repeated-error stop, time/cost budget, non-retryable errors, and human takeover. A recommended route is:

~~~text
passed -> ready_to_publish
failed && attempts < 2 -> revise
failed && attempts == 2 -> human_review
permission_denied -> failed
~~~

The offline project is a deterministic implementation of this graph. Even if real CrewAI Agents can plan autonomously, the outer Flow should retain business budgets and terminal states.

## Framework pause is not business authorization

The current Flow documentation provides <code>@human_feedback</code>. It can pause a Flow for human feedback and route outcomes listed in <code>emit</code> to listeners. The following is the **current documented API shape**, not a course example that has been run. Layer B intentionally makes no model, Slack, or approval-service call:

~~~python
from crewai.flow.flow import Flow, listen, start  # Import Flow entry and event-listener decorators.
from crewai.flow.human_feedback import HumanFeedbackResult, human_feedback  # Import the human-feedback pause and result type.

class ReviewFlow(Flow):  # Define a review Flow that needs human feedback before it continues.
    @start()  # Declare draft as the initial Flow entry.
    @human_feedback(  # Pause before draft runs, collect feedback, and convert it to a limited outcome.
        message="Please review this draft.",  # Tell the human reviewer which judgment is needed.
        emit=["approved", "rejected", "needs_revision"],  # Limit routeable results to three predefined labels.
        default_outcome="needs_revision",  # Fall back conservatively to revision rather than approval.
    )
    def draft(self):  # Return draft content for the reviewer.
        return "Content awaiting review"  # Illustrative payload; production also binds a version and action digest.

    @listen("approved")  # Listen only for feedback classified as approved.
    def continue_after_review(self, result: HumanFeedbackResult):  # Receive framework-wrapped feedback.
        return result.feedback  # Return the raw comment for subsequent low-risk steps.
~~~

There is an easy-to-miss boundary: with <code>emit</code>, the official documentation says that an LLM classifies free-text feedback into an outcome. That is useful for **workflow routing and collecting comments**, but cannot alone establish authorization to pay, send, or publish. For a high-impact action, the Tool/service boundary must still verify trusted identity, resource, normalized payload digest, validity period, and one-time receipt. Treating the <code>approved</code> label as an authorization token would turn one model classification error into a permission bypass. The pinned <code>1.15.4</code> wheel also exposes this decorator, but its default LLM is an implementation detail that can change; real projects should configure and test it explicitly rather than relying on a default.

For “review again after revision,” do not make <code>@start()</code> loop on itself: the official documentation says a start fires only once at Flow start. Place the initial trigger and <code>needs_revision</code> in a listener’s bounded <code>or_(...)</code> route, while retaining the attempt, time/cost, and human-terminal budgets described above.

## Persistence and checkpointing: current boundary

The Flows page says a persistence decorator can apply to a class or method, with SQLite as the default backend. In the pinned <code>1.15.4</code> API, write it as <code>@persist()</code> or <code>@persist(SQLiteFlowPersistence(path))</code>. Bare <code>@persist</code> replaces the target with an uncalled decorator function; do not infer syntax from a dynamic web example.

The same system has two distinct hydration operations: <code>kickoff(inputs={"id": uuid})</code> loads the latest state under the same UUID, whereas <code>kickoff(restore_from_state_id=uuid)</code> forks from that snapshot to a new UUID. Both re-enter satisfied parts of the Flow graph; neither automatically skips completed nodes. An unknown UUID can also silently begin a new Flow, so an application wrapper must verify state existence first. The separate Checkpointing page introduces <code>CheckpointConfig</code> and node skipping; it is not a synonym for <code>@persist</code>.

These capabilities can evolve across versions, and page labels differ. The engineering sequence should be:

1. Pin the <code>crewai</code> version and treat the wheel/API reference as execution authority.
2. Verify imports, save location, and recovery entry in a minimal program.
3. Simulate a crash after a step completes.
4. Verify which nodes replay and which results are skipped.
5. Add a separate idempotency receipt for every write action.

The official Checkpointing page also says that manual checkpoint writes are best effort: an error is recorded but execution continues. Enabling checkpointing therefore does not give a business operation a strong persistence guarantee.

## Parallelism and joins

The current documentation is precise: every satisfied <code>@start()</code> runs and **may usually run in parallel**. That describes runtime scheduling potential, not a business-concurrency guarantee. Layer B has one <code>@start()</code> and one receipt-writing listener, so its tests prove only single-process, serial recovery for that fixture. They cannot be generalized to multiple starts, multiple workers, or any shared-state write order.

Multiple starts or asynchronous steps may run concurrently, but only work with no data dependencies and no shared writes is safe to parallelize. A join must check expected branches, timeout, partial failure, and conflict. If two Agents overwrite the same state field, completion order can change the result.

Return worker results as independent events and merge them at one join node. Keep write tools behind that join and approval.

## Common mistakes and diagnosis

- **Treating chat history as Flow state:** extract finite fields, versions, and artifact references.
- **Returning arbitrary router text:** validate fixed labels and provide an unknown branch.
- **Leaving a loop unbudgeted:** add attempts, timeout, cost, and a human terminal state.
- **Equating persistence with idempotency:** checkpoints record an internal position; receipts prove an external action.
- **Letting several listeners write one field:** return immutable results and merge through a single aggregator.
- **Copying a page example directly:** first run minimal import and recovery tests against the pinned version, especially decorator parentheses and route-label self-listening.

## Exercise

Draw a Flow for “collect requirements → prepare quote draft → human approve → send,” and submit:

1. the <code>start</code>, <code>listen</code>, and <code>router</code> nodes and route labels;
2. Pydantic state fields and schema version;
3. terminal states for rejection, expiry, send failure, and human takeover;
4. an idempotency ID and receipt for the send action;
5. recovery tests for a crash before approval and a crash after sending but before saving.

## Mastery check

- [ ] Distinguish Flow state, events, and model-text artifacts.
- [ ] Explain the roles of start, listen, and router.
- [ ] Write a budget and terminal state for a loop.
- [ ] Explain the different roles of persistence, checkpointing, and an idempotency receipt.
- [ ] Design a recovery experiment for the pinned version instead of inferring behavior from docs.

## Next step

Continue to [[crewai/03-tool-boundaries-and-structured-output|Tool Boundaries and Structured Output]] to define what an Agent may do and how its artifacts are accepted. After the main sequence, use [[crewai/08-project-real-crewai-persistent-flow|Project: Real CrewAI Persistent Flow]] to test this lesson’s semantics.

## References

- [CrewAI Flows](https://docs.crewai.com/en/concepts/flows) (cross-checked against the <code>1.15.4</code> wheel; 2026-07-21).
- [CrewAI Human Feedback in Flows](https://docs.crewai.com/en/learn/human-feedback-in-flows) (pausing, feedback, and routing; checked 2026-07-21).
- [CrewAI Checkpointing](https://docs.crewai.com/en/concepts/checkpointing) (dynamic documentation; checked 2026-07-14).
- [CrewAI Event Listeners](https://docs.crewai.com/en/concepts/event-listener) (dynamic documentation; checked 2026-07-14).
