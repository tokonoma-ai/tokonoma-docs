# Guide: OAuth

Configure OAuth before shared or public access. Without authentication, anyone who reaches the MCP endpoint can use its tools, including memory writes.

Complete the [installation](../install.md). Use Helm 3.14+, a stable HTTPS hostname, and your deployment working directory with cluster access. Keep credentials in the [protected secret directory](credentials.md#supply-tokens-from-files). Replace placeholders; agents must ask for missing choices and secret paths, never contents.

| Input | Where to get it | When needed |
| --- | --- | --- |
| `REPLACE_WITH_KUBE_CONTEXT`, `tokonoma-values.yaml`, license file and secret directory | Your installation record and platform team | Before cluster commands |
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

For human SAML login, start with [Google Workspace](google-saml.md) or [Okta](okta-saml.md). Add credential authentication below only if needed. Both use `tokonoma-oauth.yaml`.

`mcp.auth.enabled` controls OAuth routes and bearer protection. `mcp.auth.provider` selects the optional credential verifier; SAML works without it.

## 1. Prepare the provider

For Cognito, create a user pool and record its ID and region. Add a Cognito-managed domain and resource server `toko-mcp` with scope `query`. Create a machine-to-machine app client with a secret, `client_credentials` flow, and `toko-mcp/query` scope.

The browser form and machine grant both verify this app client. Enter its ID as **Client ID** and secret as **Client Secret**. Cognito pool-user usernames and passwords do not work; use SAML for individual human login.

For legacy Google Identity Platform/Firebase, enable **Email/Password** sign-in and provision accounts. Tokonoma uses `signInWithPassword`: enter account email as **Client ID** and password as **Client Secret** in both browser and machine requests. Google OAuth app credentials do not work. Obtain that project’s API key. Create the namespace if absent:

```sh
kubectl --context "REPLACE_WITH_KUBE_CONTEXT" create namespace tokonoma
```

Save the API key in `REPLACE_WITH_SECRET_DIRECTORY/google-identity-api-key.txt` with restricted permissions and no trailing newline. Create the API key Secret:

```sh
kubectl --context "REPLACE_WITH_KUBE_CONTEXT" -n tokonoma create secret generic google-oauth \
  --from-file=apiKey="REPLACE_WITH_SECRET_DIRECTORY/google-identity-api-key.txt"
```

## 2. Save the values

Save as `tokonoma-oauth.yaml`, or merge into that file if SAML is already configured. Choose `cognito` or `google` and remove the unused provider block.

```yaml
domain: REPLACE_WITH_MCP_HOSTNAME
region: REPLACE_WITH_AWS_REGION
mcp:
  image:
    tag: "0.68.0"
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

Set `domainPrefix` to your pool’s Cognito-managed prefix in `REPLACE_WITH_COGNITO_DOMAIN_PREFIX.auth.REPLACE_WITH_AWS_REGION.amazoncognito.com`, replacing the chart default. Tokonoma uses it to verify machine credentials.

`mcp.auth.cognito.region` overrides the top-level `region`. If both are empty, the server uses `us-west-2`.

`provider: google` selects legacy credentials, not Google Workspace SAML.

Prepare `tokonoma-public.yaml` and `tokonoma-ingress.yaml` using the [public MCP guide](public-mcp-ingress.md), then deploy them with authentication below. For existing private HTTPS routing, omit both files. Set `domain` to the route’s HTTPS hostname.

## 3. Deploy and verify

```sh
helm upgrade --install tokonoma --reset-then-reuse-values oci://public.ecr.aws/tokonoma/charts/tokonoma \
  --kube-context "REPLACE_WITH_KUBE_CONTEXT" \
  --version 0.37.0 -n tokonoma --create-namespace \
  -f tokonoma-values.yaml -f tokonoma-public.yaml -f tokonoma-ingress.yaml \
  -f tokonoma-oauth.yaml \
  --set-file mcp.license="REPLACE_WITH_SECRET_DIRECTORY/license.txt" \
  --wait --timeout 10m
```

Wait for Helm to report `STATUS: deployed`. Then check the OAuth metadata:

```sh
curl -sS -o /dev/null -w '%{http_code}\n' https://REPLACE_WITH_MCP_HOSTNAME/.well-known/oauth-protected-resource/mcp
```

The expected response is `200`. Then check the protected MCP endpoint:

```sh
curl -sS -o /dev/null -w '%{http_code}\n' https://REPLACE_WITH_MCP_HOSTNAME/mcp
```

The expected response before login is `401`.

[Connect your agent](coding-agents.md#use-a-public-endpoint) to `https://REPLACE_WITH_MCP_HOSTNAME/mcp` and complete browser login.

## Choose OAuth client admission

`mcp.auth.clientRegistrationMode` controls which applications can request authorization:

| Mode | DCR `/register` | Declared clients | Unknown verified credential clients |
|---|---:|---:|---:|
| `dynamic_only` | Yes | No | No |
| `hybrid` (default) | Yes | Yes | Registered on first successful Cognito/Google credential grant for compatibility |
| `preregistered_only` | No | Yes | No |

Use `hybrid` during upgrades, or `preregistered_only` when you manage every requesting application and service client. A client blocked by the selected mode cannot use an older PostgreSQL registration to gain access.

Before changing modes, declare each credential client registered through `hybrid` as `external`, using its existing Cognito app client ID or Google account email. No database cleanup is needed. `preregistered_only` rejects undeclared clients but retains their records for rollback to `hybrid`. Reusing a dynamic client ID or switching between `configured` and `external` causes a startup error.

Do not change external client IDs to avoid collisions. IDs also identify credentials and memory ownership; changes require matching caller and identity provider updates and can create a new owner. Previously issued access tokens remain valid until expiry.

For an interactive application, save a high-entropy secret in `REPLACE_WITH_SECRET_DIRECTORY/requester-client-secret.txt`. Create its Secret, add these settings to `tokonoma-oauth.yaml`, and redeploy. Set exact redirects and grants, using an authentication method the client supports:

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

`configured` secrets are mounted read-only, never stored in PostgreSQL. To rotate without downtime, add `nextSecretRef`, deploy with both secrets, update callers, then promote the new secret and remove the old one in a second deployment. Update each reference's `checksum` when Secret data changes to roll the pod.

Omitted `scopes` defaults to `[toko-mcp/query]`; `scopes: []` is rejected. To deny access, set `enabled: false` or remove the client.

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

With `disabled`, presented credential refresh tokens are consumed and rejected; rollback to `legacy` cannot revive them. Existing access tokens retain their expiry. Authorization-code refresh tokens still follow each client’s `refresh_token` grant. Older browser password sessions may need one new login because their tokens lack the originating grant.

This release supports `authorization_code`, `refresh_token`, and `client_credentials`. These settings do not enable JWT bearer or ID-JAG redemption.

## Optional: direct Google Workspace or Okta SAML login

Select one provider with `mcp.auth.saml.provider`: [Google Workspace](google-saml.md) or [Okta](okta-saml.md). SAML requires stable HTTPS and persistent PostgreSQL token storage. If credential authentication is also configured, the login page offers both.

Google supports group sharing. Okta supports only private and `toko:everyone` access; do not configure Okta group statements.

Return to [private team access](private-access.md#team-access) or [connect a coding agent](coding-agents.md).
