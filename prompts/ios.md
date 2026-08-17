# App type: iOS only

Conventions proven by `health` (ItHurtsDoctor). No VPS footprint → `base.md` not required.
`messaging.md` is still required: an iOS app with authenticated user-to-business messaging
uses the shared public Messaging API and never bundles Chatwoot/provider credentials.

## Project setup

- **XcodeGen is the source of truth**: the `.xcodeproj` is generated from
  `ios/<AppName>/project.yml` and never hand-edited (regenerate with `xcodegen generate`;
  keep the generated project out of code review).
- SwiftUI, Swift 6, deployment target iOS 17+, `TARGETED_DEVICE_FAMILY: "1,2"`.
- Bundle id: `com.<product>.app` (product-branded, not com.dvmsoftware).
- Repo layout: `ios/<AppName>/` for the app; shared/reusable logic (API clients, models,
  sanitizers) lives in **local SwiftPM packages** beside it (`ios/<KitName>/`) with zero
  external dependencies unless justified — packages get `swift test`-able unit coverage.

## Build configurations = environments

Three configs mapped in `project.yml` (`Debug: debug`, `Staging: release`,
`Release: release`) with one xcconfig each under `Configs/`:
`Debug.xcconfig`, `Staging.xcconfig`, `Release.xcconfig`. Environment-dependent values
(server URLs, flags) live in the xcconfigs, flow through `project.yml` into Info.plist,
and are read at runtime from `Bundle.main` — never hardcoded in Swift. (In xcconfig, write
URLs as `https:/$()/host` so `//` isn't parsed as a comment.)

## Persistence & privacy defaults

- Local-first: **SwiftData** `@Model` + `ModelContainer` (explicit Application Support
  store URL, `cloudKitDatabase: .none` unless sync is a product requirement).
- No cloud storage of user data and no login by default; every `NS*UsageDescription` the
  app needs goes in Info.plist via `project.yml`.

## CI (GitHub Actions, `macos-latest`)

Triggers follow the org CI cost policy (`base.md`): **`workflow_dispatch` only** — never
push/PR triggers (macOS runners are ~10× ubuntu; pre-merge checks run locally with
`xcodegen generate` + `swift test` + `xcodebuild test`), plus `v*` tags once a release
process exists. Include the standard `concurrency` block. Job steps:

```yaml
- brew install xcodegen && xcodegen generate   # in ios/<AppName>/
- swift test                                    # each local SwiftPM package
- xcodebuild -scheme <AppName> -destination 'platform=iOS Simulator,name=<current iPhone>' test
```

Pin a simulator name with a fallback that picks any available iPhone; gather coverage in
the scheme (`gatherCoverageData: true`); tests target required from day one.

## Not yet standardized (do NOT invent)

Code signing, TestFlight/App Store release automation (fastlane vs Xcode Cloud), and
widget/watch targets have **no org convention yet**. If the task needs them, say so and ask
the operator rather than picking a tool.
