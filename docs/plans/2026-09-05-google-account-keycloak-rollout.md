# Central Google account, per-product projects, and Keycloak rollout

Updated: 2026-09-06 (America/Toronto)

## Latest checkpoint — ChatActorAI implementation

Owner clarified ChatActorAI still uses **Authentik** and authorized continuing
Keycloak. The five-binding reset is now explicitly approved. Dev Google client is created and
credentials are saved/round-trip verified in Vaultwarden:
`google/chatactorai/oauth-dev` and `chatactorai-keycloak-web-client-dev`.
Secret transfer is confirmed. The eight-resource dev realm/Google/audience plan
was applied and converges; path-scoped routing and public isolation checks pass
without a restart. Local nonce/token/issuer-binding/waitlist code and migration
are in commit `399410a`: full local API suite has 1,259 passes/7 skips, two
additional guarded-reset tests pass, and all 50 web tests pass. **Dev release
34067811054 succeeded.** Live checks confirm 8 users, 4 organizations, zero legacy
bindings, exact Keycloak issuer/API audience, and a valid app-owned PKCE redirect.
Vaultwarden-backed dev inputs and protected rollback env/database copies are in
place. Real browser Google-to-Keycloak login reached the existing dashboard;
logout cleared app/IdP sessions and blocked protected dashboard access. Post-login
counts remain 8 users/4 organizations with one Keycloak binding, zero legacy
bindings. Login wording follow-up `c9426a2` is deployed and healthy; broader live negative
and refresh checks remain open. See the checkpoint in
[`2026-09-06-chatactorai-keycloak-cutover.md`](2026-09-06-chatactorai-keycloak-cutover.md).
Historical checkpoints below must not override this status.

## Resume instruction

After restarting Codex, open `~/code/infra` and ask:

> Resume `docs/plans/2026-09-05-google-account-keycloak-rollout.md` using
> Computer Use. Comcentre is already provisioned. Use the existing master Google
> account with separate Cloud projects for ChatActorAI, EnoughLedger, and
> EnoughDating. Do not create more Google accounts. Configure each project's
> OAuth branding and Google social login independently.
> Keep all credentials in Vaultwarden.

The previous session's Computer Use channel failed with
`Sky Computer Use native pipe startup failed` and exposed no Chrome, Edge, or
in-app browser provider. The user is restarting Codex to restore the bridge.
Do not repeat the discovery or email work below.

## Current owner decision: 2026-09-06

- Latest scope: finish Google social login, then configure the remaining apps'
  Keycloak authentication and update infra standards plus HTML summaries.
  Do not confuse Google-provider setup with completed app authentication.
- Abandon per-product consumer Google account signup. Do not resume QR/SMS
  verification or create Cloud Identity/Workspace as part of this workflow.
- Use the existing master account and separate product projects. The current
  Cloud Console session is `mcoelhojob@gmail.com`; this is the selected master
  account for this continuation.
- Create ChatActorAI Production, EnoughLedger Production, and EnoughDating
  Production. Configure External OAuth audience and distinct app branding and
  authorized domains. Development projects/clients must remain separate from
  production when the app wiring is performed.
- Use the master account for OAuth user support email and developer contact.
  The user support email **is visible** in consent-screen app details; developer
  contact information serves Google's operational notifications.
- Do not grant Owner to mailbox-only `support@` addresses. An arbitrary mailbox
  is not an IAM identity; the support-email picker requires an eligible Google
  account or managed Google Group. No additional IAM grants are requested now.
- Domain ownership verification uses Google's supported verification flow;
  pointing a domain at the application server alone is insufficient proof.
- Preserve `google/chatactorai` in Vaultwarden as an incomplete signup record;
  do not reuse its credential as an OAuth client secret or delete it implicitly.
