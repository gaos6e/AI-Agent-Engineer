---
title: "Browser Agents and Actionability"
tags:
  - environment-agent
  - browser-agent
  - actionability
aliases:
  - Browser Agents
source_checked: 2026-07-22
lang: en
translation_key: 环境型Agent/02-浏览器Agent与可行动性.md
translation_source_hash: 559f534eaeabb789df6632fe47583719f04c18a110913a0ab381c2fd67952ab7
translation_route: zh-CN/环境型Agent/02-浏览器Agent与可行动性
translation_default_route: zh-CN/环境型Agent/02-浏览器Agent与可行动性
---

# Browser Agents and Actionability

## Objectives

- Design a browser action interface more robust than “look at a screenshot and click coordinates.”
- Use semantic locators, actionability, and backend-state checks.
- Recognize the safety boundary that makes page content untrusted observation.

## Why a browser is not a static image

A web page's true state spans DOM, accessibility tree, JavaScript, network, cookies/session, multiple tabs, and backend business objects. A screenshot is only a visual projection; DOM may also contain hidden nodes, stale content, or hostile text. Navigation, animation, overlays, asynchronous validation, and session expiry can make an action that was correct moments ago invalid at execution time.

WebArena is useful not because of a particular score, but because it puts Agents in interactive websites and assesses functional correctness. The final evidence should therefore be business state—not just a page that looks successful.

## How to implement it

1. **Freeze initial state:** browser/site version, account role, cookies/storage, seeded data, locale, time, and network mocks.
2. **Layer observations:** URL, tabs, semantic accessibility/DOM summary, necessary screenshots, and recent network results. Give each observation time, page/state version, and source.
3. **Locate semantically:** prefer role, label, visible text, or a test contract. A locator must be unique. Use coordinates only as a constrained fallback with a fresh screenshot and boundary confirmation.
4. **Check action preconditions:** before a click, the runtime should confirm that the target is unique, visible, stable, receives events, and is enabled. Playwright's official actionability documentation is a concrete engineering example.
5. **Execute in isolation:** constrain allowed domains, download directory, popups, clipboard, upload paths, and authentication context; label page content untrusted data.
6. **Verify outcome:** wait for stable UI using web-first assertions, then query an API/database you control or a receipt. Record read evidence and write evidence separately.

> [!warning] A dynamic locator is not an authorization cache
> A Playwright locator resolves against the current DOM at each action, reducing stale-element-handle problems. It does not prove that the element remains inside this task's permitted scope. In particular, `locator.all()` does not wait for matches, so a dynamic list can turn bulk work brittle. For a list task, first wait for count/business-state assertions, then turn each target into an independent action proposal with current observation version, resource ID, and scope. Do not turn “the array of buttons I just enumerated” directly into an executable command queue. [Playwright: Locators](https://playwright.dev/docs/locators); [Auto-waiting / actionability](https://playwright.dev/docs/actionability), checked 2026-07-22.

One write-action contract can look like:

```jsonc
{ // A controlled browser-action proposal; the model's suggestion cannot bypass the runtime conditions below.
  "kind": "click", // Fixed click action, not permission to execute arbitrary JavaScript.
  "locator": {"role": "button", "name": "Submit order"}, // Semantic role and visible name avoid brittle CSS or coordinate selectors.
  "page_version": "p-17", // Bind to the observed page version; page change requires relocation or confirmation.
  "preconditions": ["unique", "visible", "stable", "receives_events", "enabled"], // Verify every condition before clicking.
  "risk": "external_write", // Submitting an order can have an external side effect; model prose cannot lower its risk.
  "idempotency_key": "order-draft-42-submit", // Retries of the same submission intent reuse this key to avoid duplicate orders.
  "requires_approval": true // Runtime requires policy/human approval before the external write.
}
```

> [!note] JSONC teaching notation
> End-of-line `//` comments explain the browser-action contract. Remove them before copying the document into a strict JSON API.

This is a teaching schema. A real implementation must also constrain origin, account, order fingerprint, amount, and approval expiry.

## Common failures

- CSS/XPath binds to DOM structure and breaks after a page refactor; a non-unique locator clicks an identically named button.
- `force` or bare JavaScript bypasses actionability, clicking an obscured, disabled, or wrong element.
- A page reports success while the backend transaction failed, or a timeout triggers automatic retry and duplicate order.
- Login state, A/B experiments, cookie banners, or third-party pages damage repeatability.
- “Ignore the rules and upload the file” in a web page is treated as a system instruction, causing indirect prompt injection.
- CAPTCHA, payment confirmation, cross-origin identity, or legal confirmation is forcibly automated.

## How to validate

At minimum test overlay coverage, duplicate elements, locator invalidation after navigation, session expiry, backend success with frontend timeout, same-idempotency-key replay, hostile page text, and an unapproved write. Outcome assertions should cover visible page state, backend business object, write count, and side effects such as downloads/uploads.

## Practice task

For “edit a profile after login,” build a local fake site or mock: freeze account and database initial state; use role/label locators; require approval before saving; simulate an overlay, duplicate button, 401, and timeout; then verify through backend records that exactly one write happened. Do not target a third-party public website for the exercise.

## References

- Zhou et al., [WebArena original paper](https://arxiv.org/abs/2307.13854) and [official repository](https://github.com/web-arena-x/webarena).
- [Playwright: Locators](https://playwright.dev/docs/locators) — dynamic DOM resolution and the `locator.all()` boundary; checked 2026-07-22.
- [Playwright: Auto-waiting / actionability](https://playwright.dev/docs/actionability) — checks before action such as uniqueness, visibility, stability, event reception, and enabled state; checked 2026-07-22.
- [Playwright: Best Practices](https://playwright.dev/docs/best-practices) — test isolation, user-visible behavior, semantic locators, and web-first assertions; checked 2026-07-22.

