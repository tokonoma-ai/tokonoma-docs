# Endpoints

All services are ClusterIP unless you enable Ingress for the MCP. Only enabled components create their corresponding services.

Run `kubectl` commands below from an operator workstation with access to the intended cluster. Replace inputs before use; agents must ask for unresolved choices.

| Input | Source and when required |
|---|---|
| `REPLACE_WITH_KUBE_CONTEXT` | Intended cluster context from `kubectl config get-contexts`; required for cluster commands. |
| `REPLACE_WITH_CUSTOMER` | The `customer` slug in your saved values; required only for telemetry ingest headers. |
| `REPLACE_WITH_SOURCE_TOKEN` | The receiver token from your secret-management workflow; required only for alert webhook requests. |

| Service | Port | Use |
|---|---|---|
| `toko-mcp` | 8000 | MCP API at `/mcp`; readiness at `/health`. Also `/skills` (skill catalog), `/usage-stats` (licence usage), `/display/<file>` (rendered output links) and, when attachments are stored on the local volume or GCS, `/attachments/<id>`. With OAuth on: `/.well-known/oauth-authorization-server`, `/.well-known/oauth-protected-resource/mcp`, `/authorize`, `/token`, `/register`, `/revoke`; with SAML, `/saml/metadata` and `/oauth/saml/*`. Liveness (`/livez`) and Prometheus metrics (`/metrics`: `toko_mcp_*` tool, backend and usage series) are served separately on container port 8001, which the Service does not expose, so neither is reachable through the Ingress. The pods carry `prometheus.io/*` scrape annotations for it (`mcp.podAnnotations`). |
| `toko-mcp-unattended` | 8000 | The unattended instance toko-runner drives (when `mcp.sibling.enabled=true`). Same API; no Ingress, no Slack. |
| `toko-postgres` | 5432 | Memory store (internal) |
| `toko-ollama` | 11434 | Embeddings (internal) |
| `toko-searcher` | 7280 | Telemetry search API (when `telemetryPlatform=true`) |
| `toko-indexer` | 7281 | OTLP ingest (when `telemetryPlatform=true`) |
| `toko-prometheus-server` | 80 | Prometheus HTTP API; the default target of the MCP's `list_metrics` / `query_metrics` tools (when `prometheus.enabled=true`) |
| `toko-grafana` | 80 | Dashboards (when `grafana.enabled=true`) |
| `toko-grafana-mcp-server` | 8000 | Private OSS Grafana MCP subchart API at `/mcp` (when `grafanaMcp.enabled=true`). The runner connects automatically with the shared internal bearer token. No Ingress; independent of the Grafana UI. Health probes use `/healthz` on adapter container port 8081. |
| `toko-runner` | 8080 | Built-in POST alert webhooks at `/webhooks/alertmanager` and `/webhooks/datadog`, each registered only with its source token; health at `/health`, metrics at `/metrics` (when `runner.enabled=true`). With `runner.ingress.enabled=true`, the MCP Ingress routes the absolute paths explicitly selected in `runner.ingress.webhookPaths` with `Exact` matching. The deployed runner must serve each selected path. The default `[]` routes none. |

## MCP client

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma port-forward svc/toko-mcp 8000:8000
```

Leave the port-forward running. Once it reports `Forwarding from`, point your MCP client at `http://127.0.0.1:8000/mcp`. Follow the
[coding agent guide](../guides/coding-agents.md) for Claude Code, Cursor, and
Codex setup.

The MCP endpoint has no application-level authentication by default. Keep it private for initial setup. Configure [OAuth](../guides/oauth.md) before allowing shared or [public access](../guides/public-mcp-ingress.md). ClusterIP by itself does not restrict which other cluster workloads can connect.

## Alert webhook access

An in-cluster sender uses
`http://toko-runner.tokonoma.svc:8080/webhooks/alertmanager`. An external sender
uses the approved HTTPS MCP Ingress host plus its explicitly selected webhook
path. Both receivers require `Authorization: Bearer REPLACE_WITH_SOURCE_TOKEN`; selecting
an Ingress rule does not create a credential or bypass ingress-level auth.
Grafana Cloud cannot be assumed to reach a private service or Tailscale-only
hostname. See [Alertmanager/Grafana setup](../guides/alert-investigations.md#external-alertmanager-or-grafana-alerting)
or [Datadog setup](../guides/datadog-alerts.md).

## OTLP ingest

Ship logs/traces to `toko-indexer:7281` from inside the cluster with headers:

- `qw-otel-logs-index: REPLACE_WITH_CUSTOMER-logs`
- `qw-otel-traces-index: REPLACE_WITH_CUSTOMER-traces`

## Grafana

### OSS Grafana MCP

`grafanaMcp.enabled: true` adds the upstream OSS Grafana MCP subchart inside this release
for the investigation runner. It queries the Grafana URL in
`grafanaMcp.grafana.url` using the supplied Viewer service-account token. The
runner uses a separate internal bearer token against
`http://toko-grafana-mcp-server.tokonoma.svc:8000/mcp` in namespace `tokonoma`;
the URL follows the subchart's native fullname, Service port and release
namespace. The Grafana Viewer token is held by the
adapter only. Its data tools cover the configured data sources, Prometheus,
Loki, Tempo, Pyroscope and assertions, with writes disabled.

The service stays private and has no Kubernetes API permissions. Its native
`grafanaMcp.fullnameOverride` names the Deployment and Service. If changing it,
update the caller-token reference and allowed hosts together. For the
complete one-install configuration, see
[Alert-triggered investigations](../guides/alert-investigations.md#install-with-oss-grafana-mcp).

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
| `searchers`, `indexers`, `metastore`, `otel-collector` | The telemetry platform's Quickwit and collector internals. |
