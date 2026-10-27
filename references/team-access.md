# Shared engineer access

Use this checklist after the [installation checks](install.md#4-verify) pass and shared access is requested. It brings the existing authentication and routing steps together; keep the same saved values file and preserve existing configuration. The unpinned change procedure can upgrade the chart and application; review that effect before applying it.

## Prepare once

Collect the intended users and coding agents, approved private or public HTTPS hostname, DNS and certificate owners, identity provider, and runner machine credentials. Keep credentials out of chat and use [Secret references](credentials.md#use-existing-kubernetes-secrets).

| Step | Action | Completion evidence |
| --- | --- | --- |
| 1. Choose reachability | Prefer the team's approved [private route](private-access.md#team-access). Use [public MCP Ingress](public-mcp-ingress.md) only when selected. Prepare the hostname and TLS before opening shared access. | The intended users' devices and browsers can reach the chosen HTTPS hostname; unrelated clients remain excluded by the selected access policy. |
| 2. Configure machine authentication | Follow [OAuth provider setup](oauth.md#1-prepare-the-provider) and [runner credentials](alert-investigations.md#prepare-runner-credentials-when-mcp-authentication-is-enabled). Set `mcp.auth.enabled: true`; prepare provider settings, external client declaration, and runner Secret reference together. | The saved configuration contains the complete provider and caller settings, with Secret references rather than credential values. |
| 3. Configure human sign-in | Use the supported credential login or add [Google Workspace SAML](google-saml.md) or [Okta SAML](okta-saml.md). Match redirects and the auth base URL to the shared hostname. SAML does not replace the runner's machine login. | Identity-provider application and Tokonoma settings agree on hostname, redirects, and selected users. |
| 4. Apply the change | Follow [configuration preservation](upgrading.md#before-changing-configuration), applying authentication and the chosen route together. Keep the local UI on a localhost port-forward. | Workloads are healthy; OAuth metadata returns `200` and unauthenticated `/mcp` returns `401`, as checked in [OAuth verification](oauth.md#3-deploy-and-verify). |
| 5. Verify both callers | Connect a [coding agent](coding-agents.md#use-a-public-endpoint) to the shared HTTPS `/mcp` endpoint and complete real login. Repeat [monitoring verification](agentic-monitoring.md#verify-monitoring) and an approved [investigation test](alert-investigations.md#check-it-works). | The human client lists tools and can access an authorized record; detectors still evaluate and the runner completes an investigation, saves its result, and delivers to Slack when configured. |

The coding-agent guide's HTTPS login steps also apply to private HTTPS routes reachable by the client and browser. A successful human login alone does not verify runner authentication. Keep the route restricted and report the blocker if either caller fails; do not disable authentication to complete the checklist.

Record the final hostname, provider, Secret names, versions, and verification results in the installation report, without secret values. Alert webhooks use separate receiver tokens and may use a [separate route](private-access.md#slack-and-webhooks); do not expose MCP just to receive alerts.
