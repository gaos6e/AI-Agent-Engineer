---
title: "Guardrails, Sandboxes, and Human Approval"
aliases:
  - Guardrails, Sandbox, and HITL
  - Agent Defense in Depth
tags:
  - ai-security
  - guardrails
  - sandbox
  - human-in-the-loop
source_checked: 2026-07-21
content_origin: original
content_status: validated
lang: en
translation_key: AI安全/02-控制与治理/05-Guardrail沙箱与人工审批.md
translation_source_hash: 8f2fd8fee6d900d5a7d40f0e5da845f87267bf39533b2cea30e51a92f77a6857
translation_route: zh-CN/AI安全/02-控制与治理/05-Guardrail沙箱与人工审批
translation_default_route: zh-CN/AI安全/02-控制与治理/05-Guardrail沙箱与人工审批
---

# Guardrails, Sandboxes, and Human Approval

## Learning objective

Understand that content guardrails, deterministic policy, sandboxes, and human approval solve different problems. Design short-lived, parameter-bound approval for high-impact actions, and configure deny-by-default file, network, and resource boundaries for code or tool execution.

## Defense in depth: assume every layer will fail

| Control | What it handles well | What it cannot solve alone |
| --- | --- | --- |
| Input or output guardrail | Known harmful patterns, data formats, hints of sensitive fields | Complete authorization, every bypass, operating-system isolation |
| Deterministic policy | Tool allowlists, identity, object, destination, budget | Correctness of natural-language content, unknown business risk |
| Sandbox | Blast radius for files, network, processes, and resources | Whether a particular refund should execute as a business matter |
| Human approval | Informed judgment and accountability for high-impact actions | Hidden parameters, fatigue clicking, parameter substitution after approval |
| Audit and monitoring | Detection, accountability, incident evidence | Blocking every attack before it happens |

Do not generalize “guardrail” to mean every security control. A model-based content classifier is also a probabilistic component: it can false-positive, false-negative, or be affected by adversarial input. It is useful as a supplement, not as the only authorizer.

## The deterministic policy layer

The model may only propose a candidate action. The policy layer receives a trusted identity, task purpose, normalized arguments, object, data classification, environment, budget, and approval state, then returns allow, deny, or review. Deny unknown tools, fields, destinations, and states by default. Separating policy decisions from model prose makes them unit-testable and auditable.

Guardrails, sandboxes, and human approval cannot replace server-side object-level authorization. Even when an approver agrees to “send this email,” the executor must still establish that the current subject may access the body, represent that tenant to send to that recipient, and act on the same object and version bound to the approval.

## Secure human approval

Effective approval is not a reusable `approved=true`. At minimum, the approval UI shows:

- who is acting and in which tenant;
- the normalized tool, object, recipient or destination, and critical arguments;
- data categories that will be used or sent out, with a necessary summary;
- expected side effects, quantity, amount, cost, and reversibility;
- input provenance and risk warnings; and
- the approval's validity period.

The trusted service issues an approval token that binds the subject, action, normalized-argument hash, object, state version, and expiration, and consumes it once. Any change to a critical argument or object state requires reapproval. This prevents “approve A, execute B” and time-of-check/time-of-use (TOCTOU) discrepancies.

Humans in the loop can fail too: repeated popups create fatigue, an interface can hide actual arguments, and an approver may lack authority or context. Put approval only at genuinely high-impact decision points and provide a safe default, deny, edit, escalation, and timeout path.

## Sandbox design checklist

When running model-generated code or an untrusted tool, consider at least:

1. **Isolated principal**: non-privileged, short-lived, and independent for each task.
2. **File system**: mount only necessary input; write output to a dedicated directory; prohibit sensitive host paths.
3. **Network**: deny by default. If access is required, constrain domains, IPs, ports, and redirects to prevent DNS or SSRF bypass.
4. **Processes and system calls**: prohibit privileged access, devices, container sockets, and unnecessary system calls.
5. **Resources**: cap CPU, memory, disk, file count, process count, runtime, and output size.
6. **Secrets**: do not inject production credentials by default; where required, issue a short-lived least-privilege token.
7. **Artifacts**: validate type, size, and content to prevent dangerous executables or path traversal.
8. **Lifecycle**: force termination on timeout, clean up, audit, patch, and alert on escapes.

A container is one implementation tool for isolation, not an automatic security boundary. Its actual strength depends on the runtime, kernel, privileges, mounts, and network configuration. Infrastructure-security teams should choose suitable isolation technology for high-risk code.

## Example control combination

“Generate and run CSV-cleaning code” can be layered as follows: the model proposes code only; static checks reject dangerous imports; a sandbox mounts input read-only, has no network, and limits resources; output can only be the specified CSV or report; policy checks data classification; the user previews row-count changes and the output location before approving replacement of the original file; every step writes to the audit trail for the run ID.

If one layer misses something, other layers still constrain impact. For example, if static analysis misses obfuscated code, no network and a read-only mount still block exfiltration and overwrites.

## Emergency controls and safe failure

Prepare a tool-level emergency shutdown, credential revocation, queue pause, model, prompt, or dependency rollback, and a read-only degradation mode. On failure, never automatically fall back to a more privileged path. Denial reasons should be sufficient for debugging without leaking secrets. Exercise emergency switches regularly, or they may not work during an incident.

## Common mistakes

- An approval shows only the model's natural-language summary, not the actual arguments.
- Approval is permanent or reusable across users, objects, or states.
- A sandbox still mounts a Docker socket, host credentials, or the full network.
- A filter fails open “for availability.”
- Recovery consists of retrying with different wording after denial, creating a bypass loop.

## Exercise and self-check

Write a one-page control contract for “generate and run data-cleaning code”: allowed inputs and outputs; file and network policy; resource quotas; prohibited capabilities; actions requiring approval; approval-binding fields; timeout; and emergency shutdown. Then write five negative tests: path traversal, unknown network access, resource exhaustion, parameter substitution, and approval replay.

- [ ] Can state the failure modes of guardrails, policy, sandboxes, and approval.
- [ ] Can bind approval to the actual, immutable action.
- [ ] Can make the runtime environment default to no secrets, no external network, and minimum file permission.
- [ ] Can exercise disablement, access revocation, rollback, and safe degradation.

## Next step

Continue with [[ai-safety/02-controls-and-governance/06-red-teaming-monitoring-and-incident-response|Red Teaming, Monitoring, and Incident Response]] to verify that controls really work under attack and incident conditions.

## References

- [NIST AI 600-1, Generative AI Profile](https://doi.org/10.6028/NIST.AI.600-1) (July 2024; accessed 2026-07-21)
- [OWASP GenAI Security Project](https://genai.owasp.org/) (accessed 2026-07-21)
- [MITRE ATLAS](https://atlas.mitre.org/) (continuously updated; accessed 2026-07-21)
