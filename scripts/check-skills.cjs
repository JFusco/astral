'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '..');
const CONNECTOR_SKILL = 'qa-operations-connector';

function hashSkillFolder(directory) {
  const files = [];

  function collect(current, prefix = '') {
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      const relativePath = prefix ? `${prefix}/${entry.name}` : entry.name;
      const fullPath = path.join(current, entry.name);
      if (
        entry.isDirectory() &&
        entry.name !== '.git' &&
        entry.name !== 'node_modules'
      ) {
        collect(fullPath, relativePath);
      } else if (entry.isFile()) {
        files.push({ relativePath, content: fs.readFileSync(fullPath) });
      }
    }
  }

  collect(directory);
  files.sort((a, b) => a.relativePath.localeCompare(b.relativePath));

  const hash = crypto.createHash('sha256');
  for (const file of files) {
    hash.update(file.relativePath);
    hash.update(file.content);
  }
  return hash.digest('hex');
}

function checkSkills(root = ROOT) {
  const errors = [];
  const lock = JSON.parse(
    fs.readFileSync(path.join(root, 'skills-lock.json'), 'utf8'),
  );
  if (lock.version !== 1 || !lock.skills || typeof lock.skills !== 'object') {
    return ['skills-lock.json has an unsupported shape'];
  }

  const skillsRoot = path.join(root, '.agents', 'skills');
  for (const [name, entry] of Object.entries(lock.skills)) {
    const directory = path.join(skillsRoot, name);
    if (!fs.existsSync(path.join(directory, 'SKILL.md'))) {
      errors.push(`${name}: locked skill folder or SKILL.md is missing`);
      continue;
    }
    const actual = hashSkillFolder(directory);
    if (actual !== entry.computedHash) {
      errors.push(
        `${name}: lock hash ${entry.computedHash} differs from folder hash ${actual}`,
      );
    }
  }

  for (const skill of fs.readdirSync(skillsRoot, { withFileTypes: true })) {
    if (!skill.isDirectory() || skill.name === CONNECTOR_SKILL) continue;
    const link = path.join(root, '.claude', 'skills', skill.name);
    const expectedTarget = `../../.agents/skills/${skill.name}`;
    try {
      if (fs.readlinkSync(link) !== expectedTarget || !fs.existsSync(link)) {
        errors.push(
          `${skill.name}: Claude skill link does not resolve to ${expectedTarget}`,
        );
      }
    } catch {
      errors.push(`${skill.name}: Claude skill link is missing`);
    }
  }
  return errors;
}

if (require.main === module) {
  const errors = checkSkills();
  if (errors.length) {
    for (const error of errors) process.stderr.write(`${error}\n`);
    process.exitCode = 1;
  } else {
    process.stdout.write('Skill folder hashes and Claude links match.\n');
  }
}

module.exports = { checkSkills, hashSkillFolder };
