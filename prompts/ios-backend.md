# App type: iOS + backend

Read `base.md` + `ios.md` first; the backend follows `backend.md`. This file defines only
the contract between the two. Pattern proven by `health` (ItHurtsDoctor).

## Repo shape — one monorepo

```
ios/<AppName>/        # XcodeGen app project (per ios.md)
ios/<KitName>/        # local SwiftPM package holding the APIClient + shared models
backend_fastapi/      # FastAPI backend (per backend.md; deployable via base.md)
deploy/docker-compose.yml
docs/overview.md
```

The API client never lives in the app target — it goes in the SwiftPM kit so it's
unit-testable without a simulator.

## Environment wiring (the core contract)

The backend base URL flows **xcconfig → project.yml → Info.plist → runtime config**:

| Build config | `BACKEND_BASE_URL` |
|---|---|
| Debug | `http://127.0.0.1:<port>` (local backend) |
| Staging | `https://staging.api.<domain>` (VPS `dev` env) |
| Release | `https://api.<domain>` (VPS `prod` env) |

Runtime resolution order in the app (a small `AppRuntimeConfig`):
`Info.plist["BACKEND_BASE_URL"]` → `BACKEND_BASE_URL` process env override (for tests/CI)
→ compiled default. Never scatter URL literals through the code.

- iOS Staging ↔ VPS `dev`, iOS Release ↔ VPS `prod`. Backend host DNS follows `base.md`
  (per-product root domain).
- Debug builds may talk to `http://127.0.0.1` only via a scoped ATS exception — never
  disable ATS globally, never ship an ATS exception in Release.

## API contract

- Versioned paths: `/api/v1/…`; `GET /health` unauthenticated.
- Mobile clients authenticate with app-issued tokens (or attestation-based anonymous
  tokens for privacy-first apps) — not session cookies. Human/admin surfaces still use
  Authentik per `base.md`.
- Client credentials/config the app needs at runtime come from build-config values or
  Keychain — never committed. Breaking API changes require a new `/api/v2`, since old app
  builds stay in the field.

## CI

One workflow, parallel jobs: backend tests (pytest, service containers as needed), SwiftPM
kit `swift test`, `xcodebuild test` on a simulator (per `ios.md`), then the build/deploy
jobs from `base.md` for the backend only. iOS release automation: not yet standardized —
ask, don't invent.
