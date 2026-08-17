# App type: macOS app

Conventions proven by `talk2me` (menu-bar push-to-talk dictation). A macOS app itself has
no VPS footprint — add `base.md` + `frontend.md` only if the repo also ships a marketing
site, and `base.md` + `backend.md` if it gains a server component.

Read `messaging.md` even when `base.md` does not apply. Authenticated user-to-business
messaging uses the shared public Messaging API; a native app never contains Chatwoot or
notification-provider credentials.

## Repo shape — SwiftPM-first monorepo

For utilities and menu-bar apps, **SwiftPM is the project system** — no `.xcodeproj`, no
XcodeGen on the macOS side (an Xcode project is added later only when archiving/notarization
demands it):

```
Package.swift            # swift-tools 5.9+, platforms .macOS(.v13)+ (+ .iOS if shared)
Sources/<Product>Core/   # portable library: ALL logic lives here, unit-tested
Sources/<Product>/       # thin AppKit executable (the app)
Sources/<Product>Smoke/  # optional CLI for exercising providers/APIs without hardware
Tests/<Product>CoreTests/
ios/                     # optional companion iOS app: XcodeGen per ios.md,
                         #   consuming the root package (packages: <Core>: path: ..)
web/                     # optional marketing site → frontend.md + base.md apply
scripts/                 # build-app.sh, check.sh, acceptance scripts
docs/                    # all plans, specs, status/continuation notes live here
```

The core/app split is the load-bearing rule: the app target stays a shell so logic is
testable with `swift test` and reusable by the iOS app and CLI.

## App conventions

- Menu-bar/background utilities are **AppKit accessory apps**: `LSUIElement=true` in a
  hand-maintained `Resources/Info.plist` that the build script copies into the bundle.
  (SwiftUI is the default only for windowed apps and the iOS companion.)
- Bundle id `com.<product>.app` (matching `ios.md`). Existing deviations
  (`com.marcusc.Talk2Me`, `com.dvmsoftware.talk2me`) are legacy — don't copy them.
- Every capability gets its `NS*UsageDescription` (microphone, input monitoring, Apple
  events, speech recognition, …). Runtime-only grants (Accessibility) are checked at use
  time with a graceful fallback (e.g. clipboard fallback when auto-paste isn't trusted) —
  never hard-fail on a missing permission.
- Prefer Apple frameworks (Speech, AVFoundation, Foundation Models) and plain HTTPS to
  provider APIs over bundling third-party AI/audio libraries; zero external SwiftPM
  dependencies is the default posture.

## Config & secrets

- Runtime config is a JSON file at `~/Library/Application Support/<Product>/config.json` —
  providers, models, endpoints. **Secrets (API keys) live only in the macOS Keychain**,
  never in the config file, never in the repo.
- CLI/tests take env-var overrides named `<PRODUCT>_*` (e.g. `TALK2ME_PROVIDER`,
  `TALK2ME_API_KEY`) so smoke tests run headless.

## Build, sign, verify

- Build: `swift build -c release`; `scripts/build-app.sh` assembles `build/<Product>.app`
  and codesigns with a documented identity chain: `CODE_SIGN_IDENTITY` env → Apple
  Development → Developer ID Application → local dev cert → ad-hoc. A
  `<PRODUCT>_REQUIRE_STABLE_SIGNING=1` flag must forbid the ad-hoc fallback for any build
  that leaves the machine.
- `scripts/check.sh` (build + `swift test`) is the pre-commit gate; keep acceptance/smoke
  scripts beside it. **It is the only per-commit gate — CI never runs on pushes or PRs.**
- CI follows the org CI cost policy (`base.md`; retrofit via
  `prompts/gha-cost-optimization.md`) — macOS runner minutes are ~10× ubuntu, so:
  - `verify.yml`: **`workflow_dispatch` only**, `macos-latest`, runs `scripts/check.sh`.
    No packaging, no artifacts.
  - `release.yml`: `workflow_dispatch` + `push: tags: ["v*"]`, `macos-latest` — clean
    build, sign, package, publish (contents per repo until distribution is
    standardized, below).
  - Both carry the standard `concurrency` block; any job that doesn't need Xcode/AppKit
    (lint, docs, web/) runs on `ubuntu-latest`.

## Not yet standardized (do NOT invent)

Distribution is deliberately open: Developer ID notarization, DMG/zip packaging, Sparkle
updates, App Store sandboxing/entitlements, and the Apple developer team to sign under
have **no org convention yet**. If a task needs any of these, surface the decision to the
operator instead of picking a tool. (Current state: no entitlements, no sandbox, no
notarization — local/dev distribution only.)
