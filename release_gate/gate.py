#!/usr/bin/env python3
"""Root-owned release executor. SSH callers supply data, never shell or Compose code."""

from __future__ import annotations

import base64
import contextlib
import datetime as dt
import fcntl
import grp
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = Path("/etc/dvm-release")
STATE = Path("/var/lib/dvm-release")
CODE = Path("/usr/local/lib/dvm-release/gate.py")
DOCKER = ["/usr/bin/docker", "--host", "unix:///var/run/docker.sock"]
MAX_INPUT = 32_768
SHA = re.compile(r"[0-9a-f]{40}")
DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
NAME = re.compile(r"[a-z][a-z0-9-]{0,63}")


class Denied(Exception):
    pass


def require(ok: object, message: str) -> None:
    if not ok:
        raise Denied(message)


def canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()


def checksum(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def no_duplicates(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def decode(raw: bytes) -> dict:
    require(len(raw) <= MAX_INPUT, "request too large")
    try:
        result = json.loads(raw, object_pairs_hook=no_duplicates)
    except (ValueError, UnicodeError):
        raise Denied("invalid JSON") from None
    require(isinstance(result, dict), "JSON object required")
    return result


def protected(path: Path, *, secret: bool = False, account_uid: int = 0) -> bytes:
    require(path.is_absolute(), "absolute protected path required")
    for current in [*reversed(path.parents), path]:
        info = current.lstat()
        require(not stat.S_ISLNK(info.st_mode), "protected path contains a symlink")
        require(
            info.st_uid in (0, account_uid) and not info.st_mode & 0o022,
            "protected path has unsafe ownership or permissions",
        )
    info = path.stat()
    require(stat.S_ISREG(info.st_mode), "protected regular file required")
    if secret:
        require(
            stat.S_IMODE(info.st_mode) == 0o600, "protected secrets must have mode 0600"
        )
    return path.read_bytes()


def read_json(path: Path) -> dict:
    return decode(protected(path))


def atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(prefix=".new-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(canonical(value))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        Path(name).unlink(missing_ok=True)


def audit(event: str, manifest_id: str, **fields: object) -> None:
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    line = (
        canonical(
            {
                "at": dt.datetime.now(dt.UTC).isoformat(),
                "event": event,
                "manifest_id": manifest_id,
                **fields,
            }
        )
        + b"\n"
    )
    fd = os.open(
        STATE / "audit.jsonl",
        os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(fd, "ab") as stream:
        stream.write(line)
        stream.flush()
        os.fsync(stream.fileno())


def policy(app: str, environment: str, *, allow_disabled: bool = False) -> dict:
    require(
        bool(NAME.fullmatch(app)) and environment in ("dev", "prod"), "unknown target"
    )
    result = read_json(ROOT / f"{app}-{environment}.json")
    require(
        result["app"] == app and result["environment"] == environment,
        "policy target mismatch",
    )
    require(
        type(result.get("enabled")) is bool, "explicit owner enablement policy required"
    )
    require(result["enabled"] or allow_disabled, "target is disabled by owner policy")
    require(
        result["deploy_path"] == f"/opt/apps/{app}/{environment}",
        "invalid deployment path",
    )
    return result


def validate_request(request: dict, trusted: dict) -> dict:
    require(
        set(request)
        == {
            "schema",
            "app",
            "environment",
            "commit",
            "run_id",
            "run_attempt",
            "images",
        },
        "unsupported request fields",
    )
    require(
        type(request["schema"]) is int and request["schema"] == 1, "unsupported schema"
    )
    require(
        request["app"] == trusted["app"]
        and request["environment"] == trusted["environment"],
        "request is outside the SSH identity scope",
    )
    require(
        isinstance(request["commit"], str) and SHA.fullmatch(request["commit"]),
        "invalid commit",
    )
    for key in ("run_id", "run_attempt"):
        require(
            type(request[key]) is int and 0 < request[key] < 10**16,
            "invalid run identity",
        )
    images = request["images"]
    require(
        isinstance(images, dict) and set(images) == set(trusted["images"]),
        "image set mismatch",
    )
    for service, image in images.items():
        require(isinstance(image, str), "invalid image")
        repository, separator, digest = image.partition("@")
        require(
            separator
            and repository == trusted["images"][service]
            and DIGEST.fullmatch(digest),
            "only the registered repository and immutable sha256 digest are allowed",
        )
    return request


def bindings(trusted: dict) -> dict:
    deploy = Path(trusted["deploy_path"])
    return {
        "policy_sha256": checksum(trusted),
        "compose_sha256": hashlib.sha256(
            protected(Path(trusted["compose"]))
        ).hexdigest(),
        "config_sha256": hashlib.sha256(
            protected(deploy / ".env", secret=True)
        ).hexdigest(),
        "executor_sha256": hashlib.sha256(protected(CODE)).hexdigest(),
    }


def seal(request: dict, trusted: dict) -> tuple[str, dict]:
    manifest = {
        "request": validate_request(request, trusted),
        "bindings": bindings(trusted),
    }
    identity = checksum(manifest)
    atomic(STATE / "manifests" / f"{identity}.json", manifest)
    return identity, manifest


def load(identity: str) -> tuple[dict, dict]:
    require(bool(re.fullmatch(r"[0-9a-f]{64}", identity)), "invalid manifest ID")
    manifest = read_json(STATE / "manifests" / f"{identity}.json")
    require(checksum(manifest) == identity, "manifest digest mismatch")
    request = manifest["request"]
    trusted = policy(request["app"], request["environment"])
    validate_request(request, trusted)
    require(
        manifest["bindings"] == bindings(trusted),
        "configuration, policy or executor changed; prepare again",
    )
    return manifest, trusted


def github_json(repository: str, route: str, token: str) -> dict:
    require(
        bool(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository)),
        "invalid repository",
    )
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repository}/{route}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "dvm-release-gate",
        },
    )

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            raise Denied("GitHub redirects are not allowed")

    try:
        with urllib.request.build_opener(NoRedirect).open(
            request, timeout=15
        ) as response:
            raw = response.read(2_000_001)
            require(len(raw) <= 2_000_000, "GitHub response too large")
            return json.loads(raw)
    except (OSError, ValueError):
        raise Denied("GitHub provenance lookup failed") from None


