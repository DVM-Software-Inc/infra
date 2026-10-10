#!/usr/bin/env node
// Run in an operator-unlocked Vaultwarden shell. Never print credential values.
import { spawnSync } from 'node:child_process';

const itemName = 'google/smb-tax/oauth-dev';
function run(command, args, input) {
  const result = spawnSync(command, args, {
    input, encoding: 'utf8', maxBuffer: 2 * 1024 * 1024, timeout: 120000,
    stdio: ['pipe', 'pipe', 'pipe'],
  });
  if (result.error || result.status !== 0) {
    throw new Error(`${command} failed; raw output withheld to protect credentials`);
  }
  return result.stdout;
}

// This fixed remote program accepts only the two named dev inputs. No Terraform
// apply or app restart is performed; those require a reviewed, bounded plan.
const remote = String.raw`
import json, os, pathlib, re, stat, sys, tempfile
try:
    supplied = json.load(sys.stdin)
    expected = {"TF_VAR_smbtax_google_client_id", "TF_VAR_smbtax_google_client_secret"}
    if set(supplied) != expected:
        raise ValueError("Unexpected inputs")
    if not re.fullmatch(r"[0-9]+-[A-Za-z0-9_-]+\.apps\.googleusercontent\.com", supplied["TF_VAR_smbtax_google_client_id"]):
        raise ValueError("Invalid client ID")
    if not re.fullmatch(r"GOCSPX-[A-Za-z0-9_-]+", supplied["TF_VAR_smbtax_google_client_secret"]):
        raise ValueError("Invalid client secret")
    target = pathlib.Path("/opt/keycloak/.tf.env")
    info = target.lstat()
    if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600 or info.st_uid != os.geteuid():
        raise ValueError("Runtime env must be an operator-owned regular mode-600 file")
    existing = target.read_text()
    lines = existing.splitlines()
    for key in expected:
        if sum(line.startswith(key + "=") for line in lines) > 1:
            raise ValueError("Duplicate runtime input")
    retained = [line for line in lines if not any(line.startswith(key + "=") for key in expected)]
    updated = "\n".join(retained + [key + "=" + supplied[key] for key in sorted(expected)]) + "\n"
    if existing != updated:
        fd, temporary = tempfile.mkstemp(prefix=".tf.env.google-", dir=target.parent)
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
        raise ValueError("Runtime round-trip failed")
    print("EnoughLedger Google dev inputs transferred and verified; Terraform apply not run.")
except Exception:
    print("Transfer failed; credential-bearing details withheld.", file=sys.stderr)
    sys.exit(1)
`;

try {
  if (process.argv.slice(2).join(' ') !== '--transfer') {
    throw new Error('Usage: node scripts/inject-enoughledger-google.mjs --transfer');
  }
  const status = JSON.parse(run('bw', ['status']));
  if (status.serverUrl !== 'https://vault.dvmsoftware.com' || status.status !== 'unlocked') {
    throw new Error('Unlock Vaultwarden in this Terminal first; never paste BW_SESSION into chat');
  }
  run('bw', ['sync']);
  const item = JSON.parse(run('bw', ['get', 'item', itemName]));
  if (item.name !== itemName || !item.login?.username || !item.login?.password ||
      !item.notes?.includes('Project: dvm-enoughledger-dev.')) {
    throw new Error('Expected development OAuth vault item or fields missing');
  }
  const payload = JSON.stringify({
    TF_VAR_smbtax_google_client_id: item.login.username,
    TF_VAR_smbtax_google_client_secret: item.login.password,
  });
  const quoted = "'" + remote.replaceAll("'", "'\\''") + "'";
  const message = run('ssh', ['-o', 'BatchMode=yes', 'contabo', 'python3 -c ' + quoted], payload);
  if (message.trim() !== 'EnoughLedger Google dev inputs transferred and verified; Terraform apply not run.') {
    throw new Error('Unexpected transfer response; raw output withheld');
  }
  console.log(message.trim());
} catch (error) {
  // Parse errors can quote input; only our own fixed diagnostics are safe.
  const safe = error instanceof SyntaxError ? 'Invalid structured response; raw data withheld' : error.message;
  console.error(safe);
  process.exitCode = 1;
}
