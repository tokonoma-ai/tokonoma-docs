# Memory analysis

Memory analysis is required for a complete Tokonoma installation. The [values example](../examples/values.yaml) enables `mcp.memoryLlm.enabled: true`; supply an Anthropic key before installation. Analysis supports:

- Duplicate review: search groups redundant records and warns when records disagree.
- Slack features: interpreting `@Tokonoma` questions and, when automatic recall is enabled, deciding which memories to post in response to alerts.

Both send relevant content to Anthropic and share this switch. Only Anthropic API credentials are supported, regardless of the runner's model provider.

## If analysis is disabled

Search can still collapse identical re-saves, but model-based duplicate review and Slack interpretation stop. Existing reviewed records stay collapsed; other similar records remain separate.

Before changing an existing release, follow [configuration checks](upgrading.md#before-changing-configuration).

## Inputs and files

Prepare the analysis credential before [installation](install.md#3-install). Run commands from the customer working directory on its administration workstation, outside this documentation checkout. Replace placeholders before running commands; agents ask the operator for missing inputs.

| Input | Meaning and source | Required when |
|---|---|---|
| `REPLACE_WITH_KUBE_CONTEXT` | Cluster context from `kubectl config get-contexts` | Every cluster command |
| `REPLACE_WITH_SECRET_DIRECTORY` | Protected credential directory from [credentials](credentials.md) | File-based credentials |
| `anthropic-api-key.txt` | Anthropic API key from your Anthropic account, saved in the protected directory | Chart-owned credential Secret |
| `license.txt` | Tokonoma-issued license | Install or upgrade |
| `REPLACE_WITH_ANTHROPIC_SECRET_NAME`, `REPLACE_WITH_ANTHROPIC_SECRET_KEY` | Existing Secret and key from your secret manager | External Secret option |

Keep all configuration in `values.yaml` in the customer working directory. The protected files contain raw values with no quotes or trailing newline. Existing Secret users keep their references instead of providing a key file.

## Configure analysis

Keep `mcp.memoryLlm.enabled: true` in `values.yaml`. Supply the Anthropic key with `--set-file credentials.anthropicApiKey="REPLACE_WITH_SECRET_DIRECTORY/anthropic-api-key.txt"` in the complete [installation](install.md#3-install) or [upgrade](upgrading.md) command. Helm stores this value in release metadata and a Secret; restrict access to both. The runner shares the key when using the Anthropic API unless you configure a separate runner reference.

For an externally managed Secret, uncomment `mcp.memoryLlm.apiKeySecret` in [values.yaml](../examples/values.yaml) and set its `name` and `key` to the existing Secret. Use the separate `runner.engine.apiKeySecret` reference when the runner should share that key. These references do not create Secrets. See [credential setup](credentials.md#use-existing-kubernetes-secrets).

After rotating an external Secret, restart its consumers using [credential rotation](credentials.md#renew-and-rotate).

## Verify after installation

Verify the configured provider from the administration workstation:

```bash
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma get deploy toko-mcp \
  -o jsonpath='{.spec.template.spec.containers[?(@.name=="mcp")].env[?(@.name=="MEMORY_LLM_PROVIDER")].value}'
```

Expected output: `anthropic`. This confirms the configured provider, not a successful model request. Check `@Tokonoma setup` if the [Slack app](slack-app.md) is installed.

## Temporarily stop analysis

To stop analysis for maintenance, set `mcp.memoryLlm.enabled: false` in `values.yaml` and [apply the configuration change](upgrading.md#before-changing-configuration). Keep the existing key and Secret references so the runner can continue using them.

Restore `mcp.memoryLlm.enabled: true` and repeat the upgrade when maintenance ends.

## Choosing a model

Analysis and the runner default to the chart-wide `llm.model`. Set it in `values.yaml` to change both, or set `mcp.memoryLlm.model` to change analysis alone. Use an Anthropic model identifier supported by your account and test its results before changing production.

## What it costs

Usage depends on the selected model, record activity, and Slack features. Check your provider's current pricing and usage dashboard before installation.

## Data handling

Analysis sends record titles, summaries, bodies and reference URLs to Anthropic. With the Slack app on, it also sends the text of messages it triages. If your deployment forbids these outbound calls, resolve that restriction before completing installation.

Return to [integrations](integrations.md) or continue with the [Slack app](slack-app.md).
