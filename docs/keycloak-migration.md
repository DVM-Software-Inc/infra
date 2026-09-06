# Keycloak migration control plane

Last reconciled: **2026-09-06 (America/Toronto)**

This is the portfolio-level migration ledger. Application code changes belong in the
application's own repository/session; realm Terraform and proxy changes belong in
`~/code/keycloak`; shared rules, status, and acceptance evidence belong here.

The target is one Keycloak realm per product per environment. A realm is never a
customer/tenant. Customer organizations, memberships, product permissions, billing,
entitlements, support operations, and AI usage limits remain in the application.

## Status language

| Status | Meaning |
|---|---|
| Queued | Scope is known; implementation has not started. |
| In progress | An app or Keycloak session owns active work. Do not duplicate it here. |
| Implemented | Required source/config changes exist. This is not live acceptance. |
| Verifying | Realm and app entry point are live; the complete acceptance record is still open. |
| Accepted (dev) | All applicable dev gates below have evidence. Authentik can be removed from that dev app. |
| Accepted (prod) | Production gates and a post-deploy smoke test have evidence. |
| Not applicable | The app has no human or machine identity requirement. Reassess if that changes. |
| Retire | The old integration belongs to a decommissioned service and should be deleted. |

Realm creation, a healthy Keycloak container, or a successful redirect is not by itself
an accepted migration.

## Owner decision: Authentik data is disposable

This is a development migration. Do **not** build an Authentik user, credential, session,
consent, client-secret, or policy import. Create fresh Keycloak accounts, rotate client
secrets, and reset/reseed local dev identity bindings and sandbox customer/billing
fixtures where required.

Only the following intent crosses the boundary:

- exact redirect and logout URIs;
- requested scopes and required claims;
- product-role intent;
- the required client types: web BFF, native public client, API audience, or service
  account.

## Per-product mailbox and Google ownership

Owner decision (2026-09-05): products that launch customer email and Google sign-in
use one real receiving mailbox on the product domain plus aliases, rather than one
paid mailbox for every operational address.

- Keep AWS SES as the application/Keycloak outbound sender. A Namecheap mailbox is
  for inbound verification, recovery, security, and customer replies; it does not
  replace SES SMTP.
- Start with Namecheap Private Email Launch: one mailbox and up to ten aliases. Do
  not enable catch-all because it expands spam and typo-delivery exposure.
- Default mailbox: `support@<product-domain>`. Default aliases:
  `auth@<product-domain>` and `recovery@<product-domain>`. Record any
  product-specific exception in this ledger.
- Per the owner's 2026-09-06 decision, use one existing master Google account
  with separate Cloud projects and OAuth branding for each product. Do not
  create per-product consumer Google accounts or provision Cloud Identity as
  part of this rollout. Use the master account for OAuth support and developer
  contact; the support email can be visible in consent-screen app details.
- Protect the master Google account with MFA and keep credentials/recovery
  material in Vaultwarden. Product mailboxes remain at Namecheap. Google account
  verification gates must not be bypassed.
- Store the mailbox credential separately from the Google credential. Enable the
  mailbox provider's own MFA, and do not store TOTP seeds in application source,
  Terraform state, chat, or shell history.
- Buy/provision this subscription only when the product needs inbound customer mail
  or its Google OAuth configuration is entering acceptance. Development-only,
  account-free, M2M-only, and shared platform services do not get mailboxes by
  default.

Account creation, OAuth credential creation, and paid email checkout are explicit
operator checkpoints. DNS, alias creation, realm/provider configuration, secret
placement, and verification probes should otherwise be automated through supported
APIs or the authenticated administrative UI.

Mailbox acceptance observed 2026-09-05:

