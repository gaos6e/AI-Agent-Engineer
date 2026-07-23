---
title: "12 Networking and Ports"
aliases:
  - Linux network troubleshooting
  - Port and HTTP checks
tags:
  - AI-Agent-Engineer
  - Linux
  - networking
source_checked: 2026-07-14
lang: en
translation_key: Linux命令/12 网络与端口.md
translation_source_hash: c1dc0df0957a71fdfe12ab416c80e3e0333696e67a434cf7a596eb2674e5dede
translation_route: zh-CN/Linux命令/12-网络与端口
translation_default_route: zh-CN/Linux命令/12-网络与端口
---

# 12 Networking and Ports

## Learning objectives

Gather evidence layer by layer—“addresses and routing → listening sockets → name resolution → TCP/TLS → HTTP”—rather than treating “ping fails,” “a port listens,” or “HTTP 200” as a complete health conclusion.

## Draw the request path first

```text
Application URL
  └─ DNS/hosts: resolve a name to an address
      └─ Routing: choose an interface and next hop
          └─ TCP/UDP: is the target port reachable and does a process listen?
              └─ TLS: certificate, hostname, time, and protocol negotiation
                  └─ HTTP: status code, headers, response body, and application semantics
```

Every layer has distinct failure modes. A `curl` connection refusal and HTTP 503 are not the same problem. A service listening on `127.0.0.1` is not automatically externally reachable.

## Addresses, interfaces, and routes

iproute2 is a common modern Linux toolset:

```bash
ip -brief address show
ip link show
ip route show
ip route get 1.1.1.1
```

- `ip address` displays interface addresses. `UP` does not prove the link and external network are healthy.
- `ip route` shows the routing table. `route get` only shows the path the kernel would choose; it sends no packet.
- Containers and WSL see their own network-namespace/virtual-network view, which is not necessarily the host view.
- macOS/BSD do not use the same `ip` command. Common alternatives include `ifconfig`, `route`, and `netstat`, but options cannot be copied directly.

## Listening ports and connections

```bash
ss -lnt
ss -lntp
ss -tan state established
```

Option intuition: `-l` means listening, `-n` disables name resolution, `-t` means TCP, `-u` means UDP, `-p` means process information, and `-a` means all.

Notes:

- An ordinary user may not see process information for other users. Do not default to sudo merely for complete output.
- `0.0.0.0:8000` means all IPv4 interfaces, while `127.0.0.1:8000` is loopback only. IPv6 `::` behavior also depends on system configuration.
- “A socket is listening” proves only that the kernel has an endpoint; it does not prove routing, proxy, firewall, TLS, or application health.
- Sharing `ss -p` output from a shared host can expose command lines, users, or internal port layout. Redact reports.

Query one known loopback port:

```bash
ss -lnt 'sport = :8765'
```

Support for filter expressions varies by iproute2 version. When unsupported, run `ss -lnt` first and inspect it manually.

## Name resolution

```bash
getent ahosts example.com
getent hosts localhost
```

`getent` queries through the system Name Service Switch, which is closer to the resolution path an application uses. `dig`, `host`, and `resolvectl query` can be unavailable and can bypass or show a different layer; record which tool you use.

Common boundaries:

- `/etc/hosts`, DNS, mDNS, and directory services can all participate in resolution.
- Successful DNS proves only that a record was returned, not that the target port is reachable.
- DNS failure does not mean public Internet failure; it can reflect a search domain, resolver, VPN, or container configuration.
- Do not leak internal domain names or full resolver configuration in a report.

## Use curl to inspect the HTTP layer

For a local lab service:

```bash
curl --disable --noproxy '*' \
  --fail \
  --show-error \
  --location \
  --connect-timeout 3 \
  --max-time 10 \
  --output /dev/null \
  --write-out 'http=%{http_code} remote=%{remote_ip} time=%{time_total}\n' \
  http://127.0.0.1:8765/
```

- `--disable` must be curl’s first option; it ignores the user-level `.curlrc`. `--noproxy '*'` overrides proxy environment variables so this lab request accesses loopback directly.
- `--fail` turns HTTP 400 and above into failures in the usual case, but does not prove the response is true, safe, or business-correct.
- `--location` follows redirects. A redirect across hosts requires a new trust-boundary review.
- Connect timeout and total timeout differ; automation should constrain both.
- URLs, headers, and verbose output can contain tokens, cookies, query parameters, and internal addresses. Do not place secrets directly on a command line.
- `curl -k/--insecure` skips TLS certificate verification and is not a production repair.

Use `--head` to see only response headers, but some applications treat HEAD and GET differently, so one cannot substitute for the other.

## What ping can prove

```bash
ping -c 3 127.0.0.1
```

Successful ICMP echo proves a response along a particular network-layer path. Failure can be caused by permission, policy, or filtering and cannot prove an HTTP service is unavailable. Conversely, successful ping does not prove a target TCP port, TLS, or application health.

## Firewall, proxy, and container boundaries

Firewall rules, cloud security groups, Kubernetes NetworkPolicy, reverse proxies, and port mappings can live at different management layers. `iptables`, `nft`, cloud consoles, and container-orchestration configuration commonly require higher privilege or external authorization, so this introductory course provides no change commands.

Proxy variables also change curl behavior:

```bash
for name in http_proxy https_proxy all_proxy no_proxy HTTPS_PROXY ALL_PROXY NO_PROXY HTTP_PROXY; do
  if [ -n "${!name:-}" ]; then
    printf '%s is set\n' "$name"
  else
    printf '%s is unset\n' "$name"
  fi
done
```

Report only whether a variable is set, not its proxy URL, which can contain credentials. On Unix-like systems curl uses lowercase `http_proxy` only; proxy variables for other protocols can normally use either case. `ALL_PROXY`/`all_proxy` provide fallbacks, and `NO_PROXY`/`no_proxy` provide exclusion lists, with lowercase forms commonly taking priority. Even if uppercase `HTTP_PROXY` exists, it does not mean curl will use it.

## Layered troubleshooting exercise

After completing the loopback service in [[linux-commands/17-agent-service-troubleshooting-practice-and-self-check|the integrated project]], retain in order:

1. `ip -brief address`: whether loopback exists.
2. `ss -lnt 'sport = :8765'`: whether it listens and which address it binds.
3. `curl`: connection, HTTP status, and total time.
4. Logs: whether the corresponding request reaches the application.
5. PID: whether the listening endpoint belongs to the lab process.

When any layer fails, stop guessing downward. Record the exit status and current evidence first.

## Mastery check

- [ ] I can distinguish DNS, routing, listening, TCP, TLS, and HTTP layers.
- [ ] I can explain loopback, binding all interfaces, and port mapping.
- [ ] I know `ss -p`, curl verbose/header output, and proxy variables can leak secrets.
- [ ] I do not substitute a ping result for an application health check.

Next: [[linux-commands/13-archiving-and-extraction|Archiving and extraction]].

## References

Retrieved on **2026-07-14**.

- [ip(8)](https://man7.org/linux/man-pages/man8/ip.8.html)
- [ss(8)](https://man7.org/linux/man-pages/man8/ss.8.html)
- [curl command-line manual](https://curl.se/docs/manpage.html)
- [everything curl: Proxy environment variables](https://everything.curl.dev/usingcurl/proxies/env.html)
- [glibc Name Service Switch](https://sourceware.org/glibc/manual/latest/html_node/Name-Service-Switch.html)
