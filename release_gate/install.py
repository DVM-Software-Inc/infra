#!/usr/bin/env python3
"""Management-only installer. Never called by CI and never reads a private SSH key."""

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def fingerprint(line):
    match = re.search(
        r"(?:^|\s)(ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp256)\s+(\S+)", line
    )
    if not match:
        return None
    return "SHA256:" + base64.b64encode(
        hashlib.sha256(base64.b64decode(match[2], validate=True)).digest()
    ).decode().rstrip("=")


def install_file(source, target, mode):
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if target.is_symlink():
        raise SystemExit("Refusing symlink target")
    temporary = target.with_suffix(target.suffix + ".new")
    with temporary.open("wb") as stream:
        stream.write(source.read_bytes())
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(temporary, mode)
    os.chown(temporary, 0, 0)
    os.replace(temporary, target)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--compose", required=True, type=Path)
    parser.add_argument("--owner-fingerprint", required=True)
    parser.add_argument("--ci-fingerprint", required=True)
    parser.add_argument("--activate-key", action="store_true")
    args = parser.parse_args()
    if os.geteuid() != 0 or os.environ.get("SSH_ORIGINAL_COMMAND"):
        raise SystemExit("Use the owner management connection")
    os.umask(0o077)
    policy = json.loads(args.policy.read_text())
    app = policy["app"]
    if not re.fullmatch("[a-z][a-z0-9-]{0,63}", app) or policy["environment"] != "dev":
        raise SystemExit("This installer accepts one dev app at a time")
    if policy["compose"] != f"/etc/dvm-release/{app}-dev.compose.yml":
        raise SystemExit("Unexpected protected Compose path")
    if policy["repository_id"] <= 0:
        raise SystemExit("Set the immutable GitHub repository ID first")
    keys_path = Path("/root/.ssh/authorized_keys")
    lines = keys_path.read_text().splitlines()
    owner_lines = [
        line for line in lines if fingerprint(line) == args.owner_fingerprint
    ]
    ci_lines = [line for line in lines if fingerprint(line) == args.ci_fingerprint]
    if (
        len(owner_lines) != 1
        or len(ci_lines) != 1
        or args.owner_fingerprint == args.ci_fingerprint
    ):
        raise SystemExit("Expected distinct, unique owner and CI identities")
    root = Path("/etc/dvm-release")
    code = Path("/usr/local/lib/dvm-release")
    state = Path("/var/lib/dvm-release")
    for directory in (root, code, state):
        if directory.is_symlink():
            raise SystemExit("Refusing symlink directory")
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chown(directory, 0, 0)
        os.chmod(directory, 0o700)
    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%S%fZ")
    backup = Path("/opt/backups/dvm-release") / stamp
    backup.mkdir(parents=True, mode=0o700)
    shutil.copy2(keys_path, backup / "authorized_keys")
    os.chmod(backup / "authorized_keys", 0o600)
    for old in root.glob("*"):
        if old.is_file() and not old.is_symlink():
            shutil.copy2(old, backup / old.name)
    if (code / "gate.py").exists():
        shutil.copy2(code / "gate.py", backup / "gate.py")
    install_file(Path(__file__).with_name("gate.py"), code / "gate.py", 0o600)
    install_file(args.compose, root / f"{app}-dev.compose.yml", 0o600)
    install_file(args.policy, root / f"{app}-dev.json", 0o600)
    trust_path = root / "trust.json"
    trust = (
        json.loads(trust_path.read_text())
        if trust_path.exists()
        else {
            "owner_fingerprints": [],
            "registered_apps": [],
            "privileged_accounts": ["root"],
        }
    )
    trust["owner_fingerprints"] = sorted(
        set(trust["owner_fingerprints"]) | {args.owner_fingerprint}
    )
    trust["registered_apps"] = sorted(set(trust["registered_apps"]) | {app})
    with tempfile.NamedTemporaryFile(mode="w", dir=root, delete=False) as stream:
        json.dump(trust, stream)
        stream.flush()
        os.fsync(stream.fileno())
        trust_tmp = Path(stream.name)
    os.replace(trust_tmp, trust_path)
    subprocess.run(
        ["/usr/bin/python3", "-I", "-m", "py_compile", str(code / "gate.py")],
        check=True,
    )
    if args.activate_key:
        command = f'restrict,command="/usr/bin/python3 -I {code}/gate.py ci {app} dev"'
        replacement = None
        for index, line in enumerate(lines):
            if fingerprint(line) == args.ci_fingerprint:
                match = re.search(r"(ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp256)\s+", line)
                replacement = command + " " + line[match.start() :]
                lines[index] = replacement
        if not replacement or owner_lines[0] not in lines:
            raise SystemExit("Owner recovery check failed")
        with tempfile.NamedTemporaryFile(
            mode="w", dir=keys_path.parent, delete=False
        ) as stream:
            stream.write("\n".join(lines) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
            temporary = Path(stream.name)
        os.chmod(temporary, 0o600)
        os.replace(temporary, keys_path)
    print(
        json.dumps(
            {
                "installed": app,
                "ci_key_restricted": args.activate_key,
                "backup": str(backup),
                "production_enabled": False,
                "owner_key_preserved": True,
            }
        )
    )


if __name__ == "__main__":
    main()
