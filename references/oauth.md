# OAuth

Configure OAuth before shared or public access. Without authentication, anyone who reaches the MCP endpoint can use its tools, including memory writes.

Start with `values.yaml` from the [installation guide](install.md#2-prepare-your-files). Authentication can be prepared before installation. Use Helm 3.14+, a stable HTTPS hostname, and a workstation with cluster access. Run commands from your working directory, following [input conventions](placeholder-examples.md) and [credential handling](credentials.md#supply-tokens-from-files).

For an existing release, use its chart version for `REPLACE_WITH_INSTALLED_CHART_VERSION`; see [configuration checks](upgrading.md#before-changing-configuration).

| Input | Where to get it | When needed |
| --- | --- | --- |
| `REPLACE_WITH_KUBE_CONTEXT`, `values.yaml`, license file and secret directory | Your installation record and platform team | Before cluster commands |
| `REPLACE_WITH_MCP_HOSTNAME` and private or public route | Your DNS and platform owners | Before provider configuration |
| Login method and provider values | Your identity administrator: Cognito pool ID, region and domain prefix, or Google project API key | Before saving authentication values |
| Cognito app credentials or Google account credentials | The identity provider; keep secrets in protected files | Credential login and machine clients |
| Requester ID, redirect URLs, grants and secret checksum | The requesting application's configuration | Only for declared clients |

Verify the selected cluster:

```sh
kubectl config get-contexts "REPLACE_WITH_KUBE_CONTEXT"
kubectl --context "REPLACE_WITH_KUBE_CONTEXT" cluster-info
```

Stop if either command identifies a different cluster.

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

For a first installation, [install Tokonoma](install.md#3-install) with the prepared file and credentials, then verify authentication below. For an existing release, apply the updated file:

```sh
helm upgrade tokonoma --reset-then-reuse-values oci://public.ecr.aws/tokonoma/charts/tokonoma \
  --kube-context "REPLACE_WITH_KUBE_CONTEXT" \
  --version REPLACE_WITH_INSTALLED_CHART_VERSION -n tokonoma \
  --values values.yaml \
  --set-file mcp.license="REPLACE_WITH_SECRET_DIRECTORY/license.txt" \
  --wait --timeout 10m
```

Preserve existing credential inputs and Secret references. Wait for Helm to report `STATUS: deployed`. Then check the OAuth metadata:

```sh
curl -sS -o /dev/null -w '%{http_code}\n' https://REPLACE_WITH_MCP_HOSTNAME/.well-known/oauth-protected-resource/mcp
```

Expect `200`. Then check the protected MCP endpoint:

```sh
curl -sS -o /dev/null -w '%{http_code}\n' https://REPLACE_WITH_MCP_HOSTNAME/mcp
```

Expect `401` before login.

[Connect your agent](coding-agents.md#use-a-public-endpoint) to `https://REPLACE_WITH_MCP_HOSTNAME/mcp` and complete browser login.

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

Return to [private team access](private-access.md#team-access) or [connect a coding agent](coding-agents.md).
