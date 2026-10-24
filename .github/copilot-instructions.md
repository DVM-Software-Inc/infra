# DVM Software engineering instructions

This repository owns the shared application and delivery standards. Do not copy an old
deployment example from memory: load the canonical context for the task.

## Canonical context

1. Start with `prompts/base.md` for every server-deployed app.
2. Add exactly one app-type prompt from `prompts/` (`backend`, `frontend`, `fullstack`,
   `ios`, `ios-backend`, or `macos`).
3. Include `prompts/messaging.md`; its integration requirements activate when the
   product supports authenticated user-to-business communication.
4. Add `prompts/saas.md` when the product manages customer accounts, organizations,
   billing, support, entitlements, or paid usage.
5. Add `prompts/ai-product.md` for product-managed LLM/AI inference, RAG, or model-backed
   operator tools.
6. For identity migration work, use `docs/keycloak-migration.md` for portfolio status
   and acceptance gates, plus `~/code/keycloak/docs/` for realm implementation.

The live VPS runbooks in `~/code/vps_deploy/` win if they conflict with this repo. Fix
the stale document when a mismatch is confirmed.

## Non-negotiable current defaults

- Docker Compose is deployed directly under `/opt/apps/<slug>/<environment>/`; Dokploy
  and `dokploy-network` are obsolete.
- Public services join external `web-public`; private app services use an internal
  network. Traefik runs with `exposedByDefault: false`, so explicitly label only the
  intended public service.
- Compose has a unique top-level `name: <slug>-<environment>`, uses
  `restart: unless-stopped`, does not publish host ports, and references immutable
  `${IMAGE_TAG}` releases rather than `latest`.
- Push to `main` deploys dev. Production is an explicit `workflow_dispatch` using the
  protected `prod` environment when the GitHub plan supports protection.
- Use `.github/workflows/build.yml` and `deploy.yml`. The other legacy deployment
  workflows and `docker-templates/` are documented as deprecated.
- Apps completing the owner-controlled gate pilot use `deploy-gated.yml` instead of
  `deploy.yml`; see `docs/owner-controlled-releases.md`. CI submits immutable image
  digests, never Compose, runtime secrets or commands. Keep production blocked until
  all root-equivalent CI bypasses are removed and the exact owner approval is proven.
- Prefer job-scoped `GITHUB_TOKEN` for GHCR. Runtime secrets originate in Vaultwarden
  and reach the deployment through protected GitHub environment secrets; values never
  belong in source or examples.
- Human authentication uses the product environment's Keycloak realm at
  `https://auth.<product-domain>/realms/<product>-<environment>`. Never configure an app
  against the shared Keycloak host, master realm, or another product's realm.
- A Keycloak realm represents one product environment, never one customer. Tenant
  membership, authorization, billing, entitlements, operator workflows, and AI budgets
  remain application concerns.
- Existing Authentik apps move one at a time, dev before prod. Development Authentik
  identities are disposable; do not import users, credentials, sessions, secrets, or
  policies. Do not remove an old runtime dependency until the app's ledger entry is
  accepted.

## Before declaring work complete

- Run the repository's substantive local checks and `git diff --check`.
- For deployment work, verify container health, public HTTPS behavior, and rollback
  boundaries using `docs/workflows.md` and the live runbook.
- For Keycloak work, run `scripts/validate-keycloak-rollout.sh` and complete the
  application-specific positive and negative gates in `docs/keycloak-migration.md`.
- Preserve unrelated working-tree changes and record evidence separately from
  assumptions or user-reported status.
