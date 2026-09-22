# Web SaaS service-notice standard

Every customer-facing DVM web SaaS application must support a site-wide service notice at launch. The app owns its notice records and operator controls; no new central service is required for a small portfolio. ChatActorAI's `docs/service-notices.md` is the first implementation and acceptance example. The first four implementations use different app stacks, so keep the HTTP/data/QE contract shared; extract a framework-specific UI package only where multiple apps truly share that framework and component lifecycle.

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
- [x] ContextorAI: implementation prepared in `DVM-Software-Inc/contextorai#3`; provision Authentik service-operator group, merge, migrate, and complete deployed acceptance.
- [ ] DVM Architect: customer-facing architecture workspace live in dev; next implementation candidate. Its current local checkout has an in-progress platform-admin change, so reconcile the operator authorization boundary before preparing its notice PR.
- [ ] BuildFoundry: web SaaS foundation in dev. Add notices before a customer-facing release, after its operator access is finalized.
- [ ] Estimator: pre-deploy skeleton (no DNS/DB/OIDC provisioned). Add notices before launch rather than treating its scaffold as a live rollout target.
- [ ] KnowingBest: iOS customer app with staff-only web moderation console. Revisit when an end-user web experience ships; mobile service messaging needs a separate product requirement.
- [x] Scope review: `cc_dvm` and Gelopreto are internal operator tools; `builtdvm` is a static product site, not a web SaaS. They are not customer-facing launch gates under this standard. Reassess if their audience changes.
- [ ] Before each release, record whether that web app passes this acceptance suite or has a justified non-SaaS/non-customer-facing exception. Add newly deployed products to the inventory.
