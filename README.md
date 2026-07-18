# DVM Software — Infra Repository

The platform backbone for all DVM-Software projects:

- **`prompts/`** — canonical per-app-type LLM context (`base.md` + one type file). Start here.
- `.github/workflows/` — shared reusable CI/CD workflows (`build.yml`, `deploy.yml`)
- `templates/` — project starters (FastAPI, Go, Python, TypeScript) wired to the reusable workflows
- `docs/` — org conventions (branching, environments, standards, workflow contract)
- `docker-templates/` — ⛔ legacy, do not copy from (see `docs/docker-templates.md`)

Live-VPS operational docs (deploy runbook, services registry, secrets, DNS) live in
`~/code/vps_deploy/` (`DEPLOY_UTILITY.md` + `infra_llm/`), which wins on conflict.