| Domain | MX/SPF/DKIM/DMARC | Delivery evidence |
|---|---|---|
| `enoughdating.com` | Namecheap Private Email records present; one combined SPF policy for SES and Private Email | Owner confirmed delivery to `support@` and through the `auth@` and `recovery@` aliases after nine-message SES test batch. |
| `enoughledger.com` | Namecheap Private Email records present; authoritative DNS has one combined SPF policy for SES and Private Email | Owner confirmed delivery to `support@` and through the `auth@` and `recovery@` aliases after nine-message SES test batch. |
| `chatactorai.com` | Namecheap Private Email records present; one combined SPF policy for SES and Private Email | Owner confirmed delivery to `support@` and through the `auth@` and `recovery@` aliases after nine-message SES test batch. |

Mailbox credentials are stored in Vaultwarden. Their values must not be copied into
this repository, Terraform state, command output, or chat.

The restart-ready Google-account, OAuth-client, MFA, and Keycloak continuation is
saved in
[`plans/2026-09-05-google-account-keycloak-rollout.md`](plans/2026-09-05-google-account-keycloak-rollout.md).
Comcentre is already provisioned per the owner. Remaining OAuth setup is for
ChatActorAI, EnoughLedger, and EnoughDating under `mcoelhojob@gmail.com`.
Projects `dvm-chatactorai-prod`, `dvm-enoughledger-prod`, and
`dvm-enoughdating-prod` were created on 2026-09-06. After the owner approved
Google's API Services User Data Policy, all three OAuth configurations were saved
with External audience and the master email for support/developer contact.
Domain verification, branding completion, OAuth clients, and publication remain
in progress; the configurations initially use Testing status.

Google requires separate projects for testing and production. Reserve the existing
`*-prod` projects for production and create matching `*-dev` projects before saving
dev clients; separate client secrets inside one project are not sufficient. The
EnoughLedger dev-client form was prepared but **Create was not clicked** because
Computer Use's screenshot and accessibility state disagreed and URI replacement
was unreliable. No new OAuth credential exists from that attempt.

Update after the separate Chrome window restored usable control: created
`dvm-enoughledger-dev`, saved **EnoughLedger (dev)** External OAuth configuration,
and created web client **EnoughLedger Keycloak dev** with exactly
`https://auth.enoughledger.com/realms/smb-tax-dev/broker/google/endpoint` and no
JavaScript origins. Client ID/secret were saved and round-trip verified in
Vaultwarden `google/smb-tax/oauth-dev`. Confirmed **Testing** and the master
account as a saved test user. A fresh page reload confirmed authorized root domain
`enoughledger.com`, app name and support email persisted. The owner subsequently
completed the secure runtime transfer and Terraform activation passed, as recorded
below. The interactive app-session and linking gates remain open.

EnoughLedger's optional Google inputs and broker callback output are now prepared
in the local Keycloak Terraform source, via
`docs/patches/keycloak-enoughledger-google.patch`. Formatting/HCL parsing passed
with Terraform 1.9. Defaults keep the provider off unless credentials are supplied;
EnoughLedger now has supplied credentials and the provider is applied. Full
validate/convergence passed; browser acceptance remains open.

## Continuation scope and live contract check: 2026-09-06

### EnoughLedger Google activation evidence

Owner completed the Vaultwarden-to-runtime transfer. Applied the reviewed
EnoughLedger source patch on the VPS, then validated and applied a saved Terraform
plan whose only live resource change was the Google provider creation. Verified
the exact realm/callback, credential equality without value output, minimal scopes,
IMPORT sync, `trust_email=false` and `store_token=false`. A follow-up full plan
confirmed **no changes**. Existing DVM Architect metadata drift was refresh-only,
with no planned/live mutation to those resources. The temporary protected plan
was removed after convergence; Vaultwarden remains the credential source of truth.

The public app login displayed the Google provider and reached Google's chooser,
then returned to the correct EnoughLedger Keycloak realm for email verification.
The owner subsequently confirmed **“google authentication works fine”** on
2026-09-06. Record the normal Google-to-app login as **owner-verified working**;
do not ask them to repeat email verification. This does not establish collision/
linking, role/tenant negative tests, refresh/logout or full migration acceptance.

