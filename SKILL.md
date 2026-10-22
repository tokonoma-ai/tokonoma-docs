---
name: tokonoma-docs
description: Install, configure, connect, upgrade, troubleshoot, or remove a customer's Tokonoma deployment using the released Helm chart and these shared customer guides. Use when a customer asks for help operating Tokonoma in their Kubernetes cluster.
---

# Operate a Tokonoma installation

Follow the same [customer guides](README.md#read-the-documentation) that people use. Resolve every documentation path from this skill's directory.

## Rules for every step

- Use the guides' own `helm` and `kubectl` commands. Do not wrap them in scripts or use shell exports.
- Replace every `REPLACE_WITH_...` marker with a verified value. Never invent identifiers or credentials.
- Ask for credential file paths or Secret names and keys. Never ask for, print, or log secret contents. Leave provider template variables, such as Datadog's `$ID`, intact.
- Memory analysis and the runner use the Anthropic API only, and one Anthropic API key serves both. The chart's defaults mention Bedrock, Vertex, and Foundry through `runner.extraEnv`. These are not supported, so do not offer or configure them.
- The customer's request authorizes the installation or change it describes. Ask first before anything outside it: destructive changes, wider network access, or sending data to a new destination. Check [data flows](references/data-flows.md) before changing access or data destinations.
- Restarting a workload that uses a mutable image tag such as `latest` can pull newer application code. Get the customer's approval before changing the chart version or an image tag.

## 1. Identify the target

Identify the task, authorized kubeconfig context, release name, and namespace from supplied files and inspected configuration. Check for an existing release using the [prerequisite checks](references/install.md#1-check-prerequisites) when the target is known. Carry unresolved target choices into the single question batch below. A permission error does not mean the namespace is empty.

- No release: follow the new-installation path. Use the published chart and its image defaults.
- Existing release: use its installed chart version and keep its image overrides, as described in [upgrading](references/upgrading.md#before-changing-configuration).

## 2. Read the existing configuration

Read every supplied or saved values file and supporting file, including comments, in the order they are applied. Note the configured integrations, monitoring scope, access routes, and Secret references. Settings in the public example are not evidence of the customer's choices.

The runner and memory analysis are required. Use the [README checklist](README.md#2-before-you-start) as the single intake source. Start a new installation with phase 1: bundled PostgreSQL, Agentic Monitoring, automatic investigations, Slack, and internal runner authentication, even when chart defaults are off. Keep MCP private. Defer shared hostname, routing, and human sign-in to phase 2 unless requested. Preserve existing authentication and access routes; never disable them to impose phase 1 defaults. Include automatic-feature opt-outs in the batch below and preserve supplied choices unless the customer requests a change. Follow the [feature choices](references/install.md#choose-automatic-features) for those opt-outs. Enable optional additions only when selected.

## 3. Ask for what is missing

Before asking, complete the [README checklist](README.md#2-before-you-start) for the requested phase from supplied files and inspected configuration. Read the relevant guides for the configured and proposed connections so their conditional inputs are included. Reuse known answers; do not treat example values as customer choices. Phase 2 inputs do not block phase 1 unless the customer requests both together.

Ask for all currently missing inputs, conflicts, optional selections, automatic-feature opt-outs, and approval for a source-side test alert in one batch before changing the cluster. Include the default-feature question in that batch rather than asking it separately. For actions only a person can do, such as getting a license, signing in, or approving an app, say what to do and how to check it is done. Ask a follow-up only when a later answer or inspection reveals a new requirement or conflict; explain what changed.

Prepare the internal runner's access in phase 1. An existing Anthropic Secret must configure both `mcp.memoryLlm.apiKeySecret` and `runner.engine.apiKeySecret`; the shared `credentials.anthropicApiKey` input serves both automatically. Include the dedicated [runner machine credential](references/alert-investigations.md#prepare-runner-credentials-when-mcp-authentication-is-enabled), [credential-provider settings](references/oauth.md#1-prepare-the-provider), and `runner.tokoMcp.oauthClientSecretRef` in the initial batch. Declare the client in `mcp.auth.clients` with `origin: external`, `client_credentials`, `toko-mcp/query`, and `client_secret_post` as described in that guide. Human SAML login and external telemetry credentials do not replace this login.

For a new phase 1 installation, set `mcp.auth.enabled: true`, `mcp.auth.baseUrl: http://localhost:8000`, `mcp.ingress.enabled: false`, and `runner.ingress.enabled: false`. The localhost OAuth address matches the operator's port-forward; the runner exchanges credentials directly with the sibling's private Service. Leave `runner.tokoMcp.url` empty so the chart derives that Service. Prepare the provider and runner credentials without the shared-hostname or SAML steps. In phase 2, change the advertised OAuth address to the chosen HTTPS hostname and configure the selected route and human sign-in. Preserve existing addresses and authentication on upgrades. If the customer explicitly retains authentication disabled, omit the runner login reference too; credentials against a disabled `/token` endpoint fail.

Collect existing-alert and deployment-watching inputs in phase 1 even if there are no current alerts or deployment-event wiring needs follow-up with Tokonoma. The chart still requires at least one Alertmanager or Datadog receiver token. In-cluster senders can use the private runner Service; external senders need an approved [separate webhook route](references/private-access.md#slack-and-webhooks). Do not expose MCP just to receive alerts. Record delivery as pending until the route and sender are connected. GitHub MCP reads code and history; it does not configure deployment-event delivery. Record unsupported wiring as a follow-up rather than claiming it is ready.

If either automatic feature stays enabled, resolve missing telemetry endpoints, query tools, credentials, and access with the customer before applying changes. Alert webhooks and GitHub code access do not meet this prerequisite. Do not silently disable a feature or continue without its inputs. If the customer explicitly turns both off, record telemetry setup as a prerequisite for enabling them later.

## 4. Build the values file

Follow the [merge rules](references/install.md#merge-supplied-configuration). Read the example's comments before adapting any of it. Save confirmed choices in the customer's values files, in their working directory outside this checkout. Keep the commented source files: `helm get values` does not keep comments. Never replace existing configuration, credentials, storage, or values-file order with the example.

Supplied equivalents replace the guides' examples. Where a guide says to uncomment a setting, add or keep that configuration when it is selected. Do not enable a second webhook route or expose MCP when a separate route is already supplied.

## 5. Read only the guides you need

| Task | Read |
| --- | --- |
| New installation | [Install](references/install.md), [credentials](references/credentials.md), [integrations](references/integrations.md), [agentic monitoring](references/agentic-monitoring.md), then the selected integration guides |
| Cloud provider or database preparation | Applicable [AWS](references/cloud-providers/aws.md), [Google Cloud](references/cloud-providers/google-cloud.md), or [external PostgreSQL](references/external-postgres.md) guide |
| Monitoring, investigations, Slack, or model settings | [Agentic monitoring](references/agentic-monitoring.md) or [integrations](references/integrations.md), then the selected guide; [memory analysis](references/memory-llm.md) when needed |
| Shared access or login | [Private access](references/private-access.md), [OAuth](references/oauth.md), chosen [Google](references/google-saml.md) or [Okta](references/okta-saml.md) provider; [public routing](references/public-mcp-ingress.md) only when selected |
| Existing installation | [Configuration preservation](references/upgrading.md), then the feature, [troubleshooting](references/troubleshooting.md), or [uninstall](references/uninstall.md) guide |

Use the commented [values.yaml](examples/values.yaml) for field guidance, and [endpoints](references/endpoints.md) and [input conventions](references/install.md#inputs-and-placeholders) for lookups. Cloud hosting does not require optional telemetry storage.

## 6. Install or apply, then verify

Run the guide's commands, adapted to the configured release, namespace, integrations, routes, and Secret references. Run each port-forward in its own terminal or background shell, and run checks from another.

Complete the phase 1 checkpoint before shared team access:

1. Confirm Helm reports `deployed`, required workloads are ready, persistent-volume claims are `Bound`, and MCP `/health` returns `ok`.
2. Follow [monitoring verification](references/agentic-monitoring.md#verify-monitoring). Confirm setup completed for the intended scope, checks are active, and evaluation counters advance. Report inactive or degraded checks as coverage gaps.
3. Connect each selected alert sender and follow [investigation verification](references/alert-investigations.md#check-it-works) using a real alert or approved source-side test. Require accepted delivery, a completed automatic investigation, a saved result, and configured Slack delivery.

Apply feature checks only to enabled features and report explicit customer opt-outs. Pending setup, an unconnected sender, or an unverified investigation leaves phase 1 incomplete. Report the blocker and resume when resolved. Configure phase 2 access only after this checkpoint, if requested.

If something fails, keep the error and follow [troubleshooting](references/troubleshooting.md). Do not weaken authentication, uninstall, or delete data to get past it.

Standalone memory read/write tests and onboarding remain optional. Use only approved alert tests and preserve existing paging routes. Do not create a production anomaly to test monitoring.

## 7. Report

Use this template. Leave out credential values.

```text
Target:            <context> / <release> / <namespace>
Versions:          chart <version>, application image <tag>
Enabled features:  <list>
Disabled features: <customer-selected opt-outs, or "none">
Values files:      <paths, in the order applied>
Credentials:       <file paths or Secret name and key, no values>
Deployment health: <each check run and its result>
Telemetry access:  <configured connections and query evidence, or customer opt-out>
Monitoring:        <setup status, scope, active checks, evaluation evidence, coverage gaps, or customer opt-out>
Alert checks:      <each sender, accepted delivery, completed investigation, saved result, and Slack delivery, or customer opt-out>
Phase 1:           <complete, or incomplete with blockers>
Optional checks:   <each optional check run and its result, or "none run">
Remaining actions: <human or service actions, with links to the relevant guides>
```

Missing telemetry configuration blocks installation with either automatic feature enabled. Report evidence from the monitoring and alert checks separately from deployment health. Do not describe any untested feature as verified.
