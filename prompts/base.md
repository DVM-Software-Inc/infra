# DVM-Software deployment conventions — base (all server-deployed apps)

You are working in a DVM-Software-Inc app repo. Follow these conventions exactly; do not
invent alternatives. When something here conflicts with the live VPS, the VPS wins — then
update this doc.

## Topology

- **One VPS** (Contabo, `194.238.24.254`, `ssh contabo`) runs everything as Docker Compose
  stacks. No Kubernetes.
- **Traefik v3** owns host ports 80/443 with the `letsencrypt` cert resolver and discovers
  containers by docker labels on the **`web-public`** attachable overlay network (kept alive
  by a single-node swarm — never `docker swarm leave`, never bind host ports 80/443/8080).
- **Shared Postgres 18** (`pgvector/pgvector:pg18`, container `app-postgres`) hosts one
  DB + user per app+env, reachable from any `web-public` container at **`postgres:5432`**.
  Not exposed publicly; laptop access only via SSH tunnel.
- **Secrets** live only in Vaultwarden (`vault.dvmsoftware.com`). GitHub Actions secrets are
  populated from it (`bw get password <item> | gh secret set <NAME> -R DVM-Software-Inc/<repo>`).
  Never write a secret value into the repo, chat, or logs. `.env.example` lists variable
  names and the Vaultwarden item that holds each value — never values.

## Environments, branching, domains

- Environments: `dev` and `prod`, both on the same VPS.
- **Push to `main` → auto-deploys `dev`. Prod deploys only via manual `workflow_dispatch`**
  against the protected GitHub environment `prod` (required reviewers). There is no `dev`
  or `prod` branch; feature branches merge to `main` via PR.
- **Each product owns its root domain** (Namecheap), e.g. `chatactorai.com`:
  - prod: `app.<domain>` (web/UI) and `api.<domain>` (API) — single-container apps may use
    the root or one subdomain
  - dev: `dev.<domain>` / `staging.api.<domain>` (prefix the prod host)
  - `*.dvmsoftware.com` is reserved for internal utilities (vault, auth, traefik, …).
- **DNS before deploy**: create the A record → `194.238.24.254` and verify
  `dig +short <host> A` resolves before `docker compose up`, or Let's Encrypt HTTP-01 fails.

## VPS layout

