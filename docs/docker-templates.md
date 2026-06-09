# Docker Templates Overview

- `docker-templates/traefik` — Traefik reverse proxy stack
- `docker-templates/nginx` — NGINX reverse proxy stack
- `docker-templates/apps` — App docker-compose template for Traefik
- `docker-templates/databases` — Postgres, MongoDB, MSSQL templates

> **⚠️ Divergence warning (2026-06-09):** these templates predate the live VPS conventions.
> They reference network `dvm_traefik` and `restart: always`; the live VPS uses the
> attachable overlay `web-public`, `restart: unless-stopped`, and requires the
> `traefik.docker.network=web-public` label. The canonical compose template is
> `~/code/vps_deploy/DEPLOY_UTILITY.md` §4. Backends listen on internal port 8080
> (`docs/standards.md`) — note `templates/backend-fastapi/` still says 8000.
