# Connect @Claude in Slack

Claude Tag brings `@Claude` to Slack as your organization's shared identity. With Tokonoma, channel members can ask about investigations and telemetry or schedule status updates from memory records.

Complete [OAuth](oauth.md) and [public MCP](public-mcp-ingress.md) setup first. Claude Tag runs in Anthropic's cloud and requires a public HTTPS endpoint. Replace `REPLACE_WITH_MCP_HOSTNAME` throughout.

## Prerequisites

Run commands from your [installation working directory](install.md) with AWS CLI and `jq`. Use the protected secret directory with `umask 077` and follow [input conventions](install.md#inputs-and-placeholders). Console steps run in Claude and Slack.

| Input | Where to get it | When needed |
| --- | --- | --- |
| `REPLACE_WITH_MCP_HOSTNAME` | Your verified public HTTPS deployment | Token check, connector and plugin |
| `REPLACE_WITH_COGNITO_USER_POOL_ID` and `REPLACE_WITH_AWS_REGION` | Existing `mcp.auth.cognito` settings and the Cognito console | Before creating a dedicated client |
| AWS account access and secret directory | Your platform team and installation record | Before CLI commands |
| Client ID and secret | Protected files produced in step 2 | Claude connector; enter secrets only in its credential form |
| Slack workspace, pilot channel and bundle access | Claude organization Owner and Slack administrator | Before enabling the integration |

| Requirement | Why |
|---|---|
| Claude Team or Enterprise plan | Claude Tag is unavailable on Free, Pro, and Max |
| Owner in your Claude organization | Initial workspace pairing and launch require an Owner |
| A Slack workspace admin | Installing the Claude app and running `@Claude connect` |
| Routines enabled for the organization | Claude Tag requires it, and recurring posts use it |
| A funded usage balance (Team plans) | Channel work is billed to the organization and requires a funded balance |
| A public HTTPS Tokonoma endpoint | Anthropic's sandbox reaches your server over the internet |

## 1. Set up Claude Tag

Follow Anthropic’s [Claude Tag setup](https://claude.com/docs/claude-tag/admins/setup-overview) to pair Slack, set a spend limit, and enable the service. Public-beta requirements and console labels can change.

Use this organization-managed identity only in approved channels. Personal connectors remain available for members’ own requests.

## 2. Create a machine credential

Claude Tag uses the OAuth 2.0 client credentials grant. Create a dedicated client in the Cognito pool configured by `mcp.auth.cognito.userPoolId` in [OAuth](oauth.md). Check the AWS account first:

```sh
aws sts get-caller-identity
```

Confirm the returned account owns that pool, then create the client:

```sh
aws cognito-idp create-user-pool-client \
  --user-pool-id REPLACE_WITH_COGNITO_USER_POOL_ID \
  --client-name claude-slack \
  --generate-secret \
  --allowed-o-auth-flows client_credentials \
  --allowed-o-auth-scopes toko-mcp/query \
  --allowed-o-auth-flows-user-pool-client \
  --region REPLACE_WITH_AWS_REGION > "REPLACE_WITH_SECRET_DIRECTORY/claude-slack-client.json"
```

Use the correct pool ID; names can repeat and credentials from another pool are rejected. Protect the output containing `ClientId` and `ClientSecret`. The pool needs a Cognito domain and `toko-mcp/query` scope; see [OAuth](oauth.md).

In `hybrid` mode, Tokonoma can admit a verified provider client on its first grant. For `preregistered_only`, append this client to `mcp.auth.clients` in `values.yaml` before testing, preserving existing clients:

```yaml
mcp:
  auth:
    clients:
      - id: REPLACE_WITH_COGNITO_CLIENT_ID
        name: Claude in Slack
        origin: external
        enabled: true
        grantTypes: [client_credentials]
        scopes: [toko-mcp/query]
        tokenEndpointAuthMethod: client_secret_post
```

Apply the [configuration change](upgrading.md#before-changing-configuration). Extract credentials into protected files and verify them before console entry:

```sh
jq -rj '.UserPoolClient.ClientId' "REPLACE_WITH_SECRET_DIRECTORY/claude-slack-client.json" \
  > "REPLACE_WITH_SECRET_DIRECTORY/claude-slack-client-id.txt"
jq -rj '.UserPoolClient.ClientSecret' "REPLACE_WITH_SECRET_DIRECTORY/claude-slack-client.json" \
  > "REPLACE_WITH_SECRET_DIRECTORY/claude-slack-client-secret.txt"
```

```sh
curl -sS https://REPLACE_WITH_MCP_HOSTNAME/token \
  -d grant_type=client_credentials \
  -d scope=toko-mcp/query \
  --data-urlencode "client_id@REPLACE_WITH_SECRET_DIRECTORY/claude-slack-client-id.txt" \
  --data-urlencode "client_secret@REPLACE_WITH_SECRET_DIRECTORY/claude-slack-client-secret.txt" \
  | jq '{has_access_token: (.access_token | type == "string" and length > 0), token_type, expires_in, error}'
```

Expect `has_access_token: true` and no error; the filter hides the token. This uses URL-encoded form fields (`client_secret_post`). Tokonoma also supports HTTP Basic (`client_secret_basic`); the connector and registered client must use matching methods. SAML-only deployments need a Cognito or Google credential provider for machine access.

`toko-mcp/query` covers every MCP tool, including `memory_save` and `memory_update_status`. It is the only scope and permits writes.

## 3. Add the credential to a bundle

A bundle groups connectors, plugins, and allowed domains. At
[`claude.ai/admin-settings/claude-tag`](https://claude.ai/admin-settings/claude-tag),
open **Claude's access** > **Bundles**, click **Add**, name it `tokonoma`, and click **Create**. If labels changed, see Anthropic’s [bundle and connector guide](https://claude.com/docs/claude-tag/admins/add-connections).

On the bundle's page, choose **What's in it > Add > Connector > Custom connector** and enter:

| Field | Value |
|---|---|
| Name | `tokonoma` |
| Credential type | OAuth 2.0 client credentials |
| Token URL | `https://REPLACE_WITH_MCP_HOSTNAME/token` |
| Client ID | from step 2 |
| Client secret | from step 2 |
| Scope | `toko-mcp/query` |
| Allowed websites | `REPLACE_WITH_MCP_HOSTNAME` |

Anthropic injects credentials at its network boundary, only for allowed hosts. The model and sandbox never hold the secret.

To change credentials, open the connector’s **⋮** menu under **What's in it** > **Edit**. Re-enter the write-only secret field with every change.

## 4. Register a plugin that declares the MCP server

A plugin declares the server; the credential authorizes calls. A repository's `.mcp.json` is never loaded directly.

In your deployment working directory, outside the documentation checkout, create:

```
tokonoma/
├── .claude-plugin/
│   └── plugin.json
└── .mcp.json
```

`.claude-plugin/plugin.json`:

```json
{
  "name": "tokonoma",
  "description": "Tokonoma investigation memory and telemetry",
  "version": "0.1.0"
}
```

`.mcp.json`:

```json
{
  "mcpServers": {
    "tokonoma": {
      "type": "http",
      "url": "https://REPLACE_WITH_MCP_HOSTNAME/mcp/"
    }
  }
}
```

Omit any auth block; the bundle credential supplies it. Keep the trailing slash on
the URL.

Zip the directory and upload it at
[`claude.ai/admin-settings/plugins`](https://claude.ai/admin-settings/plugins) using **Add plugins**. Change **User access** from `Not available` to available. On the `tokonoma` bundle, select **What's in it** > **Add** > **Plugin** and choose it. Uploading alone does not activate it.

Apply the plugin and credential to the same channels. See Anthropic’s [custom MCP guide](https://claude.com/docs/claude-tag/admins/connections/custom#add-a-custom-mcp-server).

## 5. Choose where the bundle applies

The bundle starts disabled everywhere. Enable it for all of Slack, one workspace, or one channel.

On the `tokonoma` bundle's page, under **Where it applies**, turn on the **Slack**
row for organization-wide use. To pilot in one channel instead, click **Add
place**, choose the channel under **Where**, and click **Add**. Then click **Save
changes**.

On **Connectors**, check `tokonoma` > **Access from** > **Used at** for the chosen places. If **Not enabled** appears, click **Enable** and confirm.

## 6. Verify

Invite Claude and send a new top-level Slack message. Existing threads do not pick up newly added connections.

```text
/invite @Claude
@Claude using tokonoma, list the 3 most recent memories
```

Returned records confirm the plugin, credential, and channel access work together.

Ask `@Claude what can you access from this channel?` to check its access.

## Recurring status updates

Follow Anthropic’s [routines guide](https://claude.com/docs/claude-tag/users/proactivity) to schedule a channel update. Specify the timezone, how often to post, which record to read, and whether the job may write:

```text
@Claude every hour, re-read Tokonoma investigation REPLACE_WITH_MEMORY_ID and post a one-line
status update with its reference. Skip the post if it has not changed.
Do not modify the record.
```

Confirm the created routine in Claude before relying on it. The routine has the same credential permissions as other work in that channel.

## Attribute what Claude saves

Saved records belong to the machine client. Set `metadata.engineer` on every write so cards and receipts identify the requester. Add this rule to the `tokonoma` bundle’s **Instructions**, where it applies across channels and sessions:

```text
When calling memory_save or memory_update_status on tokonoma, always set
metadata.engineer to the display name of the Slack user who asked for the work,
not to Claude or to the API client. Only if the work came from a scheduled routine
with no requester, set it to Claude.
```

Start a new thread after changing the bundle. Instructions guide attribution; the MCP credential remains the authorization identity.

Reporting-only routines still have write access. Include "post a status update; do not modify the record" in their instructions.

## Troubleshooting

| Symptom | Cause |
|---|---|
| Claude replies that usage credits are not funded | Team plans need a funded balance; buy credits at [`claude.ai/admin-settings/usage`](https://claude.ai/admin-settings/usage) as an Owner |
| Claude replies that Routines are not enabled | Enable Routines at [`claude.ai/admin-settings/claude-code`](https://claude.ai/admin-settings/claude-code) |
| Claude does not see the Tokonoma tools | Confirm the plugin is under the bundle's **What's in it**, the bundle has a place under **Where it applies**, and you are in a new thread |
| Claude reports a blocked host | Confirm the connector's **Allowed websites** lists the host, or add it under the bundle's **What's in it** as a **Domain** |
| `invalid_grant` with `invalid client credentials` from `/token` | The client does not exist in the user pool this server verifies against; recreate it with `--user-pool-id` set to `mcp.auth.cognito.userPoolId` (step 2) |
| `unauthorized_client` from `/token` | Check the admission mode, declared client ID, allowed grant and the registered `tokenEndpointAuthMethod` against the connector’s actual request. |
| Claude asks you to sign in | The request is using a per-member connector rather than the bundle credential; verify steps 3 through 5 |

Requests, retrieved memories and telemetry used by Claude leave your deployment for Anthropic’s service, and replies are visible in the selected Slack channel.

Channel messages are untrusted input that Claude may follow. Limit the bundle to the narrowest scope needing its memory-write access.

For the separate native Tokonoma Slack app, use [Slack app setup](slack-app.md).
