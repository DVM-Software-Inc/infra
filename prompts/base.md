# DVM-Software deployment conventions — base (all server-deployed apps)

You are working in a DVM-Software-Inc app repo. Follow these conventions exactly; do not
invent alternatives. When something here conflicts with the live VPS, the VPS wins — then
update this doc.

Read `messaging.md` as a required cross-cutting standard. Authenticated
user-to-business communication goes through the shared DVM Messaging API; product apps
never call Chatwoot directly or create their own customer communication engine.

## Topology

- **One VPS** (Contabo, `194.238.24.254`, `ssh contabo`) runs everything as Docker Compose
  stacks. No Kubernetes.
- **Traefik v3** owns host ports 80/443 with the `letsencrypt` cert resolver and discovers
  containers by docker labels on the **`web-public`** attachable overlay network (kept alive
  by a single-node swarm — never `docker swarm leave`, never bind host ports 80/443/8080).
- **Shared Postgres 18** (`pgvector/pgvector:pg18`, container `app-postgres`) hosts one
  DB + user per app+env, reachable from any `web-public` container at **`postgres:5432`**.
  Not exposed publicly; laptop access only via SSH tunnel.
- **Secrets** live only in Vaultwarden (`vault.dvmsoftware.com`). GitHub Actions secrets are
  populated from it (`bw get password <item> | gh secret set <NAME> -R DVM-Software-Inc/<repo>`).
  Never write a secret value into the repo, chat, or logs. `.env.example` lists variable
  names and the Vaultwarden item that holds each value — never values.

## Environments, branching, domains

- Environments: `dev` and `prod`, both on the same VPS.
- **Push to `main` → auto-deploys `dev`. Prod deploys only via manual `workflow_dispatch`**
  against the protected GitHub environment `prod` (required reviewers). There is no `dev`
  or `prod` branch; feature branches merge to `main` via PR.
- **Each product owns its root domain** (Namecheap), e.g. `chatactorai.com`:
  - prod: `app.<domain>` (web/UI) and `api.<domain>` (API) — single-container apps may use
    the root or one subdomain
  - dev: `dev.<domain>` (web) and `api.dev.<domain>` (API) — verified against the live
    chatactorai-dev routers 2026-07-19; earlier `staging.api.<domain>` wording was wrong
  - `*.dvmsoftware.com` is reserved for internal utilities (vault, auth, traefik, …).
- **DNS before deploy**: create the A record → `194.238.24.254` and verify
  `dig +short <host> A` resolves before `docker compose up`, or Let's Encrypt HTTP-01 fails.
- **Namecheap API access**: credentials are in Vaultwarden **`namecheap_api`**
  (login username = API user, password = API key, notes = configured client IPv4).
  `ClientIp` must match the public IPv4 of the machine making the API request and
  that address must be whitelisted in Namecheap. A laptop's address can change;
  the VPS/DNS target IP is not automatically its outbound client IP. Before
  replacing an apparently invalid key, check this mismatch and the whitelist.
  See [Namecheap API troubleshooting](../docs/namecheap-api.md) for the verified
  recovery procedure and safe DNS updates.

## VPS layout

