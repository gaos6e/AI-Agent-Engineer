---
title: "Agent Service Troubleshooting Practice and Self-Check"
tags:
  - AI-Agent-Engineer
  - Linux
  - integrated-practice
aliases:
  - Linux troubleshooting project
source_checked: 2026-07-14
lang: en
translation_key: Linux命令/17-Agent服务排障实践与自测.md
translation_source_hash: aab692f1eee6c722d478f869300337e0570ec3ce25cffd2380c1a6eef3eb6cb3
translation_route: zh-CN/Linux命令/17-Agent服务排障实践与自测
translation_default_route: zh-CN/Linux命令/17-Agent服务排障实践与自测
---

# Agent Service Troubleshooting Practice and Self-Check

## Project goal

Use one complete, self-contained Bash script to complete two controlled tasks:

1. Validate line count, error count, status distribution, latency, and missing fields in deterministic fictional Agent logs.
2. Start a short-lived HTTP service bound only to `127.0.0.1`, then verify its PID, request log, listener evidence, HTTP response, and stopping result.

The outputs are `report.md` and companion evidence files. The report must distinguish facts, inferences, and limitations; “the command did not error” is not an assertion.

The complete implementation is [[linux-commands/examples/run-agent-cli-lab.sh|run-agent-cli-lab.sh]]. This page explains its design and acceptance rather than asking learners to preserve variables and traps across multiple code fences; the script is the sole execution unit.

> [!important] Safety boundary
> The script rejects root. It rejects a temporary root that overlaps `/`, a home directory, or the working tree at startup in a parent/child relationship. It verifies that the raw lab path is not a symbolic link, that its canonical path is under the expected prefix, that the directory belongs to the current user, and reasserts `pwd -P` before writing. It does not use sudo, scan every user’s processes, read the full environment, connect to the public Internet, or automatically remove the lab directory recursively.

## Prerequisite lessons

- [[linux-commands/00b-linux-environment-and-shell-basics|Linux environment and Shell basics]]: Shell, exit status, quoting, and lab boundaries.
- [[linux-commands/05-searching-and-finding|Searching and finding]] and [[linux-commands/06-text-processing|Text processing]]: constrain scope and produce statistics.
- [[linux-commands/07-pipelines-redirection-and-command-composition|Pipelines and redirection]]: stdout, stderr, `pipefail`, and component failures.
- [[linux-commands/09-process-management|Process management]]: PID, owner, SIGTERM, `wait`, and stop verification.
- [[linux-commands/12-networking-and-ports|Networking and ports]]: loopback, listening sockets, and HTTP evidence boundaries.

## Why use one complete script?

Copying multiple code blocks interactively creates two opposite risks:

- Starting a separate Shell for each block loses `lab_real`, PID, exit status, and traps.
- Pasting everything into a normal interactive Shell can cause `exit` to close it and leave traps behind.

The complete script starts a dedicated child process with `bash script`. Failure exits only that child Bash. Its EXIT trap only stops an experimental PID that the script itself stored and verified belongs to the correct owner. INT and TERM retain exit semantics 130 and 143 respectively.

## Phase 0: static check first

Run from this course directory:

```bash
bash --noprofile --norc -n ./examples/run-agent-cli-lab.sh
```

Exit status 0 proves only that Bash can parse the script. It does not prove required commands exist, Linux behavior is correct, or the project runs successfully.

## Phase 1: log and resource mode

First run the mode that does not start a network service:

```bash
bash --noprofile --norc ./examples/run-agent-cli-lab.sh --log-only
```

The script prints exactly one absolute `lab=` and `report=` path. Do not change it to `/`, `$HOME`, a real project, or a shared mount point.

### 1.1 The primary sample remains unchanged

`service.log` contains these four fixed fictional records:

```text
2026-07-14T10:00:01Z level=INFO run_id=r1 latency_ms=120 status=ok
2026-07-14T10:00:02Z level=ERROR run_id=r2 latency_ms=2200 status=timeout
2026-07-14T10:00:03Z level=WARNING run_id=r3 latency_ms=950 status=retry
2026-07-14T10:00:04Z level=ERROR run_id=r4 latency_ms=1800 status=timeout
```

The script asserts in code that:

- The primary sample has 4 lines.
- `level=ERROR` occurs twice.
- The status distribution is `ok=1`, `retry=1`, and `timeout=2`.
- The latency summary is `count=4 mean=1267.5`.

The status pipeline’s exit status and actual file are retained. Expected and actual files must pass `cmp` rather than being guessed equal by eye.

