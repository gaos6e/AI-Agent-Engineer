#!/usr/bin/env bash

set -Eeuo pipefail
umask 077

mode=${1:-full}
if [ "$#" -gt 1 ]; then
  printf 'usage: bash run-agent-cli-lab.sh [--log-only]\n' >&2
  exit 64
fi
case "$mode" in
  full) ;;
  --log-only) mode='log-only' ;;
  *)
    printf 'unknown mode: %s\n' "$mode" >&2
    exit 64
    ;;
esac

for tool in id realpath mktemp hostname uname ps wc head tail grep sort uniq awk cat df du tr cmp cp; do
  if ! command -v -- "$tool" >/dev/null 2>&1; then
    printf 'required baseline tool missing: %s\n' "$tool" >&2
    exit 69
  fi
done

if [ "$(id -u)" -eq 0 ]; then
  printf 'do not run this lab as root\n' >&2
  exit 77
fi

lab_root_raw=${TMPDIR:-/tmp}
lab_root_real=$(realpath -e -- "$lab_root_raw") || exit 1
workspace_real=$(pwd -P)
home_real=''
if [ -n "${HOME:-}" ]; then
  home_real=$(realpath -e -- "$HOME") || exit 1
fi

paths_overlap_tree() {
  if [ "$1" = '/' ] || [ "$2" = '/' ]; then
    return 0
  fi
  case "$1/" in "$2/"*) return 0 ;; esac
  case "$2/" in "$1/"*) return 0 ;; esac
  return 1
}
if [ "$lab_root_real" = '/' ] \
    || paths_overlap_tree "$lab_root_real" "$workspace_real" \
    || { [ -n "$home_real" ] && paths_overlap_tree "$lab_root_real" "$home_real"; }; then
  printf 'unsafe lab root overlaps home or working tree: %s\n' "$lab_root_real" >&2
  exit 77
fi

lab_dir=$(mktemp -d "$lab_root_real/agent-cli-lab.XXXXXX") || exit 1
if [ -L "$lab_dir" ]; then
  printf 'raw lab path is a symlink\n' >&2
  exit 77
fi
lab_real=$(realpath -e -- "$lab_dir") || exit 1
case "$lab_real" in
  "$lab_root_real"/agent-cli-lab.*) ;;
  *)
    printf 'unexpected lab path: %s\n' "$lab_real" >&2
    exit 77
    ;;
esac
if [ ! -O "$lab_dir" ]; then
  printf 'lab directory is not owned by the current user\n' >&2
  exit 77
fi

cd -- "$lab_real" || exit 1
if [ "$(pwd -P)" != "$lab_real" ]; then
  printf 'working directory assertion failed\n' >&2
  exit 77
fi

server_pid=''
cleanup_server() {
  if [ -n "${server_pid:-}" ] && kill -0 "$server_pid" 2>/dev/null; then
    owner=''
    if owner=$(ps -o uid= -p "$server_pid" 2>/dev/null | tr -d '[:space:]'); then
      :
    fi
    if [ "$owner" = "$(id -u)" ]; then
      kill -TERM "$server_pid" 2>/dev/null || true
      wait "$server_pid" 2>/dev/null || true
    else
      printf 'refuse trap cleanup: server owner is unverified\n' >&2
    fi
  fi
}
trap cleanup_server EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

{
  printf '# Agent CLI lab report\n\n'
  printf '## Environment evidence\n\n'
  printf -- '- mode: `%s`\n' "$mode"
  printf -- '- user_id: `%s`\n' "$(id -u)"
  printf -- '- hostname: `%s`\n' "$(hostname)"
  printf -- '- kernel: `%s`\n' "$(uname -srm)"
  printf -- '- working_directory: `%s`\n' "$lab_real"
  printf -- '- bash_version: `%s`\n' "${BASH_VERSION:-not-bash}"
} > report.md

if ps -p "$$" -o pid=,ppid=,user=,comm=,args= > shell-process-evidence.txt 2>/dev/null; then
  shell_process_evidence='captured'
