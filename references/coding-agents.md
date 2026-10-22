# Connect a coding agent

After installation and human login setup, connect your client to Tokonoma's Streamable HTTP MCP endpoint at `/mcp`. The standard phase 1 machine login serves the runner and local UI only. Configure [human sign-in](private-access.md#team-access) before connecting engineers' coding agents; do not copy the generated runner credential. Run commands on the client workstation.

| Input | Source | When needed |
| --- | --- | --- |
| `REPLACE_WITH_KUBE_CONTEXT` | Context verified in the installation guide | Opening a local connection |
| MCP URL | `http://127.0.0.1:8000/mcp` for the local path, or the endpoint prepared by your team | All clients |
| Client and scope | Choose Claude Code, Codex, or Cursor; these examples use user-level configuration | Confirm the intended client before changing its configuration |

## 1. Make the endpoint reachable

For a local connection, complete the [installation port-forward and health check](install.md#4-verify). Keep the port-forward running while your coding agent is connected.

## 2. Add Tokonoma to your coding agent

Choose your agent. These examples make Tokonoma available across your local
projects.

### Claude Code

```sh
claude mcp add --transport http --scope user tokonoma http://127.0.0.1:8000/mcp
```

Check the saved entry:

```sh
claude mcp get tokonoma
```

Open Claude Code and run `/mcp` to confirm that `tokonoma` is connected.

### Codex

```sh
codex mcp add tokonoma --url http://127.0.0.1:8000/mcp
```

Check the saved entry:

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

The optional [memory access check](install.md#connect-and-confirm-memory-access) saves a record and reads it back. Confirm its identifier and matching text.

## 3. Onboard your coding agent

Start a new agent session and enter:

```text
Run Tokonoma onboard.
```

Onboarding saves investigation context. It can also add a Tokonoma pointer to `AGENTS.md` or `CLAUDE.md` and install a session finalizer. The pointer and finalizer are optional.

### Optional session finalization

The finalizer can resume an agent to save an investigation, maintain a used procedure, or render a memory receipt within existing permissions. Review its proposed files and hooks before enabling it, then start a new session and follow the client's trust prompt. Unsupported clients are skipped.

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