def verify_run(request: dict, trusted: dict, token: str) -> None:
    run = github_json(trusted["repository"], f"actions/runs/{request['run_id']}", token)
    require(
        run.get("head_sha") == request["commit"] and run.get("head_branch") == "main",
        "release must be from main at the tested commit",
    )
    require(
        run.get("repository", {}).get("id") == trusted["repository_id"],
        "repository identity mismatch",
    )
    require(
        run.get("run_attempt") == request["run_attempt"]
        and run.get("event") in ("push", "workflow_dispatch"),
        "run attempt or event mismatch",
    )
    require(run.get("path") == ".github/workflows/ci.yml", "unregistered workflow")
    main = github_json(trusted["repository"], "git/ref/heads/main", token)
    require(
        main.get("object", {}).get("sha") == request["commit"],
        "stale main release refused",
    )
    jobs = github_json(
        trusted["repository"],
        f"actions/runs/{request['run_id']}/attempts/{request['run_attempt']}/jobs?per_page=100",
        token,
    )
    require(
        jobs.get("total_count", 101) <= 100, "too many jobs for bounded verification"
    )
    successful = {
        job["name"]
        for job in jobs.get("jobs", [])
        if job.get("status") == "completed" and job.get("conclusion") == "success"
    }
    require(
        set(trusted["required_jobs"]) <= successful,
        "required tests and image builds must pass first",
    )


def privileged_key_files(trust: dict) -> list[tuple[Path, int]]:
    accounts = set(trust.get("privileged_accounts", ["root"]))
    require("root" in accounts, "root management account must be registered")
    for group in ("docker", "sudo", "wheel"):
        try:
            members = set(grp.getgrnam(group).gr_mem)
        except KeyError:
            continue
        require(members <= accounts, "unreviewed Docker/sudo account blocks production")
    files = [(Path("/root/.ssh/authorized_keys"), 0)]
    for account in pwd.getpwall():
        if account.pw_name == "root":
            continue
        require(account.pw_uid != 0, "additional UID 0 account blocks production")
        path = Path(account.pw_dir) / ".ssh/authorized_keys"
        if path.exists():
            require(
                account.pw_name in accounts, "unreviewed SSH account blocks production"
            )
            files.append((path, account.pw_uid))
    return files


