# Owner-controlled VPS releases

Status: implementation and scoped dev pilot, 2026-10-24. Production stays disabled.

The shared host currently permits several CI SSH identities to run arbitrary root
commands. A workflow approval screen cannot protect production from those keys. The
founder selected a host-enforced gate while keeping the current GitHub plan. This
document supersedes the unprotected-environment-secret deployment pattern only for
applications that have completed the scoped gate cutover.

## Trust boundary

`release_gate/gate.py` is installed root-owned below `/usr/local/lib/dvm-release`.
Each CI SSH key gets exactly:

```text
restrict,command="/usr/bin/python3 -I /usr/local/lib/dvm-release/gate.py ci APP dev"
```

The existing owner's separately verified management key is preserved. The gate accepts
only `dvm-release-request-v1` and bounded JSON containing the app/environment, main
commit, GitHub run identity and registered API/web image digests. It rejects shell/SCP/
SFTP/Docker commands, unexpected fields, mutable tags, foreign images and production
requests. SSH keys authenticate a registered app; request claims alone grant nothing.
The workflow verifies the configured public CI-key fingerprint and requires live gate
refusals for shell, Docker, SFTP and owner commands before submitting each release. An
authentication/network error does not count as a successful denial check.

The executor checks the GitHub repository's immutable ID, workflow, main commit, run
attempt, event and successful required test/build jobs. The transient job-scoped GitHub
token is used for those lookups and GHCR pull only, never saved in the manifest or audit.
This is run verification, not a claim of cryptographic image-build attestation. Owner
review of exact image digests remains required for production; signed build attestations
are a possible later strengthening.

CI cannot upload Compose, env files, migration commands or smoke URLs. Root-owned policy
fixes those inputs. Policy, Compose, protected dotenv and executor hashes are sealed into
each manifest. Only registered image references change through a generated override;
numeric non-root users, dropped capabilities and no-new-privileges are enforced. The
pilot rejects host volumes, published ports, privileged services and host namespaces.
No shell receives request data. Captured subprocess output is never returned to CI.

Dev deploys serialize per app. Migrations and health checks are fixed by owner policy.
Successful, failed and interrupted attempts are distinguishable in protected host state;
`current` and `previous` record exact manifests, not moving tags. A failed migration is
not automatically rolled back: inspect its compatibility and repair through management.
Rollback to an older image does not undo a database migration.

## Production approval

No production SSH capability is issued to CI. Production runtime secrets are provisioned
through the owner/Vaultwarden path into protected host configuration, never through the
new CI workflow. The existing gateway workflow guard remains until the complete gate
and production acceptance pass. No prod policy/config is provisioned by the dev pilot.

Before an owner can approve **or execute** production, the executor examines all root
authorized keys. Each key must be an explicitly registered owner identity or an exact
scoped gate command. `restrict` by itself is insufficient because it still allows a
shell. Unknown/unmigrated keys keep production blocked. This pilot constrains only the
gateway's key; each other app must migrate without interrupting its existing services.

Owner-only operations, through the existing management SSH connection:

```text
python3 -I /usr/local/lib/dvm-release/gate.py owner show DEV_MANIFEST_ID
python3 -I /usr/local/lib/dvm-release/gate.py owner promote DEV_MANIFEST_ID
python3 -I /usr/local/lib/dvm-release/gate.py owner show PROD_MANIFEST_ID
```

Promotion uses the current accepted dev image digests and independently protected prod
configuration. After all release gates pass, the founder personally runs the approval
command in an interactive management terminal, supplies a reason and types the complete
manifest ID. Approval expires in 15 minutes, applies to that exact manifest/configuration,
and is consumed before the first migration/start. A failure cannot silently reuse it.
The agent must never approve on the founder's behalf or manufacture an approval receipt.

The eventual owner command is `owner approve PROD_MANIFEST_ID "release reason"`, followed
by `owner deploy PROD_MANIFEST_ID`. These are documented commands, not authorization to
run them. Production promotion reuses cached immutable digests already tested in dev;
it never rebuilds or resolves a mutable tag and has no CI registry token.

## Installation and cutover

1. Read current host state and verify the management SSH fingerprint separately from the
   app's CI key. Prepare a policy from `release_gate/llm-gateway-dev.example.json` with the
   actual immutable GitHub repository ID. Review the exact committed Compose; compare it
   with live content. Runtime dotenv remains root-owned mode 0600.
2. Through management SSH, stage the reviewed code, installer, policy and Compose. Run
   `install.py` **without** `--activate-key`, passing the policy/Compose and the two exact
   fingerprints. The installer backs up existing keys/policy/code, establishes protected
   directories and preserves management access. No app restarts at this step.
3. Exercise scope, malformed-request, shell/SCP/SFTP, foreign-image and unapproved-prod
   negatives. Verify rendered Compose uses only the expected services and restrictions.
4. Prepare the app workflow to call pinned `deploy-gated.yml`, passing API/web digests
   and granting `actions: read`, `contents: read`, `packages: read`. It must not pass an
   `ENV_FILE` or migration/Compose input. Review/merge infra before pinning its exact SHA.
5. Confirm no old deployment is active, rerun installation with `--activate-key`, and
   immediately merge the prepared app workflow. Reconnect independently with management
   SSH and prove the CI entry has its exact forced command. Do not restore unrestricted
   CI access as a deployment workaround. Management can repair a failed pilot safely.
6. Require a real successful CI deployment through the restricted key, healthy matching
   API/web digests and successful database readiness before calling the dev cutover done.
   Record the deployment manifest ID, CI run, protected hashes and negative-test evidence.

Protected paths: `/etc/dvm-release`, `/usr/local/lib/dvm-release`,
`/var/lib/dvm-release`, `/opt/backups/dvm-release`. These are host management state and
must join the separately protected backup/recovery plan. Config hashes are not backups.
Changing policy/Compose/runtime secrets requires an owner-controlled install/provisioning
step; auto-deploying arbitrary infrastructure changes would recreate the original bypass.

Runtime configuration rotation uses `gate.py configure APP ENV` over the verified owner
management connection. It accepts bounded dotenv through stdin, rejects host/Compose/build
overrides and duplicate keys, validates the protected Compose, backs up the old file and
atomically installs mode 0600. It audits hashes only and never restarts an app. CI cannot
invoke this operation. The next accepted release binds the new config hash. Gateway's
`render-env-file.sh ENV --install-host` streams Vaultwarden values directly to this
management path without a laptop file or GitHub environment secret. Provisioning the
first config is still an explicit environment-foundation task; this command requires an
existing protected dotenv. Other apps retain their current provisioning until migrated.

## Verification and remaining limits

Run `python3 -m unittest discover -s tests -p 'test_release_gate.py' -v` locally. Tests
exercise scope denial, immutable image validation, duplicate/oversized JSON, manifest
invalidation, single-use/expiry approval, complete SSH-key boundary, GitHub run checks,
container restrictions and fixed migration commands. No test deploys production.

The gate does not close consumer-network isolation, application vulnerabilities, data
recovery or host-root owner compromise. Those remain separate release gates. Any remaining
unrestricted CI key blocks production even when this app's dev release succeeds.

References: [GitHub OIDC/run claim contract](https://docs.github.com/en/actions/reference/security/oidc),
[Docker daemon access](https://docs.docker.com/engine/security/protect-access/).
