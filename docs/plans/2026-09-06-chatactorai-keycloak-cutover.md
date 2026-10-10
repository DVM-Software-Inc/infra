# ChatActorAI dev Keycloak cutover

Checkpoint: 2026-09-06. Owner authorized portfolio authentication migration.
EnoughLedger normal Google login is owner-verified; continue ChatActorAI next.

## Established contract

| Boundary | Value / evidence |
|---|---|
| Current app | `https://dev.chatactorai.com` |
| Current issuer | `https://auth.chatactorai.com/realms/chatactorai-dev` (live container configuration verified after release) |
| Previous issuer | `https://auth.chatactorai.com/application/o/chatactorai-dev/` (rollback/provenance only) |
| Existing app callback | `https://dev.chatactorai.com/auth/callback` (live configuration and Next route) |
| App logout destination | `https://dev.chatactorai.com/` |
| New realm | `chatactorai-dev` — provisioned and converged on 2026-09-06 |
| Intended Keycloak issuer | `https://auth.chatactorai.com/realms/chatactorai-dev` |
| Intended Google broker callback | `https://auth.chatactorai.com/realms/chatactorai-dev/broker/google/endpoint` |
| Google dev project | `dvm-chatactorai-dev`, **ChatActorAI Development**, created under `mcoelhojob@gmail.com` |
| Google dev configuration | **ChatActorAI (dev)** saved; External and Testing confirmed; master support/developer contact |
| Google production reservation | `dvm-chatactorai-prod`; do not use for dev clients |
| Domain ownership | `chatactorai.com` already verified in Search Console under master account |

## Latest implementation checkpoint

**Dev cutover deployed successfully.** Commit `399410a`, GitHub release
`34067811054`, passed all CI/build/deploy jobs. Live API/web are healthy on
`dev-399410a`; workers are running. Read-only post-deploy checks confirm **8 users,
4 organizations, zero legacy bindings**, issuer-scoped schema and exact Keycloak
issuer/API audience. The real app login returns 307 to its own realm with S256,
state and nonce. All discovery/JWKS/TLS/public isolation probes pass. A protected
mode-600 root-owned database dump was verified at
`backups/pre-deploy-20260906-195350.dump` under the dev app directory.
Commit `c9426a2` corrects the remaining login-page wording; its follow-up release
`34068968794` also succeeded. API/web are healthy on `dev-c9426a2`, workers run,
and the live sign-in page explicitly names Keycloak and Google. Final read-only
counts remain 8 users/4 organizations, one Keycloak binding, zero legacy bindings.
No shared Authentik service was removed or restarted.

**Real browser acceptance:** starting from the deployed app's `/auth/login`,
Keycloak displayed email/password and Google. Selecting the approved master
Google account returned to the existing ChatActorAI dashboard with its workspace
and assistant intact. Read-only counts remained **8 users/4 organizations**, with
**one Keycloak binding** and **zero legacy bindings**. Sign-out returned to the
public home; opening `/dashboard` required login, and the next `/auth/login`
displayed Keycloak again (the IdP session was ended). No Authentik authentication
was used. A second Google login returned to the same existing dashboard.
`pg_restore --list` successfully read the protected pre-cutover archive; no restore
was performed. Broader live negative/refresh acceptance remains open.

Full local API suite: **1,259 passed, 7 skipped**; the two additional
guarded-reset cases pass, as do all **50 web tests**, TypeScript and lint.
The app session/logout-hint cookie namespace changes to discard old Authentik
sessions. Vaultwarden-backed inputs were transferred directly from protected
runtime storage into the repository's `DEV_ENV_FILE`; no credential values
were printed or written locally. Protected old/prepared env copies remain at
`/opt/apps/chatactorai/dev/.env.pre-keycloak-20260906` and
`.env.keycloak-prepared-20260906`. The release stops only the old dev app,
takes a mode-600 database dump, applies the additive migration, then runs the
exact-count/idempotent reset before starting the new containers. The normal
Google-to-dashboard and logout journeys are verified above; this is dev-only
evidence, not full portfolio or production acceptance.

