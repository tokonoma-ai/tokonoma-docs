# Server model features

The MCP server makes its own Anthropic API calls for these features:

- Duplicate review: search groups redundant records and warns when records disagree.
- Slack triage: interpreting `@Tokonoma` questions when [multiplayer is enabled](slack-app.md#optional-incident-sessions) and, when automatic recall is enabled, deciding which memories to post in response to alerts. With multiplayer off, unmatched mentions return help without model interpretation or memory recall.
- Slack incident timelines, when multiplayer is enabled.

These features are required for a complete Tokonoma installation. They use the same Anthropic API key as the runner and turn on whenever the installation has that key. Only Anthropic API credentials are supported. This guide applies to chart [0.41.0](upgrading.md#one-anthropic-key-040x-to-0410-or-later) or later.

## If the features are off

Search can still collapse identical re-saves, but model-based duplicate review, Slack triage, and timelines stop. Existing reviewed records stay collapsed; other similar records remain separate.

The features are also off when the installation has no Anthropic API key, for example when the runner's only model credential is in `runner.extraEnv`. The install notes printed by Helm say so.

## Configure the key

One Anthropic key serves the whole installation. Supply it in one of two ways:

- Inline: follow [credential setup](credentials.md#supply-credentials-in-commands) and pass `--set-literal 'credentials.anthropicApiKey=REPLACE_WITH_ANTHROPIC_API_KEY'` through the [installation command](install.md#3-install) or [configuration change](upgrading.md#before-changing-configuration). The chart creates the Secret. Fill the key placeholder locally, not in chat.
- Existing Secret: set `llm.apiKeySecret` as shown in [values.yaml](../examples/values.yaml); see [existing Secret setup](credentials.md#use-existing-kubernetes-secrets). `llm.apiKeySecret` takes precedence over `credentials.anthropicApiKey`.

The runner and the MCP server both use it. After rotating an external Secret, restart its consumers using [credential rotation](credentials.md#renew-and-rotate).

## Verify after installation

Verify the configured provider from the administration workstation:

```bash
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma get deploy toko-mcp \
  -o jsonpath='{.spec.template.spec.containers[?(@.name=="mcp")].env[?(@.name=="MEMORY_LLM_PROVIDER")].value}'
```

Expected output: `anthropic`. Empty output means the features are off. This confirms the configured provider, not a successful model request. Check `@Tokonoma admin status` if the [Slack app](slack-app.md) is installed.

## Temporarily stop the features

To stop them for maintenance, set `llm.serverFeatures: false` in `values.yaml` and [apply the configuration change](upgrading.md#before-changing-configuration). The runner keeps the key.

Remove the setting, or set it back to unset (`null`), and repeat the upgrade when maintenance ends.

## Choosing a model

The MCP server and the runner use the chart-wide `llm.model`. Use an Anthropic model identifier supported by your account and test its results before changing production.

## What it costs

Usage depends on the selected model, record activity, and Slack features. Check Anthropic's current pricing and usage dashboard before installation.

## Data handling

Duplicate review sends record titles, summaries, bodies and reference URLs to Anthropic. With the Slack app on, triage also sends the text of messages it triages, and timelines send session messages and evidence. If your deployment forbids these outbound calls, resolve that restriction before completing installation.

Return to [integrations](integrations.md) or continue with the [Slack app](slack-app.md).
