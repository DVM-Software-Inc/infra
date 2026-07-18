# Environments

Two environments, **one VPS** (Contabo, `194.238.24.254`) — separated by deploy dir,
immutable image tag, and hostname:

| Env | Deployed by | Deploy dir | Image tag | Host pattern |
|---|---|---|---|---|
| `dev` | push to `main` | `/opt/apps/<slug>/dev` | `:dev-<shortsha>` | `dev.<domain>` / `staging.api.<domain>` |
| `prod` | manual `workflow_dispatch` | `/opt/apps/<slug>/prod` | `:prod-<shortsha>` | `app.<domain>` / `api.<domain>` |

Each app repo defines GitHub environments `dev` and `prod`. Protect `prod` with required
reviewers when the repository's GitHub plan supports them; otherwise restrict deployment
branches to `main` and retain the manual production dispatch. GitHub auto-creates an
environment unprotected on first use.

Repository-level secrets:

- `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`, `VPS_FINGERPRINT` — deploy target and pinned SSH
  host identity

Per-environment secrets:

- `ENV_FILE` — full dotenv content the deploy workflow atomically writes to
  `<deploy_path>/.env` with mode 600; use `require_env_file: true` for new callers
- App-specific runtime values when they cannot be included in `ENV_FILE`

Prefer the job-scoped `GITHUB_TOKEN` for GHCR. `GHCR_USERNAME` and `GHCR_TOKEN` remain
optional compatibility inputs for older callers.

Secret values originate in Vaultwarden and are pushed through stdin, for example:
`bw get password <item> | gh secret set ENV_FILE -R DVM-Software-Inc/<repo> --env <env>`.
Do not store `TAG`, `IMAGE_TAG`, or `DEPLOY_ENVIRONMENT` in `ENV_FILE`; the reusable deploy
workflow injects those values for each immutable release.
