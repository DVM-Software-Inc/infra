# LLM Instructions for DVM-Software

You are operating in an organization with strict but simple conventions:

- Always put source code in `/src`.
- Do not invent new top-level folders.
- Backends use port 8080 internally.
- Frontends use port 3000 internally.
- Dockerfiles and docker-compose files already exist: update, don't rewrite from scratch.
- CI/CD uses reusable workflows from the `infra` repo.
- Every project must include `/docs/overview.md` with project-specific details.
