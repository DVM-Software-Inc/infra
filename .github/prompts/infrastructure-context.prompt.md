# DVM-Software-Inc Infrastructure Context

> **Superseded (2026-07-18):** the canonical LLM context now lives in
> [`prompts/`](../../prompts/README.md) — load `prompts/base.md` plus the file matching
> the app type. The DokPloy / `dokploy-network` / `/opt/apps/PROJECT` (flat) /
> `enoughledger.com` setup formerly described here no longer exists.

Quick facts (kept for grep-ability; details in `prompts/base.md`):

- VPS: Contabo `194.238.24.254`, `ssh contabo`; Traefik v3 + Let's Encrypt on the
  `web-public` overlay network; shared Postgres at alias `postgres:5432`.
- Apps deploy to `/opt/apps/<slug>/<env>/` via the reusable workflows
  (`build.yml` + `deploy.yml`) in this repo.
- `main` → dev auto-deploy; prod via manual `workflow_dispatch` (protected environment).
- Each product owns its root domain; `*.dvmsoftware.com` is for internal utilities.
- Secrets: Vaultwarden (`vault.dvmsoftware.com`) → GitHub environment secrets. Never in repos.
