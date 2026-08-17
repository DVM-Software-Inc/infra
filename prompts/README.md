# LLM prompts by app type

Drop-in context files that make any LLM session (Claude Code, Codex, Copilot, …) follow the
DVM-Software deployment conventions without re-explanation. Every application also reads
`messaging.md`; it defines the mandatory shared path for authenticated user-to-business
communication.

## How to use

In an app repo, include **`messaging.md` plus `base.md` + exactly one type file** as agent
context. Native-only repositories that do not use `base.md` still include `messaging.md`:

- Copy them into the repo (e.g. `docs/llm/`) and reference them from `CLAUDE.md` / `AGENTS.md`, or
- Paste their content directly into the repo's `CLAUDE.md`.

| Your app is… | Use |
|---|---|
| Backend only (FastAPI, Go, Node API) | `base.md` + `backend.md` |
| Frontend (React/Next) + backend (FastAPI) | `base.md` + `fullstack.md` |
| Frontend only (static or Next) | `base.md` + `frontend.md` |
| iOS only | `ios.md` (base not needed — no VPS footprint) |
| iOS + backend | `base.md` + `ios-backend.md` |
| macOS app (menu-bar/desktop) | `macos.md`; add `base.md` + `frontend.md` if it ships a marketing site, `base.md` + `backend.md` if it has a server |

`messaging.md` does not require every app to display a message composer. It requires every
app that does support authenticated user-to-business communication to use the shared DVM
Messaging API instead of Chatwoot or an app-local messaging engine.

Cross-cutting task prompts (not app-type context — run them as one-off agent tasks):

- `gha-cost-optimization.md` — audit and rewrite a repo's workflows to the org CI cost
  policy: no automatic workflows on feature branches/PRs, automatic only on `main` and
  `v*` tags, concurrency everywhere, macOS runners only where required.

## Delivery mechanisms

- **Locally (primary):** the `dvm-app-conventions` skill (`~/.claude/skills/`) auto-routes
  any app-repo session to these files, and each app repo's `CLAUDE.md` declares
  `App type: <type>` with a pointer here. One canonical copy, no vendored drift.
- **Cloud/CI/other tools:** vendor copies into the repo (`docs/llm/`) with a
  `<!-- copied from infra@<commit> -->` header, referenced from `CLAUDE.md`/`AGENTS.md`.

## Precedence & maintenance

Source-of-truth order when these files disagree with reality:

1. The live VPS (`ssh contabo`) and what's actually running
2. `~/code/vps_deploy/DEPLOY_UTILITY.md` + `~/code/vps_deploy/infra_llm/docs/`
3. These prompt files
4. Anything else in this repo (`docker-templates/` is legacy — never copy from it)

If you find a mismatch, fix the doc as part of your work. These files decay otherwise.

Conventions here were canonicalized 2026-07-18 from the live apps (`chatactorai`,
`health`) plus the infra docs; earlier DokPloy-/`dvm_traefik`-era material is obsolete.
