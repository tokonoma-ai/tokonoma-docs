---
name: tokonoma-docs
description: Install, configure, connect, upgrade, troubleshoot, or remove a customer's Tokonoma deployment using the released Helm chart and these shared customer guides. Use when a customer asks for help operating Tokonoma in their Kubernetes cluster.
---

# Operate a Tokonoma installation

Follow the same [customer guides](README.md#read-the-documentation) humans use. They target chart **0.37.0** and application **0.68.0**. Verify existing versions before applying pinned commands. If they differ, find compatible instructions or agree an explicit version change; enabling a feature must not silently upgrade or downgrade the release.

## Establish the requested task

Identify the task, authorized cluster context, release, namespace, features, and access model. Inspect existing state before installing; a configuration change is not a reinstall.

Read the customer's saved values files in application order and check the installed release first. Inspect nonsecret integration settings and Secret references; do not print secret values. Shipped examples are defaults, not evidence of the customer's tools. Ask only about missing settings, conflicts, or requested additions. Confirm which integrations to enable and save those choices in the customer's values files.

Batch unresolved inputs and decisions into one question where practical. Explain human-only actions, such as obtaining a license, signing in, or approving an app, and how to check completion.

## Read only the relevant guides

| Task | Read |
| --- | --- |
| New installation | [Install](docs/install.md), [credentials](docs/guides/credentials.md), [connect an agent](docs/guides/coding-agents.md) |
| Platform or database preparation | Applicable [AWS](docs/platform/eks.md), [Google Cloud](docs/platform/gke.md), or [external PostgreSQL](docs/guides/external-postgres.md) guide |
| Slack, investigations, or model features | [Integrations](docs/integrations.md), then the selected guide; [memory model](docs/guides/memory-llm.md) when needed |
| Shared access or login | [Private access](docs/guides/private-access.md), [OAuth](docs/guides/oauth.md), chosen [Google](docs/guides/google-saml.md) or [Okta](docs/guides/okta-saml.md) provider; [public routing](docs/guides/public-mcp-ingress.md) only when selected |
| Existing installation | [Configuration preservation](docs/guides/upgrading.md), then the feature, [troubleshooting](docs/guides/troubleshooting.md), or [uninstall](docs/guides/uninstall.md) guide |

Check [data flows](docs/data-flows.md) before changing exposure or data destinations. Use [values](docs/reference/values.md), [endpoints](docs/reference/endpoints.md), and [input conventions](docs/reference/placeholder-examples.md) for lookups. Cloud hosting does not require optional telemetry.

## Prepare and execute

Use the guides' native commands. Do not create wrappers or shell exports. Replace every `REPLACE_WITH_...` input; never invent identifiers or credentials.

Resolve documentation paths from this skill directory. Copy examples into the customer's working directory. Preserve existing configuration, credentials, storage, and values-file order; never overwrite them with an example.

Ask for protected credential paths or Secret names and keys, never secret contents in chat. Do not print secrets. Leave provider template variables such as Datadog notification fields intact.

Explain changes and proceed within the customer's authorization. Wait for decisions that resolve missing inputs, conflicting targets, destructive changes, or expanded access or data sharing.

## Verify and hand off

Run functional checks for the selected features. Ready pods do not prove licensed reads, login, Slack replies, or investigations. Run port-forwards separately from checks. Preserve errors and troubleshoot without weakening authentication or deleting data.

Report the target, versions, enabled features, configuration files and order, credential references without values, and observed checks. Identify remaining human or service actions and link the relevant operation guides.
