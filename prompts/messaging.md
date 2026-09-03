# DVM Software shared messaging standard

This standard applies to every DVM application that lets an authenticated user
communicate with DVM staff or another accountable business operator. It applies to web,
mobile, and desktop applications whether the interface looks like chat, webmail, an
inquiry thread, or a compact message panel.

## Required architecture

- Integrate through the shared DVM Messaging API and its provider-neutral client/UI
  packages. The source repository is `~/code/chatwoot`.
- Never call Chatwoot from a product backend or browser/mobile/desktop client. Chatwoot is
  a replaceable engine behind the messaging service's `ChatwootAdapter`.
- Never build an application-local customer-to-business messaging engine, message table,
  assignment queue, unread system, or polling loop. If the shared platform lacks a
  capability, extend its public contract and adapter boundary once for the portfolio.
- Use platform-owned application, subject, conversation, message, and context IDs in
  product code. Chatwoot IDs, inbox identifiers, API tokens, SDKs, callbacks, and payloads
  are forbidden outside the shared platform's adapter and infrastructure packages.
- Keep `~/code/chatactorai` separate. It is the embeddable chatbot/RAG product; its widget,
  transcript schema, agent behavior, and APIs are not the authenticated messaging system.

This standard covers user-to-business communication. Peer-to-peer chat, game chat,
collaborative editing comments, and domain-specific event streams require a deliberate
architecture decision; do not force them into Chatwoot merely because they contain text.

## Application integration contract

Each application registers once with the messaging platform and supplies:

- a stable application key assigned by the platform;
- its trusted authentication/audience mapping;
- an allowlist of messageable business-object types;
- an authorization mechanism for every referenced business object;
- secure deep-link templates back to those objects;
- an owning team and escalation policy;
- its notification policy and verified SES sender identity where email fallback is used.

The application may pass an allowlisted context descriptor such as
`{type: "inquiry", id: "inq_123"}` only after the platform can authorize the caller's
access. A context ID, tenant ID, role, email address, or client-supplied user ID is never
proof of access.

## Identity and client behavior

- Web applications use the Keycloak/BFF pattern from `fullstack.md`: the BFF calls the
  Messaging API with the user's server-held access token. Browser JavaScript never holds
  a provider credential.
- Native applications call their own backend or the Messaging API with an approved
  app-issued/Keycloak token contract. They never bundle a Chatwoot or notification-provider
  secret.
- Prefer the shared React/client package when it supports the host stack. Native clients
  may implement native presentation over the same public API, but not a separate backend.
- Treat in-app conversation history as canonical for the customer experience. Email is a
  notification/transport that links back to the authorized thread.

## VPS network path

Co-located services use private Docker traffic rather than public DNS:

```text
product BFF/backend -> messaging-api -> chatwoot-api
                     messaging-clients   messaging-backplane
```

- Product BFF/backend containers join the external `messaging-clients` network and call
  the Messaging API by its private alias. They do not join `messaging-backplane`.
- Only the Messaging API/worker and Chatwoot Rails join `messaging-backplane`.
- The Messaging API calls `http://chatwoot-api:3000` internally. Do not route this traffic
  through `chat.dvmsoftware.com`, public DNS, or Traefik.
- The public Chatwoot hostname exists for the human operator console. Its availability
  does not authorize product code to use it.
- Native/off-VPS clients use an authenticated public Messaging API or their product
  backend; Chatwoot is never the public client API.

## Notifications

- Conversation events flow through the messaging platform's durable outbox and
  provider-neutral `NotificationAdapter`.
- Applications must not poll Chatwoot or independently reproduce message notifications,
  unread counts, preferences, digests, or retry state.
- AWS SES remains the outbound email provider. Novu is the leading in-app orchestration
  candidate, but product code must not depend on either provider directly.
- Notification links use registered route templates; never accept an arbitrary URL from a
  message or client request.

## Repository and configuration requirements

An app with authenticated user-to-business communication documents a `Messaging` section
in `docs/overview.md` containing its application key, allowed context types, authorization
path, UI entry points, deep-link routes, and notification behavior. Document names and
secret locations, never values.

Product runtime configuration may contain only provider-neutral values such as:

```text
MESSAGING_API_URL
MESSAGING_APPLICATION_KEY
MESSAGING_ENABLED
```

Chatwoot account/inbox IDs and credentials live only in the shared messaging platform's
registry/secret manager. Until the shared service is deployed for an environment, keep
the product integration behind `MESSAGING_ENABLED=false`; do not create a temporary local
messaging backend that becomes permanent by accident.

## Delivery gate

Before enabling messaging for an application, verify:

1. unauthenticated access fails;
2. cross-tenant, cross-application, and guessed-context access fails;
3. the browser/native client contains no provider IDs or credentials;
4. retries do not duplicate conversations, messages, or notifications;
5. operator replies appear through verified callbacks/webhooks rather than polling;
6. notification email uses the application's approved SES identity and deep link;
7. operators can see the application and business context in the central queue.
