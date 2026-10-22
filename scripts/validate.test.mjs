import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync, readdirSync } from 'node:fs';

const json = path => JSON.parse(readFileSync(path, 'utf8'));
const endpoint = 'https://mcp.avastudio.com/mcp';

test('all listing formats use the production endpoint without embedded credentials', () => {
  const plugin = json('plugin.json');
  assert.equal(plugin.name, json('.claude-plugin/plugin.json').name);
  assert.equal(plugin.version, json('server.json').version);
  assert.equal(json('mcp.json').mcpServers.ava.url, endpoint);
  assert.equal(json('.mcp.json').mcpServers.ava.url, endpoint);
  assert.equal(json('server.json').remotes[0].url, endpoint);
  const server = json('mcp.json').mcpServers.ava;
  assert.equal(server.extensions['com.openai'].auth.type, 'oauth');
  assert.equal(server.extensions['com.openai'].auth.client.mode, 'dcr');
  assert.equal(server.headers, undefined);
  assert.equal(json('server.json').name, 'com.avastudio/ava');
  // This repo contains listing files, not the hosted server's implementation.
  assert.equal(json('server.json').repository, undefined);
});

test('submission includes usable public URLs, icons, and exactly five positive and three negative cases', () => {
  const extension = json('plugin.json').extensions['com.openai'];
  assert.equal(extension.review.test_cases.positive.length, 5);
  assert.equal(extension.review.test_cases.negative.length, 3);
  for (const entry of [...extension.review.test_cases.positive, ...extension.review.test_cases.negative]) {
    assert(entry.prompt.length > 10 && entry.expected_behavior.length > 10);
  }
  for (const field of ['websiteURL', 'supportURL', 'privacyPolicyURL', 'termsOfServiceURL']) {
    assert.equal(new URL(extension.interface[field]).protocol, 'https:');
  }
  for (const field of ['logo', 'composerIcon']) assert(existsSync(extension.interface[field]));
  assert(extension.interface.shortDescription.length <= 30);
  assert(extension.publication.release_notes.length > 0);
});

test('76 distinct tools have explicit safety labels and read-only tools cannot be destructive', () => {
  const tools = json('listings/tool-annotations.json');
  assert.equal(tools.length, 76);
  assert.equal(new Set(tools.map(t => t.name)).size, 76);
  assert(tools.some(tool => tool.name === 'project_history'));
  for (const tool of tools) {
    assert(tool.title.length > 3);
    for (const key of ['readOnlyHint', 'destructiveHint', 'openWorldHint']) assert.equal(typeof tool.annotations[key], 'boolean');
    if (tool.annotations.readOnlyHint) assert.equal(tool.annotations.destructiveHint, false);
  }
});

test('public files exclude credentials, server implementation and unrelated packages', () => {
  const forbidden = /ava_(?:live|at|rt|cs)_[A-Za-z0-9]{12,}|-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----/;
  const walk = path => {
    for (const entry of readdirSync(path, { withFileTypes: true })) {
      if (entry.name === '.git' || entry.name === 'dist') continue;
      const name = `${path}/${entry.name}`;
      if (entry.isDirectory()) walk(name);
      else if (entry.name.endsWith('.json') || entry.name.endsWith('.md')) assert(!forbidden.test(readFileSync(name, 'utf8')), `Credential in ${name}`);
    }
  };
  walk('.');
  for (const path of ['src', 'packages', '.env', 'key.pem']) assert(!existsSync(path));
});