else
  printf 'detailed ps view unavailable in this environment\n' > shell-process-evidence.txt
  shell_process_evidence='unavailable'
fi
printf -- '- shell_process_evidence: `%s`\n' "$shell_process_evidence" >> report.md

printf '%s\n' \
  '2026-07-14T10:00:01Z level=INFO run_id=r1 latency_ms=120 status=ok' \
  '2026-07-14T10:00:02Z level=ERROR run_id=r2 latency_ms=2200 status=timeout' \
  '2026-07-14T10:00:03Z level=WARNING run_id=r3 latency_ms=950 status=retry' \
  '2026-07-14T10:00:04Z level=ERROR run_id=r4 latency_ms=1800 status=timeout' \
  > service.log

line_count=$(wc -l < service.log | tr -d '[:space:]')
if [ "$line_count" -ne 4 ]; then
  printf 'unexpected service.log line count: %s\n' "$line_count" >&2
  exit 65
fi
head -n 2 -- service.log
tail -n 2 -- service.log

if error_count=$(grep -c -- 'level=ERROR' service.log); then
  error_rc=0
else
  error_rc=$?
fi
if [ "$error_rc" -ne 0 ] || [ "$error_count" -ne 2 ]; then
  printf 'ERROR count assertion failed: rc=%s count=%s\n' "$error_rc" "${error_count:-unset}" >&2
  exit 65
fi

if awk '{
  for (i = 1; i <= NF; i++) {
    if ($i ~ /^status=/) print $i
  }
}' service.log | LC_ALL=C sort | uniq -c | awk '{ print $1, $2 }' > status-counts.txt; then
  status_pipeline_rc=0
else
  status_pipeline_rc=$?
fi
printf '%s\n' '1 status=ok' '1 status=retry' '2 status=timeout' > expected-status-counts.txt
if [ "$status_pipeline_rc" -ne 0 ] || ! cmp -s -- expected-status-counts.txt status-counts.txt; then
  printf 'status distribution assertion failed: rc=%s\n' "$status_pipeline_rc" >&2
  exit 65
fi

summarize_latency() {
  LC_ALL=C awk '
  {
    for (i = 1; i <= NF; i++) {
      if ($i ~ /^latency_ms=[0-9]+$/) {
        split($i, pair, "=")
        sum += pair[2]
        count += 1
      }
    }
  }
  END {
    if (count == 0) exit 2
    printf "count=%d mean=%.1f", count, sum / count
  }
  ' "$1"
}

if latency_summary=$(summarize_latency service.log); then
  latency_rc=0
else
  latency_rc=$?
fi
if [ "$latency_rc" -ne 0 ] || [ "$latency_summary" != 'count=4 mean=1267.5' ]; then
  printf 'latency assertion failed: rc=%s summary=%s\n' "$latency_rc" "${latency_summary:-unset}" >&2
  exit 65
fi
printf '%s\n' "$latency_summary" > latency-summary.txt

cp -- service.log service-with-missing.log
printf '%s\n' \
  '2026-07-14T10:00:05Z level=WARNING run_id=r5 status=partial note=missing_latency' \
  >> service-with-missing.log
dirty_line_count=$(wc -l < service-with-missing.log | tr -d '[:space:]')
if dirty_latency_summary=$(summarize_latency service-with-missing.log); then
  dirty_latency_rc=0
else
  dirty_latency_rc=$?
fi
if [ "$dirty_line_count" -ne 5 ] || [ "$dirty_latency_rc" -ne 0 ] || [ "$dirty_latency_summary" != "$latency_summary" ]; then
  printf 'missing-latency fixture assertion failed\n' >&2
  exit 65
fi
printf '%s\n' "$dirty_latency_summary" > latency-summary-with-missing.txt

