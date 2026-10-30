# Memory analysis

Memory analysis is required for a complete Tokonoma installation. The [values example](../examples/values.yaml) enables `mcp.memoryLlm.enabled: true`; supply an Anthropic key before installation. Analysis supports:

- Duplicate review: search groups redundant records and warns when records disagree.
- Slack features: interpreting `@Tokonoma` questions when [multiplayer is enabled](slack-app.md#optional-incident-sessions) and, when automatic recall is enabled, deciding which memories to post in response to alerts. With multiplayer off, unmatched mentions return help without model interpretation or memory recall.

Both send relevant content to Anthropic and share this switch. Only Anthropic API credentials are supported.

## If analysis is disabled

Search can still collapse identical re-saves, but model-based duplicate review and Slack interpretation stop. Existing reviewed records stay collapsed; other similar records remain separate.

## Configure analysis

Keep `mcp.memoryLlm.enabled: true` in `values.yaml`. Follow [credential setup](credentials.md#supply-credentials-in-commands) and supply `--set-literal 'credentials.anthropicApiKey=REPLACE_WITH_ANTHROPIC_API_KEY'` through the [installation command](install.md#3-install) or [configuration change](upgrading.md#before-changing-configuration). Fill the key placeholder locally, not in chat.

For an externally managed Secret, use `mcp.memoryLlm.apiKeySecret` as shown in [values.yaml](../examples/values.yaml). Set `runner.engine.apiKeySecret` too if the runner should share that key; see [existing Secret setup](credentials.md#use-existing-kubernetes-secrets).

After rotating an external Secret, restart its consumers using [credential rotation](credentials.md#renew-and-rotate).

## Verify after installation

Verify the configured provider from the administration workstation:

```bash
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma get deploy toko-mcp \
  -o jsonpath='{.spec.template.spec.containers[?(@.name=="mcp")].env[?(@.name=="MEMORY_LLM_PROVIDER")].value}'
```

Expected output: `anthropic`. This confirms the configured provider, not a successful model request. Check `@Tokonoma admin status` if the [Slack app](slack-app.md) is installed.

## Temporarily stop analysis

To stop analysis for maintenance, set `mcp.memoryLlm.enabled: false` in `values.yaml` and [apply the configuration change](upgrading.md#before-changing-configuration). Keep the existing key and Secret references so the runner can continue using them.

Restore `mcp.memoryLlm.enabled: true` and repeat the upgrade when maintenance ends.

## Choosing a model

Analysis and the runner default to the chart-wide `llm.model`. Set it in `values.yaml` to change both, or set `mcp.memoryLlm.model` to change analysis alone. Use an Anthropic model identifier supported by your account and test its results before changing production.

## What it costs

Usage depends on the selected model, record activity, and Slack features. Check Anthropic's current pricing and usage dashboard before installation.

## Data handling

Analysis sends record titles, summaries, bodies and reference URLs to Anthropic. With the Slack app on, it also sends the text of messages it triages. If your deployment forbids these outbound calls, resolve that restriction before completing installation.

Return to [integrations](integrations.md) or continue with the [Slack app](slack-app.md).
