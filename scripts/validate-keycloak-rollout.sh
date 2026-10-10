#!/usr/bin/env bash

set -u
set -o pipefail

usage() {
  cat <<'EOF'
Validate the public, deterministic part of one Keycloak app rollout.

Usage:
  validate-keycloak-rollout.sh --issuer URL [--login-url URL]
                                [--deny-realm REALM]...

Example:
  validate-keycloak-rollout.sh \
    --issuer https://auth.example.com/realms/example-dev \
    --login-url https://dev.example.com/api/v1/auth/login \
    --deny-realm another-product-dev

The check fails if the product auth host exposes the master realm or admin console.
It does not exercise an interactive callback, role, tenant, refresh, logout, email,
social-login, or service-account flow.
EOF
}

issuer=""
login_url=""
denied_realms=()

while (($# > 0)); do
  case "$1" in
    --issuer)
      (($# >= 2)) || { echo "ERROR: --issuer needs a value" >&2; exit 2; }
      issuer=${2%/}
      shift 2
      ;;
    --login-url)
      (($# >= 2)) || { echo "ERROR: --login-url needs a value" >&2; exit 2; }
      login_url=$2
      shift 2
      ;;
    --deny-realm)
      (($# >= 2)) || { echo "ERROR: --deny-realm needs a value" >&2; exit 2; }
      denied_realms+=("$2")
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$issuer" ]]; then
  echo "ERROR: --issuer is required" >&2
  usage >&2
  exit 2
fi

for command_name in curl jq; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "ERROR: required command not found: $command_name" >&2
    exit 2
  fi
done

if [[ ! "$issuer" =~ ^https://([^/]+)/realms/([^/]+)$ ]]; then
  echo "ERROR: issuer must be https://<product-auth-host>/realms/<product-env>" >&2
  exit 2
fi

auth_host=${BASH_REMATCH[1]}
realm=${BASH_REMATCH[2]}
origin="https://${auth_host}"
discovery_url="${issuer}/.well-known/openid-configuration"
failures=0

pass() {
  printf 'PASS  %s\n' "$1"
}

fail() {
  printf 'FAIL  %s\n' "$1" >&2
  failures=$((failures + 1))
}

http_status() {
  curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
    --connect-timeout 10 --max-time 20 "$1"
}

headers_file=$(mktemp)
body_file=$(mktemp)
cleanup() {
  rm -f "$headers_file" "$body_file"
}
trap cleanup EXIT

discovery_status=$(curl --silent --show-error --dump-header "$headers_file" \
  --output "$body_file" --write-out '%{http_code}' --connect-timeout 10 \
  --max-time 20 "$discovery_url") || discovery_status="000"

if [[ "$discovery_status" == "200" ]]; then
  pass "realm discovery returns 200"
else
  fail "realm discovery returns ${discovery_status}, expected 200: ${discovery_url}"
fi

if jq -e . "$body_file" >/dev/null 2>&1; then
  discovered_issuer=$(jq -r '.issuer // empty' "$body_file")
  if [[ "$discovered_issuer" == "$issuer" ]]; then
    pass "discovery issuer exactly matches ${issuer}"
  else
    fail "discovery issuer is '${discovered_issuer}', expected '${issuer}'"
  fi

  endpoint_keys=(authorization_endpoint token_endpoint jwks_uri end_session_endpoint)
  for endpoint_key in "${endpoint_keys[@]}"; do
    endpoint=$(jq -r --arg key "$endpoint_key" '.[$key] // empty' "$body_file")
    if [[ -z "$endpoint" && "$endpoint_key" == "end_session_endpoint" ]]; then
      continue
    fi
    if [[ "$endpoint" == "${issuer}/"* ]]; then
      pass "${endpoint_key} stays on the product realm"
    else
      fail "${endpoint_key} escapes the product realm: '${endpoint}'"
    fi
  done

  jwks_url=$(jq -r '.jwks_uri // empty' "$body_file")
  if [[ -n "$jwks_url" ]]; then
    jwks_status=$(curl --silent --show-error --output "$body_file" \
      --write-out '%{http_code}' --connect-timeout 10 --max-time 20 "$jwks_url") \
      || jwks_status="000"
    if [[ "$jwks_status" == "200" ]] && jq -e '.keys | length > 0' "$body_file" >/dev/null 2>&1; then
      pass "JWKS returns at least one signing key"
    else
      fail "JWKS is unavailable or contains no keys (HTTP ${jwks_status})"
    fi
  fi
else
  fail "discovery response is not valid JSON"
fi

master_status=$(http_status "${origin}/realms/master/.well-known/openid-configuration") \
  || master_status="000"
case "$master_status" in
  401|403|404)
    pass "product host denies master-realm discovery (HTTP ${master_status})"
    ;;
  *)
    fail "product host exposes master-realm discovery (HTTP ${master_status})"
    ;;
esac

for denied_realm in "${denied_realms[@]}"; do
  if [[ ! "$denied_realm" =~ ^[A-Za-z0-9._-]+$ ]]; then
    fail "invalid denied realm name: '${denied_realm}'"
    continue
  fi
  denied_status=$(http_status "${origin}/realms/${denied_realm}/.well-known/openid-configuration") \
    || denied_status="000"
  case "$denied_status" in
    401|403|404)
      pass "product host denies unrelated realm ${denied_realm} (HTTP ${denied_status})"
      ;;
    *)
      fail "product host exposes unrelated realm ${denied_realm} (HTTP ${denied_status})"
      ;;
  esac
done

admin_status=$(http_status "${origin}/admin/master/console/") || admin_status="000"
case "$admin_status" in
  401|403|404)
    pass "product host denies the master admin console (HTTP ${admin_status})"
    ;;
  *)
    fail "product host exposes or redirects the master admin console (HTTP ${admin_status})"
    ;;
esac

if [[ -n "$login_url" ]]; then
  login_status=$(curl --silent --show-error --dump-header "$headers_file" \
    --output /dev/null --write-out '%{http_code}' --connect-timeout 10 \
    --max-time 20 "$login_url") || login_status="000"
  location=$(awk 'BEGIN{IGNORECASE=1} /^location:/{sub(/^[^:]+:[[:space:]]*/, ""); sub(/\r$/, ""); print; exit}' "$headers_file")

  case "$login_status" in
    301|302|303|307|308)
      pass "app login returns a redirect (HTTP ${login_status})"
      ;;
    *)
      fail "app login returns HTTP ${login_status}, expected a redirect: ${login_url}"
      ;;
  esac

  expected_authorize_prefix="${issuer}/protocol/openid-connect/auth?"
  if [[ "$location" == "$expected_authorize_prefix"* ]]; then
    pass "app login redirects to the exact product realm"
  else
    fail "app login redirect is not the exact product realm: '${location}'"
  fi

  if [[ "$location" == *"code_challenge_method=S256"* && "$location" == *"code_challenge="* ]]; then
    pass "app login requests S256 PKCE"
  else
    fail "app login redirect does not request S256 PKCE"
  fi

  if [[ "$location" == *"state="* ]]; then
    pass "app login includes OAuth state"
  else
    fail "app login redirect does not include OAuth state"
  fi

  if [[ "$location" == *"nonce="* ]]; then
    pass "app login includes an OIDC nonce"
  else
    fail "app login redirect does not include an OIDC nonce"
  fi

  if [[ "$location" == *"client_id="* && "$location" == *"redirect_uri="* ]]; then
    pass "app login includes client_id and redirect_uri"
  else
    fail "app login redirect lacks client_id or redirect_uri"
  fi
fi

printf '\nRealm: %s\nHost:  %s\n' "$realm" "$auth_host"
if ((failures > 0)); then
  printf 'Result: FAIL (%d check%s)\n' "$failures" "$([[ $failures -eq 1 ]] && echo '' || echo 's')" >&2
  exit 1
fi

echo 'Result: PASS'
