# Organization Standards

- Source code goes in `/src` (monorepos: `apps/<service>/src`, packages in `packages/`).
- Internal container ports (Traefik `loadbalancer.server.port` must match; never publish
  host ports):
  - FastAPI/uvicorn: **8000**
  - Go: **8080**
  - Node/Next frontends & APIs: **3000**
  - Static (nginx): **80**
- Every server-deployed repo includes:
  - `/docs/overview.md` (hosts, services, env vars — what an agent can't infer)
  - `Dockerfile` per deployable service
  - `deploy/docker-compose.yml` (must set a unique top-level `name: <slug>-<env>`)
  - `.env.example` — variable names + Vaultwarden item references, never values
  - `.github/workflows/ci.yml` calling the reusable workflows from this repo
- iOS repos follow `prompts/ios.md` (XcodeGen, xcconfig-per-environment, SwiftPM kits).
- macOS repos follow `prompts/macos.md` (SwiftPM-first, core/app split, Keychain secrets).
- Full per-app-type conventions: **`prompts/`** in this repo — `base.md` + one type file
  is the canonical context to give any LLM session.
