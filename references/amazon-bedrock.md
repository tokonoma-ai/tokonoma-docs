# Amazon Bedrock

Tokonoma can reach Claude through Amazon Bedrock instead of the Anthropic API. The runner and the MCP server both use it, from one Bedrock API key and one region.

This guide needs chart 0.42.0 or later and toko-mcp 0.84.0 or later. The chart's default image tag is `latest`; if you pin `mcp.image.tag`, pin 0.84.0 or later. On an older image, the runner uses Bedrock but the [server model features](server-features.md) stay off.

## What you need

| Input | Source |
|---|---|
| Bedrock API key | Generate it in the Amazon Bedrock console, in the account that will pay for model use |
| AWS region | The region you will call Bedrock in, for example `us-west-2` |
| Anthropic model access | In the Bedrock model catalog, select an Anthropic model and submit the use case form, once per AWS account |

If this account has not used the model before, allow the key to access Bedrock Marketplace models when you create it. The first model call may need to set up the subscription.

IAM roles are not supported for this path yet. Note the key's expiry date: when it expires, investigations and server model features stop until you [rotate it](credentials.md#renew-and-rotate).

## Check the model is available

The chart's default model is `claude-sonnet-5-5`. Confirm the region offers an inference profile for it:

```bash
aws bedrock list-inference-profiles --region REPLACE_WITH_REGION \
  --query "inferenceProfileSummaries[?contains(inferenceProfileId, 'anthropic.claude-sonnet-5-5')].inferenceProfileId"
```

Tokonoma adds the region's prefix itself: `us.` for `us-*`, `eu.` for `eu-*`, `apac.` for `ap-*`, `us-gov.` for `us-gov-*`, and `global.` elsewhere. This has been validated in `us-west-2`; test another region before relying on it.

## Configure

Create the Secret in the release namespace. Paste the key at the silent prompt:

```bash
read -rs BEDROCK_KEY
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma create secret generic aws-bedrock-api-key \
  --from-literal=token="$BEDROCK_KEY"
unset BEDROCK_KEY
```

Set these values, then install or [apply the configuration change](upgrading.md#before-changing-configuration):

```yaml
llm:
  provider: bedrock
  region: REPLACE_WITH_REGION
  apiKeySecret:
    name: aws-bedrock-api-key
    key: token
```

Leave `llm.model` as a bare identifier. The MCP server's features need Claude 4.7 or later on Bedrock.

To pin one profile for the runner, set `runner.engine.model`, for example to `us.anthropic.claude-sonnet-5-5`.

The render fails, naming the fix, if `llm.region` or `llm.apiKeySecret.name` is missing, or if an Anthropic key field is still set.

## Move from `runner.extraEnv`

If you configured Bedrock for the runner through `runner.extraEnv`, it keeps working while `llm.provider` is `anthropic`, and the MCP server stays on its Anthropic key or off. To move:

1. Delete `CLAUDE_CODE_USE_BEDROCK`, `AWS_REGION` and `AWS_BEARER_TOKEN_BEDROCK` from `runner.extraEnv`.
2. Delete `credentials.anthropicApiKey` and any Anthropic key Secret reference.
3. Set the values above.

## Verify

```bash
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma get deploy toko-mcp \
  -o jsonpath='{.spec.template.spec.containers[?(@.name=="mcp")].env[?(@.name=="MEMORY_LLM_PROVIDER")].value}'
```

Expected output: `bedrock`. This confirms the configuration, not a successful model call, so run a test investigation.

Then send `@Tokonoma admin status`. With toko-mcp 0.85.0 or later, the runner and the MCP server each check access by asking the model for one token, and a healthy installation shows **Models: Ready**. The runner checks hourly and the MCP server checks on each status request. AWS bills these small calls.

On toko-mcp 0.84.0, status cannot check Bedrock access. Its Models section shows **Needs attention** with lines saying access is not checked, which is expected on that version. A missing credential reads differently: it says model access is not configured.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Invocation of model ID anthropic.claude-… with on-demand throughput isn't supported` | The `anthropic.` form of a model identifier | Use the bare identifier, or a region-prefixed profile such as `us.anthropic.claude-sonnet-5-5` |
| `The provided model identifier is invalid` | The identifier doesn't exist in this region | Check it with the command above |
| Runner works, Slack questions and duplicate review don't | toko-mcp image older than 0.84.0, or a model older than Claude 4.7 | Upgrade the image or choose a newer model |
| Status says Bedrock rejected the credentials | The key expired, was revoked, or isn't allowed to use the model | [Rotate the key](credentials.md#renew-and-rotate) or fix its permissions |
| Status says Bedrock cannot call or invoke the model | The region doesn't offer it, or the MCP server's model is older than Claude 4.7 | Check it with the command above, or choose a newer model |
| Status says access could not be verified | Throttling, a Bedrock error, or no network path to Bedrock | Check the pod's connectivity to Bedrock and your quota, then check status again |
| Failures start after working for a while | The key expired | [Rotate the key](credentials.md#renew-and-rotate) |
| Throttling errors | Your account's Bedrock quota | Request a quota increase from AWS |

## Data and cost

Model calls go to Amazon Bedrock in your AWS account and region, under AWS's terms, instead of to Anthropic. See [data flows](data-flows.md). Slack, connected MCP servers and the optional [TypeSafe Judge](credentials.md#optional-typesafe-judge) connect separately, as they do on any installation.

AWS bills model use. The dollar figures Tokonoma shows are estimates at Anthropic's API prices, so use your AWS bill for actual cost.