def ci_boundary() -> None:
    trust = read_json(ROOT / "trust.json")
    owners = set(trust["owner_fingerprints"])
    require(owners, "owner management identity required")
    commands = {
        f'restrict,command="/usr/bin/python3 -I {CODE} ci {app} dev"'
        for app in trust["registered_apps"]
    }
    owner_seen = False
    for path, uid in privileged_key_files(trust):
        for line in protected(path, secret=True, account_uid=uid).decode().splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            match = re.search(
                r"(?:^|\s)(ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp256)\s+(\S+)", line
            )
            require(match is not None, "unrecognized SSH key must be reviewed by owner")
            fingerprint = "SHA256:" + base64.b64encode(
                hashlib.sha256(base64.b64decode(match[2], validate=True)).digest()
            ).decode().rstrip("=")
            if fingerprint in owners:
                owner_seen = True
            else:
                require(
                    uid == 0 and line[: match.start()].strip() in commands,
                    "production blocked: a non-owner SSH key still has shell or unregistered access",
                )
    require(owner_seen, "owner management recovery key missing")


def approval(identity: str, manifest: dict, *, consume: bool) -> None:
    receipt_path = STATE / "approvals" / f"{identity}.json"
    require(receipt_path.exists(), "production requires exact owner approval")
    receipt = read_json(receipt_path)
    require(
        receipt.get("manifest_id") == identity and receipt.get("consumed") is False,
        "approval is mismatched or already consumed",
    )
    require(
        receipt.get("expires_at", 0) > dt.datetime.now(dt.UTC).timestamp(),
        "approval expired",
    )
    require(
        receipt.get("bindings") == manifest["bindings"],
        "approval configuration changed",
    )
    if consume:
        receipt["consumed"] = True
        atomic(receipt_path, receipt)
        audit("approval.consumed", identity)


def run(
    command: list[str], *, environment: dict, input_bytes: bytes | None = None
) -> bytes:
    # Captured output may contain application messages/secrets. It is never relayed to CI.
    result = subprocess.run(
        command,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
        timeout=900,
        check=False,
    )
    require(
        result.returncode == 0,
        "release command failed; owner must inspect protected host diagnostics",
    )
    return result.stdout