{
  printf '\n## Log facts\n\n'
  printf -- '- primary_records: `%s`\n' "$line_count"
  printf -- '- primary_error_records: `%s`\n' "$error_count"
  printf -- '- status_pipeline_rc: `%s`\n' "$status_pipeline_rc"
  printf -- '- status_distribution_matches_fixture: `yes`\n'
  printf -- '- primary_latency_summary: `%s`\n' "$latency_summary"
  printf -- '- dirty_fixture_records: `%s`\n' "$dirty_line_count"
  printf -- '- dirty_fixture_latency_summary: `%s`\n' "$dirty_latency_summary"
  printf -- '- interpretation: sample facts only; not a population trend.\n'
} >> report.md

{
  printf '\n## Resource evidence\n\n'
  if df -h -- "$lab_real"; then :; else printf 'df -h unavailable\n'; fi
  if df -ih -- "$lab_real"; then :; else printf 'df -ih unavailable\n'; fi
  if du -sh -- "$lab_real"; then :; else printf 'du unavailable\n'; fi
  if command -v -- uptime >/dev/null 2>&1; then uptime || true; else printf 'uptime unavailable\n'; fi
  if command -v -- free >/dev/null 2>&1; then free -h || true; else printf 'free unavailable\n'; fi
  printf 'app_env=%s\n' "${APP_ENV:-unset}"
} > resource-evidence.txt
printf -- '- resource_evidence_file: `resource-evidence.txt`\n' >> report.md

if [ "$mode" = 'log-only' ]; then
  {
    printf '\n## Loopback service facts\n\n'
    printf -- '- stage: `skipped by --log-only`\n'
  } >> report.md
  trap - EXIT INT TERM
  printf 'lab=%s\nreport=%s/report.md\n' "$lab_real" "$lab_real"
  exit 0
fi

for tool in python3 curl sleep; do
  if ! command -v -- "$tool" >/dev/null 2>&1; then
    printf 'required service-stage tool missing: %s\n' "$tool" >&2
    exit 69
  fi
done
if ! python3 --version >/dev/null 2>&1; then
  printf 'python3 command exists but is not runnable\n' >&2
  exit 69
fi
current_ps_uid=''
if current_ps_uid=$(ps -o uid= -p "$$" 2>/dev/null | tr -d '[:space:]'); then
  :
fi
if [ "$current_ps_uid" != "$(id -u)" ] || ! ps -p "$$" -o lstart= >/dev/null 2>&1; then
  printf 'procps-compatible ps output is required before starting the service\n' >&2
  exit 69
fi

lab_port=${LAB_PORT:-8765}
if [[ ! $lab_port =~ ^[1-9][0-9]{0,4}$ ]]; then
  printf 'LAB_PORT must be canonical 1-5 digit decimal without leading zero\n' >&2
  exit 64
