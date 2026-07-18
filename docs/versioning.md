# Versioning

`build.yml` always publishes an immutable image tag (owner/image lowercased):

- `ghcr.io/dvm-software-inc/<image>:<env>-<shortsha>` — the deployment identity and
  rollback target. `build.yml` exposes it as `image_tag`, and `deploy.yml` atomically
  writes it to `.env` as `IMAGE_TAG`/`TAG`.
- `ghcr.io/dvm-software-inc/<image>:<env>` — optional moving compatibility alias when
  `publish_moving_tag` is true. Never use it for deployment.

**`:latest` is never pushed — never reference it in a compose file.**

Optional semantic tags (`v1.0.0`) may be added for releases but aren't part of the deploy
pipeline.
