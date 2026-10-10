# App type: backend only (API service)

Read `base.md` first — this file only adds the backend-specific deltas.

## Shape

Single deployable container: one API service behind Traefik at `api.<domain>` (or the root
domain if there is no web UI). Source in `/src`. Optional sidecars (redis, worker) stay on
an app-private `internal` network.

## Internal ports (container-side; Traefik label must match)

| Stack | Port | Server |
|---|---|---|
| FastAPI (Python) | 8000 | `uvicorn src.app.main:app --host 0.0.0.0 --port 8000` |
| Go | 8080 | net/http |
| Node/TS API | 3000 | — |

Ports are container-internal only — never published on the host; changing them is fine as
long as the `loadbalancer.server.port` label matches. These are the defaults agents must
use absent an explicit reason.

## Dockerfile conventions

- Slim multi-stage builds: `python:3.12-slim` (deps via `uv` if the repo uses it, else pip),
  a currently supported Go builder matching `go.mod` (Go 1.27 for new work as of
  2026-09) → pinned distroless/alpine runner, and Node 24 LTS for new Node services.
- Bind `0.0.0.0`, `EXPOSE` the port from the table, no secrets baked into images.
- Run the final image as a non-root user. Pin release image digests after the starter's
  compatibility check; review the runtime matrix at least quarterly rather than letting
  app generators preserve an EOL default indefinitely.

## Required endpoints

- `GET /health` → 200 JSON, no auth, no DB dependency if possible. Used by humans, Traefik
  debugging, and future uptime checks.
- Version your public API under `/api/v1/…`.

## Database & migrations

- Shared VPS Postgres per `base.md`; SQLAlchemy repos use Alembic, and migrations run via
  the deploy workflow's `migrate_command`
  (`docker compose -f "$COMPOSE_FILE" run --rm api alembic upgrade head`) — never
  `create_all()` in production code paths, never migrate on container start.
- Local dev: SQLite or a local compose Postgres is fine; select via `DATABASE_URL`.

## Auth

- Machine/service clients: bearer tokens or API keys issued by the app.
- Human-facing endpoints (admin UIs, dashboards): OIDC against the product's Keycloak
  realm — see `base.md` → Authentication. APIs accept access tokens and validate
  allowed algorithm, exact product/environment issuer, explicit API audience,
  expiry/not-before/issued-at as applicable, and subject against the realm's JWKS.
  Reject ID tokens as API bearers and resolve tenant membership/permission locally.
  The issuer is the product's auth host, never `key.dvmsoftware.com`.
- Service accounts use their own confidential client, audience and minimum scopes;
  app-issued API keys/tokens are scoped, hashed at rest, revocable and auditable.