- Owner clarified during continuation that the apps are running in development;
  `www.chatactorai.com` is not deployed yet. Do not treat missing production
  webpages as a blocker for development login or deploy production sites as part
  of this task. Defer production brand verification and publication, keep OAuth
  in Testing, and resolve the actual dev realm/callback before creating clients.
  Root-domain ownership verification is still applicable to dev/auth subdomains.
- Environment correction verified against Google's production-readiness guidance:
  separate dev/testing and production **projects** are required, not only separate
  clients. Reserve the three existing `*-prod` projects. Create corresponding
  `*-dev` projects for the current development rollout; do not publish or save dev
  callbacks in the production projects.

### Provisioning checkpoint: 2026-09-06

#### Runtime activation and browser test

- Latest owner confirmation: **“google authentication works fine”**. EnoughLedger
  normal Google login is now owner-verified end to end; no further email handoff
  is pending. Continue ChatActorAI next. Keep host-isolation, role/tenant negative,
  collision/linking, refresh/logout and production acceptance gates open until
  separately tested. The earlier email-verification observation below is history.
- Owner ran the secure transfer script from the unlocked shell and reported:
  **EnoughLedger Google dev inputs transferred and verified; Terraform apply not run.**
  Computer Use explicitly denies Terminal control; do not try to take over Terminal
  or extract its `BW_SESSION`. The user must run future vault-transfer commands in
  their unlocked shell if this restriction remains.
- Applied `keycloak-enoughledger-google.patch` to `/opt/keycloak` after a successful
  dry-run. Only EnoughLedger source/input/output lines changed.
- `scripts/plan-enoughledger-google.py` validated Terraform, produced a protected
  plan, and inspected the plan JSON without emitting values. The sole live change
  was **create** `module.smb_tax_dev.keycloak_oidc_google_identity_provider.google[0]`.
  It also observed pre-existing, refresh-only DVM Architect metadata drift:
  web-client `extra_config` and realm default/optional client scopes. Both Architect
  resources were **no-op** in the plan; preserved their live configuration.
- Verified plan matches the exact realm, runtime client ID/secret, callback,
  `trust_email=false`, `store_token=false`, `openid profile email`, and IMPORT sync.
  Applied that saved plan successfully; a full follow-up plan returned **no changes**.
  Removed the temporary secret-bearing `.enoughledger-google.tfplan` after success.
  No other live realm configuration was changed.
- Browser: opened `https://dev.enoughledger.com/api/v1/auth/login`, saw the branded
  EnoughLedger dev Keycloak page with a Google button, clicked Google, and observed
  Google's account chooser. The browser then returned to the correct Keycloak realm
  at **Email verification**, with a message sent to `mcoelhojob@gmail.com`. Google
  provider authorization/code exchange succeeded; the full app callback/session
  is **not yet proven**. Asked the owner to complete the latest EnoughLedger email
  verification privately. Do not resend repeatedly or paste verification links.
- Public rollout verifier: discovery, exact issuer/endpoints, JWKS, application
  302, S256 PKCE, state, nonce, client and callback presence **passed**. Four ingress
  gates **failed**: master discovery, master admin console and `cc-dvm-dev` /
  `gelopreto-dev` discovery all returned 200 on `auth.enoughledger.com`.
  Do not mark acceptance; complete the interactive flow and fix host isolation.

#### ChatActorAI continuation after EnoughLedger owner confirmation

Created **ChatActorAI Development** (`dvm-chatactorai-dev`) under the existing
master account. Google returned **OAuth configuration created!** for
**ChatActorAI (dev)** with the approved master support/developer contact; Audience
confirmed External and Testing. Saved-list inspection confirmed the master account
as a test user. Added and saved `chatactorai.com` as the authorized root domain;
reload persistence verification remains pending. No new ChatActorAI OAuth client or
credential has been created yet.

App inspection found migration work beyond environment configuration: missing
OIDC nonce, legacy groups/offline scopes, subject-only local identity binding and
an API audience/token-type contract to tighten. The intended realm/callback,
source evidence and safe cutover order are recorded in
`2026-09-06-chatactorai-keycloak-cutover.md`. Existing Authentik/app behavior is
unchanged; do not switch the issuer before testing those changes.

