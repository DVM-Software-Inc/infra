#!/usr/bin/env python3
"""Run on the VPS. Inspect/apply only the new ChatActorAI dev realm; no raw secrets."""
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path('/opt/keycloak/terraform')
PLAN = ROOT / '.chatactorai-dev.tfplan'
PREFIX = 'module.chatactorai_dev.'
EXPECTED = {
    'keycloak_realm.this', 'keycloak_realm_events.this',
    'keycloak_oidc_google_identity_provider.google[0]',
    'keycloak_openid_client.web', 'keycloak_role.viewer', 'keycloak_role.admin',
    'keycloak_openid_user_realm_role_protocol_mapper.web_realm_roles',
    'keycloak_openid_audience_protocol_mapper.web_api_audience[0]',
}
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
    if drift:
        print(json.dumps({'drift_fields': [
            {'address': r['address'], 'fields': sorted(
                k for k in (r['change'].get('before') or {}).keys() | (r['change'].get('after') or {}).keys()
                if (r['change'].get('before') or {}).get(k) != (r['change'].get('after') or {}).get(k)),
             'planned_actions': next(x['change']['actions'] for x in document['resource_changes']
                                     if x['address'] == r['address'])}
            for r in drift]}), flush=True)
        for resource in drift:
            before = resource['change'].get('before') or {}
            after = resource['change'].get('after') or {}
            fields = {k for k in before.keys() | after.keys() if before.get(k) != after.get(k)}
            planned = next(r for r in document['resource_changes']
                           if r['address'] == resource['address'])
            # Reviewed provider refresh metadata only. No live EnoughLedger
            # update is authorized; any actual change still fails the guard.
            if (resource['address'] != 'module.smb_tax_dev.keycloak_oidc_google_identity_provider.google[0]'
                    or fields != {'extra_config'} or planned['change']['actions'] != ['no-op']):
                raise RuntimeError('Unreviewed drift; do not apply')
    if ({r['address'] for r in changes} != {PREFIX + a for a in EXPECTED}
            or any(r['change']['actions'] != ['create'] for r in changes)):
        raise RuntimeError('Plan is not exclusively the eight expected dev resources')
    if any(not name.startswith('chatactorai_dev_') and change['actions'] != ['no-op']
           for name, change in document.get('output_changes', {}).items()):
        raise RuntimeError('Unrelated output changes detected')
    values = {r['address'][len(PREFIX):]: r['change']['after'] for r in changes}
    realm = values['keycloak_realm.this']
    web = values['keycloak_openid_client.web']
    google = values['keycloak_oidc_google_identity_provider.google[0]']
    audience = values['keycloak_openid_audience_protocol_mapper.web_api_audience[0]']
    events = values['keycloak_realm_events.this']
    env = dict(line.split('=', 1) for line in pathlib.Path('/opt/keycloak/.tf.env').read_text().splitlines()
               if '=' in line and not line.startswith('#'))
    checks = {
        'realm_exact': realm.get('realm') == 'chatactorai-dev',
        'frontend_url_exact': realm.get('attributes', {}).get('frontendUrl') == 'https://auth.chatactorai.com',
        'email_verification_required': realm.get('verify_email') is True,
        'duplicates_disabled': realm.get('duplicate_emails_allowed') is False,
        'client_exact': web.get('client_id') == 'chatactorai-dev',
        'client_secret_matches_runtime': bool(env.get('TF_VAR_chatactorai_web_client_secret')) and web.get('client_secret') == env['TF_VAR_chatactorai_web_client_secret'],
        'confidential_pkce': web.get('access_type') == 'CONFIDENTIAL' and web.get('pkce_code_challenge_method') == 'S256',
        'code_flow_only': web.get('standard_flow_enabled') is True and all(web.get(k) is False for k in ('implicit_flow_enabled', 'direct_access_grants_enabled', 'service_accounts_enabled')),
        'redirect_exact': web.get('valid_redirect_uris') == ['https://dev.chatactorai.com/auth/callback'],
        'logout_exact': web.get('valid_post_logout_redirect_uris') == ['https://dev.chatactorai.com/'],
        'google_id_matches_runtime': bool(env.get('TF_VAR_chatactorai_google_client_id')) and google.get('client_id') == env['TF_VAR_chatactorai_google_client_id'],
        'google_secret_matches_runtime': bool(env.get('TF_VAR_chatactorai_google_client_secret')) and google.get('client_secret') == env['TF_VAR_chatactorai_google_client_secret'],
        'google_no_email_trust_or_token_storage': google.get('trust_email') is False and google.get('store_token') is False,
        'google_minimal_scopes': set(google.get('default_scopes', '').split()) == {'openid', 'email', 'profile'},
        'api_audience_access_only': audience.get('included_custom_audience') == 'chatactorai-dev-api' and audience.get('add_to_access_token') is True and audience.get('add_to_id_token') is False,
        'admin_payload_logging_off': events.get('admin_events_details_enabled') is False,
    }
    print(json.dumps(checks), flush=True)
    if not all(checks.values()):
        raise RuntimeError('New realm contract check failed; do not apply')


try:
    os.umask(0o077)
    action = sys.argv[1] if len(sys.argv) == 2 else ''
    if action not in ('plan', 'inspect', 'apply'):
        raise RuntimeError('Expected plan, inspect or apply')
    if action == 'plan':
        if PLAN.exists() or PLAN.is_symlink():
            raise RuntimeError('Prior plan exists; inspect before replacing')
        tf('init', '-input=false', '-lockfile=readonly')
        tf('fmt', '-check', 'chatactorai.tf', 'modules/product-realm')
        if not json.loads(tf('validate', '-json').stdout).get('valid'):
            raise RuntimeError('Terraform validation failed; raw diagnostics withheld')
        print('Terraform validation passed.', flush=True)
        tf('plan', '-input=false', '-lock-timeout=30s', '-detailed-exitcode',
           '-out=/wd/' + PLAN.name, allowed=(0, 2))
        PLAN.chmod(0o600)
        inspect_plan()
        print('ChatActorAI-only plan ready; nothing applied.', flush=True)
    else:
        if not PLAN.is_file() or PLAN.is_symlink() or (PLAN.stat().st_mode & 0o777) != 0o600:
            raise RuntimeError('Protected plan missing')
        inspect_plan()
        if action == 'apply':
            tf('apply', '-input=false', '-lock-timeout=30s', '/wd/' + PLAN.name)
            print('Reviewed ChatActorAI dev realm plan applied.', flush=True)
            result = tf('plan', '-input=false', '-lock-timeout=30s', '-detailed-exitcode', allowed=(0, 2))
            if result.returncode != 0:
                raise RuntimeError('Post-apply convergence not confirmed')
            PLAN.unlink()
            print('No-change convergence confirmed; temporary secret-bearing plan removed.', flush=True)
except Exception as error:
    print(str(error) if type(error) is RuntimeError else 'Operation failed; sensitive details withheld.',
          file=sys.stderr, flush=True)
    sys.exit(1)
