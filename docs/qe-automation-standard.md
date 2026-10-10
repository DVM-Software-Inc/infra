# Quality Engineering (QE) automation standard

Established: 2026-09-17. Reference implementation: ChatActorAI.

## Purpose and scope

Give each application a repeatable way to verify its complete customer and
operator experiences, with useful evidence when a test fails. Reuse the testing
infrastructure and conventions; customize the journeys to the application's
business rules.

This is the default pattern for new web-application QE automation. It complements
the [base infrastructure conventions](../prompts/base.md), the selected
[app-type prompt](../prompts/README.md), and the applicable
[SaaS](../prompts/saas.md), [AI](../prompts/ai-product.md) and
[messaging](../prompts/messaging.md) requirements. It does not replace those
acceptance requirements or require existing applications to change their runtime.
Native, command-line and API-only applications retain suitable platform-specific
test tools while adopting the isolation, reporting and evidence conventions here.

ChatActorAI provides a working example, not an already extracted shared package.
Adoption by another application must be implemented and verified in that
application's repository.

## Technology responsibilities

| Technology | Responsibility |
|---|---|
| Playwright + TypeScript | Drive the actual browser, follow user journeys, assert visible outcomes and collect failure evidence. Default for new web browser suites. |
| Python | Orchestrate the disposable environment: allocate ports, generate test configuration, start services, migrate/seed prerequisites, invoke Playwright and clean up. Python does not drive the browser in this pattern. |
| Docker Compose | Run isolated dependencies such as the database, cache, identity provider and captured-email service. Test Compose files belong under `deploy/`. |
| Keycloak + Mailpit | Exercise real registration, verification and recovery against a disposable product realm and read the actual emails from a private test inbox. |
| Application-native test tools | Keep focused unit, component and integration tests alongside browser journeys. ChatActorAI uses pytest for its Python backend and Vitest for its frontend; other stacks use their own appropriate tools. |

Selenium is not part of the reference implementation. Existing suites can remain
in place; adopting this standard is not an instruction to rewrite working tests.
Use repository-approved runtime versions, lock dependencies and pin the browser
tool version. Record prerequisites in each application's test README.

## Test layers and what they establish

1. **Unit, component and integration tests:** cover business rules, permissions,
   calculations, event ordering, retries and failure cases in detail. Use these
   for broad combinations that would make browser tests slow or fragile.
2. **Disposable browser acceptance:** run the real application, authentication,
   database and workers through representative customer and operator journeys.
   Control paid/external vendor responses at their network boundary when needed
   for repeatability. Keep the product code and internal workflows real.
3. **Deployed-provider acceptance:** separately verify deployed identity settings,
   actual email delivery, social login, payment-provider test-mode checkout and
   webhook delivery, and live-provider behavior where relevant.

A successful fixture-based browser run does not prove external delivery or
production configuration. Report exactly which layer ran. Load testing, browser
and device compatibility, accessibility audits and backup/restore acceptance are
additional scopes; list the relevant coverage and remaining gaps explicitly.

## Reusable foundation and application-specific parts

| Reuse as the foundation | Customize for each application |
|---|---|
| Environment lifecycle, health waits and teardown | Service commands, migrations, schema and seed prerequisites |
| Unique run IDs, isolated ports and generated credentials | Environment variables, issuer/client configuration and tenant model |
| Playwright configuration, email lookup helpers and reporting | Routes, accessible controls, navigation and journey assertions |
| Captured inbox and provider-fixture patterns | Email templates, model protocols, payment contracts and expected events |
| Artifact conventions and manual CI workflow | Roles, permissions, business outcomes and supported browsers/devices |

Do not hide application-specific assumptions in a universal base class. Helpers
should express clear actions such as signing in, following a verification email
or starting a support session. Keep business assertions visible in the journeys.
Extract a shared library only after a second application demonstrates which
parts can be reused without product-specific branching.

Suggested layout, adapted to the repository's structure:

```text
tests/browser/
  README.md                 # setup, command, coverage and limits
  run.py                    # environment lifecycle and test entry point
  seed.py                   # platform prerequisites only
  cleanup.py                # application-specific temporary-file cleanup
  playwright.config.ts
  journeys.spec.ts           # may be split by independent journey
  providers.py              # controlled external-provider behavior, if needed
  fixtures/                 # synthetic documents and other test inputs
deploy/docker-compose.e2e.yml
.github/workflows/browser-e2e.yml
.runtime/e2e/<run-id>/       # ignored runtime state and reports
```

