#!/usr/bin/env node
// lint-files.mjs — multi-file runner around lint-core.mjs.
//
// lint-core.mjs lints a SINGLE file (its 2nd positional arg is the contract dir,
// not a second file). pre-commit and CI pass many files at once, so this wrapper
// spawns lint-core once per file and fails if any file fails. Single source of
// truth stays in lint-core.mjs — this only loops.
//
// Usage:
//   node design/lint/lint-files.mjs <file>...   explicit files (pre-commit path)
//   node design/lint/lint-files.mjs             no args → walk _defaultRoots from .lintrc.json
//
// Contract dir resolves automatically to design/ at the CWD (repo root), so run
// from the repo root — which is where both pre-commit and the CI job execute.

import { spawnSync } from 'node:child_process';
import { readFileSync, readdirSync, existsSync, statSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve, join, extname } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const core = resolve(here, 'lint-core.mjs');

function walk(dir, exts, out) {
  if (!existsSync(dir)) return out;
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    const st = statSync(p);
    if (st.isDirectory()) walk(p, exts, out);
    else if (exts.has(extname(name))) out.push(p);
  }
  return out;
}

const rc = JSON.parse(readFileSync(resolve(here, '.lintrc.json'), 'utf8'));
const exclude = rc._exclude || [];
// A file is excluded if any exclude entry is a substring of its POSIX-normalized path
// (entries are repo-relative prefixes: a dir like "templates/wireframes/" or a file).
const isExcluded = (p) => {
  const norm = p.replace(/\\/g, '/');
  return exclude.some((e) => norm.includes(e));
};

let files = process.argv.slice(2);
if (files.length === 0) {
  // No args → lint the default roots declared in .lintrc.json (utility-first:
  // the Django templates are where the utility classes / tokens actually live).
  const roots = rc._defaultRoots || ['templates'];
  const exts = new Set(['.html']);
  files = roots.flatMap((r) => walk(resolve(process.cwd(), r), exts, []));
}
files = files.filter((f) => !isExcluded(f));

let failed = 0;
for (const f of files) {
  const r = spawnSync(process.execPath, [core, f], { stdio: 'inherit' });
  if (r.status !== 0) failed++;
}

if (failed) {
  console.error(`\n[lint-files] ${failed} file(s) failed design lint — blocked.`);
  process.exit(1);
}
console.log(`[lint-files] ${files.length} file(s) clean — OK.`);
process.exit(0);
