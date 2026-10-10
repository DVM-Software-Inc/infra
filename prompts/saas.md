# SaaS customer-management overlay

Use this file **in addition to** `base.md` + the selected app-type prompt whenever a
product manages customer accounts, organizations, invitations, subscriptions,
entitlements, support access, paid usage, or customer lifecycle operations.

ChatActorAI is the reference implementation for the capability set, not a package to
copy wholesale. Reuse contracts and proven patterns; keep product-specific chatbot/RAG
logic in ChatActorAI. Enable billing, paid AI, support, and messaging modules only when
the product needs them—a solo-developer business should not operate speculative systems.

## Responsibility boundaries

| Concern | Owner |
|---|---|
| Human authentication, verification, recovery, MFA, social identity | The product environment's Keycloak realm |
| Local user record, organizations, memberships, product/platform roles | The application |
| Plans, prices, subscriptions, entitlements, invoices, credits | The application, synchronized with the payment processor |
| Authenticated customer-to-business conversations | Shared DVM Messaging API per `messaging.md` |
| Operator workflows, support access, reasons, audit trail | The application administration API/UI |
| Model/provider policy, AI budget, reservation, usage and cost | Application/shared AI control layer per `ai-product.md` |

Keycloak authenticates a person; it does not decide which customer organization they
belong to, what they purchased, whether they may administer the platform, or how much AI
budget remains. A realm represents a product environment, never one customer.

## Identity and customer model

- Give every local user an application-generated stable ID. Store external identities
  separately and uniquely by `(issuer, subject)`; do not use email or `subject` alone as
  the permanent external key.
- Require a verified email before email-based first binding, invitation acceptance, or
  linking to an existing local user. Define collision/recovery behavior rather than
  silently relinking identities.
- Use `organization` (or tenant/account), `membership`, and membership-role records.
  A person can belong to more than one organization without duplicating their identity.
- Separate customer roles from platform-operator roles. Product registration never
  grants platform administration. Centralize permission checks server-side.
- Bind tenant context from the verified session/token and membership lookup. Never trust
  a request body's tenant ID as authorization.
- For PostgreSQL multi-tenancy, prefer tenant keys plus `FORCE ROW LEVEL SECURITY` when
  the product's data model supports it. Set/reset tenant context transaction-locally;
  jobs, exports, webhooks, caches, and object storage need the same boundary.
- Define suspension, reactivation, export, retention, and deletion behavior. Identity,
  billing, audit, and legally required financial records can have different lifecycles.

## Administration panel: required capability set

Customer-management products ship an operator UI backed by an explicit administration
API. Routine operations must not require direct production SQL or editing payment
provider data by hand.

At minimum, provide the applicable views and actions:

- customer and organization search, status, memberships, roles, identity bindings, and
  recent security events;
- plan, subscription, entitlement, invoice/payment/refund/dispute, credit, and usage
  history when billing exists;
- webhook inbox state, failures, safe replay, and reconciliation status for each
  external system;
- support conversations and time-bounded support-session access when required;
- AI provider/model status, per-customer usage/cost, reservation/settlement failures,
  and budget controls when managed AI exists;
- audit history showing actor, target, action, reason, timestamp, correlation ID, and
  outcome.

Every mutating operator action must:

1. require a named server-side permission;
2. require a reason for sensitive actions;
3. be idempotent where retries are possible;
4. emit an append-only audit event with before/after identifiers or a safe diff;
5. avoid logging secrets, tokens, full payment data, or unnecessary message content;
6. return a clear, actionable result to the operator.

High-risk actions—platform-role grants, account takeover/support session, refunds,
manual credits, subscription overrides, destructive deletion, and provider/model
changes—need reauthentication or MFA policy where supported and a distinct audit event.
Do not build a generic “act as customer” bypass. Support access must be purpose-bound,
time-limited, visible, revocable, and unable to reveal credentials or payment secrets.

## Billing and entitlements

Only add billing when the product has a paid offer. Keep commercial truth explicit:

- Plans describe the offer; versioned prices describe currency, interval, amount, tax
  behavior, and effective dates. Never overwrite historical price meaning.
