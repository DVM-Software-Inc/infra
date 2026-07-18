# Docker Templates Overview

> **⛔ DEPRECATED (2026-07-18):** everything under `docker-templates/` predates the live
> VPS conventions (wrong networks `dvm_traefik`/`dokploy-network`, `restart: always`,
> missing `traefik.docker.network` label, `:latest` image tags that are never pushed).
> **Do not copy from it.** The canonical compose template lives in
> [`prompts/base.md`](../prompts/base.md) (aligned with
> `~/code/vps_deploy/DEPLOY_UTILITY.md` §4). The directory is kept only until the
> reverse-proxy/database reference stacks are rewritten; treat it as read-only history.

Legacy contents: `traefik/`, `nginx/`, `apps/`, `databases/` (Postgres, MongoDB, MSSQL).
Note the VPS already runs shared Traefik and Postgres — app repos never deploy their own.
