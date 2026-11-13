#!/usr/bin/env bash
# Smoke test + load generator for Grafana.
# Usage: ./scripts/smoke_test.sh [BASE_URL] [REQUESTS]
#   ./scripts/smoke_test.sh http://localhost:8000
#   ./scripts/smoke_test.sh http://<elb-hostname> 200
set -euo pipefail
BASE="${1:-http://localhost:8000}"
BASE="${BASE%/}"
N="${2:-200}"
fail=0

check() {  # check <path> <expected status> [text that must appear]
  local path="$1" want="$2" text="${3:-}" body code
  body=$(curl -s -m 10 -w '\n%{http_code}' "$BASE$path") || true
  code="${body##*$'\n'}"; body="${body%$'\n'*}"
  if [[ "$code" == "$want" && ( -z "$text" || "$body" == *"$text"* ) ]]; then
    echo "  PASS  $path -> $code"
  else
    echo "  FAIL  $path -> $code (expected $want ${text:+containing '$text'})"; fail=1
  fi
}

echo "Smoke testing $BASE"
check /health/live 200 '"alive"'
check /health/ready 200 '"ready"'
check /metrics 200 'http_requests_total'
check /auth/login 200 'Log in'

echo "Generating $N requests for Grafana..."
paths=(/health/live /health/ready /auth/login /auth/register / /does-not-exist)
for ((i = 0; i < N; i++)); do
  curl -s -o /dev/null -m 10 "$BASE${paths[i % ${#paths[@]}]}" || true
done
echo "Done. Total requests now reported by /metrics:"
curl -s "$BASE/metrics" | awk '/^http_requests_total/ {s += $NF} END {print "  http_requests_total = " s}'
exit $fail
