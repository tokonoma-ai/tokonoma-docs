# Endpoints

Services use ClusterIP by default. You can enable Ingress for the MCP. Each service exists only when its component is enabled.

Run `kubectl` on a workstation with cluster access. Follow [input conventions](install.md#inputs-and-placeholders).

| Input | Source and when required |
|---|---|
| `REPLACE_WITH_KUBE_CONTEXT` | Intended cluster context from `kubectl config get-contexts`; required for cluster commands. |
| `REPLACE_WITH_CUSTOMER` | The `customer` slug in `values.yaml`; required only for telemetry ingest headers. |
| `REPLACE_WITH_SOURCE_TOKEN` | The receiver token from your secret-management workflow; required only for alert webhook requests. |

| Service | Port | Use |
|---|---|---|
| `toko-mcp` | 8000 | MCP API at `/mcp`; process health at `/health`. Also `/skills` (skill catalog), `/usage-stats` (licence usage), `/display/<file>` (rendered output links). With OAuth on: `/.well-known/oauth-authorization-server`, `/.well-known/oauth-protected-resource/mcp`, `/authorize`, `/token`, `/register`, `/revoke`; with SAML, `/saml/metadata` and `/oauth/saml/*`. Liveness `/livez` and Prometheus `/metrics` (`toko_mcp_*`) use container port 8001, outside this Service and Ingress. Pods carry scrape annotations in `mcp.podAnnotations`. |
| `toko-mcp-unattended` | 8000 | Dedicated MCP instance required by the runner (`mcp.sibling.enabled=true`). Same API; no Ingress or Slack. |
| `toko-postgres` | 5432 | Memory store (internal) |
| `toko-ollama` | 11434 | Embeddings (internal) |
| `toko-searcher` | 7280 | Telemetry search API (when `telemetryPlatform=true`) |
| `toko-indexer` | 7281 | OTLP ingest (when `telemetryPlatform=true`) |
| `toko-prometheus-server` | 80 | Prometheus HTTP API; the default target of the MCP's `list_metrics` / `query_metrics` tools (when `prometheus.enabled=true`) |
| `toko-grafana` | 80 | Dashboards (when `grafana.enabled=true`) |
| `toko-grafana-mcp-server` | 8000 | Private OSS Grafana MCP subchart API at `/mcp` (when `grafanaMcp.enabled=true`). The runner connects automatically with the shared internal bearer token. No Ingress; independent of the Grafana UI. Health probes use `/healthz` on adapter container port 8081. |
| `toko-runner` | 8080 | Built-in POST alert webhooks at `/webhooks/alertmanager` and `/webhooks/datadog`, each registered only with its source token; health at `/health`, metrics at `/metrics` (when `runner.enabled=true`). With `runner.ingress.enabled=true`, the MCP Ingress routes the absolute paths explicitly selected in `runner.ingress.webhookPaths` with `Exact` matching. Select only supported paths; the default `[]` routes none. |

## MCP client

The local MCP URL is `http://127.0.0.1:8000/mcp`. Open it with the [installation port-forward and health check](install.md#4-verify), then follow the [coding agent guide](coding-agents.md) for Claude Code, Cursor, or Codex.

The installation example enables MCP authentication with a generated internal machine login. Raw chart defaults do not enable authentication, and ClusterIP by itself does not restrict which other cluster workloads can connect. Keep MCP private for initial setup. Configure [human login](oauth.md) before engineers connect coding agents or use shared or [public access](public-mcp-ingress.md).

The same direct local connection serves the customer UI at `http://localhost:8000/ui/`. Open **Agentic Monitoring** for coverage and significant findings; see [monitoring checks](agentic-monitoring.md#verify-monitoring). Keep the UI local as described in [data flows](data-flows.md#private-access).

## Alert webhook access

An in-cluster sender uses
`http://toko-runner.tokonoma.svc:8080/webhooks/alertmanager`. An external sender
uses a dedicated HTTPS webhook route or an authenticated MCP Ingress with the selected webhook
path. Both receivers require `Authorization: Bearer REPLACE_WITH_SOURCE_TOKEN`; selecting
an Ingress rule does not create a credential or bypass ingress-level auth.
Verify that Grafana Cloud can reach the endpoint; a private service or Tailscale-only
hostname may be inaccessible. See [Alertmanager/Grafana setup](alert-investigations.md#external-alertmanager-or-grafana-alerting)
or [Datadog setup](datadog-alerts.md).

## OTLP ingest

Send OpenTelemetry Protocol (OTLP) logs and traces to `toko-indexer:7281` from inside the cluster with headers:

- `qw-otel-logs-index: REPLACE_WITH_CUSTOMER-logs`
- `qw-otel-traces-index: REPLACE_WITH_CUSTOMER-traces`

## Grafana

### OSS Grafana MCP

`grafanaMcp.enabled: true` adds the Grafana adapter for runner queries. It reads `grafanaMcp.grafana.url` using the Viewer token. The runner uses a separate credential at `http://toko-grafana-mcp-server.tokonoma.svc:8000/mcp`; adjust the address if you change the service name or namespace. The adapter alone holds the Viewer token. It queries configured data sources, Prometheus, Loki, Tempo, Pyroscope, and assertions with writes disabled.

The adapter is private and has no Kubernetes API permissions. If you change `grafanaMcp.fullnameOverride`, update its caller-token reference and allowed hosts too. See [Grafana setup](alert-investigations.md#install-with-oss-grafana-mcp).

### Self-monitoring Grafana UI

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma port-forward svc/toko-grafana 3000:80
```

Leave the port-forward running and expect `Forwarding from`. Open <http://127.0.0.1:3000> with user `admin`. Retrieve its password privately:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma get secret toko-grafana \
  -o jsonpath='{.data.admin-password}' | base64 -d
```

If port 3000 is in use, change the left side of the mapping and the URL.

The **Platform** folder holds the bundled dashboards, provisioned read-only:

| Dashboard | Shows |
|---|---|
| `toko-mcp` | The MCP server: tool calls by tool (rate, outcome, latency, response tokens), the backends it calls (Quickwit, Prometheus, Postgres, Ollama), clients, skill loads and memory saves. An Instance selector covers `toko-mcp` and the unattended `toko-mcp-unattended`. |
| `toko-runner` | Alert-triggered investigations: the intake funnel, run outcomes, duration, turns and tokens (when `runner.enabled=true`). |
| `searchers`, `indexers`, `metastore`, `otel-collector` | Telemetry search, ingestion, storage, and collection health. |
