# Organization Standards

- Source code goes in `/src` (monorepos: `apps/<service>/src`, packages in `packages/`).
- Internal container ports (Traefik `loadbalancer.server.port` must match; never publish
  host ports):
  - FastAPI/uvicorn: **8000**
  - Go: **8080**
  - Node/Next frontends & APIs: **3000**
  - Static (nginx): **80**
- Every server-deployed repo includes:
  - `/docs/overview.md` (hosts, services, env vars — what an agent can't infer)
  - `Dockerfile` per deployable service
  - `deploy/docker-compose.yml` (must set a unique top-level `name: <slug>-<env>`)
  - `.env.example` — variable names + Vaultwarden item references, never values
  - `.github/workflows/ci.yml` calling the reusable workflows from this repo
- iOS repos follow `prompts/ios.md` (XcodeGen, xcconfig-per-environment, SwiftPM kits).
- macOS repos follow `prompts/macos.md` (SwiftPM-first, core/app split, Keychain secrets).
- Full per-app-type conventions: **`prompts/`** in this repo — `base.md` + one type file
  is the canonical context to give any LLM session.
- Customer-management products also use **`prompts/saas.md`**. Products with managed
  LLM/AI features also use **`prompts/ai-product.md`**. These are capability overlays,
  not replacement app types.
- Keycloak portfolio rollout status and evidence gates: **`docs/keycloak-migration.md`**.
  Application implementation stays in its own repo/session; this ledger decides when a
  dev or prod cutover is actually accepted and when Authentik can be retired.

## Authentication and Google social login

- Human authentication uses one Keycloak realm per product **per environment**.
  No cross-product user directory or SSO; customer tenancy and authorization stay
  in the application. Classify account-free and machine-only workloads explicitly
  instead of creating unused realms.
- Google is an upstream identity provider of the product realm. Applications
  authenticate with Keycloak, not directly with the Google client secret.
- Owner decision, 2026-09-06: one existing master Google account administers
  independent product Cloud projects. Do not create consumer Google accounts for
  each `support@` mailbox or grant mailbox-only addresses IAM Owner.
- Use separate Google Cloud projects for **dev/testing and production**, with
  separate OAuth clients/secrets and exact environment-specific broker callbacks:
  `https://auth.<product-domain>/realms/<product>-<env>/broker/google/endpoint`.
  An existing project whose ID ends in `-prod` is not proof of publication or a
  reason to place dev callbacks in its production configuration.
- Keep dev OAuth in Testing. Do not require an undeployed production website for
  dev login; complete public homepage/privacy policy, domain ownership and
  applicable Google brand/scope verification before production publication.
- OAuth support email may be visible to users. Developer contact is separate;
  use the owner-approved master address for both during this rollout.
- Vaultwarden is the credential source of truth. Keep Google operator, Google
  OAuth and Keycloak application-client credentials in distinct items. Inject
  secrets only into approved runtime/CI configuration; protect Terraform state
  as secret-bearing data and never print values in plans, logs or documentation.
- Use only `openid profile email` for Google authentication. Preserve a reviewed
  first-broker-login flow; email collision/linking needs explicit negative tests,
  not an assumption based on `trust_email` alone.
- Acceptance requires public login and callback, authorization, refresh/logout,
  wrong issuer/audience/state/nonce rejection and safe account linking. DNS, a
  saved consent screen, or a created realm is not completed social login.

Google's [OAuth production-readiness requirements](https://developers.google.com/identity/protocols/oauth2/production-readiness/policy-compliance)
define environment-project separation and public production requirements. Current
observed fleet state belongs in the migration ledger, not a permanent fleet-wide
claim that every app has already migrated.
