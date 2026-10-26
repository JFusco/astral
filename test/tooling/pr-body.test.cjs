'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const {
  REQUIRED_CHECKS,
  validatePullRequestBody,
} = require('../../scripts/validate_pr_body.cjs');

function validBody() {
  return `## Summary

Standardize deterministic Git delivery for review.

## Linked issue

Closes #123

## Changes

- Add the canonical pull request contract.

## Verification

- npm run verify:ci passed locally.

## Risk and rollback

- Risk: Existing pull requests must adopt the required structure.
- Rollback: Revert the delivery-tooling commit.

## Checklist

${REQUIRED_CHECKS.map(item => `- [x] ${item}`).join('\n')}
`;
}

test('the canonical pull request body passes', () => {
  assert.deepEqual(validatePullRequestBody(validBody()), []);
});

test('incomplete pull request bodies fail', () => {
  const body = validBody()
    .replace('Closes #123', 'Related #123')
    .replace(
      '- Risk: Existing pull requests must adopt the required structure.',
      '- Risk: <!-- placeholder -->',
    )
    .replace(`- [x] ${REQUIRED_CHECKS[0]}`, `- [ ] ${REQUIRED_CHECKS[0]}`);
  const errors = validatePullRequestBody(body);
  assert.ok(errors.some(error => error.startsWith('Linked issue must')));
  assert.ok(errors.some(error => error.includes('nonempty `Risk:`')));
  assert.ok(errors.some(error => error.includes(REQUIRED_CHECKS[0])));
});
