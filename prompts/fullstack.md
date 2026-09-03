# App type: fullstack — React/Next frontend + FastAPI backend

Read `base.md` first. This is the pattern proven by `chatactorai`; follow it for any
web-UI + API product. Backend specifics also follow `backend.md`.

## Repo shape — monorepo, npm workspaces

```
apps/api/        # FastAPI backend (Python, uv; source at apps/api/src/app/)
apps/web/        # Next.js App Router frontend (TypeScript)
packages/*       # shared TS packages (types, embeddable widgets…)
deploy/docker-compose.yml
docs/overview.md
```

Root `package.json`: `"private": true, "workspaces": ["apps/web", "packages/*"]`.
No Turborepo unless genuinely needed.

## Two containers, two hosts

Frontend and backend are **separate images/containers**, each with its own Traefik router:

- `web` (Next.js) → `Host(${APP_HOST})`, container port **3000** — prod `app.<domain>`
- `api` (FastAPI) → `Host(${API_HOST})`, container port **8000** — prod `api.<domain>`

Both join `web-public` (with the full label set from `base.md`, unique router names like
`<slug>-<env>-web` / `<slug>-<env>-api`) **and** an app-private `internal` bridge network.
Redis/Celery workers/beat sit on `internal` only, no Traefik labels. Postgres is the shared
VPS instance — never a service in the deploy compose.

## Frontend build & serve

- Next.js **standalone** output, multi-stage `node:20-alpine` Dockerfile, final
  `CMD ["node", "server.js"]`, `ENV HOSTNAME=0.0.0.0 PORT=3000` (must bind 0.0.0.0 or
  Traefik can't reach it).
- `NEXT_PUBLIC_*` values are **baked at image build time** via `ARG`s — so images are
  per-environment. The CI build passes e.g. `NEXT_PUBLIC_API_URL=https://<api-host>` as a
  build arg; never read `NEXT_PUBLIC_*` at runtime.

## Auth — BFF pattern (the standard)

The Next app is an OIDC **backend-for-frontend** against **its product's Keycloak
realm** — see `base.md` → Authentication. The app is a *client* of the realm; it
never authenticates anyone itself.

- `openid-client` + `iron-session`: the browser holds only an encrypted session cookie;
  tokens never reach client JS.
- Next route handlers implement `/auth/login|callback|logout`, plus an `/api/[...path]`
  proxy that attaches the bearer token server-side and forwards to the api container over
  the `internal` network (`http://api:8000`).
- FastAPI validates RS256 JWTs against the **realm's** JWKS (derived from `OIDC_ISSUER_URL`). Direct-to-API clients
  (widgets, integrations) use app-issued tokens/API keys instead of the cookie.
- OIDC env var names: `OIDC_ISSUER_URL`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`,
  `OIDC_REDIRECT_URI` (`https://<app-host>/auth/callback`), `OIDC_SCOPES`
  (`openid email profile offline_access`), `SESSION_SECRET`.
- **`OIDC_ISSUER_URL` is the product's own auth host**, never `key.dvmsoftware.com`:
  `https://auth.<product-domain>/realms/<product>-<env>`. Everything else — JWKS,
  authorize, token — derives from it.
  Provisioning: `~/code/keycloak/terraform/`.

## CI/CD deltas from base

- Two `build.yml` calls (or one matrix): images `<repo>-api` and `<repo>-web`; the web
  build needs per-env build args for `NEXT_PUBLIC_*`.
- One `deploy.yml` call; `migrate_command` runs Alembic (and any seed script) via the api
  image before `up -d`.
- CI test jobs before deploy: ruff + pytest (spin up postgres/redis service containers),
  `next build`, package builds.