The owner
confirmed the secret transfer, and the reviewed plan created exactly eight
ChatActorAI dev resources. Existing realms had no live changes. The only allowed
refresh drift was EnoughLedger Google `extra_config`, with a no-op plan action.
Every realm/client/provider/audience check passed, then a full plan confirmed
no-change convergence. The mode-600 temporary secret-bearing plan was removed.

Public routing is live through
`infra/deploy/traefik/dynamic/chatactorai-keycloak-dev.yml`, deployed to
`/opt/traefik/dynamic/chatactorai-keycloak-dev.yml`. The existing watched file
provider reloaded it without restarting Traefik or Keycloak. It routes only
the exact dev realm, its slash-prefixed subpaths, and `/resources/` to
`keycloak@docker`. Do not add a duplicate whole-host router in Compose.
Discovery/TLS/JWKS and endpoint-host checks pass; master/admin and cc-dvm,
smb-tax, gelopreto and dvm-architect realm probes all return **404** on this
product host. The legacy Authentik discovery still returns **200**.

**Approved scope:** read-only live inventory found **8 users, 4 organizations,
5 old Authentik bindings**. The owner explicitly approved Keycloak/Google-only
authentication and clearing only those five dev bindings, preserving users,
roles, organizations, billing and app data. Do not delete/reseed business data
or perform an Authentik import. The reset refuses changed counts and preserves
new Keycloak bindings on rerun.

Earlier browser preview reached the new realm's **Email verification** page for the
master Google address. It used a preview-only state/nonce, not the app-owned
session; do not count this as completed Google-to-app login or use its callback
as acceptance. The owner was told to hold the preview verification link until
the app cutover. Repeat from the app's real `/auth/login` afterward.

- Google web client **ChatActorAI Keycloak dev** created in `dvm-chatactorai-dev`
  with exactly the broker callback above and no JavaScript origins. The saved
  authorized domain `chatactorai.com` was verified after reload; the master test
  user was previously confirmed in the saved Testing audience.
- Vaultwarden **`google/chatactorai/oauth-dev`** now stores its ID/secret.
  **`chatactorai-keycloak-web-client-dev`** stores the separate confidential web
  client ID `chatactorai-dev` and a fresh Vaultwarden-generated secret (48+
  characters). Both records were reopened and verified by private equality
  checks; no credential values were printed. Preserve `google/chatactorai`.
- Local Keycloak `terraform/chatactorai.tf` declares the dev realm and correct
  app paths. Optional module `web_api_audience` adds `chatactorai-dev-api` to
  web access tokens only, never ID tokens. Existing products default to no new
  mapper; no M2M client is enabled. Terraform 1.9 formatting checks passed for
  all three changed source files. Source transferred; validation and bounded
  apply succeeded as recorded above.
- Local app source now creates/persists/sends/checks nonce, clears the pending
  transaction on every callback path, rejects incomplete token responses, and
  defaults to `openid email profile`. API verification requires exact issuer,
  required iss/aud/sub/exp/iat claims and a distinct `OIDC_AUDIENCE`; discovery
  issuer is checked and the JWKS cache is issuer-scoped. ID tokens for the web
  client fail the API audience check. Issuer/subject binding, boolean-verified
  email first binding, row-locked binding updates and app-side waitlist
  enforcement are in release commit `399410a`.
- Migration `a63f290bc812` adds issuer provenance and composite uniqueness,
  requiring explicit `OIDC_LEGACY_ISSUER_URL` when bound subjects exist. For dev,
  use the previous Authentik issuer above, not the new realm issuer. It preserves existing
  subjects/user IDs and never clears bindings automatically. A populated test
  proves refusal without provenance and preservation of user/org/role data.
- Checks: **51 focused backend tests** (40 JWT/identity/provisioning, 8 admission,
  3 migration tests) and the **full 50-test web suite**, focused Python lint,
  TypeScript no-emit and whitespace checks pass. Route tests mock
  the OIDC client; they are not live cryptographic nonce/replay acceptance.
  Initial JWT-only tests used `--confcutdir`; later runs included DB fixtures.
  DB tests used local PostgreSQL `chatactorai_test`, never live dev data.
  The later full backend run and normal browser login/logout passed (above). Existing
  `docs/security.md` changes were preserved.