The deterministic verifier passed discovery/JWKS/exact issuer and app redirect
with state, nonce and S256 PKCE. Four host-isolation checks still fail with HTTP
200: master discovery, master admin UI, cc-dvm-dev and gelopreto-dev discovery.
Normal interactive Google login is owner-verified; tenant/role, refresh/logout and
negative/linking gates remain open. No app deployment or Authentik retirement was
performed in this continuation.

The owner asked to finish Google social login, configure the remaining apps'
Keycloak authentication, and update the standards/HTML pages. Comcentre remains
excluded from reprovisioning. Preserve unrelated working-tree changes, especially
the ongoing KnowingBest application changes. Do not mark source preparation as
deployment or remove Authentik before per-app acceptance.

Read-only `docker inspect` on the VPS returned the following allowlisted,
non-secret runtime settings. No passwords/tokens were inspected or emitted:

| App | Deployed issuer / client | Deployed callback | Next boundary |
|---|---|---|---|
| EnoughLedger | `https://auth.enoughledger.com/realms/smb-tax-dev` / `smb-tax-dev` | `https://dev.enoughledger.com/api/v1/auth/callback` | Google client/provider applied; normal login owner-verified. Host isolation and remaining authorization/linking/refresh/logout acceptance are open. |
| ChatActorAI | `https://auth.chatactorai.com/application/o/chatactorai-dev/` / `chatactorai-dev` | `https://dev.chatactorai.com/auth/callback` | This auth hostname already serves Authentik. Add path-scoped Keycloak routing without displacing the old route before cutover; review app token/audience/identity bindings. |
| EnoughDating / KnowingBest | issuer and client ID both empty | `https://dev.enoughdating.com/` | Existing OIDC configuration is incomplete. Confirm the admin callback and separate native-user auth contract; do not claim Google is wired by creating only an admin client. |
| BuildFoundry | `https://auth.dvmsoftware.com/application/o/buildfoundry-dev/` / `buildfoundry-dev` | `https://dev.foundry.contextor.ca/auth/callback` | API audience is `buildfoundry-dev`; preserve that verified contract when provisioning. |
| ContextorAI | `https://auth.dvmsoftware.com/application/o/contextorai-dev/` / `contextorai-dev` | `https://dev.contextor.ca/auth/callback` | Resolve product auth host and app authorization before cutover. |
| DVM Fullstack | `https://auth.dvmsoftware.com/application/o/dvm-fullstack-dev/` / `dvm-fullstack-dev` | Not returned in inspected frontend settings | Resolve actual callback/client types; do not substitute a module default. |

Additional public HTTPS probes from the VPS, with certificate verification enabled:

- EnoughLedger product discovery: **200**. Master discovery and admin console:
  **200**, so the shared host-isolation gate remains open.
- ChatActorAI proposed Keycloak realm discovery: **404**; the current app still
  uses its `/application/o/` Authentik issuer.
- `auth.enoughdating.com`: **DNS resolution failure**; no live realm claim.
- `auth.architect.dvmsoftware.com`: **self-signed certificate validation failure**.
  Local Terraform has a `dvm-architect-dev` module and the app container is running,
  but that does not establish a usable public identity endpoint. No TLS bypass.

## Current rollout ledger

Evidence marked **observed** below was probed through public HTTPS on 2026-09-05. User
reported implementation status is kept separate from observed runtime evidence.