### 1.2 A missing field contaminates only a copy

The script copies the primary sample to `service-with-missing.log` and appends a fifth record without `latency_ms`. It then asserts:

- The copy has 5 total lines.
- Four records are still usable for latency calculation.
- Its latency summary is exactly the same as the primary sample’s.

This keeps the primary facts in `service.log`, `status-counts.txt`, and the report at four records; it avoids the contradiction “the appended file has five records but the report says four.”

### 1.3 Boundary of resource evidence

`resource-evidence.txt` investigates only the lab path and calls `df`, `du`, `uptime`, and `free` when available. A momentary resource snapshot does not establish a root cause. Git Bash, minimal containers, WSL, and native Linux can differ in both available tools and resource views.

The script prints only the permitted `APP_ENV` field. It does not run bare `env`, `set`, `export -p`, or `ps -ef`, avoiding collection of unrelated secrets and other users’ command lines.

## Phase 2: complete loopback service

Run this only in WSL, a container, or a Linux environment that you own:

```bash
bash --noprofile --norc ./examples/run-agent-cli-lab.sh
```

The default port is 8765. Only after confirming a conflict and changing the lab configuration consistently may you set `LAB_PORT` to a 1–5 digit decimal integer with no leading zero. The script then parses decimal explicitly and restricts it to 1024–65535. Do not terminate an unknown process that uses the port.

### 2.1 Evidence before startup

The script requires runnable `python3` and curl, not merely paths with those names. It uses:

```text
python3 -m http.server PORT --bind 127.0.0.1 --directory LAB_REAL
```

`http.server` is solely for a controlled lab, not a production server. Binding `127.0.0.1` avoids exposing it through other interfaces. Its PID comes from `$!`, then `ps` verifies its owner and retains process evidence.

### 2.2 Readiness, response, and request log

The readiness loop puts `--disable` first in curl and uses `--noproxy '*'`, ignoring `.curlrc` and proxy environment variables to access loopback directly. It sets both a connect timeout and a total timeout and stops waiting if the process exits early. Success requires all of the following:

- curl succeeds.
- `health-response.json` and fixed `health.json` match through `cmp`.
- `server.log` contains a GET 200 record for `/health.json`.
- The request-log hit count appears in an evidence file and the report.

This makes a positive loop of “request → response → application log → PID.” It still does not prove remote reachability, TLS, authentication, dependencies, or production health.

### 2.3 Port evidence

When `ss` is available, the script retains `ss -lntp` output limited to the target port and records separately:

- Whether it observed a listener on the target port.
- Whether output allowed verification of the experimental PID.

An ordinary user or a particular environment might not expose the process field. In that case, the report must say `unavailable`, not fabricate “port owner verified.”

### 2.4 TERM, wait, and request after stopping

The script retains and checks:

- `kill -TERM` exit status, which must be 0.
- The actual `wait` exit status.
- Whether `kill -0` still observes the PID.
- The exact curl exit status after stopping.

This lab requires curl 7 (unable to connect) after stopping the loopback service and also requires the PID to be gone. Any other nonzero status is a different failure category and cannot be summarized as “stopped successfully.” The script does not use SIGKILL.

## Evidence files

| File | What it proves | What it cannot prove |
| --- | --- | --- |
| `report.md` | Assertion results and limitations actually recorded by this run | It is not a production incident report. |
| `service.log` | Four deterministic primary records | It does not represent a real traffic distribution. |
| `service-with-missing.log` | A five-record copy containing a missing field | It does not change the primary sample. |
| `status-counts.txt` | Actual output from the status pipeline | It does not represent future trends. |
| `latency-summary*.txt` | Parseable latency summaries for primary and dirty copies | A missing field is not zero. |
| `shell-process-evidence.txt` | Limited current child-Shell process evidence, or an unavailable declaration | It does not scan other users. |
| `resource-evidence.txt` | Momentary resource evidence for the lab path | It is not a root cause. |
| `server-process-evidence.txt` | Experimental service PID, owner, and command line | Generated only in complete mode. |
| `request-log-evidence.txt` | A log line for the successful health request | It does not prove business dependencies are healthy. |
| `port-evidence.txt` | Limited listener output when `ss` is available | The process field can be invisible. |

## Report writing

After reading `report.md`, write the following four sections separately. Do not mix speculation into facts.

### Confirmed facts

Write only information directly supported by assertions and evidence files, such as primary-record count, statistics, PID, and exit statuses.

### Reasonable inferences

