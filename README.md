# Ava Studio

Public connection, plugin and MCP directory listing files for Ava Studio.
The hosted service runs at https://mcp.avastudio.com/mcp.

Documentation: https://docs.avastudio.com/api-and-mcp/connect

[Privacy policy](https://app.avastudio.com/privacy-policy) ·
[Terms of service](https://app.avastudio.com/terms-of-service)

Connect Claude, ChatGPT or Cursor with the server URL and **Sign in with Ava**.
Choose permissions and an optional monthly credit budget during consent.
Only the permitted tools are visible. Existing account credits pay for work;
each paid result or completed job reports its charge.

For Claude Code, install the workflow plugin:

```text
/plugin marketplace add hologramxyz/avastudio-mcp
/plugin install avastudio@avastudio
```

The `launch-remake` skill builds motion-graphics launch films from a product's
real page and a measured reference from Ava's launch library. It needs an agent
with a local filesystem and shell, Chrome, FFmpeg and HyperFrames. Hosted MCP
access alone does not provide that renderer. The skill includes setup and
diagnostic scripts; Gemini and direct ElevenLabs keys are optional, and music
can use existing Ava credits through MCP.

The public [CLI](https://docs.avastudio.com/api-and-mcp/cli) and
[TypeScript SDK](https://docs.avastudio.com/api-and-mcp/sdk) offer the same
tools over REST. This repository contains only client guidance, artwork and
listing files; it does not contain the hosted backend, SDK implementation,
private specification package, reviewer credentials or publisher keys.

## Listing files

- `server.json`: official MCP Registry entry for `com.avastudio/ava`.
- `plugin.json`, `mcp.json`, `skills/`, `assets/`: portable OpenAI plugin.
- `.claude-plugin/` and `.mcp.json`: Claude Code plugin compatibility.
- `listings/`: directory form copy and all 83 tool annotations.

The tool titles, descriptions and safety labels are a submission snapshot of
API contract 0.9.2 (2026-11-17), including campaign draft and carousel editing,
campaign evidence, week navigation and launch styles. The API contract version
is separate from the plugin package version. `listings/tool-snapshot.json`
records the deployed build revision, tool count and snapshot checksum.
Refresh this snapshot against the deployed API specification before a directory
submission if the tool catalog has changed. Check the version and total against
`https://mcp.avastudio.com/health`; an authenticated tool list can be smaller
because it only includes tools permitted by that connection's scopes.

## Claude Marketplaces submission

Claude Marketplaces is an independent directory, separate from Anthropic's
official connector directory. Its [submission rules](https://claudemarketplaces.com/llms.txt)
require a person to sign in with GitHub and send the form; agents should not
submit or pay on their behalf.

1. Check the [existing MCP listing](https://claudemarketplaces.com/mcp/hologramxyz/avastudio-mcp)
   and [directory search](https://claudemarketplaces.com/search?q=avastudio).
   After signing in, also check for a pending submission. Do not submit duplicates.
2. Open the [prefilled MCP submission](https://claudemarketplaces.com/submit?repo=https%3A%2F%2Fgithub.com%2Fhologramxyz%2Favastudio-mcp&type=mcp)
   and choose free review. `listings/claudemarketplaces.json` contains copy to
   paste if the form asks for a name, description, category or server details;
   it is not an automated submission payload. Use **Sales & Marketing** and
   the registry name `com.avastudio/ava`.
3. Optionally request a distinct [Claude Code marketplace listing](https://claudemarketplaces.com/submit?repo=https%3A%2F%2Fgithub.com%2Fhologramxyz%2Favastudio-mcp&type=marketplace)
   if the form accepts both types for this repo. Its manifest is
   `.claude-plugin/marketplace.json`. Do not repeat a listing already pending.
4. When approved, check the public page's connection instructions and description.
   Directory acceptance does not guarantee search indexing or AI citations.

## OpenAI plugin package

Validate and build the OpenAI upload ZIP with Node.js 22+, Python 3 and `zip`:

```bash
npm test
npm run package
```

Upload `dist/avastudio-plugin.zip` through OpenAI's **With MCP** submission
flow. Never include keys, login credentials or private account data in a ZIP.
The service terms and privacy policy are linked from the manifest.

The listing and composer use the app's original 512×512 PNG icon from
https://app.avastudio.com/icon.png. The package's stable identifier remains
`avastudio`; its public display name is **Ava Studio**.