Expose one documented command from the repository root. In npm repositories:

```sh
npm run test:e2e
# Optional interactive diagnosis when implemented:
npm run test:e2e -- --headed
```

Repositories without npm can expose an equivalent script, such as
`./scripts/test-e2e.sh`, without changing their application toolchain. The command
must provision, execute, report and clean up, returning a nonzero exit status on
setup, test or required-cleanup failure.

## Required journey coverage

Maintain a coverage matrix in the application test README. Mark a capability
not applicable only with a reason; distinguish that from an unimplemented test.
These are minimum categories for applicable products, not a claim that the
reference implementation already covers every scenario below.

| Area | Required outcomes |
|---|---|
| Customer identity | Registration, verification, login, logout and password recovery. Follow real captured email links, reject the old password after reset, preserve the existing account and deny protected access after logout. Cover admission/waitlist and MFA flows when enabled. |
| Accounts and membership | Create or provision an account through its intended flow. Invite and activate members in the correct account. Check roles, duplicate handling and cross-account denial; cover suspension/reactivation and other supported lifecycle operations. |
| Core product value | Complete the main workflow from initial setup to a usable result, including persistence, background processing and a representative failure/recovery path. Assert the business result, not merely a successful request or an enabled button. |
| Operator identity and navigation | Use the operator's real login/recovery flow, reach the administration home, verify the permitted menu, and deny customer access to operator functions. Seed the initial authorized operator; public signup must never grant that role. |
| Operator management | Search/create/manage accounts as supported, verify statistics against test-created data, inspect memberships and activity, and check permission/reason/audit requirements for sensitive actions. |
| Support access | When supported, start purpose-bound access, show its scope, enforce read-only or explicitly granted permissions, and verify ending, expiry and revocation remove access. |
| Billing and entitlements | When enabled, verify paid, failed and recovered states in customer and operator views, invoice/payment history, aggregate totals, overdue counts and actual service access. Cover the product's checkout, renewal, cancellation, refund and dispute policies in the appropriate test layer. |
| Isolation and resilience | Verify unauthenticated, wrong-role and cross-tenant denial. Cover duplicate/out-of-order events, retries and provider outages through focused integration tests and representative browser recovery paths. |

Authentication remains the identity provider's responsibility. Browser tests
exercise that provider; applications must not add password-handling endpoints or
test-only authentication bypasses to make the suite easier.

For ChatActorAI, the core product journey is assistant creation, persona selection,
reference upload, worker ingestion, grounded preview, approval, publishing and a
conversation in the installed widget. Another product replaces those steps with
its own primary user outcome.

## Isolation and fixture rules

- Create a unique test environment per run: Compose project, database, realm,
  inbox, temporary files and build output. Bind laptop test services to loopback
  with allocated ports. These disposable dependencies are separate from the
  shared VPS deployment topology.
- Guard destructive setup and cleanup against non-test databases. Never reset a
  developer's existing account store, shared realm, shared cache or production
  data. Cleanup must target only resources owned by the run.
- Generate synthetic identities and secrets. Do not inherit real vendor
  credentials or send test mail to real customers. Keep secret-bearing runtime
  files private, ignore them in Git and exclude them from published artifacts.
- Seed only prerequisites such as plans, catalogs, provider configuration and an
  authorized operator. Create the customer, invitation, product data and other
  state being tested through the intended product workflows.
- Control external vendors at a documented boundary. For example, send signed
  payment events through the actual signature verifier, persistent inbox and
  worker; do not directly edit billing rows to simulate payment success.
- Make fixtures sensitive to the inputs that matter. A model fixture should fail
  when required reference/persona context is missing. An unconditional canned
  answer cannot establish that retrieval or context composition worked.
- Keep fixture endpoints outside the production application. Preserve normal
  authorization and TLS validation; trust an ephemeral local certificate within
  the test processes when required.
- Always attempt teardown after success, failure or interruption. An explicit
  debugging option may retain services, but must identify retained resources and
  explain how to stop them. Keep reports available after normal cleanup.

## Browser design and evidence

Use accessible roles, labels and stable user-facing controls. Add meaningful
accessible names where the product lacks them. Prefer Playwright's automatic
waiting and bounded polling of observable state to fixed delays. Do not weaken
production behavior or intercept internal application requests to force a pass.

