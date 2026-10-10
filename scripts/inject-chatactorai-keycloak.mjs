#!/usr/bin/env node
// Operator-unlocked Vaultwarden only. No credential values on stdout/stderr.
import { spawnSync } from 'node:child_process';

function run(command, args, input) {
  const result = spawnSync(command, args, {
    input, encoding: 'utf8', maxBuffer: 2 * 1024 * 1024, timeout: 120000,
    stdio: ['pipe', 'pipe', 'pipe'],
  });
  if (result.error || result.status !== 0) throw new Error(`${command} failed; raw output withheld`);
  return result.stdout;
}

const success = 'ChatActorAI dev Keycloak inputs transferred and verified; Terraform apply and app cutover not run.';
const remote = String.raw`
import json, os, pathlib, re, stat, sys, tempfile
try:
    supplied = json.load(sys.stdin)
    expected = {
        "TF_VAR_chatactorai_google_client_id",
        "TF_VAR_chatactorai_google_client_secret",
        "TF_VAR_chatactorai_web_client_secret",
    }
    if set(supplied) != expected or not all(isinstance(v, str) for v in supplied.values()):
        raise ValueError("Unexpected inputs")
    if not re.fullmatch(r"[0-9]+-[A-Za-z0-9_-]+\.apps\.googleusercontent\.com", supplied["TF_VAR_chatactorai_google_client_id"]):
        raise ValueError("Invalid Google ID")
    if not re.fullmatch(r"GOCSPX-[A-Za-z0-9_-]+", supplied["TF_VAR_chatactorai_google_client_secret"]):
        raise ValueError("Invalid Google secret")
    if not re.fullmatch(r"[!-~]{48,256}", supplied["TF_VAR_chatactorai_web_client_secret"]):
        raise ValueError("Invalid app secret")
    target = pathlib.Path("/opt/keycloak/.tf.env")
    info = target.lstat()
    if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600 or info.st_uid != os.geteuid():
        raise ValueError("Runtime must be operator-owned regular mode-600 file")
    lines = target.read_text().splitlines()
    for key in expected:
        found = [line.split("=", 1)[1] for line in lines if line.startswith(key + "=")]
        if len(found) > 1 or (found and found[0] not in ("", supplied[key])):
            raise ValueError("Existing input differs; explicit rotation review required")
    retained = [line for line in lines if not any(line.startswith(key + "=") for key in expected)]
    updated = "\n".join(retained + [key + "=" + supplied[key] for key in sorted(expected)]) + "\n"
    if target.read_text() != updated:
        fd, temporary = tempfile.mkstemp(prefix=".tf.env.chatactorai-", dir=target.parent)
        try:
            with os.fdopen(fd, "w") as handle:
                handle.write(updated)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    verified = dict(line.split("=", 1) for line in target.read_text().splitlines() if "=" in line and not line.startswith("#"))
    if not all(verified.get(key) == supplied[key] for key in expected):
        raise ValueError("Round-trip failed")
    print("ChatActorAI dev Keycloak inputs transferred and verified; Terraform apply and app cutover not run.")
except Exception:
    print("Transfer failed; credential-bearing details withheld.", file=sys.stderr)
    sys.exit(1)
`;

try {
  if (process.argv.slice(2).join(' ') !== '--transfer') {
    throw new Error('Usage: node scripts/inject-chatactorai-keycloak.mjs --transfer');
  }
  const status = JSON.parse(run('bw', ['status']));
  if (status.serverUrl !== 'https://vault.dvmsoftware.com' || status.status !== 'unlocked') {
    throw new Error('Unlock Vaultwarden in this Terminal first; never paste BW_SESSION into chat');
  }
  run('bw', ['sync']);
  const googleName = 'google/chatactorai/oauth-dev';
  const webName = 'chatactorai-keycloak-web-client-dev';
  const google = JSON.parse(run('bw', ['get', 'item', googleName]));
  const web = JSON.parse(run('bw', ['get', 'item', webName]));
  if (google.name !== googleName || !google.notes?.split('\n').includes('Project: dvm-chatactorai-dev') ||
      !google.login?.username || !google.login?.password || web.name !== webName ||
      web.login?.username !== 'chatactorai-dev' || !web.login?.password ||
      !web.notes?.includes('Issuer: https://auth.chatactorai.com/realms/chatactorai-dev')) {
    throw new Error('Expected dev vault records or fields missing');
  }
  const payload = JSON.stringify({
    TF_VAR_chatactorai_google_client_id: google.login.username,
    TF_VAR_chatactorai_google_client_secret: google.login.password,
    TF_VAR_chatactorai_web_client_secret: web.login.password,
  });
  const quoted = "'" + remote.replaceAll("'", "'\\''") + "'";
  const response = run('ssh', ['-o', 'BatchMode=yes', 'contabo', 'python3 -c ' + quoted], payload);
  if (response.trim() !== success) throw new Error('Unexpected transfer response; raw output withheld');
  console.log(success);
} catch (error) {
  console.error(error instanceof SyntaxError ? 'Invalid structured response; raw data withheld' : error.message);
  process.exitCode = 1;
}
