# Guide: connect a coding agent

After installation and health checks, connect your client to Tokonoma's Streamable HTTP MCP endpoint at `/mcp`. Run commands on the client workstation.

| Input | Source | When needed |
| --- | --- | --- |
| `REPLACE_WITH_KUBE_CONTEXT` | Context verified in the installation guide | Opening a local connection |
| MCP URL | `http://127.0.0.1:8000/mcp` for the local path, or the endpoint prepared by your team | All clients |
| Client and scope | Choose Claude Code, Codex, or Cursor; these examples use user-level configuration | Confirm the intended client before changing its configuration |

## 1. Make the endpoint reachable

For a cluster-local install, keep the port-forward from the installation guide running. If it is not already running, open terminal A and leave this command active:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma port-forward svc/toko-mcp 8000:8000
```

In a second terminal, verify the endpoint:

```sh
curl -fsS http://127.0.0.1:8000/health
```

The expected response is `ok`.

## 2. Add Tokonoma to your coding agent

Choose your agent. These examples make Tokonoma available across your local
projects.

### Claude Code

```sh
claude mcp add --transport http --scope user tokonoma http://127.0.0.1:8000/mcp
```

Confirm that the entry was saved:

```sh
claude mcp get tokonoma
```

Open Claude Code and run `/mcp` to confirm that `tokonoma` is connected.

### Codex

```sh
codex mcp add tokonoma --url http://127.0.0.1:8000/mcp
```

Confirm that the entry was saved:

```sh
codex mcp get tokonoma
```

Open Codex and run `/mcp` to confirm that `tokonoma` is connected. Codex CLI,
the IDE extension, and the desktop app share this MCP configuration.

### Cursor

Create or update `~/.cursor/mcp.json`. Merge this entry with any MCP servers
already in the file:

```json
{
  "mcpServers": {
    "tokonoma": {
      "type": "http",
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
```

Open **Cursor Settings > Tools & MCP** and confirm that `tokonoma` and its tools
are enabled.

## Verify memory access

Before onboarding, complete the [save-and-full-body-read check](../install.md#5-connect-and-confirm-memory-access). Require the saved record's identifier and matching text.

## 3. Onboard your coding agent

Start a new agent session and enter:

```text
Run Tokonoma onboard.
```

Onboarding saves investigation context. It can also add a Tokonoma pointer to `AGENTS.md` or `CLAUDE.md` and install a session finalizer. Both are optional.

### Optional session finalization

The finalizer can resume an agent to save an investigation, maintain a used procedure, or render a memory receipt. Existing permissions still apply. Review proposed files and hooks before enabling it, then start a new session and follow the client's trust prompt. Unsupported clients are skipped.

## Use a public endpoint

Follow [public MCP Ingress](public-mcp-ingress.md) and replace the local URL with your endpoint, such as `https://mcp.example.com/mcp`. Set `mcp.auth.enabled: true` and complete login configuration before exposure. Without authentication, any reachable caller can use it.

If you enabled [OAuth](oauth.md), complete the browser login after adding the
server. For Claude Code:

```sh
claude mcp login tokonoma
```

For Codex:

```sh
codex mcp login tokonoma
```

For Cursor, select `tokonoma` under **Tools & MCP** and complete the OAuth prompt.
