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
  `golang:1.2x` builder → distroless/alpine runner, `node:20-alpine`.
- Bind `0.0.0.0`, `EXPOSE` the port from the table, no secrets baked into images.

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
  realm — see `base.md` → Authentication. Validate tokens against the realm's JWKS;
  the issuer is the product's auth host, never `key.dvmsoftware.com`.
