# Server-side LLM work on memory records

Memory analysis is required for a complete Tokonoma installation. It needs an Anthropic key and `mcp.memoryLlm.enabled: true`. The [values example](../examples/values.yaml) enables it; supply the key before installation. When enabled, the Tokonoma server sends memory content to Anthropic for these tasks:

- Review possible duplicates. The server continuously links records that cover the same ground. A similarity score cannot tell whether they reach the same conclusion, so a model reads both and classifies their relationship. Search results collapse redundant records into one result. Records that disagree appear together with a conflict warning.
- Triage messages when the Slack app is enabled. The model decides whether another app's post is an alert that warrants memory recall, whether the retrieved memories are worth posting, and how to interpret free-text `@Tokonoma` questions.

Both features send content outside your cluster and share one switch.

## If analysis is disabled

Deduplication still runs. The server links overlapping records, and search collapses re-saves with identical authored content: the same title, summary and body.

Similarity alone does not merge records. Two records can describe the same symptoms and services in similar prose but name different root causes. Without a model to read their conclusions, those pairs remain linked and unresolved. The links accumulate without changing search results.

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

The server reviews duplicates periodically. A backlog of already-linked pairs is processed over the following passes, not immediately.

## Temporarily stop analysis

To stop analysis for maintenance, set `mcp.memoryLlm.enabled: false` in `values.yaml` and [apply the configuration change](upgrading.md#before-changing-configuration). Keep the existing key and Secret references so the required runner can continue using them. Records already collapsed stay collapsed; no new pairs are reviewed.

Restore `mcp.memoryLlm.enabled: true` and repeat the upgrade when maintenance ends.

## Anthropic only

Only Anthropic API credentials are supported for this feature. A runner configured for another model provider does not change where memory processing sends its data.

## Choosing a model

The default is the chart-wide `llm.model` (Claude Sonnet 5), which the runner
uses too. Set `llm.model` in `values.yaml` to change both, or override analysis alone:

```yaml
mcp:
  memoryLlm:
    model: claude-haiku-4-5-20251001
```

These short, structured tasks run often. Consider a smaller model if lower cost matters more than the quality of its judgments.

## What it costs

Usage depends on the selected model and the amount of content processed. Check your provider’s current pricing and usage dashboard before installation.

Duplicate review makes one call for each newly linked pair. Identical re-saves skip this step, and unrelated records are never linked. Usage therefore depends on how often your team writes about the same thing twice, rather than the total number of records.

## Data handling

Analysis sends record titles, summaries, bodies and reference URLs to Anthropic. With the Slack app on, it also sends the text of messages it triages. If your deployment forbids these outbound calls, resolve that restriction before completing installation.

Return to [integrations](integrations.md) or continue with the [Slack app](slack-app.md).
