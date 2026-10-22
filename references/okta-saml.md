# Direct Okta SAML login

Prepare your `values.yaml` with the [installation guide](install.md#2-prepare-your-files), then configure Okta login before shared access.

Okta users can use private memories and `toko:everyone`. Tokonoma does not import Okta groups; do not add a group statement.

## Prerequisites

Use Helm 3.14+ and `jq` from your working directory on a workstation with cluster access. Follow [input conventions](install.md#inputs-and-placeholders) and the [certificate-file instructions](credentials.md#certificate-files).

| Input | Where to get it | When needed |
| --- | --- | --- |
| `REPLACE_WITH_KUBE_CONTEXT`, `values.yaml`, and certificate directory | Your [installation](install.md) record; persistent PostgreSQL is required | Before cluster commands |
| `REPLACE_WITH_MCP_HOSTNAME` and allowed email domains | Your DNS and identity administrators | Before creating the Okta app |
| Okta SAML app and assigned test user | Okta administrator with app creation and assignment permissions | Before the first login |
| Okta issuer, SSO URL and signing certificate | The app's **Sign On** setup instructions, step 3 | Before saving authentication values |

Choose the hostname before creating the app. Changing the Okta issuer or persistent NameID changes the user's Tokonoma identity; private memories may stay tied to the old identity.

Use a stable HTTPS hostname reachable by users and Okta. Replace namespace `tokonoma` if your installation uses another.

Confirm the target cluster with the [installation checks](install.md#1-check-prerequisites).

## 1. Record the service-provider values

| Purpose | Exact value |
| --- | --- |
| Single sign-on URL / ACS | `https://REPLACE_WITH_MCP_HOSTNAME/oauth/saml/acs` |
| Recipient URL | `https://REPLACE_WITH_MCP_HOSTNAME/oauth/saml/acs` |
| Destination URL | `https://REPLACE_WITH_MCP_HOSTNAME/oauth/saml/acs` |
| Audience URI / SP entity ID | `https://REPLACE_WITH_MCP_HOSTNAME/saml/metadata` |
| SP metadata URL | `https://REPLACE_WITH_MCP_HOSTNAME/saml/metadata` |

The service-provider (SP) entity ID defaults to the metadata URL. An existing stable URI is also valid, but Okta Audience URI and Helm `spEntityId` must match exactly.

## 2. Create the Okta SAML app

In Okta Admin Console:

1. Open **Applications > Applications** and select **Create App Integration**.
2. Select **SAML 2.0**, then **Next**.
3. Name the app `Tokonoma`. Hide its launch icon if possible; login must start from an MCP client.
4. Enter the settings below on **Configure SAML**.

### General SAML settings

| Okta field | Required setting |
| --- | --- |
| Single sign-on URL | `https://REPLACE_WITH_MCP_HOSTNAME/oauth/saml/acs` |
| Use this for Recipient URL and Destination URL | Enabled |
| Audience URI (SP Entity ID) | `https://REPLACE_WITH_MCP_HOSTNAME/saml/metadata` |
| Default RelayState | Leave blank |
| Name ID format | `Persistent` |
| Application username | Custom expression: `user.getInternalProperty("id")` |
| Update application username on | Create only |

NameID must use the immutable Okta user ID, never email, login, or another editable field.

### Advanced settings

| Okta field | Required setting |
| --- | --- |
| Response | Unsigned |
| Assertion signature | Signed |
| Signature algorithm | RSA-SHA256 |
| Digest algorithm | SHA256 |
| Assertion encryption | Unencrypted |
| Signed requests | Disabled; do not upload an SP signing certificate |
| Single logout | Disabled / not configured |
| Maximum app session lifetime | 30 days; enable **Send value in response** when available |

Tokonoma rejects deprecated signature algorithms and honors shorter Okta session limits.

### Attribute statements

After creating the app, open **Sign On > Attributes Statements > Add expression** in the Identity Engine claims editor:

| Name | Expression | Required |
| --- | --- | --- |
| `email` | `user.profile.email` | Yes |
| `display_name` | `user.profile.displayName` | No |

The legacy editor uses `user.email` and `user.displayName`; see the [current](https://help.okta.com/oie/en-us/content/topics/apps/federated-claims-overview.htm) and [legacy](https://help.okta.com/oie/en-us/content/topics/apps/define-attribute-statements.htm) syntax. Omit `display_name` if unavailable; Tokonoma displays email instead.

Assign the test user. In Okta's assertion preview, if available, confirm:

- the issuer is the app's Identity Provider Issuer;
- NameID format is persistent and the value is not the user's email;
- one non-empty `email` attribute is present;
- the assertion is signed with the active app certificate; and
- there is no group statement.

See Okta's [SAML fields](https://help.okta.com/oie/en-us/content/topics/apps/aiw-saml-reference.htm) and [Expression Language](https://developer.okta.com/docs/reference/okta-expression-language/) references.

## 3. Collect the exact Okta IdP values

Under **Sign On > View SAML setup instructions**, copy:

- **Identity Provider Issuer**. A typical value is
  `http://www.okta.com/exk123`. It is not the SSO URL, and its `http` scheme can
  be correct because this value is an identifier.
- **Identity Provider Single Sign-On URL**, typically
  `https://YOUR_ORG.okta.com/app/YOUR_APP/APP_ID/sso/saml`.
- the complete X.509 signing certificate, including its `BEGIN CERTIFICATE`
  and `END CERTIFICATE` lines.

Issuer, audience, destination, recipient, and attribute names must match exactly, including case. Do not derive the issuer from the SSO URL.

Save the certificate as `REPLACE_WITH_SECRET_DIRECTORY/okta-signing.crt`.

## 4. Deploy the connection

For public access, merge the [HTTPS Ingress settings](public-mcp-ingress.md) into `values.yaml`. Existing private HTTPS routing needs no public Ingress settings. Keep the hostname, `domain`, and OAuth origin identical.

Follow [SAML certificate preparation](oauth.md#prepare-saml-signing-certificates) using `okta-signing.crt` and Secret `toko-mcp-okta-saml`. Keep the resulting JSON-file checksum for the values below.

Configure or preserve a Cognito or legacy Google [credential provider](oauth.md#1-prepare-the-provider) alongside SAML and prepare the [runner credentials](alert-investigations.md#prepare-runner-credentials-when-mcp-authentication-is-enabled). The required runner needs machine access.

Merge these SAML settings into `values.yaml`, preserving the credential provider, runner configuration, and other `mcp` settings. Copy the printed checksum into `checksum`:

```yaml
domain: REPLACE_WITH_MCP_HOSTNAME

mcp:
  auth:
    enabled: true
    # Keep the configured credential provider for the runner.
    saml:
      enabled: true
      provider: okta

      # Copy these values exactly from Okta's setup instructions.
      idpEntityId: REPLACE_WITH_OKTA_ISSUER
      idpSsoUrl: REPLACE_WITH_OKTA_SSO_URL

      idpSigningCertificatesSecret:
        name: toko-mcp-okta-saml
        key: idp-signing-certificates.json
        checksum: REPLACE_WITH_SHA256_OF_THE_JSON_FILE

      # Optional; derived as https://REPLACE_WITH_MCP_HOSTNAME/saml/metadata when omitted.
      spEntityId: https://REPLACE_WITH_MCP_HOSTNAME/saml/metadata

      emailAttribute: email
      displayNameAttribute: display_name
      allowedDomains:
        - REPLACE_WITH_ALLOWED_EMAIL_DOMAIN

      sessionMaxSeconds: 2592000
      clockSkewSeconds: 300
```

Do not set `groupAttribute` for Okta. If using `mcp.auth.baseUrl` instead of `domain`, build ACS and metadata URLs from that HTTPS origin.

For a first installation, [install Tokonoma](install.md#3-install) with the prepared file and credentials, then verify metadata and login below.

For an existing release, follow [the configuration-change procedure](upgrading.md#before-changing-configuration). Record the prior revision for rollback.

## 5. Verify metadata and login

Run the shared [SAML metadata check](oauth.md#verify-saml-metadata), then test login below.

Connect an MCP client to `https://REPLACE_WITH_MCP_HOSTNAME/mcp/`, select **Continue with Okta**, and finish login. The Okta app tile lacks the required OAuth transaction and cannot start login.

For an optional identity and sharing check, use uniquely named temporary memories:

1. Save a memory without `share_with`. Its result must contain
   `owner_group_id: "toko:everyone"`, and `available_groups` must contain only
   `toko:everyone` (`Everyone`).
2. Search for that exact title. Its `owner_user_id` must start with
   `okta:saml:v1:`; sign in again and confirm the same user sees the same owner
   ID.
3. Save a second memory with `share_with: "private"`. Its result must contain
   `owner_group_id: null`; fetch and update it as the same user.
4. Attempt `share_with: "group"` with any group value. Tokonoma must reject it
   as unknown or unavailable.
5. Archive both temporary records when testing is complete.

Successful login verifies the email assertion. Display names never grant access; existing memory permissions still apply.

## Roll back the connection

Unassign or deactivate the Okta users to stop new logins, then follow [SAML rollback](oauth.md#roll-back-saml-configuration). Without confirmed token revocation, wait until `sessionMaxSeconds` expires before returning to a runtime without Okta identity support.

## Troubleshooting

Okta's **System Log** reports success when it issues a response, even if Tokonoma rejects that response. For **Sign-in failed**, [find the request in Tokonoma logs](oauth.md#diagnose-saml-login), then compare the provider settings below.

| Symptom | What to compare |
| --- | --- |
| Issuer mismatch | Okta **Identity Provider Issuer** versus `idpEntityId`; do not substitute the SSO URL |
| Audience mismatch | Okta Audience URI versus `spEntityId` |
| Destination or recipient mismatch | All three URLs must use the exact HTTPS ACS URL |
| Missing email | Statement name is `email`, its expression uses the syntax for your Okta claims editor, and exactly one value is emitted |
| Non-persistent subject | Name ID format is Persistent and application username is `user.getInternalProperty("id")` |
| Signature failure | Assertion is signed and the active Okta app certificate is in the Secret |
| Unknown transaction | Start again from the MCP client; do not use the Okta tile or reuse an old browser form |
| Expired assertion | Confirm cluster and Okta clocks are synchronized; maximum accepted skew is 300 seconds |

`allowedDomains` rejects emails outside the list even when the assertion is correctly signed.

## Rotate the signing certificate

1. Generate the new certificate in Okta but keep the old one active.
2. Follow [SAML certificate rotation](oauth.md#rotate-saml-signing-certificates) with `okta-signing-old.crt`, `okta-signing-new.crt`, and Secret `toko-mcp-okta-saml` to deploy trust for both certificates.
3. Activate the new certificate in Okta and test a fresh MCP-initiated login.
4. Complete the shared procedure to remove the old certificate from Tokonoma.

See Okta's [certificate management guide](https://help.okta.com/oie/en-us/content/topics/apps/manage-signing-certificates.htm).

## Current lifecycle limits

The shared [SAML session limits](oauth.md#saml-session-limits) apply.

Return to [private team access](private-access.md#team-access) or [connect a coding agent](coding-agents.md).
