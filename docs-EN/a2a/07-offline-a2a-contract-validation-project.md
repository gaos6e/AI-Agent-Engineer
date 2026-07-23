---
title: "Project: Offline A2A Contract Validation"
aliases:
  - Offline A2A contract validator
  - A2A contract-validation project
tags:
  - a2a
  - project
  - contract-testing
source_checked: 2026-07-21
execution_verified: 2026-07-21
content_origin: original
content_status: validated
source_baseline: A2A Protocol 1.0.0 AgentCard, TaskState, and Part structure subset
lang: en
translation_key: A2A/07-离线A2A合同验证项目.md
translation_source_hash: b987ad018eff2661fefe07e5e4c36e3963ad6f0ece40542379358fbe74d535a2
translation_route: zh-CN/A2A/07-离线A2A合同验证项目
translation_default_route: zh-CN/A2A/07-离线A2A合同验证项目
---

# Project: Offline A2A Contract Validation

## Project goal

Build a validator that depends only on the Python standard library and runs three kinds of checks against teaching fixtures:

1. Required fields, interface versions, and Part/Skill baselines for an A2A \`1.0\` Agent Card.
2. IDs, Context, state transitions, and completed Artifacts in a sequence of Task snapshots.
3. Fail-closed handling for mixed-in \`0.3\` structures, terminal-state rollback, and Part one-of errors.

> [!warning] Evidence boundary
> This project validates only the structures and local state policy explicitly implemented by the course. It does not start an official SDK or validate JSON-RPC/gRPC/HTTP+JSON wire behavior, TLS, JWS, OAuth, webhooks, streaming order, a real TCK, or cross-vendor interoperability. It therefore cannot be called an A2A conformance test.

## Project files

- \`examples/a2a_contract_validator.py\`: contract and state validator.
- \`examples/a2a_cases.json\`: one valid case and three deliberately failing cases.
- \`examples/test_a2a_contract_validator.py\`: offline regression tests.

## How to run it

From the repository root, run:

\`\`\`powershell
python -B "docs-EN\a2a\examples\a2a_contract_validator.py" --cases "docs-EN\a2a\examples\a2a_cases.json" # Validate Agent Card, Task, and Artifact contracts with offline scenarios; -B prevents cache generation.
python -B "docs-EN\a2a\examples\test_a2a_contract_validator.py" # Run the A2A validator regression tests and check positive and negative contract boundaries.
\`\`\`

No dependency installation, network access, secret, or paid account is required. On success, the CLI prints \`PASS\` for each case and the tests should report 10 passing cases.

## Local baseline for a valid Agent Card

The validator requires:

- Nonempty \`name\`, \`description\`, and Agent \`version\`.
- At least one \`supportedInterfaces\` entry, with HTTPS used for production URLs.
- Every interface declares \`JSONRPC\`, \`GRPC\`, or \`HTTP+JSON\`, or uses an absolute HTTP(S) URI to identify a custom binding. The latter is this project's narrower policy for easier security checks; the official specification itself requires a URI identifier.
- This course's baseline pins \`protocolVersion: "1.0"\`.
- \`capabilities\` is an object.
- Default input/output media types and \`skills\` are nonempty.
- Every skill has \`id/name/description/tags\`.

Some requirements are mandatory A2A 1.0 fields; HTTPS and the pinned \`1.0\` are also this project's deployment and teaching policies. Validation errors explicitly identify a local baseline so that project policy is not presented as protocol text.

Input loading also rejects duplicate JSON fields and nonstandard numeric values. A Part's \`raw\` member must be decodable Base64. This prevents a parser from silently overwriting an earlier value and prevents a “nonempty string” from being mistaken for an already validated byte payload.

## Task snapshot policy

The fixture uses consecutive snapshots of the same Task to demonstrate state changes. The validator requires:

- Task ID and \`contextId\` do not change in the sequence.
- States use the A2A 1.0 enums.
- A terminal state cannot return to a working state.
- \`COMPLETED\` has at least one Artifact.
- An Artifact has an ID and a Part.
- Every Part sets only one of \`text/raw/url/data\`.

The real protocol does not require a client to retain all states in such a JSON array. This representation exists so that states and negative tests can be reproduced offline.

## The four fixtures

| Case | Expected result | Validation focus |
| --- | --- | --- |
| \`valid-v1-contract\` | Pass | 1.0 Card, working → completed, structured Artifact |
| \`reject-v03-shape\` | Fail | Top-level URL, legacy lowercase state, and \`kind\` Part |
| \`reject-terminal-regression\` | Fail | Returns from \`COMPLETED\` to \`WORKING\` |
| \`reject-ambiguous-part\` | Fail | One Part contains both \`text\` and \`data\` |

## Why test error messages

Only asserting “the result failed” makes it easy for an implementation to pass accidentally for the wrong reason. The fixture also declares \`expectedErrors\`; the CLI and tests confirm that the relevant error fragments actually appear. For example, \`reject-v03-shape\` must expose all three categories of migration problem: interface structure, state enum, and legacy Part.

## Extension exercises

1. Add a local deployment policy for \`securitySchemes/securityRequirements\`, but identify which fields are not protocol requirements.
2. Add tests for stream-event one-of constraints, Artifact-chunk aggregation, and duplicate events.
3. Add scheme, domain, resolved-IP, and redirect policies for URL Parts.
4. Build a client/server matrix with two official SDKs in different languages, and report its results separately from this project's offline validation.
5. When integrating the official Inspector/TCK, preserve the tool version, specification version, command, and a summary of raw results.

## Mastery check

- [ ] Explain the distinction between local policy and specification requirements.
- [ ] Explain which migration or security issue each negative fixture prevents.
- [ ] Add an error case without relaxing existing fail-closed behavior.
- [ ] List the evidence still missing to upgrade this project into real interoperability testing.

## References

- [A2A Protocol 1.0.0 official specification](https://a2a-protocol.org/latest/specification/)
- [A2A v1.0 change notes](https://a2a-protocol.org/latest/whats-new-v1/)
- [A2A official SDK and tutorial entry point](https://a2a-protocol.org/latest/sdk/)
