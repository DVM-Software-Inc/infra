# Go Project Template

Full conventions: `prompts/base.md` + `prompts/backend.md` in the infra repo.

## Quick Start

1. Copy this template to your new project
2. Fill `.env.example` values into the per-env `ENV_FILE` GitHub secret (or a hand-staged `.env`)
3. Push to GitHub under `DVM-Software-Inc`
4. Create GitHub environments `dev` and `prod` (protect `prod` with required reviewers) and add the secrets below to each
5. Push to `main` → deploys dev; promote to prod via `workflow_dispatch`

## Required Secrets (per environment)

| Secret | Description |
|--------|-------------|
| `GHCR_USERNAME` | GitHub username for container registry |
| `GHCR_TOKEN` | PAT with `write:packages` scope |
| `VPS_HOST` | VPS IP (194.238.24.254) |
| `VPS_USER` | SSH user (root) |
| `VPS_SSH_KEY` | SSH private key |
| `ENV_FILE` | Optional: full dotenv content, written to `<deploy_path>/.env` by CI |

## VPS Setup

Before first deploy, create the per-env app folders (and stage `.env` by hand only if you
don't use the `ENV_FILE` secret):

```bash
ssh contabo "mkdir -p /opt/apps/YOUR_PROJECT_NAME/dev /opt/apps/YOUR_PROJECT_NAME/prod"
```

Also: create the DNS A record for the env's host (per-product root domain) *before*
deploying, or Let's Encrypt issuance fails.

The compose file lives at `deploy/docker-compose.yml` in the repo and is deployed by CI.

## Endpoints

- Health: `https://<APP_DOMAIN>/health`
