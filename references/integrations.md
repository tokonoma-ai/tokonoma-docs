# Connect integrations

Tokonoma connects to compatible remote Model Context Protocol (MCP) servers for telemetry and investigation tools. Datadog and Axiom are examples; the connection settings are not tied to a provider. Check saved values before adding connections. Agents read existing choices and ask for missing inputs.

| Integration | What it does | Setup |
|---|---|---|
| MCP query tools | Connect Datadog, Axiom, or another compatible telemetry or code server | [MCP connections](#mcp-connections) |
| Existing Grafana | Private OSS Grafana MCP adapter queries permitted data sources for monitoring and investigations | [Alert investigations](alert-investigations.md#install-with-oss-grafana-mcp) |
| Alert webhooks | Deliver alerts to the runner; separate from MCP query access | [Alertmanager or Grafana Alerting](alert-investigations.md), [Datadog alerts](datadog-alerts.md) |
| Slack | Use the native Tokonoma app, or connect Claude to Tokonoma | [Tokonoma app](slack-app.md), [Claude in Slack](claude-in-slack.md) |
| Tokonoma telemetry platform | Stores and searches ingested logs, traces, and Kubernetes inventory/events | [EKS](cloud-providers/aws.md), [GKE](cloud-providers/google-cloud.md), [endpoints](endpoints.md) |

The bundled `grafanaMcp` adapter queries an existing Grafana. The separate `grafana.enabled` setting installs a UI for Tokonoma's own monitoring. They are independent options.

There is no bundled CloudWatch adapter. A separately supplied MCP server must meet the connection requirements below; enabling telemetry storage does not connect it.

Memory analysis uses the Anthropic API. The runner has its own provider configuration; verify credentials and model identifiers before changing it. See [memory analysis](memory-llm.md) and [data flows](data-flows.md).

## MCP connections

The runner supports remote Streamable HTTP MCP endpoints with Secret-backed bearer tokens or named authentication headers. It does not launch local `stdio` servers or complete third-party browser login and token refresh. Use credentials suitable for unattended access. Tokonoma's own [OAuth settings](oauth.md) authenticate callers to Tokonoma, not the runner to external providers.

### 1. Choose the connection and tools

Uncomment the matching `runner.mcpServers` entries in [values.yaml](../examples/values.yaml). Keep all servers in one list and preserve existing entries.

- Use unique lowercase names with hyphens rather than underscores. Reserve `toko`, and `grafana` when the bundled Grafana adapter is enabled.
- Obtain the full MCP endpoint from the provider. It must be reachable from the runner; use HTTPS for external connections.
- Set `kind: telemetry` for monitoring sources or `kind: source-control` for code access.
- Set `expectedTools` to exact tool names advertised by that server, without an `mcp__` prefix. Empty or missing entries permit no calls. Choose read-only tools and credentials with matching permissions.

Monitoring needs query tools that can access the selected cluster and namespaces. Alert webhooks and code-only connections do not supply telemetry access. Results can be sent to the runner's model provider; review [data flows](data-flows.md).

### 2. Prepare credentials

Follow [credential handling](credentials.md#supply-tokens-from-files) and [prepare the release namespace](credentials.md#prepare-the-namespace-for-secrets). Use an existing Secret or save each issued credential in its own protected file without a final newline. Its owner supplies the Secret name and key; replace `REPLACE_WITH_CREDENTIAL_FILE` with the matching file name:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma create secret generic REPLACE_WITH_MCP_SECRET_NAME \
  --from-file=REPLACE_WITH_MCP_SECRET_KEY="REPLACE_WITH_SECRET_DIRECTORY/REPLACE_WITH_CREDENTIAL_FILE"
```

For bearer authentication, store the raw token without `Bearer ` and fill `authSecretRef`. For named-header authentication, use the commented `headers` alternative and remove `authSecretRef`; headers take precedence. Repeat for each credential using distinct Secret names, or use your secret manager. Preserve existing Secrets on upgrades.

### 3. Apply the configuration

For a new deployment, finish the selected integrations and use the [single installation command](install.md#3-install). For an existing release, [apply the configuration change](upgrading.md#before-changing-configuration). Do not create a separate values file for each provider.

### 4. Check access after installation

These checks are optional follow-ups. With Slack enabled, `@Tokonoma setup` reports the runner's MCP connections and missing tools. A connected server does not prove every query is authorized: use a controlled [investigation check](alert-investigations.md#check-it-works) to confirm the intended data is accessible. Check [monitoring coverage](agentic-monitoring.md#verify-monitoring) separately. Updating the runner does not configure the MCP connections in your personal coding agent.

## Datadog example

Use the generic telemetry entry with `name: datadog`. Get the endpoint for your Datadog site from [Datadog's MCP setup](https://docs.datadoghq.com/mcp_server/setup/); US1 uses `https://mcp.datadoghq.com/v1/mcp`. Select the toolsets you need and copy their advertised read-only tool names into `expectedTools`.

For API and application keys, uncomment the `headers` alternative in `values.yaml`. Reference the API key under `DD_API_KEY` and the application key under `DD_APPLICATION_KEY`. These are HTTP header names. Keep each key in its referenced Secret. A supported Datadog personal or service access token can use `authSecretRef` instead. Follow [Datadog's authentication guidance](https://docs.datadoghq.com/mcp_server/setup/#authentication) for permissions.

These credentials provide query access. To receive monitor alerts too, follow [Datadog webhooks](datadog-alerts.md); its webhook token is separate.

## Axiom example

Use the generic telemetry entry with `name: axiom`. Set its URL to `https://mcp.axiom.co/mcp?org-id=REPLACE_WITH_AXIOM_ORG_ID`, using the organization ID from Axiom. Reference an Axiom personal access token through `authSecretRef`. This follows [Axiom's header-based authentication](https://axiom.co/docs/console/intelligence/mcp-server#header-based-authentication).

Start with the read-only tools `listDatasets`, `getDatasetFields`, and `queryDataset`, confirming they are available to your account. Add other tools only as needed; see [Axiom's tool reference](https://axiom.co/docs/console/intelligence/mcp-server/tools). Axiom's hosted MCP service routes query results through US infrastructure. This connection provides query access; it does not add an Axiom alert receiver.
