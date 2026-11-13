import { test } from 'node:test';
import { execFileSync } from 'node:child_process';

test('launch-remake provider helpers preserve success and report failures safely', () => {
  execFileSync(process.env.PYTHON || 'python3', ['scripts/test_launch_remake.py'], { stdio: 'inherit' });
});