- Apps deploy to **`/opt/apps/<slug>/<env>/`** — compose file + `.env` + volume bind-mount
  subdirectories, nothing else. (Utilities use `/opt/<name>/`; don't mix them.)
- Persistent data = bind mounts under the deploy dir (`./data:…`), so one `tar` backs up
  the service.

## CI/CD contract

Repos use the reusable workflows from `DVM-Software-Inc/infra` — never hand-roll
scp/ssh deploy jobs. Compose files live under **`deploy/`** in the repo (enforced).

```yaml
name: CI/CD
on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      environment:
        type: choice
        options: [dev, prod]
        default: dev
        required: true

jobs:
  # lint/test jobs here — deploy must depend on them

  build:
    uses: DVM-Software-Inc/infra/.github/workflows/build.yml@main
    permissions:
      contents: read
      packages: write
    with:
      image_name: ${{ github.event.repository.name }}
      environment: ${{ github.event_name == 'workflow_dispatch' && inputs.environment || 'dev' }}

  deploy:
    needs: build
    uses: DVM-Software-Inc/infra/.github/workflows/deploy.yml@main
    permissions:
      contents: read
      packages: read
    with:
      environment: ${{ github.event_name == 'workflow_dispatch' && inputs.environment || 'dev' }}
      compose_file: deploy/docker-compose.yml
      deploy_path: /opt/apps/${{ github.event.repository.name }}/${{ github.event_name == 'workflow_dispatch' && inputs.environment || 'dev' }}
      image_tag: ${{ needs.build.outputs.image_tag }}
      require_env_file: true
      # migrate_command: docker compose -f "$COMPOSE_FILE" run --rm api alembic upgrade head
    secrets:
      VPS_HOST: ${{ secrets.VPS_HOST }}
      VPS_USER: ${{ secrets.VPS_USER }}
      VPS_SSH_KEY: ${{ secrets.VPS_SSH_KEY }}
      VPS_FINGERPRINT: ${{ secrets.VPS_FINGERPRINT }}
```

- `build.yml` always pushes immutable `ghcr.io/dvm-software-inc/<image>:<env>-<shortsha>`
  and can publish the moving `:<env>` compatibility alias. Deployments pass the immutable
  output to `deploy.yml`, which writes `IMAGE_TAG`/`TAG` into `.env`; Compose must reference
  `${IMAGE_TAG}`. Never deploy a moving tag.
- Per-env config: create GitHub environments `dev` and `prod` (prod with required
  reviewers — GitHub auto-creates it unprotected on first use, protect it explicitly).
  Store `ENV_FILE` (the full static dotenv, excluding `TAG`/`IMAGE_TAG`) in each environment.
  The called deploy job reads the environment secret directly, transfers it as masked
  Base64, and atomically writes `<deploy_path>/.env` with mode 600.
- Migrations run through `migrate_command` (after pull, before `up -d`).
- Prefer the caller's `GITHUB_TOKEN` with job-scoped package permissions; legacy GHCR
  credentials remain supported. Pin production callers to a tested infra commit SHA.

## Canonical compose file (`deploy/docker-compose.yml`)

```yaml
name: ${PROJECT_NAME}-${DEPLOY_ENVIRONMENT}   # stable across immutable image revisions.
   # Must be UNIQUE per app+env on the VPS — compose otherwise derives it from the deploy
   # dir basename (dev/prod, shared by ALL apps) and `--remove-orphans` would delete other
   # apps' containers. deploy.yml writes DEPLOY_ENVIRONMENT and IMAGE_TAG dynamically;
   # ENV_FILE sets PROJECT_NAME=<slug> and APP_DOMAIN=<host>.
services:
  api:
    image: ghcr.io/dvm-software-inc/${PROJECT_NAME}:${IMAGE_TAG}
    container_name: ${PROJECT_NAME}-${DEPLOY_ENVIRONMENT}
    restart: unless-stopped
    env_file: [.env]
    volumes:
      - ./data:/path/inside/container   # persistent state stays under the deploy dir
    networks: [web-public]
    labels:
      - traefik.enable=true
      - traefik.docker.network=web-public
      - traefik.http.services.${PROJECT_NAME}-${DEPLOY_ENVIRONMENT}.loadbalancer.server.port=<container-port>
      - traefik.http.routers.${PROJECT_NAME}-${DEPLOY_ENVIRONMENT}.rule=Host(`${APP_DOMAIN}`)
      - traefik.http.routers.${PROJECT_NAME}-${DEPLOY_ENVIRONMENT}.entrypoints=websecure
      - traefik.http.routers.${PROJECT_NAME}-${DEPLOY_ENVIRONMENT}.tls.certresolver=letsencrypt
      - traefik.http.routers.${PROJECT_NAME}-${DEPLOY_ENVIRONMENT}-http.rule=Host(`${APP_DOMAIN}`)
      - traefik.http.routers.${PROJECT_NAME}-${DEPLOY_ENVIRONMENT}-http.entrypoints=web
      - traefik.http.routers.${PROJECT_NAME}-${DEPLOY_ENVIRONMENT}-http.middlewares=redirect-to-https@file

networks:
  web-public:
    external: true
```

Rules that matter:

- `traefik.enable=true` is required (`exposedByDefault: false`); `traefik.docker.network=web-public`
  disambiguates when a container joins multiple networks.
- `loadbalancer.server.port` is the **container** port — publish no host ports; Traefik
  reaches containers over `web-public`.
- Router/service names must be unique across the whole VPS — always suffix with env.
- Backing services an app owns (redis, workers) join an app-private `internal` bridge
  network and get **no** Traefik labels; only web-facing services join `web-public`.
- `restart: unless-stopped`, never `always`. No `version:` key (compose v2).
- Single-quote values containing `$` in `.env` (argon2 hashes etc.) — compose interpolates
  unquoted `$`. Prefer `env_file:` over `${VAR}` interpolation for secret-bearing values.
- After editing `.env` on the VPS, `docker compose up -d` to recreate — changes aren't live.

## Database (shared Postgres)

Per app+env, once, at provisioning time (superuser access via `ssh contabo "docker exec -it
app-postgres psql -U postgres"`):

```sql
CREATE USER <slug>_<env> WITH PASSWORD '<from-vaultwarden>';
CREATE DATABASE <slug>_<env> OWNER <slug>_<env>;
GRANT ALL PRIVILEGES ON DATABASE <slug>_<env> TO <slug>_<env>;
```

Store the password in Vaultwarden as `postgres-<slug>-<env>`. The app connects with
`postgresql://<slug>_<env>:<pw>@postgres:5432/<slug>_<env>` (asyncpg variant:
`postgresql+asyncpg://…`). Default to shared Postgres; dedicated instances only for heavy
load or compliance.

## Repo hygiene (every server-deployed repo)

- `Dockerfile` per deployable service; compose under `deploy/`; `.env.example` (names +
  Vaultwarden item references only); `.github/workflows/ci.yml`; `/docs/overview.md` with
  project-specific detail (hosts, services, env vars, anything an agent can't infer).
- Auth for human users goes through Authentik SSO (OIDC) — see
  `~/code/vps_deploy/infra_llm/docs/auth-playbook.md`. Don't build standalone password auth.

## Verify a deploy

```bash
ssh contabo "docker ps --filter name=<slug>"          # Up?
curl -sI http://<host>   # expect 301 → https (give Traefik ~10s after up -d)
curl -sI https://<host>  # expect 200/302 with valid cert
ssh contabo "docker logs <container> --tail 50"
```
