# LLM Instructions for DVM-Software

**Canonical agent context lives in [`prompts/`](../prompts/README.md): give every LLM
session `prompts/base.md` + the one file matching the app type** (backend, fullstack,
frontend, ios, ios-backend). This file is just the short version:

- Source code in `/src`; do not invent new top-level folders.
- Internal ports: FastAPI 8000, Go 8080, Node/Next 3000 (container-internal only).
- Dockerfiles and compose files already exist: update, don't rewrite from scratch.
- Compose files live under `deploy/` with a unique top-level `name: <slug>-<env>`.
- CI/CD uses the reusable workflows from this `infra` repo (`build.yml` + `deploy.yml`);
  never hand-roll scp/ssh deploy jobs.
- `main` → auto-deploy dev; prod only via manual `workflow_dispatch` (protected environment).
- Secrets: values only in Vaultwarden / GitHub environment secrets — never in the repo or chat.
- Every project includes `/docs/overview.md` with project-specific details.
- Do not copy from `docker-templates/` — it predates the live conventions.