| Product | Scope | Status | Evidence / next action |
|---|---|---|---|
| `cc_dvm` | dev web BFF | **Cut over** | Observed 2026-09-05 11:24–11:26Z (controller session): Google sign-in completed, `/api/v1/auth/callback` returned 303, and `users` gained a row with `oidc_subject` set and role `admin` — the role can only arrive via the realm-role→ID-token mapper, so grant, mapper and claim path are all proven. Deployed at `dev.comcentre.online`. Previously: User reports implementation complete. Observed: discovery 200 with exact issuer `https://auth.comcentre.online/realms/cc-dvm-dev`; `/api/v1/auth/login` returns 302 to that realm with state, nonce, and S256 PKCE. Open: interactive callback/role/refresh/logout proof and the shared proxy gate below. |
| `gelopreto` | dev web BFF + M2M API | **Cut over** | Observed 2026-09-05: operator login through `auth.gelopreto.com` reached `/dashboard` (middleware gates on the `groups` claim = realm role `gelopreto-admin`); a client-credentials token for `gelopreto-dev-api` was minted and decoded with `aud: ["gelopreto-dev-api","account"]` and the exact issuer, so the M2M audience mapper is proven; `scan-now` is behind that bearer. Deployed at `dev.gelopreto.com`. Authentik applications `gelopreto-dev`/`gelopreto-dev-api` still exist as the rollback path and are not yet deleted. Previously: User reports implementation complete. Observed: discovery 200 with exact issuer `https://auth.gelopreto.com/realms/gelopreto-dev`; `/login` returns 307 to that realm with state and S256 PKCE. No OIDC nonce is sent or persisted/verified by the inspected implementation; close that app-session gate before acceptance. Also open: human callback/role/logout, service-account positive and wrong-audience negative proof, and the shared proxy gate. Email flows remain off until `gelopreto.com` is a verified sending identity. |
| `smb-tax` / EnoughLedger | dev self-serve SaaS | **Verifying — Google login works** | 2026-09-06: Google provider applied declaratively; full Terraform convergence passed. Owner confirmed Google authentication works. Tenant/role/refresh/logout/linking acceptance remains open; four host-isolation probes still fail. |
| `chatactorai` | dev SaaS web/API | **In progress — preparation** | `dvm-chatactorai-dev` and External/Testing OAuth configuration saved. No OAuth client/realm/app cutover yet. Source inspection found missing nonce, legacy scopes and subject-only binding; contract and ordered work are in `plans/2026-09-06-chatactorai-keycloak-cutover.md`. Existing Authentik path remains unchanged. |
| `contextorai` | dev, then prod | **Queued** | Authentik inventory has separate dev/prod clients. Establish the real app callback and authorization contract before creating realms. |
| `knowingbest` | dev, then prod | **Queued** | Authentik inventory has separate dev/prod clients. Include native/public-client review if the shipped Apple client authenticates humans. |
| `callbackready` | dev, then prod | **Queued** | Authentik inventory has separate dev/prod clients. Determine whether it needs BFF, API audience, and/or M2M clients. |
| `mdm-wiz` | dev, then prod | **Queued** | Authentik inventory has separate dev/prod clients. Determine web versus native identity paths explicitly. |
| `dvm-fullstack` | dev, then prod | **Queued** | Preserve product-role intent, but do not import Authentik bindings or users. |
| `buildfoundry` | dev | **Queued** | Preserve admin-role intent. Add prod only when a prod workload exists. |
| `dvm-architect` | dev web BFF | **Implemented / ingress blocked** | Local realm/client/router definitions exist and app container is running. 2026-09-06: public auth host fails certificate validation. Resolve TLS, then run the complete acceptance gates. |
| `filebrowser` | current environment | **Queued / assess replacement** | Before creating a realm, decide whether this still belongs on the customer-facing fleet or should be replaced/retired. A static reverse-proxy integration needs an OIDC-aware proxy; Keycloak is not an Authentik outpost drop-in. |
| Portainer Authentik object | none | **Retire** | Service was decommissioned. Delete the obsolete Authentik object during final cleanup; no Keycloak realm. |

## Fleet classification

“Move all apps” means every active workload is explicitly classified; it does not mean
creating unused realms. A read-only live-container recheck on 2026-09-05 confirmed the
products/platform services below are running in addition to the primary ledger. Repository
evidence gives this initial scope; each owning app session must confirm its deployed
environment before implementation.

