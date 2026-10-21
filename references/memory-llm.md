# Server-side LLM work on memory records

Memory analysis is required for a complete Tokonoma installation. It needs an Anthropic key and `mcp.memoryLlm.enabled: true`. The runner example supplies both. When enabled, the Tokonoma server sends memory content to Anthropic for these tasks:

- Review possible duplicates. The server continuously links records that cover the same ground. A similarity score cannot tell whether they reach the same conclusion, so a model reads both and classifies their relationship. Search results collapse redundant records into one result. Records that disagree appear together with a conflict warning.
- Triage messages when the Slack app is enabled. The model decides whether another app's post is an alert that warrants memory recall, whether the retrieved memories are worth posting, and how to interpret free-text `@Tokonoma` questions.

Both features send content outside your cluster and share one switch.

## If analysis is disabled

Deduplication still runs. The server links overlapping records, and search collapses re-saves with identical authored content: the same title, summary and body.

Similarity alone does not merge records. Two records can describe the same symptoms and services in similar prose but name different root causes. Without a model to read their conclusions, those pairs remain linked and unresolved. The links accumulate without changing search results.

Before changing an existing release, follow [version and configuration checks](upgrading.md#before-changing-configuration). Replace `REPLACE_WITH_INSTALLED_CHART_VERSION` with its installed chart version and preserve existing image overrides.

## Inputs and files

Complete steps 1 through 5 of [installation](install.md) first. Run commands on that administration workstation, from the customer working directory outside this documentation checkout. Replace placeholders before running commands; agents ask the operator for missing inputs.

| Input | Meaning and source | Required when |
|---|---|---|
| `REPLACE_WITH_KUBE_CONTEXT` | Cluster context from `kubectl config get-contexts` | Every cluster command |
| `REPLACE_WITH_SECRET_DIRECTORY` | Protected credential directory from base installation | File-based credentials |
| `anthropic-api-key.txt` | Anthropic API key from your Anthropic account, saved in the protected directory | Chart-owned credential Secret |
| `license.txt` | Tokonoma-issued license from base installation | Helm upgrade |
| `REPLACE_WITH_ANTHROPIC_SECRET_NAME`, `REPLACE_WITH_ANTHROPIC_SECRET_KEY` | Existing Secret and key from your secret manager | External Secret option |

Keep `tokonoma-values.yaml`, the new `tokonoma-memory-llm.yaml` overlay and every existing overlay in the customer working directory. The protected files contain raw values with no quotes or trailing newline. Existing Secret users keep their references instead of providing a key file.

## Configure analysis

Save the following as `tokonoma-memory-llm.yaml` in the customer working directory:

```yaml
# tokonoma-memory-llm.yaml
mcp:
  memoryLlm:
    enabled: true
```

From that directory, deploy with Helm 3.14+. Include every existing overlay and credential input in this command:

```sh
helm upgrade tokonoma --kube-context REPLACE_WITH_KUBE_CONTEXT --reset-then-reuse-values oci://public.ecr.aws/tokonoma/charts/tokonoma \
  --version REPLACE_WITH_INSTALLED_CHART_VERSION -n tokonoma --create-namespace \
  -f tokonoma-values.yaml -f tokonoma-memory-llm.yaml \
  --set-file mcp.license="REPLACE_WITH_SECRET_DIRECTORY/license.txt" \
  --set-file credentials.anthropicApiKey="REPLACE_WITH_SECRET_DIRECTORY/anthropic-api-key.txt" \
  --wait --timeout 10m
```

Helm should report release `tokonoma` as `deployed`. The chart creates a Secret from the file. Helm also stores supplied values in release metadata; restrict access to it and to the Secret. The key is shared with the investigation runner unless you configure a separate runner key.

For an existing externally managed Secret, merge this into `tokonoma-memory-llm.yaml` instead of supplying `credentials.anthropicApiKey`. Replace the Secret name and key with the existing reference:

```yaml
mcp:
  memoryLlm:
    enabled: true
    apiKeySecret:
      name: REPLACE_WITH_ANTHROPIC_SECRET_NAME
      key: REPLACE_WITH_ANTHROPIC_SECRET_KEY
```

Naming the key source enables the feature because `mcp.memoryLlm.enabled` defaults to `true`. Supplying no key leaves it off. If you rotate an external Secret outside Helm, restart its MCP consumer on the administration workstation:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma rollout restart deployment/toko-mcp
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma rollout status deployment/toko-mcp
```

Expected result: the Deployment successfully rolls out.

Verify the configured provider from the administration workstation:

```bash
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma get deploy toko-mcp \
  -o jsonpath='{.spec.template.spec.containers[?(@.name=="mcp")].env[?(@.name=="MEMORY_LLM_PROVIDER")].value}'
```

Expected output: `anthropic`. This confirms the configured provider, not a successful model request. Check `@Tokonoma setup` if the [Slack app](slack-app.md) is installed.

The server reviews duplicates periodically. A backlog of already-linked pairs is processed over the following passes, not immediately.

## Temporarily stop analysis

To stop analysis for maintenance, set `mcp.memoryLlm.enabled: false` in the saved overlay. Keep its existing key reference if you use an external Secret:

```yaml
mcp:
  memoryLlm:
    apiKeySecret:
      name: REPLACE_WITH_ANTHROPIC_SECRET_NAME
    enabled: false
```

Repeat the complete Helm upgrade above with the changed overlay. This disables memory processing; the required investigation runner remains enabled. Records already collapsed stay collapsed; no new pairs are reviewed. Restore `mcp.memoryLlm.enabled: true` and repeat the upgrade when maintenance ends.

## Anthropic only

Only Anthropic API credentials are supported for this feature. A runner configured for another model provider does not change where memory processing sends its data.

## Choosing a model

The default is the chart-wide `llm.model` (Claude Sonnet 5), which the runner
uses too. Set `llm.model` to change both, or override this one alone:

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
