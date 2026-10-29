# Connect integrations

Tokonoma connects to compatible remote Model Context Protocol (MCP) servers for telemetry and investigation tools. Datadog and Axiom are examples; the connection settings are not tied to a provider. Check saved values before adding connections. Agents read existing choices and ask for missing inputs.

| Integration | What it does | Setup |
|---|---|---|
| MCP query tools | Connect Datadog, Axiom, or another compatible telemetry or code server | [MCP connections](#mcp-connections) |
| GitHub | Read permitted source code and commit history during investigations | [GitHub example](#github-example) |
| Existing Grafana | Private OSS Grafana MCP adapter queries permitted data sources for monitoring and investigations | [Alert investigations](alert-investigations.md#install-with-oss-grafana-mcp) |
| Alert webhooks | Deliver alerts to the runner; separate from MCP query access | [Alertmanager or Grafana Alerting](alert-investigations.md), [Datadog alerts](datadog-alerts.md) |
| Slack | Use the native Tokonoma app, or connect Claude to Tokonoma | [Tokonoma app](slack-app.md), [Claude in Slack](claude-in-slack.md) |
| Tokonoma telemetry platform | Stores and searches ingested logs, traces, and Kubernetes inventory/events | [EKS](cloud-providers/aws.md), [GKE](cloud-providers/google-cloud.md), [endpoints](endpoints.md) |

The bundled `grafanaMcp` adapter queries an existing Grafana. The separate `grafana.enabled` setting installs a UI for Tokonoma's own monitoring. They are independent options.

There is no bundled CloudWatch adapter. A separately supplied MCP server must meet the connection requirements below; enabling telemetry storage does not connect it.

Memory analysis and the runner both use the Anthropic API. Verify model identifiers before changing them. See [memory analysis](memory-llm.md) and [data flows](data-flows.md).

## MCP connections

The runner supports remote Streamable HTTP MCP endpoints with Secret-backed bearer tokens or named authentication headers. It does not launch local `stdio` servers or complete third-party browser login and token refresh. Use credentials suitable for unattended access. Tokonoma's own [OAuth settings](oauth.md) authenticate callers to Tokonoma, not the runner to external providers.

### 1. Choose the connection and tools

Uncomment the matching `runner.mcpServers` entries in [values.yaml](../examples/values.yaml). Keep all servers in one list and preserve existing entries.

- Use unique lowercase names with hyphens rather than underscores. Reserve `toko`, and `grafana` when the bundled Grafana adapter is enabled.
- Obtain the full MCP endpoint from the provider. It must be reachable from the runner; use HTTPS for external connections.
- Set `kind: telemetry` for monitoring sources or `kind: source-control` for code access.
- Set `expectedTools` to exact tool names advertised by that server, without an `mcp__` prefix. Empty or missing entries permit no calls. List read-only tools only, and use credentials with matching permissions. The runner does not filter these lists: every listed tool is available to automatic investigations and to Agentic Monitoring, whose setup and scheduled refresh run with nobody watching and replay the tool calls they recorded, such as the entity listing, on every refresh.

Automatic investigations and Agentic Monitoring require telemetry query access. Monitoring tools must also cover the selected cluster and namespaces. Alert webhooks and code-only connections do not supply telemetry access. Results are sent to the Anthropic API; review [data flows](data-flows.md).

### 2. Prepare credentials

Follow [credential setup](credentials.md#supply-credentials-in-commands) and [prepare the release namespace](credentials.md#prepare-the-namespace-for-secrets). Use an existing Secret or create one with the issued credential. Its owner supplies the Secret name and key. Replace the credential placeholder locally before running:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma create secret generic REPLACE_WITH_MCP_SECRET_NAME \
  --from-literal=REPLACE_WITH_MCP_SECRET_KEY='REPLACE_WITH_MCP_CREDENTIAL'
```

For bearer authentication, store the raw token without `Bearer ` and fill `authSecretRef`. For named-header authentication, use the commented `headers` alternative and remove `authSecretRef`; headers take precedence. Repeat for each credential using distinct Secret names, or use your secret manager. Preserve existing Secrets on upgrades.

### 3. Apply the configuration

For a new deployment, finish the selected integrations and use the [single installation command](install.md#3-install). For an existing release, [apply the configuration change](upgrading.md#before-changing-configuration). Do not create a separate values file for each provider.

### 4. Check access

With Slack enabled, `@Tokonoma admin status` reports the runner's MCP connections and missing tools. A connected server does not prove every query is authorized. When automatic investigations or monitoring are enabled, use the applicable [investigation](alert-investigations.md#check-it-works) and [monitoring checks](agentic-monitoring.md#verify-monitoring) to confirm the intended telemetry is accessible. Updating the runner does not configure the MCP connections in your personal coding agent.

## GitHub example

GitHub adds source-code context to investigations. It is optional and does not replace telemetry access. For GitHub.com, use the commented `name: github` entry in [values.yaml](../examples/values.yaml), with `kind: source-control` and GitHub's [hosted read-only endpoint](https://github.com/github/github-mcp-server/blob/main/docs/remote-server.md): `https://api.githubcopilot.com/mcp/readonly`. No local GitHub server is needed.

1. [Create a fine-grained personal access token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-fine-grained-personal-access-token). Choose the organization or account that owns the repositories, select only the repositories Tokonoma may read, and set an expiration. Grant repository **Contents: Read-only**; Metadata access is included. Obtain organization approval if required before using the token for private repositories.
2. Use [Prepare credentials](#2-prepare-credentials) to create or reuse the Secret with the raw token: the example uses `toko-runner-github`, key `token`. Fill the credential placeholder locally; never paste the token into chat.
3. Uncomment the GitHub entry in the shared `runner.mcpServers` list. Its `expectedTools` permits `get_file_contents`, `search_code`, `get_commit`, and `list_commits`. Confirm these names against the server's advertised tools; add other read-only tools and their required permissions only when needed.

Use the shared [apply](#3-apply-the-configuration) and [access checks](#4-check-access) above. For a GitHub follow-up check, read a known file from a selected private repository; connecting successfully does not prove repository access. Token expiration or loss of the owner's repository access requires [credential renewal](credentials.md#renew-and-rotate). GitHub Enterprise installations need their provider-specific endpoint and authentication; do not assume this GitHub.com example applies.

## Datadog example

Use the generic telemetry entry with `name: datadog`. Get the endpoint for your Datadog site from [Datadog's MCP setup](https://docs.datadoghq.com/mcp_server/setup/); US1 uses `https://mcp.datadoghq.com/v1/mcp`. Select the toolsets you need and copy their advertised read-only tool names into `expectedTools`.

For API and application keys, uncomment the `headers` alternative in `values.yaml`. Reference the API key under `DD_API_KEY` and the application key under `DD_APPLICATION_KEY`. These are HTTP header names. Keep each key in its referenced Secret. A supported Datadog personal or service access token can use `authSecretRef` instead. Follow [Datadog's authentication guidance](https://docs.datadoghq.com/mcp_server/setup/#authentication) for permissions.

These credentials provide query access. To receive monitor alerts too, follow [Datadog webhooks](datadog-alerts.md); its webhook token is separate.

## Axiom example

Use the generic telemetry entry with `name: axiom`. Set its URL to `https://mcp.axiom.co/mcp?org-id=REPLACE_WITH_AXIOM_ORG_ID`, using the organization ID from Axiom. Reference an Axiom personal access token through `authSecretRef`. This follows [Axiom's header-based authentication](https://axiom.co/docs/console/intelligence/mcp-server#header-based-authentication).

Start with the read-only tools `listDatasets`, `getDatasetFields`, and `queryDataset`, confirming they are available to your account. Add other tools only as needed; see [Axiom's tool reference](https://axiom.co/docs/console/intelligence/mcp-server/tools). Axiom's hosted MCP service routes query results through US infrastructure. This connection provides query access; it does not add an Axiom alert receiver.
