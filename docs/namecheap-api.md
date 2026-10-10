# Namecheap API access and changing client IPs

Use the exact Vaultwarden item **`namecheap_api`**. Its login username is the API
user, its password is the API key, and its notes contain the configured client
IPv4. The previous item name `namecheap` is obsolete. Never print the item,
credential-bearing request URL, API key, or Vaultwarden session into chat/logs.

## Diagnose before rotating a key

Namecheap can return **“API Key is invalid or API access has not been enabled”**
when the request's client-IP configuration or whitelist is wrong. That message
alone does not prove the stored key is invalid.

1. Determine the current public **IPv4 from the machine that will call the API**,
   for example `curl -4 --fail --silent --show-error https://api.ipify.org`.
   If calling from the VPS, run the check there. Do not substitute the DNS A-record
   destination (`194.238.24.254`) for the caller's address.
2. Compare it with the `namecheap_api` notes and the request's `ClientIp` value.
   Changing networks, reconnecting a VPN, or an ISP reassignment can change a
   laptop's public IP. Discover it again; do not reuse a previously recorded IP.
3. Have the owner add the current IPv4 under Namecheap **Profile → Tools →
   Business & Dev Tools → API Access → Whitelisted IPs**, or use an already
   authorized authenticated session. Preserve existing valid entries; do not
   broaden access or remove the VPS's entry to solve a laptop mismatch.
4. Update only the client-IP notes in `namecheap_api`, preserving the API username
   and key, and pass that address as `ClientIp`. Updating Vaultwarden does not
   itself update Namecheap's whitelist. Likewise, whitelisting alone does not
   correct a stale `ClientIp` in the request. Refresh the CLI vault cache after
   the owner edits an item, and update scripts still looking for `namecheap`.
5. Retry a **read-only** `namecheap.domains.dns.getHosts` request. If it still fails,
   check that production API access is enabled and the credentials belong to the
   production account; only then investigate an invalid key. Do not rotate a
   shared key blindly.

Namecheap's [`ClientIp` definition](https://www.namecheap.com/support/api/global-parameters/)
requires the caller's IPv4. Its [API introduction](https://www.namecheap.com/support/api/intro/)
requires at least one whitelisted IPv4 before API access works.

## Preserve DNS and verify publication

`setHosts` replaces the domain's entire record set. Read it first, change only
the authorized records, preserve unrelated records and MX priorities, then read
it back to verify. Use the operational DNS helper in
`~/code/vps_deploy/skills/ship-a-new-app/lib/namecheap_dns.py` with credentials
loaded securely from `namecheap_api`; never put credential values in shell
arguments or logs.

A successful API response is not proof that DNS has published. Check the domain's
authoritative nameservers and a public recursive resolver. Allow for publication
delay and cached NXDOMAIN answers; do not repeatedly rewrite correct records.
Wait for the intended A record to resolve before enabling a new Traefik/TLS route.
Also check resolution from the VPS and the deployed container: their resolver
may still cache an earlier NXDOMAIN even after public resolvers show the record.
Flushing the local cache cannot clear an upstream resolver's negative cache.
Compare the VPS's already-configured primary and secondary resolvers before
changing DNS records or credentials again. If a configured secondary is current,
an authorized VPS operator can select it without adding a new resolver, changing
the persistent network configuration, or restarting shared services. Verify host
and container resolution, then rerun the failed release check.

## Verified incident — 2026-09-19

During mobile-licensing dev provisioning, API requests ran on the owner's Mac
while the saved client IP was the VPS address. Namecheap rejected the request
with the generic key/access error above. The owner whitelisted the Mac's current
public IPv4; the `namecheap_api` notes and request `ClientIp` were aligned with it.
The existing API key then worked, and the two authorized licensing A records
were added with all unrelated records preserved. No key rotation was needed.
Authoritative DNS publication followed the successful API read-back after a delay.
