#!/usr/bin/env sh
set -eu

: "${VERIFACT_BASE_URL:?Set VERIFACT_BASE_URL to the HTTPS deployment URL, e.g. https://verifact.example}"
BASE_URL="${VERIFACT_BASE_URL%/}"
TEST_EMAIL="smoke-$(date +%s)@example.invalid"
TEST_PASSWORD="StrongPass2026"
COOKIE_JAR="$(mktemp)"
cleanup() { rm -f "$COOKIE_JAR"; }
trap cleanup EXIT

expect_status() {
  expected="$1"; shift
  actual="$(curl -sS -o /tmp/verifact-response -w '%{http_code}' "$@")"
  if [ "$actual" != "$expected" ]; then
    echo "Expected HTTP $expected, received $actual for: $*" >&2
    cat /tmp/verifact-response >&2 || true
    exit 1
  fi
}

echo 'Checking HTTPS frontend...'
expect_status 200 "$BASE_URL/"
echo 'Checking API health...'
expect_status 200 "$BASE_URL/health"
echo 'Checking API readiness...'
expect_status 200 "$BASE_URL/ready"
echo 'Checking registration...'
expect_status 201 -X POST "$BASE_URL/api/v1/auth/register" -H 'Content-Type: application/json' -c "$COOKIE_JAR" --data "{\"full_name\":\"Production Smoke\",\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\",\"confirm_password\":\"$TEST_PASSWORD\"}"
echo 'Checking authenticated session...'
expect_status 200 "$BASE_URL/api/v1/auth/me" -b "$COOKIE_JAR"
echo 'Checking logout...'
expect_status 200 -X POST "$BASE_URL/api/v1/auth/logout" -b "$COOKIE_JAR"
echo 'VeriFact production smoke test passed.'
