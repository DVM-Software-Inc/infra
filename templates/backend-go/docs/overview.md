# Go Backend Template — DVM Software

- All code lives in `/src`.
- `main.go` is the entrypoint.
- HTTP server listens on port 8080.
- Health endpoint: `GET /health`.
- Dockerfile builds a static Go binary.
- docker-compose.yml exposes the service behind Traefik.
