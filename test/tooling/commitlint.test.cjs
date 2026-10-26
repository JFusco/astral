'use strict';

const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const assert = require('node:assert/strict');
const {
  ROOT,
  run,
  must,
  write,
  repository,
  fixture,
} = require('./support.cjs');

const cli = path.join(ROOT, 'node_modules/@commitlint/cli/cli.js');
const config = path.join(ROOT, 'commitlint.config.cjs');

test('standalone Commitlint matches the selected message policy', async t => {
  const [{ default: load }, { default: lint }] = await Promise.all([
    import('@commitlint/load'),
    import('@commitlint/lint'),
  ]);
  const loaded = await load({}, { file: config, cwd: ROOT });
  const cases = [
    ['ci(quality): Add hooks', true],
    ['fix(custom-scope): preserve output', true],
    ['feat(api)!: Change request', true],
    [
      'feat(api): Change request\n\nBREAKING CHANGE: request fields changed',
      true,
    ],
    ["Merge branch 'feature'", true],
    ['fix: Missing scope', false],
    ['fix(API): Uppercase scope', false],
    ['unknown(api): Invalid type', false],
    ['fix(api): Trailing period.', false],
    ['fix(api):', false],
    [`fix(api): ${'x'.repeat(50)}`, true],
    [`fix(api): ${'x'.repeat(51)}`, false],
    [`fix(${'s'.repeat(112)}): x`, true],
    [`fix(${'s'.repeat(113)}): x`, false],
    [`fix(api): Add checks\n\n${'x'.repeat(72)}`, true],
    [`fix(api): Add checks\n\n${'x'.repeat(73)}`, false],
    [
      'docs(wiki): reconcile merged PR #3 (#13)\n\nCo-authored-by: github-actions[bot] <41898282+github-actions[bot]@users.noreply.github.com>',
      true,
    ],
    [
      'feat(api)!: Change request\n\nBREAKING CHANGE: request fields changed\nCo-authored-by: github-actions[bot] <41898282+github-actions[bot]@users.noreply.github.com>',
      true,
    ],
    [`fix(api): Add checks\n\nCo-authored-by: ${'x'.repeat(101)}`, false],
    [`fix(api): Add checks\n\nBREAKING CHANGE: ${'x'.repeat(55)}`, true],
    [`fix(api): Add checks\n\nBREAKING CHANGE: ${'x'.repeat(56)}`, false],
  ];
  for (const [message, valid] of cases) {
    await t.test(JSON.stringify(message), async () => {
      const result = await lint(message, loaded.rules, {
        parserOpts: loaded.parserPreset?.parserOpts,
        plugins: loaded.plugins,
        ignores: loaded.ignores,
        defaultIgnores: loaded.defaultIgnores,
      });
      assert.equal(
        result.valid,
        valid,
        result.errors.map(error => error.message).join('; '),
      );
    });
  }
});

test('the configured Commitlint CLI accepts a valid message and rejects an invalid one', () => {
  must(ROOT, process.execPath, [cli, '--config', config], {
    input: 'test(tooling): verify command policy\n',
  });
  const rejected = run(ROOT, process.execPath, [cli, '--config', config], {
    input: 'Missing conventional format\n',
  });
  assert.equal(rejected.status, 1, rejected.stdout + rejected.stderr);
});

test('commit range checks only introduced commits, including ones before the tip', t => {
  const root = repository(t);
  write(root, 'seed', 'seed\n');
  must(root, 'git', ['add', '.']);
  must(root, 'git', ['commit', '-m', 'Historical unscoped message']);
  const base = must(root, 'git', ['rev-parse', 'HEAD']).stdout.trim();
  must(root, 'git', [
    'commit',
    '--allow-empty',
    '-m',
    'ci(quality): Add gates',
  ]);
  const args = [cli, '--config', config, '--from', base, '--to', 'HEAD'];
  must(root, process.execPath, args);
  must(root, 'git', [
    'commit',
    '--allow-empty',
    '-m',
    'Invalid intermediate message',
  ]);
  must(root, 'git', [
    'commit',
    '--allow-empty',
    '-m',
    'ci(quality): Add another gate',
  ]);
  assert.equal(run(root, process.execPath, args).status, 1);
});

test('the installed commit-msg hook blocks an invalid commit', t => {
  const root = fixture(t);
  const before = must(root, 'git', ['rev-parse', 'HEAD']).stdout;
  const rejected = run(root, 'git', [
    'commit',
    '--allow-empty',
    '-m',
    'Missing conventional format',
  ]);
  assert.notEqual(rejected.status, 0, rejected.stdout + rejected.stderr);
  assert.equal(must(root, 'git', ['rev-parse', 'HEAD']).stdout, before);
  const message = 'commit message.txt';
  write(root, message, 'ci(quality): Accept a valid commit\n');
  must(root, 'git', ['commit', '--allow-empty', '-F', message]);
  assert.notEqual(must(root, 'git', ['rev-parse', 'HEAD']).stdout, before);
  fs.unlinkSync(path.join(root, message));
});