Provisioning sequence before runtime activation above:

- Native Computer Use successfully selected that window; screenshot and page
  controls matched. The old production-project client form was no longer open.
- Created **EnoughLedger Development**, project `dvm-enoughledger-dev`, under
  `mcoelhojob@gmail.com`, No organization. Production project left unchanged.
- Saved OAuth configuration **EnoughLedger (dev)**, External audience, master
  support/developer contact. Reused the owner's Google policy approval.
- Created **EnoughLedger Keycloak dev**, Web application, exactly one redirect:
  `https://auth.enoughledger.com/realms/smb-tax-dev/broker/google/endpoint`.
  No JavaScript origins. Google returned **OAuth client created**.
- Created Vaultwarden login item `google/smb-tax/oauth-dev` after a duplicate
  search. Stored client ID as username and client secret as password; reopened
  and compared both in memory to verify the saved values, without emitting them.
  No credential values in this file. Cleared transient credential variables.
- Audience page confirmed **Testing** and saved `mcoelhojob@gmail.com` as a test
  user. Added and saved `enoughledger.com` as the authorized root domain; a fresh
  page reload confirmed the app name, support email and domain persisted. Public homepage/privacy/terms remain
  blank, and the dev UI says verification is not required while Testing.
- Vaultwarden CLI is **locked** although the extension is unlocked. Asked the
  owner to open a fresh Terminal tab and run `export BW_SESSION="$(bw unlock --raw)"`,
  entering the master password privately. Do not ask them to paste the session
  token. Terminal Computer Use was subsequently denied; the owner ran the transfer
  script themselves from that unlocked shell, as recorded above.
- Prepared `scripts/inject-enoughledger-google.mjs --transfer` for that unlocked
  shell. It syncs and reads only the exact vault item, verifies the project,
  transfers the two Google dev inputs through SSH stdin to the mode-600
  `/opt/keycloak/.tf.env`, and verifies them without outputting values. Syntax
  checked, then executed by the owner as recorded above. It does not apply
  Terraform or restart anything; activation was a separate reviewed step.
- A vault snapshot exposed sensitive text embedded in unrelated legacy item
  titles; owner was notified to review/rotate those credentials. Do not repeat
  the titles or values. Keep future observations limited to exact allowlisted
  controls; do not print generic vault button/item lists.

Historical next step (now completed through activation above): unlock CLI, transfer the saved credential, apply the reviewed source patch
to the VPS working copy (do not overwrite unrelated configuration), validate and
inspect a secret-suppressed Terraform plan, and enable only the intended provider.
Then test public Google login and safe linking. ChatActorAI/EnoughDating dev
projects and realm/application work remain outstanding; do not duplicate the
EnoughLedger project or OAuth client.

Earlier continuation: user explicitly authorized finishing social login and fleet
Keycloak configuration. Opened EnoughLedger overview and confirmed correct project
and master account, saved OAuth configuration and **no OAuth clients**. Prepared
the web-client form named `EnoughLedger Keycloak dev` with the known dev callback,
but did **not** click Create. Computer Use again returned inconsistent screenshot
and accessibility state; attempts to replace the URI appeared to concatenate it.
Asked the owner to inspect the form and leave Create unclicked. Before resuming,
cancel that unsaved production-project form and create the client in the separate
dev project. No OAuth secret has been generated or stored by this continuation.

Read-only live app contract inventory and remaining host/TLS gates are now in
`../keycloak-migration.md`, section “Continuation scope and live contract check”.
Standards and both HTML summaries have been updated with the central-account,
separate-environment-project decision and observed—not assumed—migration state.

