import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync, existsSync, readdirSync } from 'node:fs';

const json = path => JSON.parse(readFileSync(path, 'utf8'));
const endpoint = 'https://mcp.avastudio.com/mcp';

test('all listing formats use the production endpoint without embedded credentials', () => {
  const plugin = json('plugin.json');
  assert.equal(plugin.name, json('.claude-plugin/plugin.json').name);
  assert.equal(plugin.version, json('server.json').version);
  assert.equal(plugin.version, json('.claude-plugin/plugin.json').version);
  assert.equal(plugin.version, json('package.json').version);
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

test('the complete tool snapshot has explicit safety labels and matches its provenance', () => {
  const tools = json('listings/tool-annotations.json');
  const snapshot = json('listings/tool-snapshot.json');
  assert.equal(snapshot.tool_count, 83);
  assert.equal(snapshot.spec_version, '0.9.2');
  assert.match(snapshot.build_revision, /^[a-f0-9]{40}$/);
  assert.equal(snapshot.endpoint, endpoint);
  assert.equal(tools.length, snapshot.tool_count);
  assert.equal(new Set(tools.map(t => t.name)).size, snapshot.tool_count);
  assert.equal(createHash('sha256').update(readFileSync('listings/tool-annotations.json')).digest('hex'), snapshot.sha256);
  for (const name of [
    'project_history', 'campaign_evidence', 'concept_draft_get', 'concept_draft_update',
    'launch_style_get', 'launch_style_list', 'plan_list', 'slides_update',
  ]) assert(tools.some(tool => tool.name === name), `Missing current tool: ${name}`);
  for (const tool of tools) {
    assert(tool.title.length > 3);
    for (const key of ['readOnlyHint', 'destructiveHint', 'openWorldHint']) assert.equal(typeof tool.annotations[key], 'boolean');
    if (tool.annotations.readOnlyHint) assert.equal(tool.annotations.destructiveHint, false);
  }
});

test('directory copy has matching connection details and human-only free submission links', () => {
  const listing = json('listings/claudemarketplaces.json');
  const repository = json('.claude-plugin/plugin.json').repository;
  assert.equal(listing.name, json('server.json').title);
  assert.equal(listing.repository, repository);
  assert.equal(listing.server_url, endpoint);
  assert.equal(listing.registry_name, json('server.json').name);
  assert.equal(listing.category, 'Sales & Marketing');
  assert.equal(listing.type, 'mcp');
  assert.equal(listing.review, 'free');
  assert.equal(listing.human_submission_required, true);
  for (const [field, type] of [['submit_url', 'mcp'], ['optional_marketplace_submit_url', 'marketplace']]) {
    const url = new URL(listing[field]);
    assert.equal(url.origin, 'https://claudemarketplaces.com');
    assert.equal(url.pathname, '/submit');
    assert.equal(url.searchParams.get('repo'), repository);
    assert.equal(url.searchParams.get('type'), type);
  }
});

test('public files exclude credentials, server implementation and unrelated packages', () => {
  const forbidden = /ava_(?:live|at|rt|cs)_[A-Za-z0-9]{12,}|-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----/;
  const walk = path => {
    for (const entry of readdirSync(path, { withFileTypes: true })) {
      if (entry.name === '.git' || entry.name === 'dist') continue;
      const name = `${path}/${entry.name}`;
      if (entry.isDirectory()) walk(name);
      else if (/\.(json|md|py|sh|js|cjs|mjs)$/.test(entry.name)) assert(!forbidden.test(readFileSync(name, 'utf8')), `Credential in ${name}`);
    }
  };
  walk('.');
  for (const path of ['src', 'packages', '.env', 'key.pem']) assert(!existsSync(path));
});

test('bundled skills have discoverable names and supported descriptions', () => {
  for (const entry of readdirSync('skills', { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    const file = `skills/${entry.name}/SKILL.md`;
    const source = readFileSync(file, 'utf8');
    const frontmatter = source.match(/^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/)?.[1];
    assert(frontmatter, `Missing skill frontmatter: ${file}`);
    assert.equal(frontmatter.match(/^name:\s*(.+)$/m)?.[1].trim(), entry.name);
    const description = frontmatter.match(/^description:\s*(.+)$/m)?.[1].trim();
    assert(description && description.length <= 1024 && !/[<>]/.test(description), `Invalid skill description: ${file}`);
  }
});
