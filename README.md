# Ava Studio for Agents

Public connection, plugin and MCP directory listing files for Ava Studio.
The hosted service runs at https://mcp.avastudio.com/mcp.

Documentation: https://docs.avastudio.com/api-and-mcp/connect

Connect Claude, ChatGPT or Cursor with the server URL and **Sign in with Ava**.
Choose permissions and an optional monthly credit budget during consent.
Only the permitted tools are visible. Existing account credits pay for work;
each paid result or completed job reports its charge.

For Claude Code, install the workflow plugin:

```text
/plugin marketplace add hologramxyz/avastudio-mcp
/plugin install avastudio@avastudio
```

The public [CLI](https://docs.avastudio.com/api-and-mcp/cli) and
[TypeScript SDK](https://docs.avastudio.com/api-and-mcp/sdk) offer the same
tools over REST. This repository contains only client guidance, artwork and
listing files; it does not contain the hosted backend, SDK implementation,
private specification package, reviewer credentials or publisher keys.

## Listing files

- `server.json`: official MCP Registry entry for `com.avastudio/ava`.
- `plugin.json`, `mcp.json`, `skills/`, `assets/`: portable OpenAI plugin.
- `.claude-plugin/` and `.mcp.json`: Claude Code plugin compatibility.
- `listings/`: Claude/Smithery form copy and all 75 tool annotations.

Validate and build the OpenAI upload ZIP with Node.js 22+ and `zip`:

```bash
npm test
npm run package
```

Upload `dist/avastudio-plugin.zip` through OpenAI's **With MCP** submission
flow. Never include keys, login credentials or private account data in a ZIP.
The service terms and privacy policy are linked from the manifest.