Applied the narrowly scoped `../patches/keycloak-enoughledger-google.patch` to
the sibling Keycloak repository with owner-approved filesystem access. The
`smb_tax_dev` module now reads optional `smbtax_google_client_id` and sensitive
`smbtax_google_client_secret` inputs and exports the non-secret broker callback.
Both inputs default empty: this is **source preparation only**, not an enabled
provider. Vaultwarden target item is `google/smb-tax/oauth-dev`; check for an
existing item before creating one. No secret value has been generated or injected,
and no Terraform apply or app deploy ran. Preserve the pre-existing DVM Architect
changes in the same files; do not sync the entire dirty repository blindly.

Checks passed: `git diff --check` in infra and Keycloak, Terraform 1.9
`fmt -check -` for both modified Terraform files (VPS container, no credentials),
and HTML5 parsing plus duplicate-ID, local-anchor and local-file-link checks for
both HTML pages. Full Terraform validate/plan and rendered browser verification
remain outstanding; native Computer Use state is still inconsistent.

All three projects were created and opened successfully in Google Cloud Console
under `mcoelhojob@gmail.com` (No organization):

| Project name | Project ID | Saved OAuth app name |
|---|---|---|
| ChatActorAI Production | `dvm-chatactorai-prod` | ChatActorAI |
| EnoughLedger Production | `dvm-enoughledger-prod` | EnoughLedger |
| EnoughDating Production | `dvm-enoughdating-prod` | EnoughDating |

The user approved Google's API Services User Data Policy on 2026-09-06. Accepted
it and saved all three OAuth configurations; each returned **OAuth configuration
created!**. Each uses External audience and `mcoelhojob@gmail.com` as both user
support email and developer contact.

Entered and saved each project's matching authorized root domain; persistence
checks are in progress. Continue website/policy URLs and domain verification. The wizard says
External starts in Testing; production project names do not mean OAuth has been
published. No OAuth clients/secrets or additional IAM grants have been created,
and no Keycloak settings have been changed in this continuation.

Domain verification: added Google's TXT record at `@` in Namecheap for
`chatactorai.com`; Search Console returned **Ownership verified** under the
master account. Keep that TXT record. EnoughLedger's verification property is
prepared and its matching TXT record was added at `@` in Namecheap after
expanding **Show More** and checking for duplicates. The new row was observed
as saved text rather than an editable field. Google's EnoughLedger verification
result still needs confirmation. EnoughDating verification remains pending.
No verification token values are recorded here.

Computer Use became unreliable across Chrome windows: screenshots, address-bar
focus, and the inspected page sometimes referred to different tabs, including
an unrelated `dvmsoftware.com` DNS tab. Reset the session and opened a separate
Chrome window, but the active target continued switching. Requested the owner
bring the EnoughLedger Search Console tab forward and leave Chrome idle before
further UI writes. No DNS changes were made to `dvmsoftware.com`.

Dev callback evidence: the local Keycloak Terraform module declares product
`smb-tax`, env `dev`, and host `auth.enoughledger.com`; the public discovery
endpoint returned exact issuer `https://auth.enoughledger.com/realms/smb-tax-dev`.
Thus the Google callback is
`https://auth.enoughledger.com/realms/smb-tax-dev/broker/google/endpoint`.
The current local Terraform root does not declare ChatActorAI or KnowingBest
realms; resolve those before creating their OAuth clients. No runtime changes
were made by these read-only checks.

Public-site checks: `chatactorai.com` has no apex A answer, though MX records
remain present; `www.chatactorai.com` has an A record in Namecheap. HTTPS probes
for `www.chatactorai.com` and `enoughledger.com` failed local issuer validation;
`enoughdating.com` returned a TLS internal-error alert. These probes do not yet
establish usable public home/privacy/terms pages. Do not bypass certificate
warnings or invent policy URLs; investigate deployment separately if needed.

## Historical owner clarification: 2026-09-05

- Comcentre is already provisioned and is outside the remaining rollout.
- Create new Google Accounts through the existing-email flow for
  `support@chatactorai.com`, `support@enoughledger.com`, and
  `support@enoughdating.com`, in that order.
