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
- [ ] DVM Fullstack: apply the same contract to its public and authenticated pages and operator console.
- [ ] Review the inventory of other customer-facing web SaaS apps before each release; each must either pass this acceptance suite or record a justified non-SaaS exception.
