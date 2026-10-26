'use strict';

const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const assert = require('node:assert/strict');
const {
  ROOT,
  environment,
  run,
  must,
  write,
  repository,
  fixture,
} = require('./support.cjs');

test('Husky activates locally and leaves CI hook configuration untouched', t => {
  const root = repository(t);
  write(
    root,
    'package.json',
    JSON.stringify({ scripts: { prepare: 'husky' } }),
  );
  fs.symlinkSync(
    path.join(ROOT, 'node_modules'),
    path.join(root, 'node_modules'),
    'junction',
  );
  must(root, 'npm', ['run', 'prepare'], { env: environment({ HUSKY: '0' }) });
  assert.equal(
    must(root, 'git', ['config', '--get', 'core.hooksPath']).stdout.trim(),
    '.disabled-hooks',
  );
  assert.equal(fs.existsSync(path.join(root, '.husky/_')), false);
  must(root, 'npm', ['run', 'prepare']);
  assert.equal(
    must(root, 'git', ['config', '--get', 'core.hooksPath']).stdout.trim(),
    '.husky/_',
  );
});

test('pre-push clears Git-local variables and propagates verification failure', t => {
  const root = fixture(t);
  const pkg = JSON.parse(
    fs.readFileSync(path.join(root, 'package.json'), 'utf8'),
  );
  pkg.scripts['verify:push'] = 'node verify-push.cjs';
  write(root, 'package.json', JSON.stringify(pkg));
  write(
    root,
    'verify-push.cjs',
    "const selected = Object.fromEntries(['GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE'].map(key => [key, process.env[key]])); require('node:fs').writeFileSync('.git/push-env.json', JSON.stringify(selected)); process.exit(19);\n",
  );
  const result = run(root, 'sh', ['.husky/_/pre-push', 'origin', 'unused'], {
    env: environment({
      GIT_DIR: path.join(root, '.git'),
      GIT_WORK_TREE: root,
      GIT_INDEX_FILE: path.join(root, '.git/index'),
    }),
  });
  assert.equal(result.status, 19, result.stdout + result.stderr);
  const env = JSON.parse(
    fs.readFileSync(path.join(root, '.git/push-env.json'), 'utf8'),
  );
  for (const name of ['GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE'])
    assert.equal(env[name], undefined);
});

test('pre-push rejects every main destination while allowing verified feature pushes', t => {
  const root = fixture(t);
  const remote = path.join(root, '.git', 'push-fixture.git');
  must(root, 'git', ['init', '--bare', remote]);
  must(root, 'git', ['remote', 'add', 'origin', remote]);
  // Seed only this isolated bare fixture without its developer hook.
  must(root, 'git', [
    '-c',
    'core.hooksPath=.disabled-hooks',
    'push',
    'origin',
    'HEAD:refs/heads/main',
  ]);
  const baseline = must(remote, 'git', [
    'rev-parse',
    'refs/heads/main',
  ]).stdout.trim();
  must(root, 'git', ['switch', '-c', 'codex/123-push-guard']);
  must(root, 'git', [
    'commit',
    '--allow-empty',
    '-m',
    'test(hooks): Exercise push destinations',
  ]);
  const head = must(root, 'git', ['rev-parse', 'HEAD']).stdout.trim();
  const pkg = JSON.parse(
    fs.readFileSync(path.join(root, 'package.json'), 'utf8'),
  );
  pkg.scripts['verify:push'] = 'node verify-push.cjs';
  write(root, 'package.json', JSON.stringify(pkg));
  write(
    root,
    'verify-push.cjs',
    "require('node:fs').appendFileSync('.git/push-verified', 'verified\\n');\n",
  );
  for (const refs of [
    ['HEAD:refs/heads/main'],
    ['+HEAD:refs/heads/main'],
    [':refs/heads/main'],
    ['HEAD:refs/heads/codex/123-push-guard', 'HEAD:refs/heads/main'],
  ]) {
    const rejected = run(root, 'git', ['push', 'origin', ...refs]);
    assert.notEqual(rejected.status, 0, rejected.stdout + rejected.stderr);
    assert.match(rejected.stderr, /Direct pushes to main are blocked/);
    assert.equal(
      must(remote, 'git', ['rev-parse', 'refs/heads/main']).stdout.trim(),
      baseline,
    );
    assert.notEqual(
      run(remote, 'git', [
        'rev-parse',
        '--verify',
        'refs/heads/codex/123-push-guard',
      ]).status,
      0,
    );
    assert.equal(fs.existsSync(path.join(root, '.git/push-verified')), false);
  }
  must(root, 'git', ['push', 'origin', 'HEAD:refs/heads/codex/123-push-guard']);
  assert.equal(
    must(remote, 'git', [
      'rev-parse',
      'refs/heads/codex/123-push-guard',
    ]).stdout.trim(),
    head,
  );
  assert.equal(
    fs.readFileSync(path.join(root, '.git/push-verified'), 'utf8'),
    'verified\n',
  );
  assert.equal(
    must(remote, 'git', ['rev-parse', 'refs/heads/main']).stdout.trim(),
    baseline,
  );
});