- Apps deploy to **`/opt/apps/<slug>/<env>/`** — compose file + `.env` + volume bind-mount
  subdirectories, nothing else. (Utilities use `/opt/<name>/`; don't mix them.)
- Persistent **app-owned service state** (caches, SQLite, generated config, queues) =
  bind mounts under the deploy dir (`./data:…`), so one `tar` backs up the service.
  **Customer files are not service state** — they go to object storage (see "Object
  storage" below), never to a bind mount.

## CI/CD contract

Repos use the reusable workflows from `DVM-Software-Inc/infra` — never hand-roll
scp/ssh deploy jobs. Compose files live under **`deploy/`** in the repo (enforced).

**Scoped release-gate pilot (2026-10-24):** AskPaje is moving to
`deploy-gated.yml`, with a root-owned host executor, fixed Compose/config/migration
policy and digest-only CI requests. It preserves automatic dev deployment while CI
loses shell/SCP/Docker access. Production uses exact, expiring, single-use owner approval
outside ordinary CI, and remains blocked while any unreviewed root-equivalent CI access
exists. No production runtime secrets go through this workflow. Keep existing production
guards until the app's cutover and negative tests pass; migrate other CI identities one
app at a time. See [owner-controlled releases](../docs/owner-controlled-releases.md).
The legacy example below is not permission to retain unrestricted root SSH for production.

```yaml
name: CI/CD
on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      environment:
        type: choice
        options: [dev, prod]
        default: dev
        required: true

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  # lint/test jobs here — deploy must depend on them

  build:
    uses: DVM-Software-Inc/infra/.github/workflows/build.yml@main
    permissions:
      contents: read
      packages: write
    with:
      image_name: ${{ github.event.repository.name }}
      environment: ${{ github.event_name == 'workflow_dispatch' && inputs.environment || 'dev' }}

  deploy:
    needs: build
    uses: DVM-Software-Inc/infra/.github/workflows/deploy.yml@main
    permissions:
      contents: read
      packages: read
    with:
      environment: ${{ github.event_name == 'workflow_dispatch' && inputs.environment || 'dev' }}
      compose_file: deploy/docker-compose.yml
      deploy_path: /opt/apps/${{ github.event.repository.name }}/${{ github.event_name == 'workflow_dispatch' && inputs.environment || 'dev' }}
      image_tag: ${{ needs.build.outputs.image_tag }}
      require_env_file: true
      # migrate_command: docker compose -f "$COMPOSE_FILE" run --rm api alembic upgrade head
    # MUST be `inherit`, not an explicit list: an explicit secrets: block is
    # evaluated in the caller's context, which has no environment, so the
    # per-environment ENV_FILE secret arrives empty and require_env_file fails
    # (bit talk2me 2026-07-18). With inherit, the called job's `environment:`
    # resolves environment secrets correctly.
    secrets: inherit
```

- **CI cost policy (local-first):** feature branches and pull requests trigger **no**
  workflows — automatic runs happen only on push to `main` and on `v*` release tags;
  everything else is `workflow_dispatch`. Pre-merge verification is local
  (`./scripts/check.sh` or the repo's equivalent). `macos-*` runners are never used
  where `ubuntu-latest` suffices, and macOS jobs never run automatically outside `v*`
  release workflows. Every workflow includes the `concurrency` block above so obsolete
  runs cancel instead of billing. To retrofit an existing repo, run
  `prompts/gha-cost-optimization.md`.
- `VPS_FINGERPRINT` must be the **ECDSA** host-key fingerprint
  (`ssh-keyscan -t ecdsa 194.238.24.254 | ssh-keygen -lf -`), not ed25519 —
  appleboy/ssh-action's Go SSH client negotiates ECDSA first and fails with
  "host key fingerprint mismatch" otherwise (bit talk2me 2026-07-18).
- `build.yml` always pushes immutable `ghcr.io/dvm-software-inc/<image>:<env>-<shortsha>`
  and can publish the moving `:<env>` compatibility alias. Deployments pass the immutable
  output to `deploy.yml`, which writes `IMAGE_TAG`/`TAG` into `.env`; Compose must reference
  `${IMAGE_TAG}`. Never deploy a moving tag.
- Per-env config: create GitHub environments `dev` and `prod` (prod with required
  reviewers — GitHub auto-creates it unprotected on first use, protect it explicitly).
  Store `ENV_FILE` (the full static dotenv, excluding `TAG`/`IMAGE_TAG`) in each environment.
  The called deploy job reads the environment secret directly, transfers it as masked
  Base64, and atomically writes `<deploy_path>/.env` with mode 600.
- Migrations run through `migrate_command` (after pull, before `up -d`).
- Prefer the caller's `GITHUB_TOKEN` with job-scoped package permissions; legacy GHCR
  credentials remain supported. Pin production callers to a tested infra commit SHA.

## Canonical compose file (`deploy/docker-compose.yml`)

```yaml
name: ${PROJECT_NAME}-${DEPLOY_ENVIRONMENT}   # stable across immutable image revisions.
   # Must be UNIQUE per app+env on the VPS — compose otherwise derives it from the deploy
   # dir basename (dev/prod, shared by ALL apps) and `--remove-orphans` would delete other
   # apps' containers. deploy.yml writes DEPLOY_ENVIRONMENT and IMAGE_TAG dynamically;
   # ENV_FILE sets PROJECT_NAME=<slug> and APP_DOMAIN=<host>.
services:
  api:
    image: ghcr.io/dvm-software-inc/${PROJECT_NAME}:${IMAGE_TAG}
    container_name: ${PROJECT_NAME}-${DEPLOY_ENVIRONMENT}
    restart: unless-stopped
    env_file: [.env]
    volumes:
      - ./data:/path/inside/container   # app-owned state only; customer files → object storage
    networks: [web-public]
    labels:
      - traefik.enable=true
      - traefik.docker.network=web-public
      - traefik.http.services.${PROJECT_NAME}-${DEPLOY_ENVIRONMENT}.loadbalancer.server.port=<container-port>
      - traefik.http.routers.${PROJECT_NAME}-${DEPLOY_ENVIRONMENT}.rule=Host(`${APP_DOMAIN}`)
      - traefik.http.routers.${PROJECT_NAME}-${DEPLOY_ENVIRONMENT}.entrypoints=websecure
      - traefik.http.routers.${PROJECT_NAME}-${DEPLOY_ENVIRONMENT}.tls.certresolver=letsencrypt
      - traefik.http.routers.${PROJECT_NAME}-${DEPLOY_ENVIRONMENT}-http.rule=Host(`${APP_DOMAIN}`)
      - traefik.http.routers.${PROJECT_NAME}-${DEPLOY_ENVIRONMENT}-http.entrypoints=web
      - traefik.http.routers.${PROJECT_NAME}-${DEPLOY_ENVIRONMENT}-http.middlewares=redirect-to-https@file

networks:
  web-public:
    external: true
```

Rules that matter:

- `traefik.enable=true` is required (`exposedByDefault: false`); `traefik.docker.network=web-public`
  disambiguates when a container joins multiple networks.
- `loadbalancer.server.port` is the **container** port — publish no host ports; Traefik
  reaches containers over `web-public`.
- Router/service names must be unique across the whole VPS — always suffix with env.
- Backing services an app owns (redis, workers) join an app-private `internal` bridge
  network and get **no** Traefik labels; only web-facing services join `web-public`.
- **Monitored apps also join the `monitoring` overlay** (external, attachable, swarm-scoped
  like `web-public`; created 2026-07-18). cc_dvm pulls `/health` and receives pushed
  business metrics over it — its ingest endpoint is *only* reachable there, never from the
  public edge. Declare it in compose (`monitoring: {external: true, name: monitoring}`) —
  a manual `docker network connect` does not survive redeploys. If a compose sets
  `container_name`, know that cc_dvm's app definitions reference containers by DNS name —
  update its seed (cc_dvm `backend/cmd/seed-apps`) when a monitored container is renamed.
  Do NOT scaffold this network away when regenerating a monitored app's compose.
- `restart: unless-stopped`, never `always`. No `version:` key (compose v2).
- Single-quote values containing `$` in `.env` (argon2 hashes etc.) — compose interpolates
  unquoted `$`. Prefer `env_file:` over `${VAR}` interpolation for secret-bearing values.
- After editing `.env` on the VPS, `docker compose up -d` to recreate — changes aren't live.

## Database (shared Postgres)

Per app+env, once, at provisioning time (superuser access via `ssh contabo "docker exec -it
app-postgres psql -U postgres"`):

```sql
CREATE USER <slug>_<env> WITH PASSWORD '<from-vaultwarden>';
CREATE DATABASE <slug>_<env> OWNER <slug>_<env>;

-- Isolation. Postgres grants CONNECT to PUBLIC on every new database, so
-- without these every app's role can reach every other app's database on the
-- shared instance. Verified 2026-07-31: all 37 databases were mutually
-- reachable by any valid role. Data was not readable (no PUBLIC grants on app
-- tables), but schema, table, column and role names were enumerable estate-wide
-- from a single leaked credential.
REVOKE CONNECT ON DATABASE <slug>_<env> FROM PUBLIC;
GRANT  CONNECT ON DATABASE <slug>_<env> TO <slug>_<env>;

-- Then, connected to the new database (\c <slug>_<env>):
-- PUBLIC gets CREATE on schema public by default, letting any role plant
-- objects here.
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
```

**A database and user created for an app must be able to reach only that app's
database.** One leaked `DATABASE_URL` is then worth exactly one database, not
the whole instance. Do not skip the REVOKEs because "it's only dev" — the
2026-07-31 incident leaked a dev credential from a compromised container.

`GRANT ALL PRIVILEGES ON DATABASE` is unnecessary when the role already owns the
database, and it does not grant what people assume — it covers CONNECT, CREATE
and TEMP, never table access.

Store the password in Vaultwarden as `postgres-<slug>-<env>`. The app connects with
`postgresql://<slug>_<env>:<pw>@postgres:5432/<slug>_<env>` (asyncpg variant:
`postgresql+asyncpg://…`). Default to shared Postgres; dedicated instances only for heavy
load or compliance.

## Object storage (Contabo S3)

**Decided 2026-09-06.** Customer files (uploads, generated documents, exports) never live
on a container filesystem or a bind mount: no redundancy, no lifecycle, and the
2026-09-02 EnoughLedger cutover showed a root-owned `./data` dir silently breaking every
upload. They go to **Contabo Object Storage** (S3-compatible, Ceph-based), the account
that already holds the Vaultwarden offsite backups. Reference implementation:
`smb-tax` `internal/filestore` (Go, aws-sdk-go-v2).

- **Endpoint** `https://usc1.contabostorage.com` (US-central), **path-style** addressing,
  signing region `us-east-1` (Contabo accepts it; there is no region-specific signing).
- **One bucket per app per env**, named `dvm-<slug>-<env>` (e.g. `dvm-smb-tax-dev`).
  The Contabo bucket namespace is shared across customers, hence the `dvm-` prefix.
  Provision from the VPS, which already has the account remote configured:
  `ssh contabo "rclone mkdir contabo:dvm-<slug>-<env>"`. Record the bucket in
  `infra_llm/docs/services.md`.
- **Only the app's API holds credentials.** No client-direct uploads, no presigned URLs
  unless a documented need appears (then ≤5 min, one exact key, issued after the same
  authorization as a download). No public ACLs, ever.
- **Key layout is tenant-first** so a tenant can be listed, exported or deleted with one
  prefix operation, and keys are **derived from the database row, never from request
  input**:
  `tenants/<tenant_id>/files/<file_id>/original/<sanitised-name>` and
  `…/derived/<artefact>`. Object storage has no row-level security: isolation is the
  app authorizing the row (under Postgres RLS where the product has it) *before* touching
  the key. Deletion is prefix-scoped from app code; never a bucket-wide operation.
- **Env var names** (every app, same names):
  `OBJECT_STORE_DRIVER=s3|local`, `OBJECT_STORE_ENDPOINT`, `OBJECT_STORE_REGION`,
  `OBJECT_STORE_BUCKET`, `OBJECT_STORE_ACCESS_KEY`, `OBJECT_STORE_SECRET_KEY`,
  `OBJECT_STORE_PATH_STYLE=true`. `local` (filesystem) is for laptops and tests only.
- **Boot and health:** fail to start when the bucket is unreachable (a bad key fails the
  deploy smoke check, not the first upload); report `object_store` in `/health` from a
  cached probe but do **not** fail the container health check on it — a provider blip
  must not take the app down.
- **SDK gotchas (aws-sdk-go-v2 ≥ 2025):** set request/response checksum calculation to
  `WhenRequired` — Ceph rejects the default CRC32 request checksums and trailer-signed
  streaming uploads. Buffer bodies you have already size-capped so they are seekable.
- **Credentials — the honest state (decided 2026-09-06).** Contabo has **no per-bucket
  keys**: a key pair is per Contabo user and reaches every bucket in the account. Bucket
  restriction there is a *deny-list bucket policy per user ARN* (Contabo KB 103000282920),
  which is default-open and must be re-applied for every new user and bucket. Owner's
  decision: **stay on Contabo for now with one bucket per app per env and the shared
  account key** (Vaultwarden `accounts/contabo-s3`, custom fields `Access Key` /
  `Secret Key`), and **migrate to a provider with per-bucket access control — Cloudflare
  R2 or similar — before prod**. Accepted interim risk, dated: one leaked app key
  exposes every bucket, including `dvm-vault-backups`. Apps therefore must stay
  provider-neutral: S3 driver, endpoint + region + bucket + key from env, no
  Contabo-specific API, no public share links. Migration is then per bucket:
  `rclone sync contabo:dvm-<slug>-<env> r2:dvm-<slug>-<env>`, new bucket-scoped key as
  `<app>/<env>/object-store`, swap the env values, redeploy, verify, delete the old bucket.
- Versioning off, no lifecycle rules by default; the bucket is the durable copy. Backup =
  `rclone sync` of the bucket to a second bucket or provider; define and restore-test it
  before the product's prod launch.

## Authentication — Keycloak, one realm per product

**Decided 2026-09-02, replacing Authentik.** Reasoning:
`~/code/vps_deploy/infra_llm/docs/auth.md` §16. Design and runbooks:
`~/code/keycloak/docs/`.

Every DVM app is a **customer-facing product**, including ones built first to
serve a DVM function. Products do not share a user directory: someone who
registers at two products has two unrelated accounts, and that is the feature.

- **One Keycloak realm per product per environment** — `<product>-dev`,
  `<product>-prod`. There is no `internal` realm.
- **No SSO between products.** Not a missing feature; the thing being removed.
- **A realm is a product, never a customer.** Multi-tenancy lives *inside* the
  product (gelopreto: `tenant_id` under `FORCE ROW LEVEL SECURITY`). Realms per
  customer would mean thousands of realms and no way to operate them.
- **No global usernames.** Email is the identifier. A username unique across
  products requires one shared namespace, which is a shared directory wearing a
  hat — and "that name is taken" leaks a holder in an unrelated product.

### The app is an OIDC CLIENT of its realm

This is the distinction that gets muddled, so state it plainly: **the
application authenticates to Keycloak.** It is not an authentication authority
and it never sees a credential. Users authenticate against the realm; the app
receives and validates tokens.

- The app never handles a password, a social login, or an MFA challenge.
- The app's job is: redirect to the realm, validate the token, trust the claims.
- Registration, verification, password reset and identity linking all belong to
  the realm. Do not reimplement any of them.

### Token and authorization contract

“The signature is valid” is only the first check. Every application declares its
accepted token type, issuer, audience and authorization inputs:

- The web BFF uses the **ID token only to complete the OIDC callback and establish
  its server-side application session**. Validate the exact issuer, client
  audience/authorized party, allowed algorithm, expiry/issued-at, state and the
  nonce that was created before redirect. Require `email_verified=true` before an
  email-based first binding or invitation match.
- APIs accept **access tokens**, never ID tokens as bearer credentials. Validate
  allowed algorithm, the exact product/environment issuer, an explicit API
  audience, expiry/not-before/issued-at as applicable, and a non-empty subject.
  A token for another product, environment, API or client must fail even when the
  same Keycloak instance signed it.
- Realm/client roles are authorization inputs, not the whole decision. Resolve the
  local user, organization membership, product permission and entitlement on the
  server; never trust a client-supplied tenant ID.
- Give machine clients their own confidential service account, audience and
  minimal scopes. Native human clients are public clients using the system browser
  and authorization code + S256 PKCE; they never embed a client secret.
- Derive discovery/JWKS from the exact issuer. Cache signing keys by issuer and
  `kid`; on an unknown `kid`, refresh once with rate limiting so key rotation works
  without turning arbitrary tokens into an upstream-request flood.

Acceptance includes negative tests for wrong state/nonce, realm/environment,
audience/token type, tenant/role, expiry and signing key. See
`~/code/infra/docs/keycloak-migration.md`.

### The issuer is the PRODUCT's host — never the shared one

Keycloak runs at `key.dvmsoftware.com`, but **no product ever points at it.**
Each realm sets a `frontendUrl`, so its login pages and every OIDC endpoint it
advertises are on the product's own domain:

```
OIDC_ISSUER_URL = https://auth.<product-domain>/realms/<product>-<env>
```

e.g. `https://auth.comcentre.online/realms/cc-dvm-dev`. JWKS, authorize and
token endpoints all derive from that issuer — verified end to end, including the
`iss` claim in a minted token.

**If you find `key.dvmsoftware.com` in an app's configuration, it is wrong.**
That host is the admin console and the master realm. A product pointing at it
tells its users that fourteen other products share the same infrastructure,
which is the whole thing this architecture prevents.

### Google social login — central administration, isolated projects

Use the existing owner-approved master Google account with separate Cloud projects
per product **and environment**. Do not create a consumer Google account for every
product mailbox. The OAuth user support address can be visible to users; use only
an approved eligible account/group, never a mailbox-only IAM Owner workaround.

Google clients belong to Keycloak's Google provider, not the app BFF. Register the
exact `/realms/<product>-<env>/broker/google/endpoint` on the product auth host.
Use `openid profile email`, distinct Vaultwarden OAuth/client items, and approved
runtime injection. Dev remains Testing; production gets separate projects and
credentials, public policy/homepage and applicable verification. Test broker
collision/linking; do not silently auto-link on email. See `docs/standards.md` and
the Google rollout plan in the infra repository.

### Transition state — use the ledger, never assume

The migration is active. On 2026-09-06, the owner confirmed `cc_dvm` is already
provisioned and excluded it from remaining Google work. `gelopreto` remains under
verification. `smb-tax` has live Keycloak discovery and deployed app issuer/client
configuration; Google login is owner-verified, while broader acceptance and host
isolation remain open. ChatActorAI's new realm/Google provider and isolated route
are live. Its dev app cutover `399410a` succeeded: exact Keycloak issuer/API
audience and PKCE redirect pass; the approved five-binding reset preserved all
8 users and 4 organizations. Real browser Google-to-dashboard login and logout
are verified; broader live negative/refresh acceptance remains open.
EnoughDating's running API has empty OIDC issuer/client values.
Other applications keep their current authentication path until their individual
cutover is verified. Use the ledger for dated evidence and unresolved gates.

- **New work** follows this standard.
- **Implementation is not acceptance.** Realm creation or a successful redirect
  does not authorize removal of the old runtime dependency.
- **Existing apps** move one product at a time, dev before prod. Do not make an
  opportunistic cross-repo auth change outside the owning app session.
- Authentik development identities are disposable by owner decision. Do not import
  its users, credentials, sessions, consents, secrets or policies; use fresh
  Keycloak identities and reseed affected dev bindings/fixtures.
- Product auth hosts must deny `/admin`, `/realms/master`, and unrelated realms.
  This shared proxy gate is still open on the observed live hosts.

Portfolio status and acceptance evidence:
`~/code/infra/docs/keycloak-migration.md`. Realm design and implementation plan:
`~/code/keycloak/docs/migration-from-authentik.md`.

Adding a realm is three coordinated changes, not one — DNS A record for the auth
host, a Traefik router (one per host, never an OR-rule), then Terraform. See
`~/code/keycloak/terraform/README.md`.

## Repo hygiene (every server-deployed repo)

- `Dockerfile` per deployable service; compose under `deploy/`; `.env.example` (names +
  Vaultwarden item references only); `.github/workflows/ci.yml`; `/docs/overview.md` with
  project-specific detail (hosts, services, env vars, anything an agent can't infer).
- Auth for human users goes through **Keycloak** (OIDC) — see "Authentication" above.
  Don't build standalone password auth.
- If the product offers authenticated user-to-business communication, document and test
  its integration according to `prompts/messaging.md`. Product secrets and compose files
  must not contain Chatwoot credentials or inbox IDs.

## Verify a deploy

```bash
ssh contabo "docker ps --filter name=<slug>"          # Up?
curl -sI http://<host>   # expect 301 → https (give Traefik ~10s after up -d)
curl -sI https://<host>  # expect 200/302 with valid cert
ssh contabo "docker logs <container> --tail 50"
```
