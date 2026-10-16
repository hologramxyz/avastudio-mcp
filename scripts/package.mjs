import { execFileSync } from 'node:child_process';
import { mkdirSync, readdirSync, lstatSync, renameSync } from 'node:fs';
import { randomUUID } from 'node:crypto';
import { join, resolve } from 'node:path';

// Explicit public plugin payload; listing drafts and operator notes stay out.
const inputs = ['plugin.json', 'mcp.json', 'skills', 'assets'];
function check(path) {
  const stat = lstatSync(path);
  if (stat.isSymbolicLink()) throw new Error(`Refusing symlink in package: ${path}`);
  if (stat.isDirectory()) for (const name of readdirSync(path)) check(join(path, name));
}
for (const path of inputs) check(path);
mkdirSync('dist', { recursive: true });
const output = resolve('dist/avastudio-plugin.zip');
// A new output on every run prevents removed files remaining in a ZIP update.
const temporary = resolve(`dist/${randomUUID()}.zip`);
execFileSync('zip', ['-q', '-r', temporary, ...inputs]);
renameSync(temporary, output);
console.log(output);