| Product/service | Initial classification |
|---|---|
| `pro-cure-ai` | **Queued.** Active dev API. Generic RS256 issuer/audience verification exists and the environment still names an Authentik secret. Determine the human BFF/client path and create a product dev realm plus explicit API audience. |
| `estimator` | **Queued / auth gap review.** Active dev web/API. Authentik BFF variables exist only as commented scaffold in the inspected example. If customers use the running app, implement Keycloak rather than carrying an unauthenticated or half-configured state forward. Apply `saas.md` because its data model already has organizations/tenant isolation. |
| `mermaind` (`mermaid-thing` repo) | **Queued / legacy-auth replacement.** Active dev services. Repository docs still describe Basic Auth and HS256 pending an Authentik cutover. Skip Authentik and implement the Keycloak product realm/BFF contract directly. |
| `builtdvm` | **Queued / identity requirement assessment.** Active dev web/API, but no OIDC/Keycloak/Authentik contract was found in the initial repository scan. Decide whether the product is intentionally account-free; otherwise add Keycloak before customer use. |
| `chatwoot` | **Platform service; no customer product realm.** Active shared messaging backend. Product customers should enter through the DVM Messaging API with registered product issuer/audience mappings, not receive accounts in a cross-product Chatwoot directory. Operator SSO is a separate platform-access decision. |
| `audition-parse` | **Not applicable, subject to confirmation.** Active dev and prod API; previously reported not to use Authentik. Keep realm-free only while it has no human account identity requirement. |
| `talk2me` | **Not applicable, subject to confirmation.** Active local/native-oriented dev and prod service; no Authentik evidence found. Use a public Keycloak client only if human accounts become a product requirement. |
| Shared Messaging API | **Platform trust integration, not a product realm.** Register explicit allowed product issuers/audiences and verify tenant/subject/context authorization without creating a cross-product user directory. |

Suggested order after `smb-tax`: `chatactorai` (reference SaaS), `buildfoundry`,
`contextorai`, `dvm-fullstack`, `knowingbest`, `pro-cure-ai`, then the legacy/gap reviews
for `filebrowser`, `mermaind`, `estimator`, and `builtdvm`. Inactive/unobserved products
such as `callbackready` and `mdm-wiz` follow when they return to the deploy queue.

Add any newly deployed workload to this table before calling the fleet complete.

## Shared blocker across every product host

Observed on both currently live product hosts:

- `https://auth.comcentre.online/realms/master/.well-known/openid-configuration` → 200
- `https://auth.gelopreto.com/realms/master/.well-known/openid-configuration` → 200
- each product host serves the other product's live realm discovery document → 200.

Product auth hosts must deny `/admin`, `/realms/master`, and unrelated product realms.
They should allow only the host's product realm plus the Keycloak resource paths required
to render and operate its login/account flows. Fix this once in the shared Keycloak proxy
configuration and rerun positive and negative tests for every live host.

The intended Traefik HTTPS-router shape is:

```text
Host(`auth.<product-domain>`) &&
  (Path(`/realms/<product>-<env>`) ||
   PathPrefix(`/realms/<product>-<env>/`) ||
   PathPrefix(`/resources/`))
```

The exact `Path` plus slash-terminated `PathPrefix` avoids accepting a realm whose name
only starts with the intended realm. An apply-ready source patch for the three current
routers is at `docs/patches/keycloak-product-host-isolation.patch`; apply it from a
Keycloak-repo session, deploy with the Keycloak runbook, then rerun the shared verifier.

Keep `key.dvmsoftware.com` as the separately restricted operator/admin host. Before
deploying this rule, validate every applicable login, action-email, registration/reset,
broker callback, account-console, logout, and theme-asset path in dev; add another
allowlisted path only with observed evidence. Unmatched product-host paths should fall
through to Traefik 404 rather than a Keycloak admin or unrelated realm.

Do not decommission Authentik until this blocker, Keycloak backup/restore coverage, and
all per-app cutovers are closed.

## Per-environment acceptance record

