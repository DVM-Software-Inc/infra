"""Security assertions for a root executor; every deployment uses a fake runner."""

import base64
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "gate", Path(__file__).parents[1] / "release_gate/gate.py"
)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class GateTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.policy = json.loads(
            (
                Path(__file__).parents[1] / "release_gate/llm-gateway-dev.example.json"
            ).read_text()
        )
        self.policy["repository_id"] = 123
        self.request = {
            "schema": 1,
            "app": "llm-gateway",
            "environment": "dev",
            "commit": "a" * 40,
            "run_id": 1234,
            "run_attempt": 1,
            "images": {
                key: value + "@sha256:" + "b" * 64
                for key, value in self.policy["images"].items()
            },
        }
        self.state_patch = patch.object(gate, "STATE", self.root / "state")
        self.state_patch.start()
        self.addCleanup(self.state_patch.stop)

    def denied(self, request):
        with self.assertRaises(gate.Denied):
            gate.validate_request(request, self.policy)

    def test_exact_registered_digest_request_is_accepted(self):
        self.assertEqual(gate.validate_request(self.request, self.policy), self.request)

    def test_shell_paths_unknown_fields_other_apps_and_prod_are_denied(self):
        cases = [
            ("app", "../prod"),
            ("environment", "prod"),
            ("commit", "a" * 40 + ";id"),
            ("run_id", True),
            ("run_attempt", -1),
            ("schema", True),
            ("command", "id"),
            ("compose", "arbitrary.yml"),
            ("env_file", "DATABASE_URL=stolen"),
        ]
        for field, value in cases:
            with self.subTest(field=field):
                request = deepcopy(self.request)
                request[field] = value
                self.denied(request)

    def test_mutable_tags_foreign_images_digest_injection_and_missing_services_denied(
        self,
    ):
        for image in [
            "ghcr.io/dvm-software-inc/llm-gateway-api:dev",
            "evil.test/api@sha256:" + "b" * 64,
            self.request["images"]["api"] + ";id",
            "ghcr.io/dvm-software-inc/llm-gateway-api@sha256:short",
        ]:
            request = deepcopy(self.request)
            request["images"]["api"] = image
            self.denied(request)
        request = deepcopy(self.request)
        del request["images"]["web"]
        self.denied(request)

    def test_duplicate_json_and_oversized_input_denied(self):
        for raw in [b'{"app":"one","app":"two"}', b"[]", b"x" * (gate.MAX_INPUT + 1)]:
            with self.assertRaises(gate.Denied):
                gate.decode(raw)

    def test_configuration_change_invalidates_manifest(self):
        original = {
            "policy_sha256": "a",
            "compose_sha256": "b",
            "config_sha256": "c",
            "executor_sha256": "d",
        }
        with patch.object(gate, "bindings", return_value=original):
            identity, manifest = gate.seal(self.request, self.policy)
        with (
            patch.object(gate, "read_json", return_value=manifest),
            patch.object(gate, "policy", return_value=self.policy),
            patch.object(
                gate, "bindings", return_value={**original, "config_sha256": "changed"}
            ),
        ):
            with self.assertRaises(gate.Denied):
                gate.load(identity)

    def test_manifest_content_changes_identity(self):
        one = gate.checksum(self.request)
        changed = deepcopy(self.request)
        changed["images"]["api"] = self.policy["images"]["api"] + "@sha256:" + "c" * 64
        self.assertNotEqual(one, gate.checksum(changed))

    def test_production_requires_exact_unexpired_single_use_approval(self):
        identity = "a" * 64
        manifest = {"bindings": {"config_sha256": "fixed"}}
        with self.assertRaises(gate.Denied):
            gate.approval(identity, manifest, consume=False)
        receipt = {
            "manifest_id": identity,
            "bindings": manifest["bindings"],
            "consumed": False,
            "expires_at": 9999999999,
        }
        path = gate.STATE / "approvals" / f"{identity}.json"
        gate.atomic(path, receipt)
        with patch.object(
            gate, "read_json", side_effect=lambda p: json.loads(p.read_text())
        ):
            gate.approval(identity, manifest, consume=True)
            with self.assertRaises(gate.Denied):
                gate.approval(identity, manifest, consume=True)
            for changes in [
                {"manifest_id": "b" * 64},
                {"expires_at": 1},
                {"bindings": {"config_sha256": "new"}},
            ]:
                gate.atomic(path, {**receipt, **changes})
                with self.assertRaises(gate.Denied):
                    gate.approval(identity, manifest, consume=False)

    def key(self, value):
        raw = value.encode()
        fingerprint = "SHA256:" + base64.b64encode(
            hashlib.sha256(raw).digest()
        ).decode().rstrip("=")
        return f"ssh-ed25519 {base64.b64encode(raw).decode()} label", fingerprint

    def test_any_non_owner_shell_key_blocks_production_even_with_restrict(self):
        keyfiles = patch.object(
            gate,
            "privileged_key_files",
            return_value=[(Path("/root/.ssh/authorized_keys"), 0)],
        )
        keyfiles.start()
        self.addCleanup(keyfiles.stop)
        owner, fingerprint = self.key("owner")
        ci, _ = self.key("ci")
        trust = {
            "owner_fingerprints": [fingerprint],
            "registered_apps": ["llm-gateway"],
        }
        for options in ["", "restrict ", 'command="id" ']:
            with (
                patch.object(gate, "read_json", return_value=trust),
                patch.object(
                    gate, "protected", return_value=f"{owner}\n{options}{ci}\n".encode()
                ),
            ):
                with self.assertRaises(gate.Denied):
                    gate.ci_boundary()
        restricted = f'restrict,command="/usr/bin/python3 -I {gate.CODE} ci llm-gateway dev" {ci}'
        with (
            patch.object(gate, "read_json", return_value=trust),
            patch.object(
                gate, "protected", return_value=f"{owner}\n{restricted}\n".encode()
            ),
        ):
            gate.ci_boundary()

    def test_unreviewed_docker_account_blocks_production(self):
        class Group:
            gr_mem = ["unreviewed-ci"]

        with patch.object(gate.grp, "getgrnam", return_value=Group()):
            with self.assertRaises(gate.Denied):
                gate.privileged_key_files({"privileged_accounts": ["root"]})

    def test_ci_cannot_approve_or_execute_production_or_run_scp(self):
        with patch.dict(
            gate.os.environ, {"SSH_ORIGINAL_COMMAND": "dvm-release-request-v1"}
        ):
            with self.assertRaises(gate.Denied):
                gate.owner("approve", "a" * 64, "not an owner")
            with self.assertRaises(gate.Denied):
                gate.ci("llm-gateway", "prod")
        for command in [
            "id",
            "scp -t /root/.ssh",
            "internal-sftp",
            "docker ps",
            "dvm-release-request-v1;id",
        ]:
            with patch.dict(gate.os.environ, {"SSH_ORIGINAL_COMMAND": command}):
                with self.assertRaises(gate.Denied):
                    gate.ci("llm-gateway", "dev")

    def test_run_checks_require_registered_main_success_and_current_attempt(self):
        run = {
            "head_sha": self.request["commit"],
            "head_branch": "main",
            "repository": {"id": 123},
            "run_attempt": 1,
            "event": "push",
            "path": ".github/workflows/ci.yml",
        }
        main = {"object": {"sha": self.request["commit"]}}
        jobs = {
            "total_count": 5,
            "jobs": [
                {"name": name, "status": "completed", "conclusion": "success"}
                for name in self.policy["required_jobs"]
            ],
        }
        with patch.object(gate, "github_json", side_effect=[run, main, jobs]):
            gate.verify_run(self.request, self.policy, "synthetic-token")
        for changes in [
            {"head_branch": "feature"},
            {"head_sha": "b" * 40},
            {"run_attempt": 2},
            {"repository": {"id": 999}},
            {"event": "pull_request"},
            {"path": ".github/workflows/other.yml"},
        ]:
            with patch.object(
                gate, "github_json", side_effect=[{**run, **changes}, main, jobs]
            ):
                with self.assertRaises(gate.Denied):
                    gate.verify_run(self.request, self.policy, "synthetic-token")
        for altered_main, altered_jobs in [
            ({"object": {"sha": "old"}}, jobs),
            (main, {"total_count": 0, "jobs": []}),
        ]:
            with patch.object(
                gate, "github_json", side_effect=[run, altered_main, altered_jobs]
            ):
                with self.assertRaises(gate.Denied):
                    gate.verify_run(self.request, self.policy, "synthetic-token")

    def compose(self):
        return {
            "name": "llm-gateway-dev",
            "services": {
                name: {
                    "user": str(uid),
                    "cap_drop": ["ALL"],
                    "security_opt": ["no-new-privileges:true"],
                }
                for name, uid in self.policy["users"].items()
            },
        }

    def test_rendered_compose_cannot_gain_host_access_or_root(self):
        gate.validate_compose(self.compose(), self.policy)
        for changes in [
            {"privileged": True},
            {"ports": ["22:22"]},
            {"cap_add": ["SYS_ADMIN"]},
            {"volumes": [{"source": "/var/run/docker.sock"}]},
            {"network_mode": "host"},
            {"pid": "host"},
            {"user": "0"},
            {"cap_drop": []},
            {"security_opt": []},
            {"build": "."},
            {"use_api_socket": True},
        ]:
            rendered = self.compose()
            rendered["services"]["api"].update(changes)
            with self.assertRaises(gate.Denied):
                gate.validate_compose(rendered, self.policy)

    def test_dev_executor_never_runs_caller_commands_and_uses_only_fixed_migrations(
        self,
    ):
        manifest = {"request": self.request, "bindings": {"config_sha256": "fixed"}}
        commands = []

        def fake_run(command, **kwargs):
            commands.append(command)
            self.assertEqual(kwargs["environment"]["PATH"], "/usr/bin:/bin")
            if "config" in command:
                return json.dumps(self.compose()).encode()
            if command[0] == "/usr/bin/curl":
                return b'{"status":"ok"}\n200'
            return b""

        with (
            patch.object(gate, "run", side_effect=fake_run),
            patch.object(gate, "load"),
            patch.object(
                gate.tempfile,
                "TemporaryDirectory",
                return_value=tempfile.TemporaryDirectory(dir=self.root),
            ),
        ):
            gate.execute(
                "a" * 64,
                manifest,
                self.policy,
                {"username": "actor", "token": "synthetic-token"},
            )
        self.assertTrue(
            any(command[-3:] == ["alembic", "upgrade", "head"] for command in commands)
        )
        self.assertTrue(
            any(
                "up" in command and "--pull" in command and "never" in command
                for command in commands
            )
        )
        self.assertFalse(
            any("bash" in command or "sh" in command for command in commands)
        )
        self.assertTrue(all("synthetic-token" not in command for command in commands))
        self.assertNotIn("synthetic-token", (gate.STATE / "audit.jsonl").read_text())

    def test_unapproved_prod_stops_before_docker_or_migrations(self):
        manifest = {"request": {**self.request, "environment": "prod"}, "bindings": {}}
        with patch.object(gate, "ci_boundary"), patch.object(gate, "run") as runner:
            with self.assertRaises(gate.Denied):
                gate.execute("a" * 64, manifest, self.policy, None)
            runner.assert_not_called()

    def test_readiness_tolerates_proxy_startup_race_and_still_requires_healthy_https(
        self,
    ):
        with (
            patch.object(
                gate,
                "run",
                side_effect=[gate.Denied("synthetic 404"), b'{"status":"ok"}\n200'],
            ) as runner,
            patch.object(gate.time, "sleep") as sleep,
        ):
            gate.readiness(["https://api.example.test/health/ready"], "a" * 64, {})
        self.assertEqual(runner.call_count, 2)
        sleep.assert_called_once_with(3)
        self.assertNotIn("--insecure", runner.call_args.args[0])
        self.assertNotIn("--location", runner.call_args.args[0])

    def test_readiness_never_accepts_redirects_unhealthy_json_or_broken_tls(self):
        for output in [
            b'{"status":"ok"}\n302',
            b'{"status":"error"}\n200',
            b"not json\n200",
        ]:
            with (
                patch.object(gate, "run", return_value=output) as runner,
                patch.object(gate.time, "sleep"),
            ):
                with self.assertRaises(gate.Denied):
                    gate.readiness(
                        ["https://api.example.test/health/ready"], "a" * 64, {}
                    )
                self.assertEqual(runner.call_count, 12)
        with (
            patch.object(
                gate, "run", side_effect=gate.Denied("synthetic TLS refusal")
            ) as runner,
            patch.object(gate.time, "sleep"),
        ):
            with self.assertRaises(gate.Denied):
                gate.readiness(["https://api.example.test/health/ready"], "a" * 64, {})
            self.assertEqual(runner.call_count, 12)

    def test_readiness_refuses_plaintext_or_missing_checks(self):
        for urls in [[], ["http://api.example.test/health"]]:
            with patch.object(gate, "run") as runner, self.assertRaises(gate.Denied):
                gate.readiness(urls, "a" * 64, {})
            runner.assert_not_called()

    def test_owner_cannot_approve_without_an_interactive_terminal(self):
        manifest = {"request": {**self.request, "environment": "prod"}, "bindings": {}}
        with (
            patch.dict(gate.os.environ, {"SSH_ORIGINAL_COMMAND": ""}),
            patch.object(gate, "load", return_value=(manifest, self.policy)),
            patch.object(gate, "ci_boundary"),
            patch.object(gate.sys, "stdin", io.StringIO("")),
        ):
            with self.assertRaises(gate.Denied):
                gate.owner("approve", "a" * 64, "synthetic release approval")

    def test_ci_cannot_provision_runtime_secrets(self):
        with (
            patch.dict(
                gate.os.environ, {"SSH_ORIGINAL_COMMAND": "dvm-release-request-v1"}
            ),
            patch.object(gate, "run") as runner,
        ):
            with self.assertRaises(gate.Denied):
                gate.configure("llm-gateway", "dev", b"DATABASE_URL=synthetic-secret\n")
            runner.assert_not_called()

    def test_dotenv_rejects_host_compose_build_overrides_and_duplicate_keys(self):
        gate.validate_dotenv(
            b"# names and values stay private\nPROJECT_NAME=llm-gateway\nDATABASE_URL=synthetic-secret\n"
        )
        for raw in [
            b"PROJECT_NAME=one\nPROJECT_NAME=two\n",
            b"COMPOSE_FILE=/tmp/evil.yml\n",
            b"DOCKER_HOST=tcp://evil\n",
            b"IMAGE_TAG=latest\n",
            b"DEPLOY_ENVIRONMENT=prod\n",
            b"PATH=/tmp\n",
            b"LD_PRELOAD=evil\n",
            b"GIT_SHA=forged\n",
            b"invalid assignment\n",
        ]:
            with self.subTest(raw=raw), self.assertRaises(gate.Denied):
                gate.validate_dotenv(raw)

    def test_config_install_validates_first_backs_up_and_never_restarts_or_logs_secrets(
        self,
    ):
        deploy = self.root / "deploy"
        deploy.mkdir()
        (deploy / ".env").write_bytes(b"DATABASE_URL=old-synthetic-secret\n")
        trusted = {**self.policy, "deploy_path": str(deploy)}
        raw = b"PROJECT_NAME=llm-gateway\nDATABASE_URL=new-synthetic-secret\n"
        commands = []

        def fake_run(command, **kwargs):
            commands.append(command)
            return json.dumps(self.compose()).encode()

        with (
            patch.dict(gate.os.environ, {"SSH_ORIGINAL_COMMAND": ""}),
            patch.object(gate, "policy", return_value=trusted),
            patch.object(
                gate, "protected", side_effect=lambda path, **kw: path.read_bytes()
            ),
            patch.object(gate, "run", side_effect=fake_run),
        ):
            result = gate.configure("llm-gateway", "dev", raw)
        self.assertEqual((deploy / ".env").read_bytes(), raw)
        self.assertEqual((deploy / ".env").stat().st_mode & 0o777, 0o600)
        self.assertFalse(result["applications_restarted"])
        self.assertEqual(len(commands), 1)
        self.assertIn("config", commands[0])
        self.assertNotIn("up", commands[0])
        backups = list((gate.STATE / "config-backups").glob("*.env"))
        self.assertEqual(
            backups[0].read_bytes(), b"DATABASE_URL=old-synthetic-secret\n"
        )
        self.assertNotIn("synthetic-secret", (gate.STATE / "audit.jsonl").read_text())

    def test_invalid_rendered_config_cannot_replace_existing_runtime_config(self):
        deploy = self.root / "deploy"
        deploy.mkdir()
        previous = b"DATABASE_URL=preserved-synthetic-secret\n"
        (deploy / ".env").write_bytes(previous)
        trusted = {**self.policy, "deploy_path": str(deploy)}
        with (
            patch.dict(gate.os.environ, {"SSH_ORIGINAL_COMMAND": ""}),
            patch.object(gate, "policy", return_value=trusted),
            patch.object(
                gate, "protected", side_effect=lambda path, **kw: path.read_bytes()
            ),
            patch.object(
                gate, "run", return_value=b'{"name":"wrong-project","services":{}}'
            ),
        ):
            with self.assertRaises(gate.Denied):
                gate.configure(
                    "llm-gateway", "dev", b"DATABASE_URL=rejected-synthetic-secret\n"
                )
        self.assertEqual((deploy / ".env").read_bytes(), previous)
        self.assertFalse(list(deploy.glob(".env.pending-*")))

    def test_config_audit_failure_preserves_previous_runtime_config(self):
        deploy = self.root / "deploy"
        deploy.mkdir()
        previous = b"DATABASE_URL=preserved-synthetic-secret\n"
        (deploy / ".env").write_bytes(previous)
        trusted = {**self.policy, "deploy_path": str(deploy)}
        with (
            patch.dict(gate.os.environ, {"SSH_ORIGINAL_COMMAND": ""}),
            patch.object(gate, "policy", return_value=trusted),
            patch.object(
                gate, "protected", side_effect=lambda path, **kw: path.read_bytes()
            ),
            patch.object(gate, "run", return_value=json.dumps(self.compose()).encode()),
            patch.object(
                gate, "audit", side_effect=OSError("synthetic audit unavailable")
            ),
        ):
            with self.assertRaises(OSError):
                gate.configure(
                    "llm-gateway", "dev", b"DATABASE_URL=rejected-synthetic-secret\n"
                )
        self.assertEqual((deploy / ".env").read_bytes(), previous)
        self.assertFalse(list(deploy.glob(".env.pending-*")))


if __name__ == "__main__":
    unittest.main()
