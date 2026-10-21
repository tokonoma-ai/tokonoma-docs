# Direct Okta SAML login

Complete the [installation](install.md), then configure Okta login.

Okta users can use private memories and `toko:everyone`. Tokonoma does not import Okta groups; do not add a group statement.

## Prerequisites

Use Helm 3.14+ and `jq`. Run commands from your deployment directory on a computer with cluster access. Configure Okta in Okta Admin Console. Keep credentials in the [protected secret directory](credentials.md#supply-tokens-from-files). Replace placeholders. Agents must ask for missing choices and secret paths, keeping secret contents out of chat.

Before running Helm, resolve `REPLACE_WITH_INSTALLED_CHART_VERSION` using [configuration checks](upgrading.md#before-changing-configuration). This keeps the installed chart version while changing its settings.

| Input | Where to get it | When needed |
| --- | --- | --- |
| `REPLACE_WITH_KUBE_CONTEXT`, `tokonoma-values.yaml`, license file and secret directory | Your [installation](install.md) record; persistent PostgreSQL is required | Before cluster commands |
| `REPLACE_WITH_MCP_HOSTNAME` and allowed email domains | Your DNS and identity administrators | Before creating the Okta app |
| Okta SAML app and assigned test user | Okta administrator with app creation and assignment permissions | Before the first login |
| Okta issuer, SSO URL and signing certificate | The app's **Sign On** setup instructions, step 3 | Before saving authentication values |
| Current Helm revision | `helm history` below | Before changing an existing release |

Choose the hostname before creating the app. Changing the Okta issuer or persistent NameID changes the user's Tokonoma identity; private memories may stay tied to the old identity.

Use a stable HTTPS hostname reachable by users and Okta. Replace namespace `tokonoma` if your installation uses another.

Verify the target cluster before changing it:

```sh
kubectl config get-contexts "REPLACE_WITH_KUBE_CONTEXT"
kubectl --context "REPLACE_WITH_KUBE_CONTEXT" cluster-info
```

Stop if either command identifies a different cluster.

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

Prepare public routing files with the [HTTPS Ingress guide](public-mcp-ingress.md) and deploy them with authentication below. For an existing private HTTPS proxy, omit `tokonoma-public.yaml` and `tokonoma-ingress.yaml` from both commands. Keep the hostname, `domain`, and OAuth origin identical.

Create the namespace and certificate Secret, then record the JSON-file checksum. The namespace command also works if it already exists. If you lack namespace permissions, ask the platform team to create it first:

```sh
kubectl --context "REPLACE_WITH_KUBE_CONTEXT" create namespace tokonoma \
  --dry-run=client -o yaml \
  | kubectl --context "REPLACE_WITH_KUBE_CONTEXT" apply -f -

jq -Rs '[.]' "REPLACE_WITH_SECRET_DIRECTORY/okta-signing.crt" \
  > "REPLACE_WITH_SECRET_DIRECTORY/idp-signing-certificates.json"

kubectl --context "REPLACE_WITH_KUBE_CONTEXT" -n tokonoma \
  create secret generic toko-mcp-okta-saml \
  --from-file=idp-signing-certificates.json="REPLACE_WITH_SECRET_DIRECTORY/idp-signing-certificates.json" \
  --dry-run=client -o yaml \
  | kubectl --context "REPLACE_WITH_KUBE_CONTEXT" apply -f -

sha256sum "REPLACE_WITH_SECRET_DIRECTORY/idp-signing-certificates.json"
```

On macOS, use `shasum -a 256`. Hash the JSON file, not the certificate fingerprint or raw PEM. Put only the Secret name, key, and checksum in Helm values.

Save as `tokonoma-oauth.yaml`, preserving any existing credential-provider settings. Copy the printed checksum into `checksum`:

```yaml
domain: REPLACE_WITH_MCP_HOSTNAME

mcp:
  auth:
    enabled: true
    # SAML can be the only login path. Keep an existing cognito/google
    # provider here only when the deployment intentionally offers both.
    provider: none

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

Record the current revision before changing an existing release:

```sh
helm --kube-context "REPLACE_WITH_KUBE_CONTEXT" history tokonoma \
  --namespace tokonoma
```

Render, then deploy with every existing values file and the new overlays. The rendered file contains Secrets; keep it protected and uncommitted:

```sh
helm template tokonoma oci://public.ecr.aws/tokonoma/charts/tokonoma \
  --kube-context "REPLACE_WITH_KUBE_CONTEXT" \
  --version REPLACE_WITH_INSTALLED_CHART_VERSION \
  --namespace tokonoma \
  --values tokonoma-values.yaml \
  --values tokonoma-public.yaml --values tokonoma-ingress.yaml \
  --values tokonoma-oauth.yaml \
  --set-file mcp.license="REPLACE_WITH_SECRET_DIRECTORY/license.txt" > "REPLACE_WITH_SECRET_DIRECTORY/rendered.yaml"

helm upgrade --install tokonoma --reset-then-reuse-values \
  oci://public.ecr.aws/tokonoma/charts/tokonoma \
  --kube-context "REPLACE_WITH_KUBE_CONTEXT" \
  --version REPLACE_WITH_INSTALLED_CHART_VERSION \
  --namespace tokonoma \
  --create-namespace \
  --values tokonoma-values.yaml \
  --values tokonoma-public.yaml --values tokonoma-ingress.yaml \
  --values tokonoma-oauth.yaml \
  --set-file mcp.license="REPLACE_WITH_SECRET_DIRECTORY/license.txt" \
  --wait --timeout 10m
```

Expect Helm `STATUS: deployed` and namespace/Secret results `created`, `configured`, or `unchanged`.

Rendering rejects incomplete SAML settings, non-HTTPS SSO, empty domain allowlists, or missing certificate checksums. Changing the checksum restarts the Tokonoma pod.

## 5. Verify metadata and login

Wait for `deployment "toko-mcp" successfully rolled out`, then fetch the HTTPS metadata:

```sh
kubectl --context "REPLACE_WITH_KUBE_CONTEXT" -n tokonoma \
  rollout status deployment/toko-mcp
curl -fsS https://REPLACE_WITH_MCP_HOSTNAME/saml/metadata
```

The metadata must contain:

- `entityID="https://REPLACE_WITH_MCP_HOSTNAME/saml/metadata"`;
- `AuthnRequestsSigned="false"`;
- `WantAssertionsSigned="true"`;
- persistent NameID format; and
- ACS location `https://REPLACE_WITH_MCP_HOSTNAME/oauth/saml/acs`.

Connect an MCP client to `https://REPLACE_WITH_MCP_HOSTNAME/mcp/`, select **Continue with Okta**, and finish login. The Okta app tile lacks the required OAuth transaction and cannot start login.

Verify identity and access with uniquely named temporary memories:

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

Disconnect or revoke test clients, archive test memories, and restore the recorded revision:

```sh
helm --kube-context "REPLACE_WITH_KUBE_CONTEXT" rollback tokonoma \
  REPLACE_WITH_PREVIOUS_REVISION \
  --namespace tokonoma \
  --wait --timeout 10m
```

Rollback restores workloads and values. It does not revoke access or refresh tokens, delete test memories, remove the certificate Secret, or change the Okta app. Without confirmed token revocation, wait until `sessionMaxSeconds` expires before returning to a runtime without Okta identity support.

## Troubleshooting

Okta's **System Log** reports success when it issues a response, even if Tokonoma rejects that response. For **Sign-in failed**, find the request ID on the page or in `X-Tokonoma-Request-ID`, then search Tokonoma logs:

```sh
kubectl --context "REPLACE_WITH_KUBE_CONTEXT" -n tokonoma \
  logs deployment/toko-mcp --since=15m \
  | grep 'REPLACE_WITH_REQUEST_ID'
```

Tokonoma logs the toolkit's safe failure reason without the assertion payload.

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

Keep both certificates trusted while you switch:

1. Generate the new certificate in Okta but keep the old one active.
2. Put both PEM certificates in the trusted JSON array.
3. Apply the Secret change, update the Helm checksum, and wait for rollout.
4. Activate the new certificate in Okta.
5. Test a fresh MCP-initiated login.
6. Remove the old certificate, update the checksum, and deploy again.

See Okta's [certificate management guide](https://help.okta.com/oie/en-us/content/topics/apps/manage-signing-certificates.htm).

## Current lifecycle limits

Direct Okta SAML has no single logout (SLO), automated account provisioning (SCIM), provider-initiated login, account linking, multiple direct SAML providers, or immediate token revocation. Unassigning or deactivating a user blocks new logins but can leave existing access valid until the session maximum.

The default maximum is 2,592,000 seconds (30 days) from login; a shorter Okta `SessionNotOnOrAfter` takes precedence. Access tokens last at most 24 hours, and refresh-token rotation cannot extend the original session.

Return to [private team access](private-access.md#team-access) or [connect a coding agent](coding-agents.md).
