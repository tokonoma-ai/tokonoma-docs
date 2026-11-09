# Connect an existing Prometheus

Connect Tokonoma to your Prometheus-compatible service to query metrics during investigations and monitoring. To receive alerts too, configure [Alertmanager or Grafana Alerting](alert-investigations.md).

## Before you start

This connection requires **`telemetryPlatform: true`** and telemetry tools enabled (`mcp.disableTelemetryTools: false`). Do not enable the platform just to connect Prometheus: it also adds storage components and operating costs. If it is off, connect through your existing [Grafana](alert-investigations.md#install-with-oss-grafana-mcp) or a [compatible telemetry MCP server](integrations.md#mcp-connections).

Confirm your installed chart and application support these settings. Preserve your existing configuration when [applying changes](upgrading.md#before-changing-configuration).

## Choose the endpoint and monitored cluster

Ask your Prometheus owner for its **query base URL**, including any provider path prefix but not `/api/v1/query`. For an in-cluster service, confirm its service name, namespace, and port. Keep credentials out of the URL.

Also [choose the cluster and namespaces to monitor](agentic-monitoring.md#choose-the-monitored-cluster). The URL alone does not select them.

Merge this fragment into the existing values, preserving all other `mcp` and `telemetry` settings:

```yaml
# Requires an already configured telemetryPlatform: true installation.
mcp:
  telemetry:
    prometheusUrl: "REPLACE_WITH_PROMETHEUS_QUERY_BASE_URL"
    prometheusAuth:
      mode: none
```

Use `none` only for an endpoint that permits unauthenticated queries. Otherwise choose an authentication mode below. You do not need to enable bundled Prometheus; this URL takes precedence over it.

## Prepare authentication

Use read-only credentials for the intended tenant or workspace. [Create or reuse Secrets](credentials.md#supply-credentials-in-commands) in the release namespace; keep their contents out of chat and values files. Fill credential placeholders and run credential commands locally.

Keep `prometheusUrl` set and merge one of the following authentication options into the same `mcp.telemetry` block.

### Bearer token

Store the raw token without the `Bearer ` prefix:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma create secret generic REPLACE_WITH_PROMETHEUS_SECRET_NAME \
  --from-literal=token='REPLACE_WITH_PROMETHEUS_TOKEN'
```

```yaml
mcp:
  telemetry:
    prometheusAuth:
      mode: bearer
      secretRef:
        name: REPLACE_WITH_PROMETHEUS_SECRET_NAME
        tokenKey: token
```

### Basic authentication

Create or reuse a Secret containing the username and password (for some providers, the password is an API token):

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma create secret generic REPLACE_WITH_PROMETHEUS_SECRET_NAME \
  --from-literal=username='REPLACE_WITH_PROMETHEUS_USERNAME' \
  --from-literal=password='REPLACE_WITH_PROMETHEUS_PASSWORD'
```

```yaml
mcp:
  telemetry:
    prometheusAuth:
      mode: basic
      secretRef:
        name: REPLACE_WITH_PROMETHEUS_SECRET_NAME
        usernameKey: username
        passwordKey: password
```

### Amazon Managed Prometheus (SigV4)

Use the workspace query base URL and its region:

```yaml
mcp:
  telemetry:
    prometheusUrl: "https://aps-workspaces.REPLACE_WITH_AWS_REGION.amazonaws.com/workspaces/REPLACE_WITH_WORKSPACE_ID"
    prometheusAuth:
      mode: sigv4
      sigv4Region: REPLACE_WITH_AWS_REGION
```

Have your platform owner configure IRSA or EKS Pod Identity for both Tokonoma MCP instances. Their role needs `aps:QueryMetrics`, `aps:GetLabels`, `aps:GetSeries`, and `aps:GetMetricMetadata` on the intended workspace. SigV4 uses that identity, not a token Secret. If `sigv4Region` is omitted, the chart uses top-level `region`.

### Tenant headers

For a backend such as Mimir, set the tenant header required by its owner:

```yaml
mcp:
  telemetry:
    prometheusHeaders:
      X-Scope-OrgID: "REPLACE_WITH_TENANT_ID"
```

Quote header values. Headers are stored as plain text: use `prometheusAuth` for credentials, not a header.

## Allow network access

Allow DNS and outbound access to the Prometheus host and port from both Tokonoma MCP instances, including the one used by the runner. Check backend firewall rules and private routing too; access from your laptop alone is not enough.

Use HTTPS for external endpoints and credentials, with a certificate trusted by Tokonoma. Any proxy must permit Prometheus query, series, label, and metadata requests. Review [data flows](data-flows.md) before granting access: query results can reach your agent and the runner's model.

## Apply and verify

1. [Apply the saved configuration](upgrading.md#before-changing-configuration), preserving existing settings.
2. [Connect your coding agent](coding-agents.md) and confirm that it lists `list_metrics` and `query_metrics`.
3. Ask the agent to call `list_metrics` with `{"match":"^up$"}`, then `query_metrics` with `{"query":"up","stats":["last","last_seen"],"top_k":5}`. Check the returned labels and recent sample times. These queries cover the last hour by default. If your source does not collect `up`, use a known gauge instead.
4. Repeat with the source's actual cluster and namespace labels to confirm access to the systems you chose. An empty result is not proof of health; `up=0` means a scrape target is down.
5. Complete the [monitoring checks](agentic-monitoring.md#verify-monitoring) to confirm the runner can query your telemetry and its checks are running.

If tools are missing, check the prerequisites and URL. For 401/403 errors, check credentials, tenant headers, and permissions. For timeouts or certificate errors, check routing and certificate trust from both MCP instances. Follow [credential renewal](credentials.md#renew-and-rotate) when rotating a Secret.
