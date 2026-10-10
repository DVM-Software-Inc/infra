# Gelopreto hybrid cyber defense — proposed direction

Captured 2026-09-06 for a later brainstorm. **Documentation/context only: not
an approved fleet standard, implementation plan, or authorization to deploy.**

The intended split is Traefik for the HTTP boundary, access-log evidence and
eventual enforcement; Gelopreto for behavior analysis, CVE/assessment correlation
and operator-reviewed decisions; applications for structured security events
such as authentication failures, privilege denials and business-specific abuse.
Application logging libraries remain app-specific; Loguru is not mandated.

Gelopreto already has a read-only Traefik JSON-log detector. Preserve that
contract; a shipper/queue is an option to evaluate, not a prerequisite. Blocking,
new rate-limit policies and application-event ingestion require later design.
Keep detection separate from narrowly privileged enforcement, with scoped
decisions, expiry, audit, reconciliation and a tested recovery path. Automatic
blocking is not authorized by this note.

Technical constraints: native IPAllowList is not a general denylist, and the
Traefik admin API exposes state rather than accepting configuration writes.
File/HTTP providers can supply dynamic configuration (HTTP is polled), but an
actual deny mechanism still needs selection and review. Trusted client-IP
attribution and redaction are prerequisites for actionable cross-app evidence.
The detailed Gelopreto note contains official provider references.

## Sources of truth

- Product context and open questions:
  [Gelopreto hybrid cyber defense](https://github.com/DVM-Software-Inc/gelopreto/blob/feat/security-workflows/docs/superpowers/specs/2026-09-06-hybrid-cyber-defense-context.md)
  (feature branch pending merge; local checkout:
  `~/code/gelopreto/docs/superpowers/specs/2026-09-06-hybrid-cyber-defense-context.md`).
- Operational handoff: `~/code/vps_deploy/infra_llm/docs/cyber-defense.md`.
- Runtime configuration: `~/code/vps_deploy/traefik/`, not this repository's
  legacy `docker-templates/`.

Before implementation, agree event schema/privacy, initial detection scenarios,
enforcement adapter and scope, approval/expiry policy, transport reliability,
failure behavior and dev-canary acceptance tests. Update shared application
standards only after those decisions; this note does not change existing ones.