fi
lab_port=$((10#$lab_port))
if ((lab_port < 1024 || lab_port > 65535)); then
  printf 'LAB_PORT must be between 1024 and 65535\n' >&2
  exit 64
fi

printf '%s\n' '{"status":"ok","service":"agent-cli-lab"}' > health.json
python3 -m http.server "$lab_port" \
  --bind 127.0.0.1 \
  --directory "$lab_real" \
  > server.log 2>&1 &
server_pid=$!

server_uid=''
if server_uid=$(ps -o uid= -p "$server_pid" 2>/dev/null | tr -d '[:space:]'); then
  :
fi
if [ "$server_uid" != "$(id -u)" ]; then
  printf 'server owner mismatch or process exited early\n' >&2
  cat -- server.log >&2 || true
  exit 70
fi
ps -p "$server_pid" -o pid=,ppid=,user=,lstart=,comm=,args= > server-process-evidence.txt

ready=0
last_curl_rc=0
for attempt in 1 2 3 4 5 6 7 8 9 10; do
  if curl --disable --noproxy '*' \
      --fail --silent --show-error \
      --connect-timeout 1 --max-time 2 \
      --output health-response.json \
      "http://127.0.0.1:$lab_port/health.json"; then
    ready=1
    break
  else
    last_curl_rc=$?
  fi
  if ! kill -0 "$server_pid" 2>/dev/null; then
    break
  fi
  sleep 0.2
done
if [ "$ready" -ne 1 ]; then
  printf 'service did not become ready: curl_rc=%s\n' "$last_curl_rc" >&2
  cat -- server.log >&2 || true
  exit 70
fi

if ! cmp -s -- health.json health-response.json; then
  printf 'health response mismatch\n' >&2
  exit 65
fi
response_matches='yes'

request_logged=0
for attempt in 1 2 3 4 5; do
  if grep -E -- '"GET /health\.json HTTP/[0-9.]+" 200([[:space:]]|$)' server.log > request-log-evidence.txt; then
    request_logged=1
    break
  fi
  sleep 0.1
done
if [ "$request_logged" -ne 1 ]; then
  printf 'successful request was not found in server.log\n' >&2
  cat -- server.log >&2 || true
  exit 65
fi
request_log_count=$(wc -l < request-log-evidence.txt | tr -d '[:space:]')

port_listener_observed='not-checked'
port_owner_verified='not-checked'
: > port-evidence.txt
if command -v -- ss >/dev/null 2>&1; then
  if ss -lntp "sport = :$lab_port" > port-evidence.txt 2> port-evidence.err; then
    if grep -F -- ":$lab_port" port-evidence.txt >/dev/null; then
      port_listener_observed='yes'
    else
      port_listener_observed='no'
    fi
    if grep -F -- "pid=$server_pid," port-evidence.txt >/dev/null; then
      port_owner_verified='yes'
    else
      port_owner_verified='unavailable'
    fi
  else
    port_listener_observed='ss-filter-failed'
    port_owner_verified='unavailable'
  fi
fi

stopped_pid=$server_pid
if kill -TERM "$stopped_pid"; then
  kill_rc=0
else
  kill_rc=$?
fi
if [ "$kill_rc" -ne 0 ]; then
  printf 'SIGTERM failed: rc=%s\n' "$kill_rc" >&2
  exit 70
fi
if wait "$stopped_pid"; then
  wait_rc=0
else
  wait_rc=$?
fi
server_pid=''

if kill -0 "$stopped_pid" 2>/dev/null; then
  pid_exists_after_wait='yes'
  printf 'server PID still exists after wait\n' >&2
  exit 70
else
  pid_exists_after_wait='no'
fi

if curl --disable --noproxy '*' \
    --silent --connect-timeout 1 --max-time 2 \
    --output /dev/null "http://127.0.0.1:$lab_port/health.json"; then
  post_stop_curl_rc=0
else
  post_stop_curl_rc=$?
fi
if [ "$post_stop_curl_rc" -ne 7 ]; then
  printf 'expected curl connection failure 7 after stop, got %s\n' "$post_stop_curl_rc" >&2
  exit 70
fi

{
  printf '\n## Loopback service facts\n\n'
  printf -- '- bind: `127.0.0.1:%s`\n' "$lab_port"
  printf -- '- server_pid: `%s`\n' "$stopped_pid"
  printf -- '- response_matches_fixture: `%s`\n' "$response_matches"
  printf -- '- successful_request_log_records: `%s`\n' "$request_log_count"
  printf -- '- port_listener_observed: `%s`\n' "$port_listener_observed"
  printf -- '- port_owner_verified_by_ss: `%s`\n' "$port_owner_verified"
  printf -- '- sigterm_rc: `%s`\n' "$kill_rc"
  printf -- '- wait_rc: `%s`\n' "$wait_rc"
  printf -- '- pid_exists_after_wait: `%s`\n' "$pid_exists_after_wait"
  printf -- '- post_stop_curl_rc: `%s`\n' "$post_stop_curl_rc"
  printf -- '- interpretation: PID disappearance and curl rc 7 are bounded observations, not production health proof.\n'
} >> report.md

trap - EXIT INT TERM
printf 'lab=%s\nreport=%s/report.md\n' "$lab_real" "$lab_real"
