# Go Project Template

## Quick Start

1. Copy this template to your new project
2. Update `.env.example` → `.env` with your domain
3. Push to GitHub under `DVM-Software-Inc`
4. Add environment secrets (prod/dev) in repo settings
5. Push to `main` to deploy

## Required Secrets (per environment)

| Secret | Description |
|--------|-------------|
| `GHCR_USERNAME` | GitHub username for container registry |
| `GHCR_TOKEN` | PAT with `write:packages` scope |
| `VPS_HOST` | VPS IP (194.238.24.254) |
| `VPS_USER` | SSH user (root) |
| `VPS_SSH_KEY` | SSH private key |

## VPS Setup

Before first deploy, create the per-env app folders and stage `.env` on the VPS
(CI ships only the compose file — see `docs/workflows.md` caller preconditions):
```bash
ssh contabo "mkdir -p /opt/YOUR_PROJECT_NAME/dev /opt/YOUR_PROJECT_NAME/prod"
scp .env contabo:/opt/YOUR_PROJECT_NAME/dev/
```

The compose file lives at `deploy/docker-compose.yml` in the repo and is deployed by CI.

## Endpoints

- Health: `https://your-app.enoughledger.com/health`
