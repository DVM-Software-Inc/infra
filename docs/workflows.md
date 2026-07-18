# CI/CD Workflows

Shared reusable workflows in `.github/workflows`:

| Workflow | Status | What it does |
|---|---|---|
| `build.yml` | ✅ canonical | Parameterized Docker build (`context`, `dockerfile`, build args, cache), pushing immutable `:<env>-<shortsha>` plus an optional moving `:<env>` compatibility tag. Exposes the immutable tag/ref/digest. |
| `deploy.yml` | ✅ canonical | scp the compose file, atomically write protected environment content, inject the immutable image tag, validate/pull, run optional release hooks, wait for Compose health, and smoke-check URLs. Declares `environment:` so prod approval gates apply here. |
| `lint.yml` / `tests.yml` | placeholder | Define real lint/tests in the caller |
| `build-and-push.yml` | ⛔ deprecated | Uppercase GHCR path (push fails). Use `build.yml`. |
| `deploy-dev.yml` / `deploy-prod.yml` | ⛔ deprecated | Remote-side `$(cat artifact/…)` heredoc bug writes an empty compose file. Use `deploy.yml`. |

Caller contract (full annotated example: `prompts/base.md`):

```yaml
on:
  push:
    branches: [main]          # → dev
  workflow_dispatch:          # → dev or prod (manual promotion)
    inputs:
      environment:
        type: choice
        options: [dev, prod]
        default: dev
        required: true

jobs:
  build:
    uses: DVM-Software-Inc/infra/.github/workflows/build.yml@main
    permissions:
      contents: read
      packages: write
    with:
      image_name: ${{ github.event.repository.name }}
      environment: ${{ github.event_name == 'workflow_dispatch' && inputs.environment || 'dev' }}
      # dockerfile: apps/api/Dockerfile
      # build_args: |
      #   PUBLIC_API_URL=https://api.example.com
  deploy:
    needs: build
    uses: DVM-Software-Inc/infra/.github/workflows/deploy.yml@main
    permissions:
      contents: read
      packages: read
    with:
      environment: ${{ github.event_name == 'workflow_dispatch' && inputs.environment || 'dev' }}
      compose_file: deploy/docker-compose.yml   # must live under deploy/
      deploy_path: /opt/apps/<slug>/${{ github.event_name == 'workflow_dispatch' && inputs.environment || 'dev' }}
      image_tag: ${{ needs.build.outputs.image_tag }}
      require_env_file: true
      # migrate_command: docker compose -f "$COMPOSE_FILE" run --rm api alembic upgrade head
    secrets:
      VPS_HOST: ${{ secrets.VPS_HOST }}
      VPS_USER: ${{ secrets.VPS_USER }}
      VPS_SSH_KEY: ${{ secrets.VPS_SSH_KEY }}
      VPS_FINGERPRINT: ${{ secrets.VPS_FINGERPRINT }}
```

**Caller setup preconditions (per repo):**

1. Create GitHub environments `dev` and `prod`, with **required reviewers on `prod`** —
   `deploy.yml`'s `environment:` line only gates approval if the environment is protected;
   GitHub auto-creates it unprotected on first use.
2. Provide `.env`: set the per-environment `ENV_FILE` secret. The called deploy job targets
   the selected GitHub environment and reads that secret directly; environment secrets
   cannot be passed from the caller job. The workflow transfers it as masked Base64 and
   atomically writes `deploy_path/.env` with mode 600. `require_env_file: true` is strongly
   recommended; pre-provisioned files remain supported for legacy callers.
3. Compose files must live under `deploy/` in the repo (enforced by a validation step;
   required by the scp `strip_components` contract so the file lands flat in `deploy_path`
   next to `.env`).
4. Set a unique top-level `name:` in every compose file (e.g. `<slug>-dev`) — compose
   otherwise derives the project name from the deploy directory's basename (`dev`/`prod`,
   shared by ALL apps in the `/opt/apps/<slug>/<env>` layout), and `up -d --remove-orphans`
   would delete other apps' containers.
5. Reference images as `:${IMAGE_TAG}`. The deploy workflow writes the immutable
   `<environment>-<shortsha>` value; do not put `TAG` or `IMAGE_TAG` in the static
   `ENV_FILE` secret. Moving `:dev`/`:prod` aliases are compatibility-only and must not be
   used for deployment.
6. Prefer `GITHUB_TOKEN` with job-scoped `packages: write`/`packages: read`. The old
   `GHCR_USERNAME` and `GHCR_TOKEN` secrets remain optional for compatibility.
7. After publishing a tested infra release, pin callers to its commit SHA rather than
   leaving production callers on the mutable `@main` ref.

Environment model: ONE VPS. Push to `main` → dev (dir `/opt/apps/<slug>/dev`, immutable tag,
host `dev.<domain>` / `staging.api.<domain>`); manual `workflow_dispatch` → prod
(dir `/opt/apps/<slug>/prod`, immutable tag, host `app.<domain>` / `api.<domain>`, GitHub
environment `prod` requires reviewer approval). Apps use their own root domain;
`*.dvmsoftware.com` is for internal utilities.

Compose files MUST follow the live VPS conventions — canonical template in
`prompts/base.md` (aligned with `~/code/vps_deploy/DEPLOY_UTILITY.md` §4: network
`web-public`, `traefik.docker.network=web-public`, restart `unless-stopped`, cert resolver
`letsencrypt`) — NOT the older templates in `docker-templates/`.

Migration note (2026-07-18): `chatactorai` is the first multi-image caller. Its migration
uses two `build.yml` jobs, one immutable tag shared by API/web, a flat
`/opt/apps/chatactorai/<env>/` layout, and the protected `ENV_FILE` contract. Publish and
pin the infra workflow revision before enabling that caller on `main`.