Copy this checklist into the app migration plan. Mark a gate only with a command, test,
or operator-observed result and its date.

### Realm and ingress

- [ ] Realm, clients, roles, scopes, mappers, and flows are declared in reviewed
      Terraform; a no-change plan converges.
- [ ] Product auth DNS and certificate work; discovery's `issuer`, authorization,
      token, logout, and JWKS URLs use the exact product host and realm.
- [ ] Product host denies `/admin`, `/realms/master`, and unrelated realms while login,
      registration/reset, account UI, and required assets still work.
- [ ] Client secrets are new, stored in Vaultwarden/GitHub environment secrets, and do
      not appear in source, logs, Terraform output, or command history.
- [ ] Keycloak database/config/state backup is scheduled, off-host, and restore-tested.

### Web or native login

- [ ] App login redirects through public ingress with exact callback URI, state, nonce,
      authorization code, and S256 PKCE.
- [ ] Fresh account reaches the correct local user and organization; authentication alone
      does not grant product or platform-admin access.
- [ ] Wrong state, wrong issuer/environment, wrong audience, expired token, and missing
      product/tenant role are rejected.
- [ ] Refresh, concurrent refresh, logout, session expiry, and provider revocation behave
      predictably; cookies/tokens use the platform's secure storage rules.
- [ ] Email signup/verification/reset and social collision/linking paths pass when those
      features are enabled. Disabled flows fail clearly, not after accepting the user.
- [ ] Native clients, when present, are public clients using the system browser and S256
      PKCE with no embedded secret.

### API, service account, and SaaS overlay

- [ ] API authorization validates access-token purpose, exact issuer, explicit audience,
      time claims, allowed algorithm, subject, tenant membership, and product role.
- [ ] M2M clients, when present, use dedicated service accounts and minimal scopes;
      wrong-client, wrong-realm, and replay/expiry tests fail.
- [ ] Local external identities use `(issuer, subject)` linked to an internal user ID.
      Verified email is required before email-based invitation or first binding.
- [ ] Customer-management apps prove organization lifecycle, RBAC, audited operator
      actions, support access, billing/entitlement reconciliation, and AI usage limits as
      applicable. Keycloak roles do not replace those application controls.
- [ ] Messaging accepts only registered product issuer/audience combinations and verifies
      tenant, subject, and conversation context.

### Cutover and cleanup

- [ ] Deployed environment contains no required Authentik issuer, outpost, client secret,
      middleware, or runtime dependency. Historical tests/docs may remain only when
      clearly marked archive or migration history.
- [ ] Fresh dev users and affected sandbox fixtures were reseeded; no Authentik data was
      imported or retained for migration purposes.
- [ ] Logs, health checks, and audit events show the new flow without tokens or sensitive
      personal data.
- [ ] Rollback boundary is documented. Promote to prod only after the dev record passes;
      then repeat prod-specific DNS, secrets, role, backup, and smoke tests.

## Deterministic public verifier

Use the shared check for discovery, endpoint branding, JWKS availability, login redirect,
and the product-host isolation negatives:

```bash
./scripts/validate-keycloak-rollout.sh \
  --issuer https://auth.comcentre.online/realms/cc-dvm-dev \
  --login-url https://dev.comcentre.online/api/v1/auth/login \
  --deny-realm gelopreto-dev
```

The script is expected to fail on live product hosts until master/admin paths are blocked.
Interactive account, role, tenant, refresh, logout, social/email, and M2M checks remain
application-specific and cannot be replaced by this public probe.

## Cross-session handoff

Every app session should return this compact record to this ledger:

```text
Product/environment:
Realm + auth host:
Client types:
App commit/deployed digest:
Terraform commit/applied plan:
Positive evidence:
Negative evidence:
Authentik runtime references remaining:
Open blockers / rollback:
Accepted by/date:
```

The infra session owns consolidation and the final “nothing points to Authentik” audit.
The final shutdown is a separate, explicit operation after every required row is accepted.
