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

Confirm the task, the authorized kubeconfig context, the release name, and the namespace. Check for an existing release using the [prerequisite checks](references/install.md#1-check-prerequisites). A permission error does not mean the namespace is empty.

- No release: follow the new-installation path. Use the published chart and its image defaults.
- Existing release: use its installed chart version and keep its image overrides, as described in [upgrading](references/upgrading.md#before-changing-configuration).

## 2. Read the existing configuration

Read every supplied or saved values file and supporting file, including comments, in the order they are applied. Note the configured integrations, monitoring scope, access routes, and Secret references. Settings in the public example are not evidence of the customer's choices.

The runner and memory analysis are required. The public example also enables agentic monitoring and automatic investigations. Together they need:

- an Anthropic API key
- at least one alert source: Alertmanager or Datadog
- telemetry query access: a `kind: telemetry` entry in `runner.mcpServers`, or `grafanaMcp.enabled: true`
- the monitored cluster name and exact namespace names. An empty namespace list watches every namespace, including system namespaces.

Slack, shared team access, an external database, and cloud telemetry storage are optional. Summarize what is already configured, list the remaining options from the [integration guide](references/integrations.md), and ask whether the customer wants any of them. Enable an option only when the customer selects it.

## 3. Ask for what is missing

Ask about missing required inputs, conflicts, and selected additions together, in one question where practical. For actions only a person can do, such as getting a license, signing in, or approving an app, say what to do and how to check it is done. Resolve missing inputs and conflicting targets before running anything that changes the cluster.

If the customer has no telemetry connection yet, continue with the installation and note it for the report in step 7.

## 4. Build the values file

Follow the [merge rules](references/install.md#merge-supplied-configuration). Read the example's comments before adapting any of it. Save confirmed choices in the customer's values files, in their working directory outside this checkout. Keep the commented source files: `helm get values` does not keep comments. Never replace existing configuration, credentials, storage, or values-file order with the example.

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

The installation is complete when Helm reports `deployed`, the required workloads are ready, persistent-volume claims are `Bound`, and the MCP `/health` check returns `ok`. Monitoring setup continues in the background. Do not wait for setup, evaluation results, or a completed investigation.

If something fails, keep the error and follow [troubleshooting](references/troubleshooting.md). Do not weaken authentication, uninstall, or delete data to get past it.

Memory read and write tests, Slack replies, controlled test alerts, and monitoring checks are optional follow-ups. Run them only when the customer asks. Do not create a production anomaly to test monitoring.

## 7. Report

Use this template. Leave out credential values.

```text
Target:            <context> / <release> / <namespace>
Versions:          chart <version>, application image <tag>
Enabled features:  <list>
Values files:      <paths, in the order applied>
Credentials:       <file paths or Secret name and key, no values>
Deployment health: <each check run and its result>
Telemetry access:  <configured connections, or "none configured">; end-to-end access not yet validated
Follow-up checks:  <each optional check run and its result, or "none run">
Remaining actions: <human or service actions, with links to the relevant guides>
```

The telemetry line is information, not a failure. Change "not yet validated" only when a follow-up check showed telemetry data being queried, such as `@Tokonoma setup` reporting no missing access or a controlled investigation that used telemetry. Do not describe any untested feature as verified.