- Test diagnostic safety: one failed subprocess traceback exposed an inherited
  `CLIPROXY_AUTH_TOKEN` in tool output. No value is recorded here; owner notified
  to treat it as exposed. Both migration test helpers now capture diagnostics
  and raise fixed errors rather than `CalledProcessError`; reruns used
  `--tb=no --show-capture=no`. The final 48 authentication/admission tests and
  3 migration tests pass. Do not print or reuse the exposed token.
- **Additional cutover gate:** Authentik currently enforces the pre-login
  admission gate. The app's unknown-user branch in `auth/identity.py` calls
  provisioning directly when self-serve is enabled, while `_waitlist_admits`
  was only used by the pre-login gate. This existing waitlist/approval policy
  is now enforced and tested locally inside verified-identity resolution.

Completed operator transfer command (reference; do not generate new credentials):

```sh
node /Users/marcusc/code/infra/scripts/inject-chatactorai-keycloak.mjs --transfer
```

The script validates exact vault item names/project/issuer, transfers only three
ChatActorAI dev variables into `/opt/keycloak/.tf.env` (regular, operator-owned,
mode 600), refuses a different existing value, and verifies the runtime values
without printing them. It does **not** apply Terraform, modify the app's env or
restart anything. Owner confirmation received; Terraform comparisons independently
verified all three runtime values before apply.

Do not deploy the current app edits alone: `OIDC_AUDIENCE` must be configured
with its access-token mapper in the same reviewed cutover. The mapper/realm/route
are live; the approved coordinated app/database release succeeded.

## App-side review findings before changing the issuer

The items below describe the original findings; local implementation is recorded
above. Deployment, reviewed binding reset and live acceptance remain required.

Source inspected in `/Users/marcusc/code/chatactorai`:

- `apps/web/app/auth/login/route.ts`: state and S256 PKCE exist, but no nonce is
  generated, persisted or sent. Add nonce and verify it in the callback.
- `apps/web/lib/session.ts` / `app/auth/callback/route.ts`: extend the transient
  session contract and clear all transient values after success/failure; test
  wrong state/nonce and replay before changing live authentication.
- `apps/web/lib/oidc.ts`: default scopes still include `groups` and
  `offline_access`. Use `openid email profile` for the new realm unless a
  separately justified offline-access requirement is established. A custom role
  claim is not an OAuth scope.
- API `auth/oidc.py`: audience is the configured client ID; declare an explicit
  Keycloak access-token audience mapper for this API. Tighten issuer comparison
  and access-token requirements; current code tolerates trailing slash variation
  and does not itself distinguish an ID token from an access token.
- API `models/user.py` and `auth/identity.py`: identity is currently stored and
  looked up by `oidc_subject` alone. Implement the `(issuer, subject)` boundary
  and verified-email first-binding policy with tests. Existing bound subjects
  reject new identities with the same email, so changing only environment
  variables can lock out returning dev users.
- Use fresh Keycloak identities, not an Authentik import. Resolve/reset only
  in-scope dev identity bindings with a reviewed migration/fixture strategy;
  do not delete organizations, billing data or unrelated user work implicitly.
- Existing `docs/security.md` edits are user-owned; preserve them.

## Deployment order and acceptance

1. Finish dev OAuth domain/test-user configuration and create the web OAuth client
   for the intended broker endpoint; store/verify it in Vaultwarden.
2. Declare realm/client/audience/provider in Keycloak source, preserving other
   realms. Generate a fresh confidential app-client secret in Vaultwarden.
3. Add **path-scoped** Keycloak routing on `auth.chatactorai.com`; the existing
   hostname already serves Authentik. Do not replace the whole-host route before
   the app cutover. Prove discovery, TLS and deny-master/admin/cross-realm behavior.
4. Implement and test the app contract changes in its repository, then perform the
   reviewed dev cutover with Vaultwarden-backed runtime/CI inputs. Preserve a
   documented rollback boundary, and do not deploy prod.
5. Prove Google/email onboarding, exact issuer/audience, roles/tenancy, wrong
   state/nonce/token type, verified-email collision/linking, refresh and logout.
6. Only then mark accepted and remove this app's obsolete Authentik dependency.
   Do not decommission the shared Authentik service while other apps use it.
