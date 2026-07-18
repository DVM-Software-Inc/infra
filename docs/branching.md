# Branching Strategy

One long-lived branch, deliberate promotion (canonicalized 2026-07-18; the old
`dev`-branch model is retired):

- Feature branches (`feat/<short-name>`) branch from `main`, merged via PR.
- **Push to `main` → auto-deploys the `dev` environment.**
- **Prod is never deployed by a branch push** — promote via `workflow_dispatch`
  (environment: `prod`) on the same commit, gated by the protected `prod` GitHub
  environment (required reviewers).
- Hotfixes: branch from `main`, PR, merge (deploys dev), then dispatch to prod.
