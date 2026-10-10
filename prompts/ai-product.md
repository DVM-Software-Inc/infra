# AI/LLM product overlay — quality and cost

Use this file **in addition to** the app-type prompt when an application exposes an
LLM/AI workflow or the business pays for model inference on a customer's behalf. The
standard applies across providers; do not hardcode one vendor into product policy.

The goal is not “use AI everywhere.” Use it where probabilistic language/vision reasoning
improves a customer outcome enough to justify cost, latency, privacy risk, and operational
work. Authentication, authorization, tenant isolation, money math, entitlements,
migrations, and destructive actions remain deterministic.

## Where AI can create an advantage

Prioritize workflows with measurable leverage:

- extraction/classification from messy domain documents, images, audio, or messages;
- grounded answers and explanations over customer-authorized sources;
- drafting support replies, summaries, next actions, and operator incident triage;
- translating expert intent into a reviewable structured plan or configuration;
- developer/test assistance that reduces delivery and maintenance time.

Do not ship a generic chat box as differentiation. The moat is the product's workflow,
authorized context, validation, feedback data, reliable fallback, and cost discipline.

## One control path for every managed call

All business-funded model calls pass through a shared application-level gateway or
library that provides:

- a provider/model catalogue with stable internal model IDs, capabilities, context/output
  limits, status, price version/effective date, and allowed data classification;
- task policy that maps a named use case to an ordered model/fallback set, maximum input
  and output, latency target, quality threshold, and per-call/customer budget;
- tenant/user/feature attribution plus correlation, prompt/schema version, provider
  request ID, token/unit counts, latency, outcome, retry, and estimated/final cost;
- atomic budget reservation before the call, settlement to actual usage afterward, and
  automatic release/repair for failures or abandoned reservations;
- provider timeouts, bounded retries with jitter, circuit breaking, rate limiting, and a
  non-model fallback where the workflow can continue safely;
- kill switches by provider, model, feature, product, and customer plan.

Never call a paid model directly from browser/mobile code or trust a client-reported
usage/cost value. Provider keys are server-side secrets. The catalogue is an operational
control plane; changing an alias must not silently rewrite historical cost or evaluation
meaning.

## Cost ladder

Apply the cheapest reliable stage first:

1. deterministic parsing, rules, indexes, templates, or a previously validated cached
   result;
2. compact context retrieval and a smaller/cheaper model;
3. stronger model only when task risk, uncertainty, or an evaluation-backed router says
   the expected value is higher;
4. human review/exception handling for high-impact ambiguity.

Additional controls:

- bound input, retrieved chunks, tool calls, output, retry count, and concurrency;
- summarize/compress only when its quality and extra call cost beat sending raw context;
- cache by tenant, authorization boundary, normalized input, model, prompt/schema version,
  and source revision; never leak results across tenants;
- batch asynchronous work when latency is not customer-visible and the provider terms
  make it cheaper;
- meter images, audio, search, embeddings, storage, and tool/API charges as well as text
  tokens;
- set daily/monthly customer and portfolio budgets with alerts before the hard stop;
- review cost per **successful customer outcome**, not just cost per token or request.

Do not self-host a model merely to avoid an API bill. Include accelerator rental/purchase,
idle capacity, inference engineering, monitoring, upgrades, availability, and your time.
Adopt self-hosting only when measured volume, privacy, latency, or offline requirements
make total cost and quality better.

## Quality and evaluation

Every AI feature has a named task contract and a versioned evaluation set drawn from
realistic, permission-safe examples. Before release and when changing model, prompt,
retrieval, schema, or routing, compare against the current baseline.

Measure what the customer experiences:

- task success/completion and critical error rate;
- factual/grounding correctness and citation/source validity where applicable;
- structured-output/schema validity and deterministic business-rule validation;
- human correction/rework time and escalation rate;
- p50/p95 latency, timeout/fallback rate, and availability;
- total cost and cost per successful outcome, sliced by tenant/plan/feature/model version.

Use deterministic checks for schemas, calculations, permissions, and citations that can
be verified. Use calibrated human review or model-assisted grading only where necessary,
with blinded samples and periodic agreement checks. An LLM judge never replaces security,
financial, or authorization assertions.

Ship model/prompt changes behind a feature flag or canary. Record the evaluation artifact,
decision, expected unit economics, and rollback target. Do not claim competitive
superiority without a current, reproducible benchmark against named alternatives.

## Grounding, tools, and agents

- Retrieve only sources the current subject may access; authorization happens before and
  after retrieval. Preserve tenant/source IDs and revision timestamps.
- Tell the model to distinguish source facts, inference, and uncertainty. Return citations
  that the server validates against retrieved sources before display.
- Treat model output as untrusted input. Validate structured arguments, allowlist tools,
  scope credentials, cap steps/spend/time, and make mutations idempotent.
- Require explicit human confirmation for payments/refunds, permission or identity
  changes, customer suspension/deletion, external publication/messaging, and other
  consequential writes. Show the proposed action and affected records, not just prose.
- Defend tool/RAG paths against prompt injection by separating instructions from content,
  constraining tools/data, and testing adversarial documents/messages. A system prompt is
  not an authorization control.

## Privacy, security, and customer trust

- Classify data per feature/provider. Send the minimum context; remove secrets and
  unnecessary personal data. Never place passwords, tokens, payment data, or private keys
  in prompts.
- Document provider retention/training terms and approved regions/subprocessors for the
  actual account configuration. Provide customer disclosures/controls appropriate to the
  data and product.
- Partition prompts, caches, retrieval indexes, traces, and feedback by tenant. Define
  retention, export, and deletion behavior, including provider-side artifacts where
  available.
- Log metadata by default, not full prompts/responses. Content sampling requires an
  explicit purpose, access control, redaction, retention limit, and audit trail.
- Moderate or constrain input/output according to the domain risk. Provide a clear path
  for correction, retry, source inspection, and support.

## Administration and operations

The customer-management admin panel from `saas.md` shows, where applicable:

- provider/model health and kill switches;
- task-policy and prompt/schema versions;
- usage, reservation, settlement, failure, and cost by customer/plan/feature/model;
- budget/rate-limit state and safe manual adjustments with reason/audit;
- evaluation/canary status and the deployed rollback target;
- provider reconciliation differences and stuck reservations.

Use AI to draft support replies, summarize account history, explain cost anomalies, and
cluster failures—these are high-leverage solo-developer tools. Feed the assistant only
authorized/minimized context, label drafts, cite underlying records, and require operator
confirmation for external or mutating actions.

## Minimum launch gate

- [ ] Named customer task, deterministic fallback, and reason AI is better than the
      non-AI baseline are documented.
- [ ] Versioned evaluation set passes chosen task-quality, critical-error, latency, and
      cost-per-success thresholds.
- [ ] Every managed call is attributed, budgeted/reserved, settled, and reconcilable to
      provider records; duplicate/retry paths cannot double-charge customer credits.
- [ ] Input/output/tool limits, timeouts, bounded retries, circuit breaker, and provider/
      model/feature kill switches are tested.
- [ ] Tenant authorization, cache/RAG isolation, prompt-injection, data deletion, and
      no-secret/no-sensitive-log tests pass.
- [ ] Budget exhaustion and provider/model outage degrade predictably without breaking
      access to existing customer data.
- [ ] High-impact actions require validated arguments and human confirmation; the audit
      trail links proposal, confirmation, execution, and outcome.
- [ ] Customer-facing claims, limits, disclosures, and pricing match enforced behavior.
