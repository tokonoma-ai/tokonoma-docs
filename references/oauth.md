# OAuth

Configure OAuth before shared or public access. Without authentication, anyone who reaches the MCP endpoint can use its tools, including memory writes.

Start with `values.yaml` from the [installation guide](install.md#2-prepare-your-files), Helm 3.14+, and a workstation with cluster access. Prepare runner machine authentication in phase 1. A stable HTTPS hostname and human sign-in belong to phase 2, after the [installation checkpoint](install.md#check-monitoring-and-integrations). Run commands from your working directory, following [input conventions](install.md#inputs-and-placeholders) and [credential handling](credentials.md#supply-tokens-from-files).

| Input | Where to get it | When needed |
| --- | --- | --- |
| `REPLACE_WITH_KUBE_CONTEXT`, `values.yaml`, license file and secret directory | Your installation record and platform team | Before cluster commands |
| `REPLACE_WITH_MCP_HOSTNAME` and private or public route | Your DNS and platform owners | Phase 2 shared access |
| Login method and provider values | Your identity administrator: Cognito pool ID, region and domain prefix, or Google project API key | Before saving authentication values |
| Cognito app credentials or Google account credentials | The identity provider; keep secrets in protected files | Credential login and machine clients |
| Requester ID, redirect URLs, grants and secret checksum | The requesting application's configuration | Only for declared clients |

Confirm the target cluster with the [installation checks](install.md#1-check-prerequisites).

For human SAML login, use [Google Workspace](google-saml.md) or [Okta](okta-saml.md) alongside the credential provider below. The required runner needs machine credentials when MCP authentication is enabled. Keep both configurations in `values.yaml`.

`mcp.auth.enabled` controls OAuth routes and bearer protection. `mcp.auth.provider` selects Cognito or legacy Google to verify machine credentials. SAML supplies human login.

## 1. Prepare the provider

For Cognito, create a user pool and record its ID and region. Add a Cognito-managed domain and resource server `toko-mcp` with scope `query`. Create a machine-to-machine app client with a secret, `client_credentials` flow, and `toko-mcp/query` scope.

Both browser and machine login verify this app client. Enter its ID as **Client ID** and secret as **Client Secret**. Cognito pool-user usernames and passwords do not work; use SAML for individual human login.

For legacy Google Identity Platform/Firebase, enable **Email/Password** sign-in and provision accounts. Tokonoma uses `signInWithPassword`: enter account email as **Client ID** and password as **Client Secret** in both browser and machine requests. Google OAuth app credentials do not work. Get that project's API key. Before creating its Secret, [prepare the release namespace](credentials.md#prepare-the-namespace-for-secrets).

Save the API key in `REPLACE_WITH_SECRET_DIRECTORY/google-identity-api-key.txt` with restricted permissions and no trailing newline. Create the API key Secret:

```sh
kubectl --context "REPLACE_WITH_KUBE_CONTEXT" -n tokonoma create secret generic google-oauth \
  --from-file=apiKey="REPLACE_WITH_SECRET_DIRECTORY/google-identity-api-key.txt"
```

## 2. Save the values

Merge these settings into `values.yaml`, preserving existing `mcp` settings and any SAML configuration. Choose `cognito` or `google` and remove the unused provider block.

For a new phase 1 installation, omit the `domain` field below, set `mcp.auth.baseUrl: http://localhost:8000`, and keep `mcp.ingress.enabled` and `runner.ingress.enabled` false. Leave `runner.tokoMcp.url` empty so the runner uses its private MCP service. Prepare provider settings and runner credentials now; add the shared HTTPS hostname, routing, and human sign-in in phase 2. Preserve existing addresses and authentication on upgrades.

```yaml
domain: REPLACE_WITH_MCP_HOSTNAME
region: REPLACE_WITH_AWS_REGION
mcp:
  auth:
    enabled: true
    provider: cognito
    cognito:
      userPoolId: REPLACE_WITH_COGNITO_USER_POOL_ID
      domainPrefix: REPLACE_WITH_COGNITO_DOMAIN_PREFIX
    google:
      apiKeySecret:
        name: google-oauth
        key: apiKey
```

Set `domainPrefix` to your pool's Cognito-managed prefix in `REPLACE_WITH_COGNITO_DOMAIN_PREFIX.auth.REPLACE_WITH_AWS_REGION.amazoncognito.com`, replacing the chart default. Tokonoma uses it to verify machine credentials.

`mcp.auth.cognito.region` overrides the top-level `region`. If both are empty, the server uses `us-west-2`.

`provider: google` selects legacy credentials, not Google Workspace SAML.

Prepare the [runner machine credentials](alert-investigations.md#prepare-runner-credentials-when-mcp-authentication-is-enabled) before deploying authentication.

For public access, merge the [public MCP routing settings](public-mcp-ingress.md) into the same `values.yaml`. Existing private HTTPS routing needs no public Ingress settings. Set `domain` to the route's HTTPS hostname.

## 3. Deploy and verify

For a first installation, [install Tokonoma](install.md#3-install) with the prepared file and credentials. For an existing release, follow [the configuration-change procedure](upgrading.md#before-changing-configuration). In phase 1, use the installation's local port-forward and replace the HTTPS base URL in the checks below with `http://localhost:8000`. Once the deployment is healthy, check OAuth metadata:

```sh
curl -sS -o /dev/null -w '%{http_code}\n' https://REPLACE_WITH_MCP_HOSTNAME/.well-known/oauth-protected-resource/mcp
```

Expect `200`. Then check the protected MCP endpoint:

```sh
curl -sS -o /dev/null -w '%{http_code}\n' https://REPLACE_WITH_MCP_HOSTNAME/mcp
```

Expect `401` before login.

In phase 2, [connect your agent](coding-agents.md#use-a-public-endpoint) to the shared endpoint `https://REPLACE_WITH_MCP_HOSTNAME/mcp` and complete browser login.

## Choose OAuth client admission

`mcp.auth.clientRegistrationMode` controls which applications can request authorization:

| Mode | Dynamic registration `/register` | Declared clients | Unknown verified credential clients |
|---|---:|---:|---:|
| `dynamic_only` | Yes | No | No |
| `hybrid` (default) | Yes | Yes | Registered on first successful Cognito/Google credential grant for compatibility |
| `preregistered_only` | No | Yes | No |

Use `hybrid` during upgrades, or `preregistered_only` when you manage every requesting application and service client. A client blocked by the selected mode cannot use an older PostgreSQL registration to gain access.

Before changing modes, declare each credential client registered through `hybrid` as `external`, using its existing Cognito app client ID or Google account email. No database cleanup is needed. `preregistered_only` rejects undeclared clients but retains their records for rollback to `hybrid`. Reusing a dynamic client ID or switching between `configured` and `external` causes a startup error.

Do not change external client IDs to avoid collisions. IDs also identify credentials and memory ownership; changes require matching caller and identity provider updates and can create a new owner. Previously issued access tokens remain valid until expiry.

For an interactive application, save a high-entropy secret in `REPLACE_WITH_SECRET_DIRECTORY/requester-client-secret.txt`. Create its Secret and merge these settings into `values.yaml`. Set exact redirects, grants, and a supported authentication method before redeploying:

```sh
kubectl --context "REPLACE_WITH_KUBE_CONTEXT" -n tokonoma create secret generic requester-oauth-client \
  --from-file=current="REPLACE_WITH_SECRET_DIRECTORY/requester-client-secret.txt"
```

```yaml
mcp:
  auth:
    enabled: true
    clientRegistrationMode: preregistered_only
    clients:
      - id: REPLACE_WITH_REQUESTER_CLIENT_ID
        name: Interactive requester
        origin: configured
        enabled: true
        redirectUris: [REPLACE_WITH_EXACT_REDIRECT_URI]
        grantTypes: [authorization_code, refresh_token]
        responseTypes: [code]
        scopes: [toko-mcp/query]
        tokenEndpointAuthMethod: client_secret_basic
        secretRef:
          name: requester-oauth-client
          key: current
          checksum: REPLACE_WITH_SECRET_CHECKSUM
```

`configured` secrets are mounted read-only, never stored in PostgreSQL. To rotate without downtime, add `nextSecretRef`, deploy with both secrets, update callers, then promote the new secret and remove the old one in a second deployment. Update each reference's `checksum` when Secret data changes so the pod restarts.

If you omit `scopes`, it defaults to `[toko-mcp/query]`; `scopes: []` is rejected. To deny access, set `enabled: false` or remove the client.

For `external` clients, set `id` to the Cognito app client ID or legacy Google Identity/Firebase account email. Use `client_credentials` without `secretRef`; `mcp.auth.provider` verifies every credential use. Match `tokenEndpointAuthMethod` to the caller: `client_secret_post` for form fields or `client_secret_basic` for HTTP Basic:

```yaml
mcp:
  auth:
    clients:
      - id: REPLACE_WITH_PROVIDER_CLIENT_ID
        origin: external
        enabled: true
        grantTypes: [client_credentials, refresh_token]
        scopes: [toko-mcp/query]
        tokenEndpointAuthMethod: client_secret_post
```

`mcp.auth.clientCredentialsRefreshMode: legacy` preserves refresh tokens for `client_credentials`. Prefer `disabled` for new managed deployments; switch existing automation only after confirming it can repeat the credential grant.

With `disabled`, the server consumes and rejects credential refresh tokens; rollback to `legacy` cannot revive them. Existing access tokens retain their expiry. Authorization-code refresh tokens still follow each client's `refresh_token` grant. Older browser password sessions may need one new login because their tokens lack the originating grant.

Supported grants are `authorization_code`, `refresh_token`, and `client_credentials`; JWT bearer and ID-JAG redemption are unsupported.

## Optional: direct Google Workspace or Okta SAML login

Select one provider with `mcp.auth.saml.provider`: [Google Workspace](google-saml.md) or [Okta](okta-saml.md). SAML requires stable HTTPS and persistent PostgreSQL token storage. Keep the credential provider for the runner; the login page offers both methods.

Google supports group sharing. Okta supports only private and `toko:everyone` access; do not configure Okta group statements.

### Prepare SAML signing certificates

Use `jq` to turn the complete PEM certificate into the JSON array Tokonoma expects. Keep the files in your [protected credential directory](credentials.md#supply-tokens-from-files) and [prepare the release namespace](credentials.md#prepare-the-namespace-for-secrets) before creating the Secret.

Replace the placeholders below with the values for your provider:

| Provider | `REPLACE_WITH_CERTIFICATE_FILENAME` | `REPLACE_WITH_SAML_SECRET_NAME` |
| --- | --- | --- |
| Google Workspace | `google-signing.crt` | `toko-mcp-google-saml` |
| Okta | `okta-signing.crt` | `toko-mcp-okta-saml` |

```sh
jq -Rs '[.]' "REPLACE_WITH_SECRET_DIRECTORY/REPLACE_WITH_CERTIFICATE_FILENAME" \
  > "REPLACE_WITH_SECRET_DIRECTORY/idp-signing-certificates.json"
```

Continue with the Secret and checksum below, then return to your provider's values block.

### Apply the SAML certificate Secret

Use the Secret name from the table above. This command creates or updates it:

```sh
kubectl --context "REPLACE_WITH_KUBE_CONTEXT" -n tokonoma \
  create secret generic REPLACE_WITH_SAML_SECRET_NAME \
  --from-file=idp-signing-certificates.json="REPLACE_WITH_SECRET_DIRECTORY/idp-signing-certificates.json" \
  --dry-run=client -o yaml \
  | kubectl --context "REPLACE_WITH_KUBE_CONTEXT" apply -f -

sha256sum "REPLACE_WITH_SECRET_DIRECTORY/idp-signing-certificates.json"
```

Expect the Secret result `created`, `configured`, or `unchanged`. On macOS, use `shasum -a 256`. Hash the JSON file, not the certificate fingerprint or raw PEM. Copy the checksum into `mcp.auth.saml.idpSigningCertificatesSecret.checksum` in `values.yaml`; keep only the Secret name, key, and checksum in that file.

The chart rejects incomplete SAML settings, non-HTTPS SSO, empty domain allowlists, missing Google group attributes, or missing certificate checksums. A changed checksum restarts the Tokonoma pod when you apply the values.

### Verify SAML metadata

After the [installation](install.md#3-install) or [configuration change](upgrading.md#before-changing-configuration) completes, fetch the metadata:

```sh
curl -fsS https://REPLACE_WITH_MCP_HOSTNAME/saml/metadata
```

Check these fields before testing login in the provider guide:

- `entityID` matches your configured `spEntityId`, defaulting to `https://REPLACE_WITH_MCP_HOSTNAME/saml/metadata`.
- `AuthnRequestsSigned="false"`.
- `WantAssertionsSigned="true"`.
- NameID format is persistent.
- ACS location is `https://REPLACE_WITH_MCP_HOSTNAME/oauth/saml/acs`.

### Rotate SAML signing certificates

Download the old and new certificates as separate PEM files using the names in your provider's rotation steps. Keep the old certificate active at the provider until Tokonoma trusts both.

```sh
jq -n \
  --rawfile old "REPLACE_WITH_SECRET_DIRECTORY/REPLACE_WITH_OLD_CERTIFICATE_FILENAME" \
  --rawfile new "REPLACE_WITH_SECRET_DIRECTORY/REPLACE_WITH_NEW_CERTIFICATE_FILENAME" \
  '[$old, $new]' > "REPLACE_WITH_SECRET_DIRECTORY/idp-signing-certificates.json"
```

[Apply the Secret and checksum](#apply-the-saml-certificate-secret), then [deploy the configuration change](upgrading.md#before-changing-configuration). After the rollout, return to your provider's instructions to activate the new certificate and test a fresh login.

Once login succeeds, repeat [certificate preparation](#prepare-saml-signing-certificates) with only the new certificate file. Apply the updated Secret, checksum, and configuration again before removing the old certificate at the provider.

### Roll back SAML configuration

Stop new logins through the provider's app assignment controls. Disconnect or revoke affected clients where possible, archive test memories, and restore the revision recorded before the change:

```sh
helm --kube-context "REPLACE_WITH_KUBE_CONTEXT" rollback tokonoma \
  REPLACE_WITH_PREVIOUS_REVISION \
  --namespace tokonoma \
  --wait --timeout 10m
```

Rollback restores workloads and values. It does not revoke access or refresh tokens, delete memories, remove the certificate Secret, or change the provider app. Existing sessions can last until `sessionMaxSeconds` expires. A certificate Secret changed outside Helm also needs its previous contents restored if the rolled-back configuration requires them.

### Diagnose SAML login

For **Sign-in failed**, find the request ID on the page or in `X-Tokonoma-Request-ID`, then search Tokonoma logs:

```sh
kubectl --context "REPLACE_WITH_KUBE_CONTEXT" -n tokonoma \
  logs deployment/toko-mcp --since=15m \
  | grep 'REPLACE_WITH_REQUEST_ID'
```

The logs include a failure reason without the assertion payload. Compare it with the troubleshooting table in your provider guide.

### SAML session limits

Direct SAML has no single logout (SLO), automated account provisioning (SCIM), provider-initiated login, account linking, multiple direct SAML providers, or immediate token revocation. Disabling an app or user stops new logins but leaves existing sessions valid.

The default session maximum is 2,592,000 seconds (30 days) from login; a shorter provider `SessionNotOnOrAfter` takes precedence. Access tokens last at most 24 hours, and refresh-token rotation cannot extend the original session.

Return to [private team access](private-access.md#team-access) or [connect a coding agent](coding-agents.md).
