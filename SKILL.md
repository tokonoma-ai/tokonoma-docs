---
name: tokonoma-docs
description: Install, configure, connect, upgrade, troubleshoot, or remove a customer's Tokonoma deployment using the released Helm chart and these shared customer guides. Use when a customer asks for help operating Tokonoma in their Kubernetes cluster.
---

# Operate a Tokonoma installation

Follow the shared customer guides in `references/`. Resolve every documentation path from this skill's directory.

Check the [native-auth release prerequisite](references/upgrading.md#native-machine-authentication-release-prerequisite) before applying this revision. Do not use these settings with earlier application or chart releases.

## Rules for every step

- Use the guides' own `helm` and `kubectl` commands. Do not wrap them in scripts or use shell exports.
- Replace every `REPLACE_WITH_...` marker with a verified value. Never invent identifiers or credentials.
- Prepare credential commands with placeholders for the customer to fill and run locally. Reuse existing Secret references or supplied credential files when available. Never ask for secret contents or filled commands in chat, and never print or log secrets. Leave provider template variables, such as Datadog's `$ID`, intact.
- The MCP server's model features and the runner use the Anthropic API or [Amazon Bedrock](references/amazon-bedrock.md), set by `llm.provider`, and one key serves both. The chart's defaults mention Vertex and Foundry through `runner.extraEnv`. These are not supported, so do not offer or configure them.
- The customer's request authorizes the installation or change it describes. Ask first before anything outside it: destructive changes, wider network access, or sending data to a new destination. Check [data flows](references/data-flows.md) before changing access or data destinations.
- Restarting a workload that uses a mutable image tag such as `latest` can pull newer application code. Get the customer's approval before changing the chart version or an image tag.

## 1. Identify the target

Identify the task, authorized kubeconfig context, release name, and namespace from supplied files and inspected configuration. Check for an existing release using the [prerequisite checks](references/install.md#1-check-prerequisites) when the target is known. Carry unresolved target choices into the single question batch below. A permission error does not mean the namespace is empty.

- No release: follow the new-installation path. Use the published chart and its image defaults.
- Existing release: review its saved configuration and image overrides using [upgrading](references/upgrading.md#before-changing-configuration). The unpinned commands can upgrade the chart; confirm that effect is within the requested change before applying them.

## 2. Read the existing configuration

Read every supplied or saved values file and supporting file, including comments, in the order they are applied. Note the configured integrations, monitoring scope, access routes, and Secret references. Settings in the public example are not evidence of the customer's choices.

The runner and the server model features are required. Follow the [installation approach](README.md#what-to-expect) and the guides below. Ask up front whether the customer wants the telemetry platform and whether they want MCP query access for coding agents. These are independent choices. The quickest setup uses existing telemetry and required Slack, with MCP private. Complete every selected option in the same installation; options can also be added later. Do not impose phases. Use bundled PostgreSQL and enable both automatic features for new installations, even when chart defaults are off. Preserve supplied or existing authentication and access routes. Include automatic-feature opt-outs in the batch below and preserve supplied choices unless the customer requests a change. Follow the [feature choices](references/install.md#choose-automatic-features) for those opt-outs. Enable optional additions only when selected.

## 3. Ask for what is missing

Read the prerequisites and guides for selected connections before asking. Collect known answers from supplied files, then ask one batch covering:

- Target cluster, release, namespace, and monitoring scope.
- Required license, model credentials, Slack tokens, channels, and app membership.
- Whether to enable the telemetry platform and whether to expose MCP for coding-agent queries. Collect storage and identity inputs for the platform, and hostname, routing, TLS, and human login inputs for shared MCP access.
- Existing telemetry providers, selected alert senders, optional code access, and automatic-feature opt-outs.
- Approval for a source-side test alert when an alert sender is selected.

Ask a follow-up only when later information reveals a requirement or conflict, and explain it. Bring the relevant commands into the conversation. Explain account approval and other administrator actions, including how the customer can check completion.

For a new private installation, keep the example's authenticated MCP, `provider: none`, localhost auth URL, and disabled ingress. Leave `runner.tokoMcp.url` and its credential reference unset so Helm creates the local machine login. GitOps/offline rendering and existing or external credentials use the [runner authentication guide](references/alert-investigations.md#prepare-runner-credentials-when-mcp-authentication-is-enabled). Do not request an external identity provider or copy credentials solely for the runner. Configure human authentication and the HTTPS auth URL when shared access is selected. Preserve existing credentials and routes on upgrades; local authentication changes must not alter credentials for an external MCP.

Use one [model credential](references/credentials.md) for the runner and server features. Follow the [Bedrock guide](references/amazon-bedrock.md) when selected, including explicit clearing of saved Anthropic settings during migration.

Receiver tokens are required only for selected alert senders. In-cluster senders can use the private runner Service; external senders need an approved webhook route. Do not expose MCP just to receive alerts. Record absent senders as **none configured**, and selected senders as pending until delivery is verified. GitHub access reads code and history; it does not configure deployment-event delivery. Record unsupported wiring as follow-up work.

For existing telemetry providers, resolve query endpoints, read-only tools, credentials, and access before deployment. For a new telemetry platform, prepare its backend and storage now; application collection follows completed Tokonoma setup. Keep data-dependent checks pending until data arrives. Alert webhooks and code access do not supply telemetry queries. Do not silently disable features to get past missing inputs.

## 4. Build the values file

Follow the [merge rules](references/install.md#merge-supplied-configuration). Read the example's comments before adapting any of it. Save confirmed choices in the customer's values files, in their working directory outside this checkout. Keep the commented source files: `helm get values` does not keep comments. Never replace existing configuration, credentials, storage, or values-file order with the example.

Supplied equivalents replace the guides' examples. Where a guide says to uncomment a setting, add or keep that configuration when it is selected. Do not enable a second webhook route or expose MCP when a separate route is already supplied.

## 5. Read only the guides you need

| Task | Read |
| --- | --- |
| New installation | [Install](references/install.md), [credentials](references/credentials.md), [integrations](references/integrations.md), [agentic monitoring](references/agentic-monitoring.md), then the selected integration guides |
| Cloud provider or database preparation | Applicable [AWS](references/cloud-providers/aws.md), [Google Cloud](references/cloud-providers/google-cloud.md), or [external PostgreSQL](references/external-postgres.md) guide |
| Monitoring, investigations, Slack, or model settings | [Agentic monitoring](references/agentic-monitoring.md) or [integrations](references/integrations.md), then the selected guide; [server model features](references/server-features.md) when needed |
| Shared access or login | [Shared access checklist](references/team-access.md), then its selected provider and route guides |
| Existing installation | [Configuration preservation](references/upgrading.md), then the feature, [troubleshooting](references/troubleshooting.md), or [uninstall](references/uninstall.md) guide |

Use the commented [values.yaml](examples/values.yaml) for field guidance, and [endpoints](references/endpoints.md) and [input conventions](references/install.md#inputs-and-placeholders) for lookups. Cloud hosting does not require optional telemetry storage.

## 6. Install or apply, then verify

Run the guide's commands, adapted to the configured release, namespace, integrations, routes, and Secret references. Have the customer run credential commands whose input or output contains secrets; continue verification without asking to see them. Run each port-forward in its own terminal or background shell, and run checks from another.

Verify the selected installation. If a new platform has no application data yet, defer data-dependent monitoring and investigation checks below, mark them pending, and complete backend, Slack, authentication, and selected access checks first:

1. Confirm Helm reports `deployed`, required workloads are ready, persistent-volume claims are `Bound`, and MCP `/health` returns `ok`.
2. Follow [monitoring verification](references/agentic-monitoring.md#verify-monitoring). Confirm setup completed for the intended scope, checks are active, and evaluation counters advance. Report inactive or degraded checks as coverage gaps.
3. Connect each selected alert sender and follow [investigation verification](references/alert-investigations.md#check-it-works) using a real alert or approved source-side test. Require accepted delivery, a completed automatic investigation, a saved result, and configured Slack delivery.

Apply checks to enabled features and record explicit opt-outs. Complete selected shared MCP access using the authentication and routing checklist, including both human and runner login. Distinguish absent alert senders from pending or verified delivery. For a new platform awaiting customer data, verify backend health, storage, indexes, Slack, and selected access first. Then provide the [collector example](references/customer-telemetry.md) with verified endpoints, index names, and network requirements. Do not deploy it without approval. The bundled collector only gathers Tokonoma telemetry. Record customer collection and data-dependent checks as pending and resume them after ingestion; do not claim they passed or withhold the example until they do.

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
Credentials:       <Secret names and keys, or supplied file paths; no values>
Deployment health: <each check run and its result>
Telemetry access:  <configured connections and query evidence, or customer opt-out>
Monitoring:        <setup status, scope, active checks, evaluation evidence, coverage gaps, or customer opt-out>
Alert checks:      <each sender, accepted delivery, completed investigation, saved result, and Slack delivery, or customer opt-out>
Installation:      <complete, or incomplete with blockers>
Optional checks:   <each optional check run and its result, or "none run">
Remaining actions: <human or service actions, with links to the relevant guides>
```

Report deployment health, selected MCP access, and telemetry-platform health separately from customer collection, monitoring coverage, and alert checks. Do not describe any untested feature as verified.