- Then create each product's Google Cloud project and configure IAM and OAuth
  for Google social login. Keep credentials and recovery material in Vaultwarden.
- This supersedes the earlier `auth@` identity choice and cc-dvm-first instruction.
- Chrome page inspection is restored; an isolated Incognito signup session has
  been opened for ChatActorAI.
- Entered `ChatActorAI` as the product display name. The owner completed personal
  details and selected the existing-email flow. Submitted
  `support@chatactorai.com`; Google sent a verification email. The owner then
  completed email verification and reached **Create a strong password**.
  The owner subsequently reported Google requiring QR/SMS verification and
  rejecting their number as used too many times. Account creation is not yet
  confirmed; automation is paused at this Google verification gate.
- Created and verified Vaultwarden login item `google/chatactorai`, username
  `support@chatactorai.com`, URI `https://accounts.google.com/`, with the password
  left blank. Checked the address and item name first to avoid duplication.
  The owner was handed password generation/storage and Google password entry;
  the saved password has not subsequently been inspected. Account submission,
  MFA, Cloud project, IAM, and OAuth remain pending.
- Current blocker: Google signup's QR/SMS phone verification reports the number
  has been used too many times. Google's official guidance is to use another
  eligible number (with its owner's permission). Do not automate this gate or
  claim that waiting/retrying will reset the limit. Reference:
  <https://support.google.com/accounts/answer/114129?hl=en>.
- Vaultwarden extension has an existing mailbox item
  `namecheap_chatactorai_auth_mail`, username `support@chatactorai.com`, website
  `privateemail.com`. Private Email rejected its credential twice, including a
  fresh-copy retry, with **Invalid mailbox or password**. Stop further retries
  until the owner corrects the Vaultwarden item or signs into the mailbox.
  This did not prevent the owner from completing Google's email verification.
  The Incognito mailbox password field was cleared. The regular Chrome window
  has an existing EnoughLedger webmail session, not the ChatActorAI mailbox.

## Historical checkpoint: 2026-09-05, cc-dvm account inspection

- Native Computer Use initially worked for Chrome and Bitwarden; no browser
  provider was exposed. Vaultwarden desktop was unlocked on
  `vault.dvmsoftware.com`.
- An existing item named `google_comcentre_auth_mail` uses
  `support@comcentre.online` and contains recovery material. Its name alone does
  not establish whether this is the current Google project owner. The owner
  subsequently confirmed comcentre is already provisioned; do not create another
  account or re-audit it as part of this rollout.
- The initial Bitwarden accessibility snapshot unexpectedly included recovery
  codes from the item's notes. Do not copy these into this file or repeat them;
  replace the affected codes during the owner's Google MFA review. Use suppressed
  and sanitized observations for vault screens on continuation.
- The personal Chrome Google Cloud session opened project
  `command-center-507423`, which Google reported as shut down and scheduled for
  deletion. This does **not** establish that it backs cc-dvm's working OAuth
  provider. No project lifecycle changes were made.
- Opened a Chrome Guest window for isolated account inspection. Computer Use
  then returned window titles without page controls, and screenshots were
  unavailable. Closed that Guest window; the personal Cloud project selector
  became active again, but inspection remained unavailable after reconnecting
  and resetting the Computer Use session. Alternate browser discovery returned
  `No browser is available`.
- No Google account, OAuth client, ownership, credential, or Keycloak settings
  were changed. cc-dvm mailbox delivery and Google project ownership remain
  unverified by this session. The subsequent owner clarification above resolves
  scope and identity choice; these cc-dvm checks are no longer pending work.

## Objective

Use one existing master Google account to administer separate product Google
Cloud OAuth configurations, store recovery material and credentials in
Vaultwarden, and enable/test Google login in the product's own Keycloak realm.

Account creation and Google OAuth-client creation are user-confirmed external
actions. Automation must stop for CAPTCHA, Google risk-based phone verification,
the final account-creation submission, and physical MFA enrollment. Do not bypass
Google safeguards and do not promise that signup will remain phone-free.

## Owner decisions

- One real Namecheap Private Email mailbox per selected product domain:
  `support@<domain>`.
- Two mailbox aliases: `auth@<domain>` and `recovery@<domain>`.
- Use the existing master Google account. Product `support@` mailboxes remain
  customer-support inboxes; new Google account signup is abandoned.
- Prefer a passkey/security key or authenticator app for Google MFA; do not plan
  SMS as the factor.
- AWS SES remains the automated outbound sender for Keycloak/application mail.
  Namecheap Private Email provides the human inbox and human SMTP.
- No catch-all mailbox.
- Credentials and recovery codes belong in Vaultwarden; never print them into
  chat, source, Terraform output, logs, or shell history.
- Do not purchase more Private Email plans without the owner. When needed, add
  them to the Namecheap cart only; the owner applies the promo code and pays.
- Authentik data is disposable development data. Do not import or preserve its
  users, credentials, sessions, or client secrets.

The `recovery@` alias lands in the same `support@` mailbox, so it is a convenient
address but not an independent recovery channel. Keep an enrolled hardware key or
passkey and Vaultwarden recovery codes so loss of the domain mailbox is not a
total lockout.

## Selected products and addresses

| Order | Product | Domain | Google identity | Keycloak target |
|---:|---|---|---|---|
| 1 | ChatActorAI | `chatactorai.com` | Master: `mcoelhojob@gmail.com` | Create and wire the product realm during the ChatActorAI migration. |
| 2 | smb-tax / EnoughLedger | `enoughledger.com` | Master: `mcoelhojob@gmail.com` | Existing `smb-tax-dev`; wire Google after the account/project/client exists. |
| 3 | KnowingBest / EnoughDating | `enoughdating.com` | Master: `mcoelhojob@gmail.com` | Create and wire the product realm when the app migration reaches it. |

Comcentre (`support@comcentre.online`, `cc-dvm-dev`) is already provisioned per
the owner and excluded from remaining work.

`chatacotai.com` was a typo seen in conversation. The deployed and configured
domain is `chatactorai.com`.

## Completed email work

Public DNS and an actual delivery batch were checked on 2026-09-05.

| Domain | DNS result | Delivery result |
|---|---|---|
| `enoughdating.com` | Namecheap Private Email MX and DKIM present; DMARC `p=none`; one combined SPF policy authorizing SES and Private Email. | SES accepted messages to `support@`, `auth@`, and `recovery@`; owner confirmed all three arrived. |
| `enoughledger.com` | Namecheap Private Email MX and DKIM present; DMARC `p=none`; authoritative Namecheap DNS publishes one combined SPF policy. A recursive resolver briefly retained the previous duplicate records during propagation. | SES accepted messages to `support@`, `auth@`, and `recovery@`; owner confirmed all three arrived. |
| `chatactorai.com` | Namecheap Private Email MX and DKIM present; DMARC `p=none`; one combined SPF policy authorizing SES and Private Email. | SES accepted messages to `support@`, `auth@`, and `recovery@`; owner confirmed all three arrived. |
| `comcentre.online` | Namecheap Private Email MX was observed and Keycloak SES outbound was previously proven. | Owner confirmed already provisioned; excluded from this rollout. |

The combined SPF value used by the three newly configured domains is:

```text
v=spf1 include:amazonses.com include:spf.privateemail.com ~all
```

Longer term, prefer SES custom MAIL FROM on a dedicated `mail.<domain>` subdomain
with its SES MX/SPF records, leaving the apex SPF for human Private Email. Move
DMARC from monitoring to quarantine/reject only after all legitimate senders and
alignment reports are verified.

## Historical Google account workflow — superseded, do not execute

1. Confirm `support@`, `auth@`, and `recovery@` delivery for the domain.
2. Open a new isolated browser profile/window. Do not reuse another product's
   signed-in Google session.
3. Choose **Create account** and **Use your existing email**. Enter the product's
   `support@` mailbox address.
4. Let the owner enter or explicitly approve any personal attributes Google
   requires. Do not invent a birthday, gender, phone number, or recovery fact.
5. Retrieve the verification code from the `support@` mailbox and enter it only
   into the matching Google signup.
6. Pause immediately before the final create-account submission for user
   confirmation. If Google requires phone verification or CAPTCHA, hand control
   to the owner; do not evade it.
7. Set `recovery@<domain>` where allowed. Because it resolves to the same mailbox,
   also enroll a genuinely independent passkey/security key.
8. Enable Google 2-Step Verification. The owner completes the physical MFA step.
   Generate recovery codes and store them in the product's Vaultwarden item.
9. Confirm a clean sign-out/sign-in using the non-SMS factor before continuing.

Suggested Vaultwarden item names (confirm the existing names before creating
anything):

```text
google/smb-tax
google/knowingbest
google/chatactorai
```

Do not create duplicate Vaultwarden items. The CLI was locked at the end of the
previous session, although the owner confirmed the credentials are in the vault.

## Google Cloud and Keycloak workflow

For each product project under the existing master account:

1. Create the product Google Cloud project under the existing master account.
   Verify its owner in IAM. Keep app branding, authorized domain, privacy policy,
   and Terms URL product specific; use the master address for user support and
   developer contact. No additional Owner grants are needed for this setup.
2. Verify the product domain through the supported Google flow.
3. Create separate dev/testing and production projects with environment-specific
   OAuth web clients. Do not reuse a dev project, callback or secret in prod.
4. Register the exact Keycloak broker redirect URI:

   ```text
   https://auth.<product-domain>/realms/<product>-<env>/broker/google/endpoint
   ```

5. Store the OAuth client ID/secret in Vaultwarden and inject them into Terraform
   through secret environment variables. Never commit them or expose them in a
   Terraform plan/output.
6. Enable the Keycloak Google identity provider declaratively. Preserve the
   conservative first-broker-login behavior and explicitly test verified-email
   collision/linking.
7. Test public browser login, exact issuer/audience, callback state/nonce/S256
   PKCE, product role/tenant authorization, refresh, logout, and negative cases.

Google MFA protects the Google operator account. Product-user MFA is a separate
Keycloak policy. If product-user MFA is required, declare the realm policy and
required action (or a reviewed conditional browser flow) and test enrollment and
recovery; do not assume upstream Google MFA covers password-based Keycloak users.

## Completion evidence

- The master Google Account has a verified owner/recovery path and MFA; no new
  per-product Google account is required.
- Each product Google Cloud project/client has the exact redirect URI and an
  identifiable owner/recovery path.
- Secrets exist only in Vaultwarden and approved runtime injection.
- The Keycloak provider is declared in Terraform and a no-change plan converges.
- Google login creates or links the expected fresh realm account without unsafe
  email collision behavior.
- Wrong realm, issuer, audience, role, tenant, state, and nonce tests fail.
- Refresh/logout work and no Authentik dependency remains in the accepted app.

## References

- Google separate testing/production project requirements:
  <https://developers.google.com/identity/protocols/oauth2/production-readiness/policy-compliance>
- Google existing-email account creation:
  <https://support.google.com/accounts/answer/27441>
- Google 2-Step Verification:
  <https://support.google.com/accounts/answer/10956730>
- AWS SES custom MAIL FROM:
  <https://docs.aws.amazon.com/ses/latest/dg/mail-from.html>
- Namecheap Private Email DNS:
  <https://www.namecheap.com/support/knowledgebase/article.aspx/1338/2176/how-to-set-up-namecheap-private-email-dns-records-for-domains-on-namecheap-basicpremium-nameservers/>
