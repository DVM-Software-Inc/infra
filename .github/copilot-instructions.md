# DVM-Software-Inc Development Guidelines

## Infrastructure Overview

### VPS (Contabo)
- **IP**: 194.238.24.254
- **SSH**: `ssh contabo` (configured in ~/.ssh/config)
- **User**: root
- **Platform**: DokPloy (Docker Compose management)

### Reverse Proxy (Traefik)
- Traefik v3.5 runs as `dokploy-traefik`
- **Network**: All services must use `dokploy-network` (NOT `proxy`)
- SSL via Let's Encrypt with `letsencrypt` certresolver
- Entrypoints: `websecure` (443), `web` (80)

### Container Registry
- **Registry**: ghcr.io/dvm-software-inc
- **Auth**: PAT with `write:packages` scope stored as `GHCR_TOKEN`

### DNS
- Domain: `enoughledger.com` (managed in Namecheap)
- Wildcard or per-app A records pointing to 194.238.24.254

## CI/CD Pipeline

### Reusable Workflows (infra repo)
Located in `DVM-Software-Inc/infra/.github/workflows/`:

1. **build.yml** - Builds and pushes Docker image to GHCR
2. **deploy.yml** - SSHs to VPS and runs `docker compose pull && up -d`

### Required Secrets (per repo, per environment)
| Secret | Value |
|--------|-------|
| `GHCR_USERNAME` | DVM-Software-Inc |
| `GHCR_TOKEN` | PAT with write:packages |
| `VPS_HOST` | 194.238.24.254 |
| `VPS_USER` | root |
| `VPS_SSH_KEY` | SSH private key (ed25519) |

### Environments
- `dev` - for dev branch deploys
- `prod` - for main branch deploys

## Project Setup Checklist

When creating a new project:

1. **Copy template** from `infra/templates/{go,python,typescript}/`
2. **Create GitHub repo** under DVM-Software-Inc
3. **Add environments** (Settings → Environments → New: `dev`, `prod`)
4. **Add secrets** to each environment (see table above)
5. **Create VPS folder**: `ssh contabo "mkdir -p /opt/apps/PROJECT_NAME"`
6. **Copy docker-compose.yml and .env** to VPS
7. **Add DNS record** in Namecheap: `app-name.enoughledger.com → 194.238.24.254`
8. **Push to main** to trigger deploy

## Docker Compose Template

```yaml
services:
  api:
    image: ghcr.io/dvm-software-inc/PROJECT_NAME:latest
    container_name: PROJECT_NAME
    env_file:
      - .env
    networks:
      - dokploy-network  # IMPORTANT: must be dokploy-network
    restart: always
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.PROJECT_NAME.rule=Host(`${APP_DOMAIN}`)"
      - "traefik.http.routers.PROJECT_NAME.entrypoints=websecure"
      - "traefik.http.routers.PROJECT_NAME.tls.certresolver=letsencrypt"
      - "traefik.http.services.PROJECT_NAME.loadbalancer.server.port=8080"

networks:
  dokploy-network:
    external: true
```

## Common Issues

### 504 Gateway Timeout
- Check container is on `dokploy-network` (not `proxy`)
- Verify container is running: `docker ps`
- Check Traefik can reach container: `docker exec dokploy-traefik wget -qO- http://CONTAINER:PORT`

### SSL Certificate Errors
- Ensure DNS is configured and propagated
- Check Traefik logs: `docker logs dokploy-traefik 2>&1 | grep ACME`

### Push to GHCR Denied
- Verify PAT has `write:packages` scope
- Check `GHCR_TOKEN` secret is set in the environment

## Local Development

- **SSH to VPS**: `ssh contabo`
- **View logs**: `docker logs CONTAINER_NAME -f`
- **Restart**: `cd /opt/apps/PROJECT && docker compose up -d --force-recreate`
