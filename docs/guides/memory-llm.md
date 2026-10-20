# Server-side LLM work on memory records

Off by default. When you enable it, the Tokonoma server makes outbound calls to
Anthropic carrying the content of memory records, to do two things:

- **Adjudicate duplicate candidates.** The server continuously links records
  that cover the same ground. Deciding whether two similar records actually
  reach the *same conclusion* is the part no similarity measure can do, so a
  model reads both and classifies the relationship. Records judged redundant
  are collapsed to one in search results; records that disagree are shown
  together with a conflict warning.
- **Triage Slack messages** (only when the Slack app is enabled). The model
  decides whether another app's post is an alert worth a recall, judges
  whether the memories found are worth posting, and interprets free-text
  `@Tokonoma` questions.

One switch governs these features because both send content outside your cluster.

## What happens without it

Deduplication still runs. The server links records that overlap, and search
still collapses **re-saves whose authored content is identical** (same title,
summary and body).

What it will not do is merge anything on similarity alone. Two records can
share a symptom, a service set and most of their prose while naming different
root causes. Without a model to read the conclusions,
those pairs are linked but left alone.
They accumulate as unresolved links and have no effect on what you see.

Before changing an existing release, follow [version and configuration checks](upgrading.md). If its versions differ from this guide, resolve that difference before running the pinned command.

## Inputs and files

Complete the [base installation](../install.md) first. Run commands on that administration workstation, from the customer working directory outside this documentation checkout. Replace placeholders before running commands; agents ask the operator for missing inputs.

| Input | Meaning and source | Required when |
|---|---|---|
| `REPLACE_WITH_KUBE_CONTEXT` | Cluster context from `kubectl config get-contexts` | Every cluster command |
| `REPLACE_WITH_SECRET_DIRECTORY` | Protected credential directory from base installation | File-based credentials |
| `anthropic-api-key.txt` | Anthropic API key from your Anthropic account, saved in the protected directory | Chart-owned credential Secret |
| `license.txt` | Tokonoma-issued license from base installation | Helm upgrade |
| `REPLACE_WITH_ANTHROPIC_SECRET_NAME`, `REPLACE_WITH_ANTHROPIC_SECRET_KEY` | Existing Secret and key from your secret manager | External Secret option |

Keep `tokonoma-values.yaml`, the new `tokonoma-memory-llm.yaml` overlay and every existing overlay in the customer working directory. The protected files contain raw values with no quotes or trailing newline. Existing Secret users keep their references instead of providing a key file.

## Enable it

Save the following as `tokonoma-memory-llm.yaml` in the customer working directory:

```yaml
# tokonoma-memory-llm.yaml
mcp:
  image:
    tag: "0.68.0"
  memoryLlm:
    enabled: true
```

From that directory, deploy with Helm 3.14+. Include every existing overlay and credential input in this command:

```sh
helm upgrade tokonoma --kube-context REPLACE_WITH_KUBE_CONTEXT --reset-then-reuse-values oci://public.ecr.aws/tokonoma/charts/tokonoma \
  --version 0.37.0 -n tokonoma --create-namespace \
  -f tokonoma-values.yaml -f tokonoma-memory-llm.yaml \
  --set-file mcp.license="REPLACE_WITH_SECRET_DIRECTORY/license.txt" \
  --set-file credentials.anthropicApiKey="REPLACE_WITH_SECRET_DIRECTORY/anthropic-api-key.txt" \
  --wait --timeout 10m
```

Helm should report release `tokonoma` as `deployed`. The chart creates a Secret from the file. Helm also stores supplied values in release metadata; restrict access to it and to the Secret. The key is shared with the investigation runner when that feature is enabled.

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

Duplicate review runs on the server's periodic reconciliation pass, so a backlog of
already-linked pairs drains over the following passes rather than immediately.

## Turn it off without removing the secret

Set `mcp.memoryLlm.enabled: false` in the saved overlay. Keep its existing key reference if you use an external Secret:

```yaml
mcp:
  memoryLlm:
    apiKeySecret:
      name: REPLACE_WITH_ANTHROPIC_SECRET_NAME
    enabled: false
```

Repeat the complete Helm upgrade above with the changed overlay. This disables memory processing; it does not disable a separately enabled investigation runner. Records
already collapsed stay collapsed; nothing new is judged.

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

The work is short, high-volume and structured, so a smaller model is a
reasonable override where cost matters more than judgement.

## What it costs

Usage depends on the selected model and the amount of content processed. Check your provider’s current pricing and usage dashboard before enabling it.

For adjudication, one call per newly linked pair, once. Identical re-saves never reach it, and
unrelated records are not linked in the first place, so volume tracks how often
your team writes up the same thing twice rather than how many records you have.

## Data handling

Enabling this sends record titles, summaries, bodies and reference URLs to
Anthropic, and, with the Slack app on, the text of Slack messages it triages. If your deployment forbids outbound calls carrying customer content,
leave it off. The behaviour described under "What happens without it" remains supported.

Return to [integrations](../integrations.md) or continue with the [Slack app](slack-app.md).
