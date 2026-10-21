---
name: tokonoma-docs
description: Install, configure, connect, upgrade, troubleshoot, or remove a customer's Tokonoma deployment using the released Helm chart and these shared customer guides. Use when a customer asks for help operating Tokonoma in their Kubernetes cluster.
---

# Operate a Tokonoma installation

Follow the same [customer guides](README.md#read-the-documentation) humans use. New installations use the published chart and its image defaults. For configuration changes, use the installed chart version and preserve existing image overrides as described in [upgrading](references/upgrading.md#before-changing-configuration). Explain that restarting a mutable image tag such as `latest` can fetch newer application code; agree any version change before proceeding.

## Establish the requested task

Identify the requested task, authorized cluster context, release, namespace, features, and access model. Check the existing installation before making changes.

The Tokonoma runner and memory analysis are required. Configure an Anthropic credential for analysis even if the runner uses another provider. The supplied `values.yaml` enables the required services. Before installing, prepare analysis credentials, at least one alert source, and the selected investigation tools. Configure selected integrations in the same file.

Read the customer's saved values files, including comments, in application order and check the installed release first. Inspect nonsecret integration settings and Secret references; do not print secret values. Do not infer the customer's tools from the defaults in the supplied examples. Ask only about missing settings, conflicts, or requested additions. Confirm which integrations to enable and save those choices in the customer's values files.

Group missing inputs and decisions into one question where practical. Explain human-only actions, such as obtaining a license, signing in, or approving an app, and how to check completion.

## Read only the relevant guides

| Task | Read |
| --- | --- |
| New installation | [Install](references/install.md), [credentials](references/credentials.md), [integrations](references/integrations.md), [runner setup](references/alert-investigations.md), [memory analysis](references/memory-llm.md), [connect an agent](references/coding-agents.md) |
| Cloud provider or database preparation | Applicable [AWS](references/cloud-providers/aws.md), [Google Cloud](references/cloud-providers/google-cloud.md), or [external PostgreSQL](references/external-postgres.md) guide |
| Slack, investigations, or model features | [Integrations](references/integrations.md), then the selected guide; [memory model](references/memory-llm.md) when needed |
| Shared access or login | [Private access](references/private-access.md), [OAuth](references/oauth.md), chosen [Google](references/google-saml.md) or [Okta](references/okta-saml.md) provider; [public routing](references/public-mcp-ingress.md) only when selected |
| Existing installation | [Configuration preservation](references/upgrading.md), then the feature, [troubleshooting](references/troubleshooting.md), or [uninstall](references/uninstall.md) guide |

Check [data flows](references/data-flows.md) before changing exposure or data destinations. Use the commented [values.yaml](examples/values.yaml) example for field guidance, and [endpoints](references/endpoints.md) and [input conventions](references/placeholder-examples.md) for lookups. Cloud hosting does not require optional telemetry.

## Prepare and execute

Use the guides' native commands. Do not create wrappers or shell exports. Replace every `REPLACE_WITH_...` input; never invent identifiers or credentials.

Resolve documentation paths from this skill directory. Read the comments before adapting an example and keep the source YAML in the customer's working directory; `helm get values` does not retain comments. Preserve existing configuration, credentials, storage, and values-file order; never overwrite them with an example.

Ask for protected credential paths or Secret names and keys, never secret contents in chat. Do not print secrets. Leave provider template variables such as Datadog notification fields intact.

Explain the changes and proceed within the customer's authorization. Resolve missing inputs and conflicting targets before acting. Ask before destructive changes or broader access or data sharing.

## Verify and hand off

For a new installation, check analysis configuration, verify licensed reads and a completed runner investigation with its saved result and configured delivery. Run functional checks for other selected features. Ready pods do not prove licensed reads, login, Slack replies, or investigations. Run port-forwards separately from checks. Preserve errors and troubleshoot without weakening authentication or deleting data.

Report the target, versions, enabled features, configuration files and order, credential references without values, and observed checks. Identify remaining human or service actions and link the relevant operation guides.