Use API observations to corroborate browser outcomes, such as confirming the
account ID or an aggregate total. They must not replace a UI workflow the test
claims to exercise. Respect component encapsulation; the reference widget uses
Chromium's accessibility tree for its closed shadow root.

Keep independent journeys independently runnable where practical. If a sequence
intentionally shares state, declare it serial and document the dependency. When
an earlier step fails, report later dependent tests as skipped, never passed.
Record retries and flaky results rather than treating a retry as proof of
repeatability.

Each run must produce:

- Named journey steps and an HTML report readable by developers and operators.
- Machine-readable results such as JSON/JUnit, including failures and skips.
- Failure screenshots and browser traces; video and service logs where useful.
- The tested commit, environment mode, browser, fixture boundaries and coverage
  gaps in the QA record or CI metadata.

Protect artifacts containing cookies, tokens or personal data. Publish only
synthetic/sanitized evidence, exclude private runtime configuration, and apply a
bounded retention policy. The reference CI retains artifacts for seven days.

## Local checks and CI

Follow the [local-first CI policy](../prompts/base.md): run pre-merge checks locally;
new feature-branch and pull-request automation should not introduce automatic
workflow runs. Browser QE can use `workflow_dispatch`; any automatic runs must
remain within the approved main/release policy. Include concurrency cancellation,
a bounded timeout and artifact collection even on failure. Use Linux runners for
web suites unless a specific platform test requires otherwise.

The QE workflow runs tests and never deploys. Existing CI that predates the cost
policy is a separate retrofit; adding the QE guide or suite does not authorize an
unrelated migration of working workflows. Keep lint, type checks, unit/integration
tests and production builds appropriate to the application alongside browser QE.

## Adoption procedure and completion criteria

1. Inventory the application's roles, core workflows, dependencies and enabled
   capabilities. Create its coverage matrix, including deployed-provider gaps.
2. Adapt the reference runner, Compose dependencies and report conventions.
   Configure the application's own service commands, test realm and seed data.
3. Implement its customer journey, then its operator journey. Add negative role
   and tenant checks, and payment/service behavior when applicable.
4. Add provider fixtures with explicit contracts. Keep live-provider acceptance
   separate and use provider test mode for financial operations.
5. Run the whole command in a fresh environment, fix reproduced defects and add
   focused regressions. Repeat from another fresh environment to establish
   repeatability and verify cleanup.
6. Document prerequisites, one-command execution, supported platforms, artifact
   locations and unresolved acceptance work. Add the manual CI entry point.

An application has adopted this standard when its documented command succeeds
from a clean setup, applicable critical journeys pass, negative access checks
pass, reports identify untested/skipped scopes honestly, and teardown leaves
unrelated resources untouched. A green browser report alone is not production
release acceptance; applicable infrastructure and capability gates still apply.

## Reference implementation

Pinned ChatActorAI reference, commit
`72a16542bb2f3e2821f49c1c810b406574639090`:

- [Setup, scope and provider boundaries](https://github.com/DVM-Software-Inc/chatactorai/blob/72a16542bb2f3e2821f49c1c810b406574639090/tests/browser/README.md)
- [Python environment runner](https://github.com/DVM-Software-Inc/chatactorai/blob/72a16542bb2f3e2821f49c1c810b406574639090/tests/browser/run.py)
- [Playwright customer/operator journeys](https://github.com/DVM-Software-Inc/chatactorai/blob/72a16542bb2f3e2821f49c1c810b406574639090/tests/browser/journeys.spec.ts)
- [Disposable dependencies](https://github.com/DVM-Software-Inc/chatactorai/blob/72a16542bb2f3e2821f49c1c810b406574639090/deploy/docker-compose.e2e.yml)
- [Manual browser workflow](https://github.com/DVM-Software-Inc/chatactorai/blob/72a16542bb2f3e2821f49c1c810b406574639090/.github/workflows/browser-e2e.yml)
- [QA evidence and defects found](https://github.com/DVM-Software-Inc/chatactorai/blob/72a16542bb2f3e2821f49c1c810b406574639090/docs/reviews/browser-journey-qa-2026-09-17.md)

The pinned example exercises four desktop Chromium journeys. Its model responses
and payment-event origin are controlled; hosted checkout, Internet email delivery,
social login, pending waitlist approval and wider browser/device coverage remain
separate acceptance scopes. Copy its structure and verified patterns, then close
the gaps applicable to the adopting product.
