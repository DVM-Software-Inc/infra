# DVM-Software-Inc Infrastructure Context

Use this prompt at the start of new sessions to provide context about our infrastructure.

## Quick Reference

### VPS
- IP: 194.238.24.254
- SSH: `ssh contabo`
- Platform: DokPloy + Traefik v3.5
- Apps folder: `/opt/apps/`

### Docker Network
- **Use `dokploy-network`** for all services (Traefik is on this network)
- Do NOT use `proxy` network

### CI/CD
- Reusable workflows in `DVM-Software-Inc/infra/.github/workflows/`
- `build.yml` → builds & pushes to ghcr.io/dvm-software-inc
- `deploy.yml` → SSH to VPS, docker compose pull & up
- Secrets: `GHCR_USERNAME`, `GHCR_TOKEN`, `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`
- Environments: `dev` (dev branch), `prod` (main branch)

### DNS
- Domain: `enoughledger.com` (Namecheap)
- Pattern: `app-name.enoughledger.com → 194.238.24.254`

### Project Templates
- Located at: `~/code/infra/templates/{go,python,typescript}/`
- Include: Dockerfile, docker-compose.yml, .github/workflows/ci.yml, .env.example

### Standard Ports
- Go: 8080
- Python (FastAPI/Uvicorn): 8000
- TypeScript (Node): 3000

## New Project Checklist

1. Copy template from `infra/templates/LANG/`
2. Create repo under DVM-Software-Inc
3. Add `dev` and `prod` environments with secrets
4. Create VPS folder: `ssh contabo "mkdir -p /opt/apps/PROJECT"`
5. SCP docker-compose.yml and .env to VPS
6. Add DNS A record
7. Push to main → auto deploys

## Traefik Labels (required)

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.NAME.rule=Host(`domain.enoughledger.com`)"
  - "traefik.http.routers.NAME.entrypoints=websecure"
  - "traefik.http.routers.NAME.tls.certresolver=letsencrypt"
  - "traefik.http.services.NAME.loadbalancer.server.port=PORT"
```

## Debugging

```bash
# SSH to VPS
ssh contabo

# Check container
docker ps | grep NAME
docker logs NAME -f

# Test internal connectivity
docker exec dokploy-traefik wget -qO- http://CONTAINER:PORT/health

# Check Traefik routing
docker logs dokploy-traefik 2>&1 | grep NAME
```
