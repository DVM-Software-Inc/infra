# Branching Strategy

- `dev` branch → deploys to dev environment
- `main` branch → deploys to prod environment

Workflow:

- Feature branches branch from `dev`, merged via PR.
- Hotfix branches can be merged into `main` after testing.
