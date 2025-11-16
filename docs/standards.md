# Organization Standards

- Source code goes in `/src`.
- Backends listen on internal port 8080.
- Frontends listen on internal port 3000.
- Every repo includes:
  - `/docs/overview.md`
  - `Dockerfile`
  - `docker-compose.yml`
  - `.env.example`
  - `.github/workflows/ci.yml`
- CI/CD uses reusable workflows from this `infra` repo.
