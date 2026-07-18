# App type: frontend only

Read `base.md` first. For a web UI with no backend of its own (the API it talks to is
someone else's deployment, or there is none).

## Shape

Single container behind Traefik at `app.<domain>` (or the root domain):

- **Next.js** (default): standalone build per `fullstack.md`'s frontend section — container
  port 3000.
- **Pure static** (Vite/React SPA, docs sites): multi-stage build ending in
  `nginx:alpine` serving `/usr/share/nginx/html` — container port 80, Traefik
  `loadbalancer.server.port=80`.

## Rules

- API base URLs and other client config are baked at build time (`NEXT_PUBLIC_*` /
  `VITE_*` build args) → per-environment images tagged `:<env>`.
- A frontend-only container holds **no secrets** — anything in the bundle is public. If a
  secret seems needed (API keys, signing), the app has a backend: switch to `fullstack.md`.
- If login is required, don't implement auth in the SPA — front it with Authentik
  (forward-auth middleware or make it a Next BFF per `fullstack.md`).
- SPA fallback for client-side routing (nginx `try_files … /index.html`).