- The payment processor owns payment execution. The application owns product
  entitlements and a durable mapping to processor customer/subscription/payment IDs.
- Treat webhooks as an inbox: verify signatures against the raw request, persist the
  event ID/body metadata, enforce uniqueness, process asynchronously where practical,
  and record attempts/outcomes. Delivery can be duplicated, delayed, or reordered.
- Derive entitlement changes idempotently and tolerate out-of-order events. Provide safe
  replay plus scheduled reconciliation against processor state.
- Separate money records, entitlement records, and usage/credit ledgers. Corrections are
  append-only adjustments, not silent balance rewrites.
- Define renewal, failed payment, grace, cancellation, downgrade, refund, partial refund,
  dispute, and account-suspension semantics before enabling checkout.
- Launch with included/prepaid allowances before postpaid usage overage unless strong
  demand justifies the collection and credit risk.
- Place the processor behind a small internal boundary—customer, checkout, subscription,
  refund, webhook verification/retrieval. Do not build a universal abstraction for a
  hypothetical second provider.

## Messaging and customer interaction

- Use the shared Messaging API for authenticated user-to-business communication. Product
  code and secrets do not contain Chatwoot credentials or inbox IDs.
- Register exact product issuer/audience mappings. The messaging platform verifies the
  product, environment, tenant membership, subject, and conversation context; accepting
  “any valid Keycloak token” would recreate a cross-product trust boundary.
- Keep support messaging distinct from a product's AI chatbot or RAG feature. A support
  conversation can use AI-assisted drafts under `ai-product.md`, but the customer must
  know when they are interacting with automation and how to reach a person where offered.
- Define notification delivery, retry, unread/read state, retention, export, deletion,
  and abuse/rate-limit behavior.

## Operations and recovery

- Health/readiness checks cover application dependencies without exposing customer data.
  Alert on failed webhook backlog, reconciliation drift, payment/entitlement mismatch,
  invitation/verification failure spikes, audit-write failure, and AI reservation leaks.
- Use structured correlation IDs across request, webhook, payment, entitlement, message,
  and AI-usage records.
- Back up and restore-test customer, billing, entitlement, audit, and identity-link data.
  A Keycloak realm replay does not restore application customer state.
- Keep an emergency kill switch for checkout and managed AI spend without disabling
  customer access to existing data. Prefer read-only/degraded behavior over a total
  outage.
- Publish customer-visible policy and behavior that match the code: price, limits,
  cancellation, refund, retention, AI use, and support expectations.

## Minimum acceptance suite

- [ ] Fresh Keycloak identity binds to the intended local user and organization; an
      unverified/mismatched identity cannot capture an invitation or existing account.
- [ ] Customer, tenant-admin, support-operator, billing-operator, and platform-admin
      permissions have positive and negative tests.
- [ ] Tenant A cannot read, mutate, export, cache-hit, enqueue, or receive Tenant B data.
- [ ] Invitation, suspension/reactivation, role change, export, and deletion/retention
      flows behave as documented.
- [ ] Duplicate/out-of-order webhook, failed renewal, cancellation/downgrade, refund,
      dispute, safe replay, and reconciliation tests pass when billing is enabled.
- [ ] Operator mutations require permission/reason and leave a usable audit trail;
      support access expires and is visible/revocable.
- [ ] Messaging issuer/audience/tenant/context negatives pass when messaging is enabled.
- [ ] AI budget, reservation/settlement, provider outage, and cost reconciliation gates
      in `ai-product.md` pass when managed AI is enabled.
- [ ] Backup restore proves customer access, entitlements, audit evidence, and external
      reconciliation—not merely that tables exist.

## Solo-developer cost rule

Start with one application service boundary and one administration surface. Package a
shared module only after ChatActorAI and at least one second product prove the same
contract. Prefer configuration and small adapters over a new microservice. Automate
reconciliation, support summaries, anomaly triage, and safe operator drafts before
adding headcount-like infrastructure; retain human confirmation for financial,
permission, identity-linking, and destructive decisions.