def execute(
    identity: str, manifest: dict, trusted: dict, credentials: dict | None
) -> None:
    request = manifest["request"]
    production = request["environment"] == "prod"
    if production:
        ci_boundary()
        approval(identity, manifest, consume=False)
    with tempfile.TemporaryDirectory(prefix="dvm-release-", dir="/run") as directory:
        work = Path(directory)
        environment = {
            "PATH": "/usr/bin:/bin",
            "HOME": "/root",
            "DOCKER_CONFIG": str(work / "docker"),
            "IMAGE_TAG": f"{request['environment']}-{request['commit'][:7]}",
            "DEPLOY_ENVIRONMENT": request["environment"],
        }
        override = {
            "services": {
                service: {
                    "image": request["images"][image],
                    "user": str(trusted["users"][service]),
                }
                for service, image in trusted["services"].items()
            }
        }
        (work / "images.json").write_bytes(canonical(override))
        command = [
            *DOCKER,
            "compose",
            "--project-directory",
            trusted["deploy_path"],
            "--env-file",
            str(Path(trusted["deploy_path"]) / ".env"),
            "-f",
            trusted["compose"],
            "-f",
            str(work / "images.json"),
        ]
        if credentials:
            require(
                set(credentials) == {"username", "token"}
                and isinstance(credentials["token"], str)
                and 0 < len(credentials["token"]) <= 4096
                and re.fullmatch(r"[A-Za-z0-9_-]+", credentials["username"]),
                "invalid registry credential",
            )
            run(
                [
                    *DOCKER,
                    "login",
                    "ghcr.io",
                    "--username",
                    credentials["username"],
                    "--password-stdin",
                ],
                environment=environment,
                input_bytes=credentials["token"].encode(),
            )
        rendered = json.loads(
            run(
                [*command, "--profile", "maintenance", "config", "--format", "json"],
                environment=environment,
            )
        )
        validate_compose(rendered, trusted)
        if production:
            # Promotion reuses the exact images already tested/pulled in dev. Production
            # has no CI registry credential and never resolves a mutable tag.
            for image in request["images"].values():
                details = json.loads(
                    run([*DOCKER, "image", "inspect", image], environment=environment)
                )
                require(
                    image in details[0].get("RepoDigests", []),
                    "tested image digest is not cached",
                )
        else:
            run([*command, "pull"], environment=environment)
        # Recheck protected inputs after potentially slow registry operations.
        load(identity)
        if production:
            ci_boundary()
            approval(identity, manifest, consume=True)
        atomic(
            STATE / "attempts" / f"{identity}.json",
            {"state": "started", "manifest_id": identity},
        )
        audit(
            "deployment.started",
            identity,
            app=request["app"],
            environment=request["environment"],
        )
        for migration in trusted["migrations"]:
            require(
                isinstance(migration, list)
                and migration
                and all(isinstance(v, str) for v in migration),
                "invalid owner migration policy",
            )
            run(
                [
                    *command,
                    "run",
                    "--rm",
                    "--no-deps",
                    "--pull",
                    "never",
                    "migrate",
                    *migration,
                ],
                environment=environment,
            )
        run(
            [
                *command,
                "up",
                "-d",
                "--no-build",
                "--pull",
                "never",
                "--remove-orphans",
                "--wait",
                "--wait-timeout",
                "180",
            ],
            environment=environment,
        )
        readiness(trusted["smoke_urls"], identity, environment)
        previous = STATE / "current" / f"{request['app']}-{request['environment']}.json"
        if previous.exists():
            atomic(STATE / "previous" / previous.name, read_json(previous))
        atomic(previous, {"manifest_id": identity, "manifest": manifest})
        atomic(
            STATE / "attempts" / f"{identity}.json",
            {"state": "succeeded", "manifest_id": identity},
        )
        audit(
            "deployment.succeeded",
            identity,
            app=request["app"],
            environment=request["environment"],
        )


def readiness(urls: list[str], identity: str, environment: dict) -> None:
    require(bool(urls), "readiness checks are required")
    for index, url in enumerate(urls):
        require(url.startswith("https://"), "verified HTTPS readiness required")
        for attempt in range(12):
            try:
                output = run(
                    [
                        "/usr/bin/curl",
                        "--fail",
                        "--silent",
                        "--show-error",
                        "--max-time",
                        "10",
                        "--write-out",
                        "\n%{http_code}",
                        url,
                    ],
                    environment=environment,
                )
                body, _, status_code = output.rpartition(b"\n")
                require(status_code == b"200", "readiness must return HTTP 200")
                require(
                    json.loads(body).get("status") == "ok",
                    "readiness JSON is not healthy",
                )
                break
            except (Denied, ValueError, AttributeError):
                if attempt == 11:
                    raise Denied("readiness checks did not become healthy") from None
                audit(
                    "deployment.readiness_retry",
                    identity,
                    check_index=index,
                    attempt=attempt + 1,
                )
                time.sleep(3)


def validate_compose(rendered: dict, trusted: dict) -> None:
    require(
        rendered.get("name") == f"{trusted['app']}-{trusted['environment']}",
        "Compose project mismatch",
    )
    require(
        set(rendered["services"]) == set(trusted["services"]),
        "Compose service mismatch",
    )
    for name, service in rendered["services"].items():
        require(
            not any(
                service.get(key)
                for key in (
                    "privileged",
                    "ports",
                    "devices",
                    "cap_add",
                    "volumes_from",
                    "build",
                    "develop",
                    "use_api_socket",
                )
            ),
            "unsafe service privileges",
        )
        require(
            service.get("network_mode") is None
            and service.get("pid") is None
            and service.get("ipc") not in ("host",)
            and service.get("userns_mode") != "host",
            "host namespace forbidden",
        )
        require(
            service.get("user") == str(trusted["users"][name]),
            "non-root numeric user required",
        )
        require(
            str(trusted["users"][name]).isdigit() and int(trusted["users"][name]) > 0,
            "root user forbidden",
        )
        require(
            set(service.get("cap_drop", [])) == {"ALL"}
            and "no-new-privileges:true" in service.get("security_opt", []),
            "container protections required",
        )
        require(
            not service.get("volumes"),
            "host and engine volumes are not approved for this pilot",
        )


