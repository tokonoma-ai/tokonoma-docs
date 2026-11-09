# Connect an existing Prometheus

Tokonoma's native `list_metrics` and `query_metrics` tools can query an existing Prometheus-compatible HTTP API. This is query access, not a scrape configuration, remote-write destination, or alert receiver. To receive alerts as well, configure [Alertmanager or Grafana Alerting](alert-investigations.md).

## Check the deployment path first

The chart currently renders `mcp.telemetry.prometheusUrl` and its authentication settings **only when `telemetryPlatform: true`**. Setting a URL while the platform is off does not enable these tools. `mcp.disableTelemetryTools: true` also hides metric tools, even when the URL is configured.

Use this guide for an installation already using the telemetry platform. Do not turn on the platform just to connect Prometheus: it also enables telemetry storage components and requires their cloud, storage, and capacity preparation. If the platform is off, use an existing [Grafana adapter](alert-investigations.md#install-with-oss-grafana-mcp) or a [compatible telemetry MCP server](integrations.md#mcp-connections) instead, or agree on a separately planned platform installation.

Check the installed chart's values and application release for these settings and tools before applying changes. Follow [configuration preservation](upgrading.md#before-changing-configuration); do not silently upgrade the chart or application.

## Choose the endpoint and monitored cluster

Obtain the Prometheus **query base URL** from its owner. Include any provider path prefix, but not `/api/v1/query`: Tokonoma appends the API paths. For example, a service in another namespace might use `http://prometheus-server.monitoring.svc.cluster.local:9090`; confirm the actual service name and port. An Amazon Managed Prometheus URL includes `/workspaces/REPLACE_WITH_WORKSPACE_ID`. Never embed credentials in the URL.

The URL selects a backend, not a monitored cluster. Before enabling monitoring, [choose the cluster and namespaces](agentic-monitoring.md#choose-the-monitored-cluster). Use the cluster identity found in that source's telemetry, which may differ from the Kubernetes context or the cluster hosting Tokonoma. Do not assume a multi-cluster backend means all clusters will be monitored.

Merge this fragment into the existing values, preserving all other `mcp` and `telemetry` settings:

```yaml
# Requires an already configured telemetryPlatform: true installation.
mcp:
  telemetry:
    prometheusUrl: "REPLACE_WITH_PROMETHEUS_QUERY_BASE_URL"
    prometheusAuth:
      mode: none
```

Use `none` only when the endpoint intentionally permits these queries without authentication. An explicit URL takes precedence over bundled Prometheus. If the URL is empty and `prometheus.enabled: true`, the chart uses `http://toko-prometheus-server`; with both absent, the metric tools are off. You do not need to enable bundled Prometheus to query an existing one, and should preserve any bundled instance used by other features.

## Prepare authentication

Use read-only credentials limited to the intended tenant or workspace. These credentials authenticate Tokonoma **to Prometheus**; they are separate from [MCP caller authentication](oauth.md). Referenced Secrets must exist in the release namespace. Follow [credential setup](credentials.md#supply-credentials-in-commands) and [namespace preparation](credentials.md#prepare-the-namespace-for-secrets). Keep secret contents out of chat, values files, and this repository.

Choose one authentication mode and merge it under the same `mcp.telemetry` block. Every mode other than `none` requires an explicit `prometheusUrl`.

### Bearer token

Store the raw token without the `Bearer ` prefix. Have the credential owner fill and run the placeholder command locally, or reuse a Secret supplied by your secret manager:

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

If `sigv4Region` is empty, the chart uses top-level `region`; a region is required. Signing uses the MCP pod's AWS credential chain, including IRSA or EKS Pod Identity, not a bearer-token Secret. Have the platform owner grant the MCP ServiceAccount's role `aps:QueryMetrics`, `aps:GetLabels`, `aps:GetSeries`, and `aps:GetMetricMetadata` for the intended workspace. The runner queries through its dedicated MCP instance, so check the identity of that pod too. Preserve existing IAM and ServiceAccount configuration; a URL alone does not provision access.

### Tenant headers

For a backend such as Mimir, set the tenant header required by its owner:

```yaml
mcp:
  telemetry:
    prometheusHeaders:
      X-Scope-OrgID: "REPLACE_WITH_TENANT_ID"
```

Quote all values, including numeric tenant IDs. Headers are rendered as plain environment values, not Secret references. Do not put passwords, tokens, or an `Authorization` header here; use `prometheusAuth`.

## Allow the query connection

The interactive MCP pod and the runner's dedicated MCP pod open connections to Prometheus. Allow DNS resolution and outbound traffic from those pods to the chosen host and port, plus any backend-side firewall or NetworkPolicy access. A URL reachable from your laptop or the runner alone is not enough. For private services, verify cluster DNS, routing, and any cross-cluster or VPC connectivity.

Use HTTPS for external endpoints and credentials, with a certificate trusted by the MCP container. Do not bypass certificate verification or expose Prometheus or MCP publicly to fix a routing problem.

The backend or proxy must allow the Prometheus query API: POST `/api/v1/query`, `/api/v1/query_range`, and `/api/v1/series`; GET `/api/v1/labels`, `/api/v1/label/<label>/values`, and `/api/v1/metadata`. Tokonoma also tries GET `/api/v1/status/config` for the scrape interval, falling back to 60 seconds when unavailable. SigV4 also needs the configured AWS identity mechanism to work.

Queries and returned metrics are available to the calling agent and to the runner's model during investigations and monitoring. Review [data flows](data-flows.md) before granting access.

## Apply and verify

1. Apply the saved configuration using the [existing-release workflow](upgrading.md#before-changing-configuration). Do not replace other integrations or authentication. After Secret rotation, follow [credential renewal](credentials.md#renew-and-rotate); these credentials are read through pod environment variables.
2. [Connect your coding agent](coding-agents.md) and confirm that Tokonoma advertises `list_metrics` and `query_metrics`.
3. Call the following tools through that connection. The arguments are JSON, not shell commands:

   `list_metrics`:
   ```json
   {"match":"^up$"}
   ```

   `query_metrics`:
   ```json
   {"query":"up","stats":["last","last_seen"],"top_k":5}
   ```

   These default to the last hour. Inspect the returned labels and recent sample times. `up=0` means a scrape target is down; it does not mean the connection failed. Empty results do not prove success or health: confirm that the backend collects `up`, or repeat with a known gauge and a time window with data.
4. Use the discovered label names to narrow a query to the chosen cluster and namespace. Do not assume every source uses a label named `cluster` or `namespace`. Confirm that the returned series belong to the intended systems, including `common_labels` in the query result. Limit broad queries if the backend reports too many series.
5. For unattended monitoring, verify the dedicated MCP connection and complete the [monitoring checks](agentic-monitoring.md#verify-monitoring). A successful interactive query does not prove the runner's access, detector coverage, or alert delivery.

If tools are missing, check the platform gate, effective URL, application version, and telemetry-tool settings. For 401/403 responses, check the selected mode, Secret names and keys, tenant header, and provider permissions. For timeouts or TLS failures, check connectivity from the MCP pods and certificate trust. Report the failing check rather than disabling authentication or claiming monitoring is ready.
