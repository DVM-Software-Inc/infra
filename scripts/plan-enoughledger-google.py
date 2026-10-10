#!/usr/bin/env python3
"""Run on the Keycloak VPS; never emit Terraform values or raw diagnostics."""
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path('/opt/keycloak/terraform')
PLAN = ROOT / '.enoughledger-google.tfplan'
ADDRESS = 'module.smb_tax_dev.keycloak_oidc_google_identity_provider.google[0]'
# Observed refresh-only drift on 2026-09-06. These resources must remain no-op;
# this does not authorize changing Architect's live configuration.
REFRESH_ONLY = {
    'module.dvm_architect_dev.keycloak_openid_client.web': {'extra_config'},
    'module.dvm_architect_dev.keycloak_realm.this': {
        'default_default_client_scopes', 'default_optional_client_scopes'},
}
CALLBACK = 'https://auth.enoughledger.com/realms/smb-tax-dev/broker/google/endpoint'
TF = ['docker', 'run', '--rm', '--env-file', '/opt/keycloak/.tf.env',
      '-v', str(ROOT) + ':/wd', '-w', '/wd', 'hashicorp/terraform:1.9']


def tf(*args, allowed=(0,)):
    result = subprocess.run(TF + list(args), capture_output=True, text=True, timeout=180)
    if result.returncode not in allowed:
        raise RuntimeError('Terraform ' + args[0] + ' failed; raw output withheld')
    return result


def inspect_plan():
    document = json.loads(tf('show', '-json', '/wd/' + PLAN.name).stdout)
    changes = [r for r in document.get('resource_changes', [])
               if r['change']['actions'] != ['no-op']]
    drift = [r for r in document.get('resource_drift', [])
             if r['change']['actions'] != ['no-op']]
    print(json.dumps({'changes': [{'address': r['address'], 'actions': r['change']['actions']}
                                  for r in changes],
                      'drift_addresses': [r['address'] for r in drift]}), flush=True)
    for resource in drift:
        before, after = resource['change'].get('before') or {}, resource['change'].get('after') or {}
        fields = {key for key in before.keys() | after.keys() if before.get(key) != after.get(key)}
        planned = next((r for r in document['resource_changes'] if r['address'] == resource['address']), None)
        if (resource['address'] not in REFRESH_ONLY or not fields <= REFRESH_ONLY[resource['address']]
                or planned is None or planned['change']['actions'] != ['no-op']):
            raise RuntimeError('Unreviewed drift detected; do not apply')
    if len(changes) != 1 or changes[0]['address'] != ADDRESS or changes[0]['change']['actions'] != ['create']:
        raise RuntimeError('Plan is not the single intended provider creation; do not apply')
    after = changes[0]['change']['after']
    env = dict(line.split('=', 1) for line in pathlib.Path('/opt/keycloak/.tf.env').read_text().splitlines()
               if '=' in line and not line.startswith('#'))
    realm_module = next(m for m in document['planned_values']['root_module']['child_modules']
                        if m['address'] == 'module.smb_tax_dev')
    realm = next(r['values']['id'] for r in realm_module['resources']
                 if r['address'] == 'module.smb_tax_dev.keycloak_realm.this')
    checks = {
        'correct_realm': bool(realm) and after.get('realm') == realm,
        'client_id_matches_runtime': bool(env.get('TF_VAR_smbtax_google_client_id')) and after.get('client_id') == env['TF_VAR_smbtax_google_client_id'],
        'client_secret_matches_runtime': bool(env.get('TF_VAR_smbtax_google_client_secret')) and after.get('client_secret') == env['TF_VAR_smbtax_google_client_secret'],
        'trust_email_false': after.get('trust_email') is False,
        'store_token_false': after.get('store_token') is False,
        'minimal_scopes': set(after.get('default_scopes', '').split()) == {'openid', 'email', 'profile'},
        'import_sync': after.get('sync_mode') == 'IMPORT',
        'callback_exact': document.get('output_changes', {}).get('smb_tax_dev_google_redirect_uri', {}).get('after') == CALLBACK,
    }
    print(json.dumps(checks), flush=True)
    if not all(checks.values()):
        raise RuntimeError('Provider settings failed validation; do not apply')


try:
    os.umask(0o077)
    action = sys.argv[1] if len(sys.argv) == 2 else ''
    if action not in ('plan', 'inspect', 'apply'):
        raise RuntimeError('Expected plan, inspect or apply')
    if action == 'plan':
        if PLAN.exists() or PLAN.is_symlink():
            raise RuntimeError('A prior plan exists; inspect it before replacing it')
        tf('fmt', '-check', 'main.tf', 'variables.tf')
        validation = json.loads(tf('validate', '-json').stdout)
        if not validation.get('valid'):
            raise RuntimeError('Terraform validation failed; diagnostics withheld')
        print('Terraform validation passed.', flush=True)
        tf('plan', '-input=false', '-lock-timeout=30s', '-detailed-exitcode',
           '-out=/wd/' + PLAN.name, allowed=(0, 2))
        PLAN.chmod(0o600)
        inspect_plan()
        print('Bounded plan ready; nothing applied.', flush=True)
    else:
        if not PLAN.is_file() or PLAN.is_symlink() or (PLAN.stat().st_mode & 0o777) != 0o600:
            raise RuntimeError('Expected protected reviewed plan is missing')
        inspect_plan()
        if action == 'inspect':
            print('Reviewed protected plan passes all bounds; nothing applied.', flush=True)
            sys.exit(0)
        tf('apply', '-input=false', '-lock-timeout=30s', '/wd/' + PLAN.name)
        print('Reviewed EnoughLedger provider plan applied.', flush=True)
        result = tf('plan', '-input=false', '-lock-timeout=30s', '-detailed-exitcode', allowed=(0, 2))
        if result.returncode != 0:
            raise RuntimeError('Post-apply plan still has changes; convergence not confirmed')
        PLAN.unlink()
        print('No-change Terraform convergence confirmed; temporary secret-bearing plan removed.', flush=True)
except Exception as error:
    # Our explicit errors contain only fixed messages, never provider input.
    print(str(error) if type(error) is RuntimeError else 'Operation failed; sensitive details withheld.',
          file=sys.stderr, flush=True)
    sys.exit(1)