def validate_dotenv(raw: bytes) -> None:
    require(
        0 < len(raw) <= MAX_INPUT and b"\0" not in raw,
        "invalid configuration size/content",
    )
    keys = set()
    for line in raw.decode("utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(r"([A-Z][A-Z0-9_]*)=(.*)", line)
        require(
            match is not None,
            "configuration must contain single-line uppercase assignments",
        )
        key = match[1]
        require(key not in keys, "duplicate configuration key")
        require(
            key
            not in {
                "TAG",
                "IMAGE_TAG",
                "DEPLOY_ENVIRONMENT",
                "GIT_SHA",
                "PATH",
                "HOME",
                "BASH_ENV",
                "ENV",
            }
            and not key.startswith(("COMPOSE_", "DOCKER_", "LD_", "PYTHON")),
            "host/build/deploy environment overrides are forbidden",
        )
        keys.add(key)


def configure(app: str, environment: str, raw: bytes) -> dict:
    require(
        not os.environ.get("SSH_ORIGINAL_COMMAND"),
        "CI cannot provision runtime configuration",
    )
    validate_dotenv(raw)
    trusted = policy(app, environment, allow_disabled=True)
    deploy = Path(trusted["deploy_path"])
    # Initial config provision belongs to the explicit environment foundation runbook.
    # This command rotates an existing protected config, not arbitrary host files.
    with locked(app, environment):
        existing = protected(deploy / ".env", secret=True)
        fd, filename = tempfile.mkstemp(prefix=".env.pending-", dir=deploy)
        candidate = Path(filename)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            env = {
                "PATH": "/usr/bin:/bin",
                "HOME": "/root",
                "DEPLOY_ENVIRONMENT": environment,
                "IMAGE_TAG": environment + "-config-validation",
            }
            rendered = json.loads(
                run(
                    [
                        *DOCKER,
                        "compose",
                        "--project-directory",
                        str(deploy),
                        "--env-file",
                        str(candidate),
                        "-f",
                        trusted["compose"],
                        "--profile",
                        "maintenance",
                        "config",
                        "--format",
                        "json",
                    ],
                    environment=env,
                )
            )
            validate_compose(rendered, trusted)
            backup = STATE / "config-backups"
            backup.mkdir(mode=0o700, exist_ok=True)
            old_digest = hashlib.sha256(existing).hexdigest()
            old_path = backup / f"{app}-{environment}-{old_digest}.env"
            if not old_path.exists():
                backup_fd = os.open(
                    old_path,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                    0o600,
                )
                with os.fdopen(backup_fd, "wb") as stream:
                    stream.write(existing)
                    stream.flush()
                    os.fsync(stream.fileno())
            digest = hashlib.sha256(raw).hexdigest()
            audit(
                "configuration.installing",
                "",
                app=app,
                environment=environment,
                config_sha256=digest,
                previous_config_sha256=old_digest,
            )
            os.replace(candidate, deploy / ".env")
            directory_fd = os.open(deploy, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
            audit(
                "configuration.installed",
                "",
                app=app,
                environment=environment,
                config_sha256=digest,
                previous_config_sha256=old_digest,
            )
            return {
                "state": "configured",
                "app": app,
                "environment": environment,
                "config_sha256": digest,
                "applications_restarted": False,
            }
        finally:
            candidate.unlink(missing_ok=True)


@contextlib.contextmanager
def locked(app: str, environment: str):
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (STATE / f"{app}-{environment}.lock").open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def ci(app: str, environment: str) -> dict:
    require(environment == "dev", "CI cannot execute production")
    require(
        os.environ.get("SSH_ORIGINAL_COMMAND") == "dvm-release-request-v1",
        "only the release protocol is allowed",
    )
    trusted = policy(app, environment)
    envelope = decode(sys.stdin.buffer.read(MAX_INPUT + 1))
    require(set(envelope) == {"request", "registry"}, "unsupported envelope")
    request = validate_request(envelope["request"], trusted)
    credentials = envelope["registry"]
    require(
        isinstance(credentials, dict) and isinstance(credentials.get("token"), str),
        "registry credential required",
    )
    verify_run(request, trusted, credentials["token"])
    with locked(app, environment):
        identity, manifest = seal(request, trusted)
        try:
            execute(identity, manifest, trusted, credentials)
        except Exception:
            atomic(
                STATE / "attempts" / f"{identity}.json",
                {"state": "failed", "manifest_id": identity},
            )
            audit("deployment.failed", identity, app=app, environment=environment)
            raise
    return {"manifest_id": identity, "state": "succeeded"}


def owner(action: str, identity: str, reason: str = "") -> dict:
    require(
        not os.environ.get("SSH_ORIGINAL_COMMAND"), "CI cannot access owner commands"
    )
    manifest, trusted = load(identity)
    request = manifest["request"]
    if action == "show":
        return {"manifest_id": identity, **manifest}
    if action == "promote":
        require(request["environment"] == "dev", "only a dev release can be promoted")
        current = read_json(STATE / "current" / f"{request['app']}-dev.json")
        require(
            current["manifest_id"] == identity,
            "only the current accepted dev release can be promoted",
        )
        target = policy(request["app"], "prod")
        promoted = {**request, "environment": "prod"}
        new_id, new_manifest = seal(promoted, target)
        audit("candidate.prepared", new_id, source_manifest=identity)
        return {"manifest_id": new_id, **new_manifest}
    require(
        request["environment"] == "prod",
        "owner approval applies to production releases",
    )
    with locked(request["app"], "prod"):
        if action == "approve":
            ci_boundary()
            require(
                sys.stdin.isatty() and sys.stdout.isatty(),
                "owner approval requires an interactive management terminal",
            )
            require(10 <= len(reason) <= 500, "a release reason is required")
            print(json.dumps({"manifest_id": identity, **manifest}, indent=2))
            require(
                input(
                    "Owner: type the complete manifest ID to approve this exact release: "
                )
                == identity,
                "owner approval was not confirmed",
            )
            atomic(
                STATE / "approvals" / f"{identity}.json",
                {
                    "manifest_id": identity,
                    "bindings": manifest["bindings"],
                    "reason": reason,
                    "consumed": False,
                    "expires_at": (
                        dt.datetime.now(dt.UTC) + dt.timedelta(minutes=15)
                    ).timestamp(),
                },
            )
            audit("owner.approved", identity, reason=reason)
        elif action == "deploy":
            execute(identity, manifest, trusted, credentials=None)
        else:
            raise Denied("unknown owner operation")
    return {"manifest_id": identity, "state": action}


def main() -> int:
    os.umask(0o077)
    try:
        require(os.geteuid() == 0, "root-owned executor required")
        protected(CODE)
        require(
            len(sys.argv) >= 4,
            "expected ci APP dev or owner ACTION MANIFEST_ID [REASON]",
        )
        if sys.argv[1] == "configure":
            require(len(sys.argv) == 4, "unsupported arguments")
            require(
                not os.environ.get("SSH_ORIGINAL_COMMAND"),
                "CI cannot provision configuration",
            )
            result = configure(
                sys.argv[2], sys.argv[3], sys.stdin.buffer.read(MAX_INPUT + 1)
            )
        elif sys.argv[1] == "ci":
            require(len(sys.argv) == 4, "unsupported arguments")
            result = ci(sys.argv[2], sys.argv[3])
        else:
            require(
                sys.argv[1] == "owner" and len(sys.argv) in (4, 5),
                "unsupported arguments",
            )
            result = owner(
                sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) == 5 else ""
            )
        print(json.dumps(result, sort_keys=True))
        return 0
    except (
        Denied,
        KeyError,
        TypeError,
        ValueError,
        OSError,
        RecursionError,
        subprocess.TimeoutExpired,
    ):
        # No request/credential/subprocess output reaches the caller on failure.
        print(
            '{"state":"denied","message":"release refused; check scope, passed checks and owner policy"}',
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
