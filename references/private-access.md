# Private access

The default `toko-mcp` Service is `ClusterIP`; the chart creates no public Ingress unless you enable one. ClusterIP limits how Kubernetes routes the Service, but it does not authenticate callers or isolate pods from one another.

## Inputs and command location

| Input | Where to get it | When needed |
| --- | --- | --- |
| Cluster context and installed release | Your [installation](install.md) record | Local port-forward access |
| Approved private route and intended users | Your platform and identity administrators | Before shared access |
| Stable HTTPS hostname, DNS and certificate | Your platform team | Before shared team access |
| Login provider and its settings | [OAuth](oauth.md), [Google SAML](google-saml.md), or [Okta SAML](okta-saml.md) | Before opening the team route |
| Client or webhook sender location | The team operating that client or sender | Before choosing private or public reachability |

Run cluster commands from your working directory on a workstation with cluster access. Test connections from a user's device or the actual sender. Follow [input conventions](install.md#inputs-and-placeholders).

## Local access

Use the [installation port-forward and health check](install.md#4-verify). It binds to localhost by default and requires Kubernetes access. Keep it on localhost; do not add `--address 0.0.0.0` for shared access.

The local Setup/Monitoring UI remains readable without MCP authentication. Detector actions require authentication.

## Team access

For the full sequence from a verified installation to human and runner login, use the [shared access checklist](team-access.md).

Preserve existing authentication and routes when configuring shared access.

1. Agree on a private route with your platform team, such as an existing VPN or internal Ingress. Choose its stable HTTPS hostname without opening shared access yet.
2. Configure [OAuth](oauth.md), including the [runner and local UI credentials](alert-investigations.md#prepare-runner-credentials-when-mcp-authentication-is-enabled). Add [Google SAML](google-saml.md) or [Okta SAML](okta-saml.md) for human sign-in when selected. Set `mcp.auth.enabled: true` explicitly in `values.yaml`. Use the same hostname for the auth base URL and identity-provider redirect configuration.
3. [Apply the configuration change](upgrading.md#before-changing-configuration) with the authentication settings and private route. The hostname must be reachable by the MCP client and the user's browser.
4. From a user's device, request `https://REPLACE_WITH_MCP_HOSTNAME/mcp` without credentials and expect `401`. Complete login through a [coding agent](coding-agents.md) and confirm it can list Tokonoma tools.

Your platform team manages private connectivity, DNS, certificates, and network policy. The chart does not install Tailscale, a VPN, PrivateLink, or a NetworkPolicy. Keep user authentication enabled on shared routes.

`mcp.auth.enabled: false` is appropriate only when the reachable clients are trusted and network access is deliberately restricted. With authentication disabled, anyone who reaches the endpoint can use its exposed features.

Use the [Ingress guide](public-mcp-ingress.md) with an internal controller or load balancer; its public examples need adapting for private access. Apply access restrictions consistently to `/mcp`, login, and callback paths. Keep the web UI on a local port-forward; it rejects proxied requests.

## Slack and webhooks

The native [Tokonoma Slack app](slack-app.md) connects outbound through Socket Mode. Slack event delivery needs no public inbound URL. Links posted in Slack still need an address their readers can reach.

Alertmanager running in your cluster can call the runner's private Service. External Grafana Cloud or Datadog senders need an approved inbound HTTPS route. Select only the required webhook paths, configure their bearer tokens, and test that unauthenticated requests are denied. The runner's bearer tokens are separate from MCP OAuth.

Datadog can use a [separate webhook route](datadog-alerts.md#separate-webhook-route-private-mcp) while MCP stays private. Keep both chart ingress switches disabled and route only `/webhooks/datadog` to `toko-runner:8080`. This does not require MCP OAuth while MCP remains restricted to trusted private clients. To share an existing authenticated MCP hostname instead, use the [shared route](datadog-alerts.md#shared-authenticated-mcp-ingress).

Cloud-hosted MCP clients, including Claude in Slack, cannot use your laptop's `127.0.0.1` or a private cluster address unless that service has supported connectivity to it. Follow [Claude in Slack](claude-in-slack.md) for a reachable authenticated endpoint.
