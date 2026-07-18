# Repository Conventions

## Product monorepos (default for apps)

A product ships from **one repo named after the product** (e.g. `chatactorai`, `health`),
containing all its deployables:

- Fullstack web: `apps/api/` + `apps/web/` + `packages/*` (npm workspaces) — see
  `prompts/fullstack.md`
- iOS + backend: `ios/<AppName>/` + `ios/<KitName>/` + `backend_fastapi/` — see
  `prompts/ios-backend.md`

Images are suffixed per service: `ghcr.io/dvm-software-inc/<repo>-api`, `<repo>-web`.

## Single-component repos

When a repo is genuinely one component, prefix by kind and stack:

- Backends: `backend-go-<name>`, `backend-fastapi-<name>`, `backend-dotnet-<name>`, `backend-django-<name>`
- Frontends: `frontend-nextjs-<name>`, `frontend-svelte-<name>`, `frontend-vue-<name>`, `frontend-angular-<name>`

The repo name doubles as the image name and the `/opt/apps/<slug>/` deploy slug.
