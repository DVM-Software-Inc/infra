#!/usr/bin/env node
// Credentials stay in protected remote runtime/CI storage; never printed or written locally.
import { spawnSync } from 'node:child_process';

function run(command, args, input) {
  const r = spawnSync(command, args, {input, encoding:'utf8', timeout:120000,
    maxBuffer:4*1024*1024, stdio:['pipe','pipe','pipe']});
  if (r.error || r.status !== 0) throw new Error(`${command} failed; raw diagnostics withheld`);
  return r.stdout;
}

const remote = String.raw`
import json, os, pathlib, re, stat, subprocess, sys
try:
    root = pathlib.Path('/opt/apps/chatactorai/dev')
    target = root / '.env'
    tf_path = pathlib.Path('/opt/keycloak/.tf.env')
    for path in (target, tf_path):
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600 or info.st_uid != os.geteuid():
            raise ValueError('Expected operator-owned protected runtime files')
    raw = target.read_text()
    tf = dict(line.split('=',1) for line in tf_path.read_text().splitlines()
              if '=' in line and not line.startswith('#'))
    secret = tf['TF_VAR_chatactorai_web_client_secret']
    if not 48 <= len(secret) <= 256 or any(c in secret for c in "'\\\r\n"):
        raise ValueError('Secret cannot be safely represented by this bounded dotenv writer')
    current = subprocess.run(['docker','compose','-f',str(root/'docker-compose.yml'),
        'config','--format','json'],capture_output=True,text=True,check=True)
    live = json.loads(current.stdout)['services']['api']['environment']
    old = 'https://auth.chatactorai.com/application/o/chatactorai-dev/'
    new = 'https://auth.chatactorai.com/realms/chatactorai-dev'
    if live.get('OIDC_ISSUER_URL') != old:
        raise ValueError('The source environment is not the reviewed legacy dev configuration')
    updates = {
        'OIDC_ISSUER_URL': new,
        'OIDC_CLIENT_ID': 'chatactorai-dev',
        'OIDC_CLIENT_SECRET': secret,
        'OIDC_AUDIENCE': 'chatactorai-dev-api',
        'OIDC_SCOPES': 'openid email profile',
        'OIDC_REDIRECT_URI': 'https://dev.chatactorai.com/auth/callback',
        'OIDC_POST_LOGOUT_REDIRECT_URI': 'https://dev.chatactorai.com/',
        'OIDC_LEGACY_ISSUER_URL': old,
        'KEYCLOAK_DEV_RESET_LEGACY_BINDINGS': '1',
    }
    lines = raw.splitlines()
    for key in updates:
        if sum(bool(re.match(r'^\s*(?:export\s+)?'+key+r'\s*=',line)) for line in lines) > 1:
            raise ValueError('Duplicate runtime key')
    retained = [line for line in lines if not any(re.match(r'^\s*(?:export\s+)?'+key+r'\s*=',line) for key in updates)]
    updated = '\n'.join(retained + [key+"='"+value+"'" for key,value in updates.items()])+'\n'
    backup = root / '.env.pre-keycloak-20260906'
    staged = root / '.env.keycloak-prepared-20260906'
    os.umask(0o077)
    for path, content in ((backup,raw),(staged,updated)):
        if path.exists() or path.is_symlink():
            if not path.is_file() or path.is_symlink() or path.read_text() != content:
                raise ValueError('Existing protected artifact differs; review required')
        else:
            with path.open('x') as handle:
                handle.write(content)
        if stat.S_IMODE(path.stat().st_mode) != 0o600:
            raise ValueError('Artifact permission check failed')
    # Exercise Compose's real env_file parser (including literal dollar signs).
    config = 'services:\n  check:\n    image: scratch\n    env_file:\n      - '+str(staged)+'\n'
    checked = subprocess.run(['docker','compose','-f','-','config','--format','json'],
        input=config,capture_output=True,text=True,check=True)
    actual = json.loads(checked.stdout)['services']['check']['environment']
    if any(actual.get(k) != v for k,v in updates.items()):
        raise ValueError('Staged dotenv round-trip mismatch')
    # This stdout is consumed only by the local secret-safe wrapper, never logged.
    sys.stdout.write(updated)
except Exception:
    print('Protected staging failed; sensitive details withheld.',file=sys.stderr)
    sys.exit(1)
`;

try {
  if (process.argv.slice(2).join(' ') !== '--stage-dev') throw new Error('Expected --stage-dev');
  const quoted = "'" + remote.replaceAll("'", "'\\''") + "'";
  const prepared = run('ssh',['-o','BatchMode=yes','contabo','python3 -c '+quoted]);
  if (!prepared.includes("OIDC_ISSUER_URL='https://auth.chatactorai.com/realms/chatactorai-dev'")) {
    throw new Error('Expected dev issuer absent; no CI write performed');
  }
  run('gh',['secret','set','DEV_ENV_FILE','--repo','DVM-Software-Inc/chatactorai'],prepared);
  console.log('Protected dev inputs staged and GitHub DEV_ENV_FILE updated; app containers unchanged.');
} catch {
  console.error('Release input staging failed; no credential values or raw diagnostics emitted.');
  process.exitCode=1;
}
