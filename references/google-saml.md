# Direct Google Workspace SAML login

Complete the [installation](install.md), then configure Google Workspace login.

Google SAML supplies memory-sharing groups at login. Tokonoma does not query or synchronize Google Directory.

## Prerequisites

Use Helm 3.14+ and `jq`. Run commands from your deployment directory on a computer with cluster access. Configure Google in Google Admin Console. Keep credentials in the [protected secret directory](credentials.md#supply-tokens-from-files). Replace placeholders. Agents must ask for missing choices and secret paths, keeping secret contents out of chat.

Before running Helm, resolve `REPLACE_WITH_INSTALLED_CHART_VERSION` using [configuration checks](upgrading.md#before-changing-configuration). This keeps the installed chart version while changing its settings.

| Input | Where to get it | When needed |
| --- | --- | --- |
| `REPLACE_WITH_KUBE_CONTEXT`, `tokonoma-values.yaml`, license file and secret directory | Your [installation](install.md) record; persistent PostgreSQL is required | Before cluster commands |
| `REPLACE_WITH_MCP_HOSTNAME` and allowed email domains | Your DNS and identity administrators | Before creating the Google app |
| Stable NameID attribute and assigned users | Google Workspace or Cloud Identity super administrator | Before the first login |
| Google Entity ID, SSO URL and signing certificate | Google custom SAML app, steps 3 and 4 | Before saving authentication values |
| Test users and selected groups | Identity administrator: one assigned user, plus two group members and an outsider for group checks | Before login verification |

Choose the hostname and stable NameID before creating the app. Changing NameID creates a new Tokonoma identity; private memories may stay tied to the old identity. Hostname or service-provider (SP) entity ID changes require matching updates in Google and Tokonoma.

Use a stable HTTPS hostname reachable by users and Google. Replace namespace `tokonoma` if your installation uses another.

Verify the target cluster before changing it:

```sh
kubectl config get-contexts "REPLACE_WITH_KUBE_CONTEXT"
kubectl --context "REPLACE_WITH_KUBE_CONTEXT" cluster-info
```

Stop if either command identifies a different cluster.

## 1. Record the service-provider values

| Purpose | Exact value |
| --- | --- |
| ACS URL | `https://REPLACE_WITH_MCP_HOSTNAME/oauth/saml/acs` |
| Entity ID / audience | `https://REPLACE_WITH_MCP_HOSTNAME/saml/metadata` |
| SP metadata URL | `https://REPLACE_WITH_MCP_HOSTNAME/saml/metadata` |
| Start URL / RelayState | Leave blank |

The SP entity ID defaults to the metadata URL. An existing stable URI is also valid, but Google's Entity ID and Tokonoma's `spEntityId` must match exactly.

## 2. Prepare a stable NameID attribute

Set NameID format to **Persistent**. Use an immutable identifier, never primary email: renames would change the user's Tokonoma identity.

Use an existing immutable directory identifier, or create a single-value text attribute with a unique, opaque value per assigned user. In Google Admin Console:

1. Open **Directory > Users**.
2. Select **More options > Manage custom attributes**.
3. Add a category such as `Tokonoma Identity` with a single-value text field
   such as `Stable ID`.
4. Populate the field on each assigned user's **User information** page. Treat
   the value as immutable after the user's first Tokonoma login.

See Google's [custom-attribute instructions](https://knowledge.workspace.google.com/admin/users/create-custom-attributes-for-user-profiles).

## 3. Create the Google custom SAML app

In Google Admin Console:

1. Open **Apps > Web and mobile apps**.
2. Select **Add app > Add custom SAML app**.
3. Name the app `Tokonoma`, then continue to **Google Identity Provider
   details**.
4. Copy the exact **Entity ID** and **SSO URL**, and download the X.509
   certificate. Keep this browser tab open.
5. On **Service provider details**, enter:

   | Google field | Required setting |
   | --- | --- |
   | ACS URL | `https://REPLACE_WITH_MCP_HOSTNAME/oauth/saml/acs` |
   | Entity ID | `https://REPLACE_WITH_MCP_HOSTNAME/saml/metadata` |
   | Start URL | Leave blank |
   | Signed response | Leave unchecked; Google still signs the assertion |
   | Name ID format | `Persistent` |
   | Name ID | The stable directory/custom attribute prepared above |

6. On **Attribute mapping**, add:

   | Google Directory attribute | App attribute | Required |
   | --- | --- | --- |
   | Primary email | `email` | Yes |
   | Display name, or another suitable display field | `display_name` | No |

7. Under **Group membership**, select up to 75 groups users may share with and set the app attribute to `groups`. Google returns the group label. Its ID is the label prefixed with `google:`. Use the returned `available_groups` during verification.
8. Finish the app. Under **User access**, enable the intended organizational units or access groups, including the test users.

See Google's [app setup](https://knowledge.workspace.google.com/admin/apps/set-up-your-own-custom-saml-app?hl=en) and [group mapping](https://knowledge.workspace.google.com/admin/apps/about-group-membership-mapping) references for field details and nested membership.

Start login from the MCP client, not Google's app tile or **Test SAML login**. Tokonoma requires the client's OAuth state and Proof Key for Code Exchange (PKCE) transaction.

### Optional: add a customer-ID boundary

`allowedDomains` is required. To also check an exact tenant ID, map a single-value directory/custom attribute to `customer_id`. Set both `customerIdAttribute: customer_id` and `allowedCustomerId: REPLACE_WITH_CUSTOMER_ID`, or neither. Tokonoma rejects missing or mismatched values before issuing credentials.

## 4. Collect the exact Google IdP values

Record these Google Identity Provider values:

- the exact **Entity ID**, typically
  `https://accounts.google.com/o/saml2?idpid=...`;
- the exact **SSO URL**, typically
  `https://accounts.google.com/o/saml2/idp?idpid=...`; and
- the complete X.509 signing certificate, including its `BEGIN CERTIFICATE`
  and `END CERTIFICATE` lines.

Do not derive either URL from the other. Issuer, audience, destination,
recipient, and attribute names must match exactly, including case.

Save the certificate as `REPLACE_WITH_SECRET_DIRECTORY/google-signing.crt`.

## 5. Deploy the connection

Prepare public routing files with the [HTTPS Ingress guide](public-mcp-ingress.md) and deploy them with authentication below. For an existing private HTTPS proxy, omit `tokonoma-public.yaml` and `tokonoma-ingress.yaml` from both commands. Keep the hostname, `domain`, and OAuth origin identical.

Create the namespace and certificate Secret, then record the JSON-file checksum:

```sh
kubectl --context "REPLACE_WITH_KUBE_CONTEXT" create namespace tokonoma \
  --dry-run=client -o yaml \
  | kubectl --context "REPLACE_WITH_KUBE_CONTEXT" apply -f -

jq -Rs '[.]' "REPLACE_WITH_SECRET_DIRECTORY/google-signing.crt" \
  > "REPLACE_WITH_SECRET_DIRECTORY/idp-signing-certificates.json"

kubectl --context "REPLACE_WITH_KUBE_CONTEXT" -n tokonoma \
  create secret generic toko-mcp-google-saml \
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
    # Use none when SAML is the only login method. Keep an existing cognito or
    # google credential provider only when the deployment intentionally offers
    # both methods.
    provider: none

    saml:
      enabled: true
      provider: google

      # Copy these values exactly from Google Identity Provider details.
      idpEntityId: REPLACE_WITH_GOOGLE_ENTITY_ID
      idpSsoUrl: REPLACE_WITH_GOOGLE_SSO_URL

      idpSigningCertificatesSecret:
        name: toko-mcp-google-saml
        key: idp-signing-certificates.json
        checksum: REPLACE_WITH_SHA256_OF_THE_JSON_FILE

      # Optional; derived as https://REPLACE_WITH_MCP_HOSTNAME/saml/metadata when omitted.
      spEntityId: https://REPLACE_WITH_MCP_HOSTNAME/saml/metadata

      emailAttribute: email
      displayNameAttribute: display_name
      groupAttribute: groups
      allowedDomains:
        - REPLACE_WITH_ALLOWED_EMAIL_DOMAIN

      sessionMaxSeconds: 2592000
      clockSkewSeconds: 300
```

If using `mcp.auth.baseUrl` instead of `domain`, build ACS and metadata URLs from that HTTPS origin.

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

Rendering rejects incomplete SAML settings, non-HTTPS SSO, empty domain allowlists, missing Google group attributes, or missing certificate checksums. Changing the checksum restarts the Tokonoma pod.

## 6. Verify metadata and login

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
- the persistent NameID format; and
- ACS location `https://REPLACE_WITH_MCP_HOSTNAME/oauth/saml/acs`.

Connect an MCP client to `https://REPLACE_WITH_MCP_HOSTNAME/mcp/`, select **Continue with Google Workspace**, and finish login.

Verify identity and access with uniquely named temporary memories:

1. Save a memory with the default sharing. Its result must contain
   `owner_group_id: "toko:everyone"`. Record the returned `owner_user_id` and
   `available_groups`.
2. Confirm `owner_user_id` starts with `google:`. Sign in again as the same user
   and confirm the value is unchanged.
3. Save a private memory with `share_with: "private"`; fetch and update it as
   the same user.
4. Choose the exact selected Google group ID or label from `available_groups`.
   Save a memory with `share_with: "group"` and that value in `group`.
5. Sign in as a second member of that Google group and confirm the
   group-shared memory is readable. Sign in as the outsider and confirm
   the memory is not returned or fetchable. Neither user should be able to read the
   first user's private memory.
6. Archive all temporary records when testing is complete.

Successful login verifies the email assertion. Display names never grant access.

## Roll back the connection

To stop new Google logins, turn off Google app access for the assigned users.
For a Helm-owned deployment, restore the revision recorded before the change:

```sh
helm --kube-context "REPLACE_WITH_KUBE_CONTEXT" rollback tokonoma \
  REPLACE_WITH_PREVIOUS_REVISION \
  --namespace tokonoma \
  --wait --timeout 10m
```

Rollback restores workloads and values. It does not revoke access or refresh tokens, delete test memories, remove the certificate Secret, or change the Google app. Revoke affected clients where possible; existing access can last until the configured `sessionMaxSeconds` expires.

## Troubleshooting

Google reports success when it issues a response, even if Tokonoma rejects that response. For **Sign-in failed**, find the request ID on the page or in `X-Tokonoma-Request-ID`, then search Tokonoma logs:

```sh
kubectl --context "REPLACE_WITH_KUBE_CONTEXT" -n tokonoma \
  logs deployment/toko-mcp --since=15m \
  | grep 'REPLACE_WITH_REQUEST_ID'
```

Tokonoma logs the toolkit's safe failure reason without the assertion payload.

| Symptom | What to compare |
| --- | --- |
| Google `app_not_configured` | Google Entity ID versus Tokonoma `spEntityId`; the comparison is case-sensitive |
| Google `app_not_enabled_for_user` | The app's **User access** assignment and propagation status |
| ACS mismatch | Google ACS URL versus `https://REPLACE_WITH_MCP_HOSTNAME/oauth/saml/acs` |
| Issuer mismatch | Downloaded Google Entity ID versus `idpEntityId`; do not substitute the SSO URL |
| Audience mismatch | Google Entity ID field versus Tokonoma `spEntityId` |
| Missing email | Primary email maps to one exact `email` value |
| Non-persistent subject | Name ID format is Persistent and uses the populated stable attribute, not email |
| Signature failure | The assertion is signed and the app's active Google certificate is in the Secret |
| Missing groups | Selected groups map to the exact `groups` app attribute; the user is a direct or indirect member and completed a fresh login |
| Disallowed domain/customer | Assertion values match `allowedDomains` and, when enabled, the paired customer-ID settings |
| Unknown transaction | Start again from the MCP client; do not use the Google tile or reuse an old browser form |
| Expired assertion | Confirm Google and cluster clocks are synchronized; maximum accepted skew is 300 seconds |

See Google's [SAML errors](https://knowledge.workspace.google.com/admin/apps/saml-app-error-messages). App-access or certificate changes can take up to 24 hours.

After group membership or mapping changes, log in again before checking `available_groups`. Reselect renamed groups in the app's **Group membership** settings.

## Rotate the signing certificate

Google supports two SAML certificates. Trust both in Tokonoma before switching:

1. In Google Admin Console, open **Security > Authentication > SSO with SAML
   applications** and add a second certificate.
2. Download the new certificate while leaving the old app certificate assigned.
3. Build a JSON array containing both complete PEM values:

   ```sh
   jq -n \
     --rawfile old "REPLACE_WITH_SECRET_DIRECTORY/google-signing-old.crt" \
     --rawfile new "REPLACE_WITH_SECRET_DIRECTORY/google-signing-new.crt" \
     '[$old, $new]' > "REPLACE_WITH_SECRET_DIRECTORY/idp-signing-certificates.json"
   ```

4. Update the Kubernetes Secret, update the
   checksum, deploy, and wait for the Tokonoma rollout.
5. Assign the new certificate to the Tokonoma app in Google Admin Console.
   Allow for Google's documented propagation window, then perform a fresh
   MCP-initiated login.
6. Remove the old certificate from Tokonoma's trusted list, update the checksum,
   and deploy again. Delete the old Google certificate only after every app
   using it has migrated.

See Google's [Maintain SAML certificates](https://knowledge.workspace.google.com/admin/apps/maintain-saml-certificates)
guide for certificate assignment and expiry details.

## Current lifecycle limits

Direct Google SAML has no single logout (SLO), automated account provisioning (SCIM), provider-initiated login, account linking, multiple direct SAML providers, immediate token revocation, or silent group updates. Disabling an app or user stops new logins but leaves existing sessions valid.

The default session maximum is 2,592,000 seconds (30 days) from login; Google's shorter limit takes precedence. Access tokens last at most 24 hours, and refresh-token rotation cannot extend the original session.

Return to [private team access](private-access.md#team-access) or [connect a coding agent](coding-agents.md).
