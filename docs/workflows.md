# CI/CD Workflows

Shared workflows in `.github/workflows`:

- `build-and-push.yml` — build Docker image and push to GHCR
- `deploy.yml` — deploy via SSH to VPS, run docker compose
- `lint.yml` — placeholder for linting
- `tests.yml` — placeholder for tests
- `env-map.yml` — map environment to secrets

Application repos call them via:

```yaml
jobs:
  build:
    uses: DVM-Software-Inc/infra/.github/workflows/build-and-push.yml@main
```