State judgments supported, but not directly proved, by combined evidence, such as “the experimental child process is likely this HTTP service.”

### Unknowns

List unverified remote networking, TLS, authentication, dependencies, production traffic, and real service-manager state.

### Actions requiring approval

List external-state changes such as restart, elevation, package installation, firewall changes, port exposure changes, and directory removal. The project does not execute them.

## Why the lab directory is not automatically removed

Automatic cleanup destroys evidence for review and can turn a path-calculation mistake into a recursive-deletion incident. On completion, manually inspect the printed absolute path, owner, symbolic links, contents, and report. The recursive-deletion signature is for recognition only:

```text
rm -rf -- VERIFIED_ABSOLUTE_LAB_PATH
```

Do not run this template in the course. The learner decides whether to clean up only after independent confirmation.

## Self-check

1. Why cannot `$SHELL` prove which Shell is currently running?
2. Why does the script reject `/`, a home directory, and the startup working tree as a `$TMPDIR` canonical root?
3. Why check both whether raw `lab_dir` is a symlink and the canonical prefix?
4. Does `wc -l` count records, logical lines, or newline characters?
5. What do GNU grep exit statuses 0, 1, and 2 mean?
6. Why does the status pipeline save exit status and compare an expected file?
7. Why put the record lacking latency in a copy rather than appending it to the primary sample?
8. Why can `count=4 mean=1267.5` not be extrapolated to a production population?
9. What differs among `127.0.0.1`, `0.0.0.0`, and port mapping?
10. What evidence does each of curl success, HTTP 200, response-body matching, and a request log add?
11. What should the report say if `ss` cannot show the PID?
12. Why check kill return code, wait return code, PID, and post-stop curl return code after SIGTERM?
13. Why cannot every nonzero curl result mean “connection refused”?
14. Why does the script use a dedicated child Bash instead of cross-fence copying or contaminating an everyday Shell?
15. Which real repair actions need authorization, rollback, and a service manager?

## Scoring and acceptance

| Item | Points | Objective evidence |
| --- | ---: | --- |
| Path and identity guardrails | 15 | Non-root; dangerous roots rejected; raw symlink, canonical prefix, owner, and `pwd -P` assertions pass |
| Primary-log assertions | 15 | Four lines, two ERROR records, and fixed status distribution all asserted in code |
| Missing-field test | 10 | Copy has five lines but latency count remains four and summary matches |
| Pipeline and exit status | 10 | Status-pipeline rc is 0 and actual/expected files match |
| Request loop | 15 | Fixed response matches and GET 200 log evidence exists |
| PID and listener | 10 | PID owner verified; `ss` evidence honestly marked yes/unavailable |
| Stop verification | 15 | TERM rc, wait rc, PID disappearance, and curl rc 7 all retained |
| Report boundary | 10 | Facts, inferences, unknowns, and approval-needed actions are separate |

The total is 100. A passing score is at least 80, and “path and identity guardrails,” “request loop,” and “stop verification” must not be zero. `--log-only` accepts only log and resource portions and cannot establish a complete-project pass.

## Mastery criteria

- [ ] I constrain environment, user, path, and object before writing or sending a signal.
- [ ] I express log statistics as assertions that can fail, rather than manually describing expected values.
- [ ] I can form a limited evidence loop from PID, HTTP, logs, and optional socket evidence.
- [ ] I accurately record unverified items and do not present Git Bash or static syntax checks as Linux execution.
- [ ] I can explain why production services belong to a service manager, monitoring, and change process.

## Actual verification boundary for this review

Retrieved on **2026-07-14**. This round performed Git Bash static syntax checks on the complete script and course Bash fences, and ran `--log-only` in Git Bash to verify deterministic log assertions. No usable WSL distribution was available locally, so loopback, systemd, iproute2, and tmux behavior was not executed on a live Linux system. Git Bash results do not replace Linux acceptance.

Obsidian Reading View was not automatically verified in this review.

## References

- [GNU Bash Reference Manual](https://www.gnu.org/software/bash/manual/bash.html)
- [GNU grep Exit Status](https://www.gnu.org/software/grep/manual/html_node/Exit-Status.html)
- [GNU Coreutils Manual](https://www.gnu.org/software/coreutils/manual/coreutils.html)
- [Python `http.server`](https://docs.python.org/3/library/http.server.html)
- [curl command-line manual](https://curl.se/docs/manpage.html)
- [kill(2)](https://man7.org/linux/man-pages/man2/kill.2.html)
- [ss(8)](https://man7.org/linux/man-pages/man8/ss.8.html)
