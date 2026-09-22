# Web SaaS service-notice standard

Every customer-facing DVM web SaaS application must support a site-wide service notice at launch. The app owns its notice records and operator controls; no new central service is required for a small portfolio. ChatActorAI's `docs/service-notices.md` is the first implementation and acceptance example. A shared component/package is worth extracting only after a second app proves the same contract.

## Required behavior

- Authorized operators can create, edit, and disable notices for planned maintenance, degraded service, and general information. Record who changed the notice, when, and why in the app audit log. Customer roles cannot publish notices.
- A notice has plain-text message, kind, required timezone-aware `starts_at` and `ends_at`, optional estimated resolution `eta_at`, and an enabled flag. Validate `starts_at < ends_at`. Store UTC timestamps. Never put secrets or customer-specific facts in the public notice.
- Public reads return only enabled notices where `starts_at <= server_now < ends_at`. The response is safe without authentication and uses no-store caching. Frontends refresh when focused and at least every 30 seconds, while removing expired notices locally without waiting for a network response.
- The banner appears above authenticated, sign-in, and public/marketing pages. Make degraded-service notices accessible as alerts and ordinary notices as status messages. Show ETA when supplied. Do not allow dismissing an active critical notice by default.
- Operators can revise the ETA/end time and disable a notice immediately. Retain expired and disabled records for audit. A full app/API outage requires an external status channel; an in-app banner alone cannot announce it.

## QE acceptance

Test future start, exact start, just before end, exact end, disabled, edit/extension, stale browser data, public read without login, customer write denial, operator audit trail, and accessibility. Exercise the same cases in each web SaaS app's E2E suite and use the app's own operator dashboard to schedule a maintenance notice before launch.

## Future release: multi-language

Add supported locale selection, fallback, translated UI/public/help/billing/support copy, localized service-notice text, email templates, and locale-aware dates/numbers/currencies. Keep a single notice window and localized variants for its text. Add QE journeys and accessibility checks per supported locale. This is a portfolio backlog item, not a launch gate for the current English-language releases.

## Rollout tracking

- [x] ChatActorAI: first implementation prepared; merge and deployed acceptance remain.
- [x] DVM Fullstack: implementation prepared in `DVM-Software-Inc/dvm-fullstack#35`; merge and deployed acceptance remain.
- [x] EnoughLedger (`smb-tax`): implementation prepared in `DVM-Software-Inc/smb-tax#5`; configure operator IDs, merge, migrate, and complete deployed acceptance.
- [ ] Confirm the remaining candidate inventory against the live deployment registry: `cc_dvm`, `gelopreto`, `contextorai`, `estimator`, `buildfoundry`, `dvm-architect`, `builtdvm`, and `knowingbest` (which may have only an internal web admin). This list is an initial repository scan, not a claim that every product is active or customer-facing.
- [ ] Before each release, record whether that web app passes this acceptance suite or has a justified non-SaaS/non-customer-facing exception. Add newly deployed products to the inventory.
