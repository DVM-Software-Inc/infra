# CI/CD Workflows

Shared reusable workflows in `.github/workflows`:

| Workflow | Status | What it does |
|---|---|---|
| `build.yml` | ✅ canonical | Build Docker image, push to GHCR as `:<env>` + `:<env>-<shortsha>` (owner/image lowercased) |
| `deploy.yml` | ✅ canonical | scp the compose file to `deploy_path` on the VPS, `docker compose pull && up -d`. Declares `environment:` so prod approval gates apply here. |
| `lint.yml` / `tests.yml` | placeholder | Define real lint/tests in the caller |
| `build-and-push.yml` | ⛔ deprecated | Uppercase GHCR path (push fails). Use `build.yml`. |
| `deploy-dev.yml` / `deploy-prod.yml` | ⛔ deprecated | Remote-side `$(cat artifact/…)` heredoc bug writes an empty compose file. Use `deploy.yml`. |

Caller contract (see `DVM-Software-Inc/backend-fastapi-audition-reader/.github/workflows/ci.yml` for a working example):

```yaml
jobs:
  build:
    uses: DVM-Software-Inc/infra/.github/workflows/build.yml@main
    with:
      image_name: <repo-name>
      environment: dev   # or prod
    secrets:
      GHCR_USERNAME: ${{ secrets.GHCR_USERNAME }}
      GHCR_TOKEN: ${{ secrets.GHCR_TOKEN }}
  deploy:
    needs: build
    uses: DVM-Software-Inc/infra/.github/workflows/deploy.yml@main
    with:
      environment: dev
      compose_file: deploy/docker-compose.dev.yml   # keep compose files under deploy/
      deploy_path: /opt/<slug>/dev
    secrets:
      GHCR_USERNAME: ${{ secrets.GHCR_USERNAME }}
      GHCR_TOKEN: ${{ secrets.GHCR_TOKEN }}
      VPS_HOST: ${{ secrets.VPS_HOST }}
      VPS_USER: ${{ secrets.VPS_USER }}
      VPS_SSH_KEY: ${{ secrets.VPS_SSH_KEY }}
```

**Caller setup preconditions (per repo):** (1) create the `prod` GitHub environment **with required reviewers** — `deploy.yml`'s `environment:` line only gates approval if the environment is protected; GitHub auto-creates it unprotected on first use. (2) Pre-provision `deploy_path` on the VPS with its `.env` file before the first deploy — the workflow ships only the compose file. (3) Compose files must live under `deploy/` in the repo (enforced by a validation step; required by the scp `strip_components` contract so the file lands flat in `deploy_path` next to `.env`).

Environment model: ONE VPS. `dev` branch → dev (subdomain `<slug>-dev.dvmsoftware.com`, dir `/opt/<slug>/dev`, tag `:dev`); `main` branch → prod (subdomain `<slug>.dvmsoftware.com`, dir `/opt/<slug>/prod`, tag `:prod`, GitHub environment `prod` requires reviewer approval).

Compose files MUST follow the live VPS conventions in `~/code/vps_deploy/DEPLOY_UTILITY.md` §4 (network `web-public`, `traefik.docker.network=web-public`, restart `unless-stopped`, cert resolver `letsencrypt`) — NOT the older templates in `docker-templates/`.
