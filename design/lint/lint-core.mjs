#!/usr/bin/env node
// lint-core.mjs — portable design-system linter
// Usage: node lint-core.mjs <markup-file> [--contract <dir>] [--strict] [--report-unused]
//        The contract directory is also accepted as a second positional, kept for the hooks
//        already installed; new invocations are written in the named form.
// Exit 0 = no error, 1 = at least one error, 2 = invocation/environment error,
//      3 = contract in the 1.x format, migration required.
//
// PERIMETER — what a green run does and does not establish.
//   Scans ONE markup file as text. Five rules, all derived at runtime from tokens.json +
//   components.json + policies.json; no hard-coded value, no AST, no CSS, no cross-file state.
//   In scope : literal class="…"/className="…", var(--…) references, raw hex inside
//              style="…" and inline <style>, shaded colour-utility namespaces.
//   Out of scope by construction : dynamic class bindings, stylesheets, platform theme
//              files, database-stored content, adapters, contrast ratios, ARIA roles,
//              applied background colours, any consistency between two files.
//   The class vocabulary is OPEN by default: a class whose block is not declared is treated
//   as a utility and ignored. It closes only under --strict, as a WARNING, and only on
//   BEM-shaped classes (containing __ or --) outside $utilityPrefixes.
//   Extending coverage belongs to a sc-<language>:design-bridge pivot, never to a rule here.
//   Every run states the contract it resolved and by which route; a guessed contract that is
//   not the only one of its tree is refused (exit 2) rather than picked.
//
// Also invoked, unmodified and per-file, by `adjust/02-freeze.md § Étape 2bis` over the
// mode-derived glob, so code-vs-contract has one scanning implementation. Rules 1 and 4 carry
// the blocking code → manifest direction; the manifest → code direction is --report-unused,
// which never affects the exit code.

import { readFileSync, existsSync, readdirSync } from 'fs';
import { resolve, dirname, relative } from 'path';
import { fileURLToPath } from 'url';

// The contract directory takes two forms. `--contract <dir>` is the named form every other tool
// of the plugin uses and the one to write from now on; the trailing positional is kept working
// so the pre-commit hooks already installed in consuming projects keep running unmodified.
// Giving both is only accepted when they designate the same directory — two different answers to
// one question is a decision the tool declines to make.
const rawArgs = process.argv.slice(2);
const strict = rawArgs.includes('--strict');
const reportUnused = rawArgs.includes('--report-unused');
// Machine-readable report for tools/run-gates.py. Under --json, stdout is either empty or
// exactly one JSON object: every diagnostic path already writes to stderr, so nothing else
// can reach it. Adds no rule and changes no exit code — it is a second rendering of the run.
const jsonOut = rawArgs.includes('--json');

const usageBanner =
  'Usage: node lint-core.mjs <markup-file> [--contract <dir>] [<contract-dir>] [--strict] [--report-unused] [--json]\n' +
  '  Scans ONE markup file as text. Five rules, one file at a time, no state between runs:\n' +
  '  class vocabulary (BEM mode), var(--…) references, raw hex in style="…"/<style>,\n' +
  '  colour-utility namespaces (utility-first mode), unused manifest entries (--report-unused).\n' +
  '  Not covered: CSS, dynamic bindings, stored content, contrast, ARIA, cross-file checks.\n' +
  '  Class vocabulary is open by default; --strict warns on BEM-shaped undeclared blocks.\n' +
  '  Rules outside this perimeter are declared in policies.json § usage.rules[] and realized\n' +
  '  elsewhere — see references/enforcement-registry.md.';

const positional = [];
let namedContract = null;
for (let i = 0; i < rawArgs.length; i++) {
  const a = rawArgs[i];
  if (a === '--strict' || a === '--report-unused' || a === '--json') continue;
  if (a === '--contract' || a.startsWith('--contract=')) {
    const value = a.startsWith('--contract=') ? a.slice('--contract='.length) : rawArgs[++i];
    if (!value || value.startsWith('--')) {
      console.error('--contract expects a directory as its value.\n' + usageBanner);
      process.exit(2);
    }
    namedContract = value;
    continue;
  }
  if (a.startsWith('--')) {
    console.error(`Unknown option: ${a}\n` + usageBanner);
    process.exit(2);
  }
  positional.push(a);
}

const [htmlFile, positionalContract] = positional;

if (!htmlFile) {
  console.error(usageBanner);
  process.exit(2);
}

if (namedContract && positionalContract && resolve(namedContract) !== resolve(positionalContract)) {
  console.error(
    `Conflicting contract directories: --contract ${namedContract} and positional ${positionalContract}.\n` +
    '  Pass one. The tool does not pick for you.'
  );
  process.exit(2);
}

const contractDirArg = namedContract || positionalContract;

const htmlPath = resolve(htmlFile);
const htmlDir = dirname(htmlPath);
const cwd = process.cwd();

// Resolve contract dir:
// 1) explicit CLI argument, named or positional — a decision, taken as given
// 2) same directory as the HTML file
// 3) design/ at CWD
// Paths 2 and 3 GUESS. A guessed root is accepted only when it holds the sole contract of
// its tree: a nested contract means the markup may belong to either, and the tool refuses to
// pick (exit 2, per the exit-code space "a required decision the tool refuses to guess").
// Without this the wrong contract lints silently — a BEM contract over utility-first markup
// leaves Rules 1/3/4 inert and returns 0, a green run proving nothing.
// `release.json` is the root of a 2.0 contract, and its absence is the 1.x signature. There is
// no 1.x read path: an unmigrated contract is diagnosed (exit 3), never parsed.
const isContractDir = (d) => existsSync(resolve(d, 'release.json'));
const is1xContractDir = (d) =>
  existsSync(resolve(d, 'tokens.json')) && existsSync(resolve(d, 'components.json'));

// The migration script is located, never assumed. The linter runs from two layouts: inside the
// plugin (adapters/, script three levels up in tools/) and copied into a consuming project
// (design/lint/, where 01-build-linter.md copies the script alongside it). A path built for one
// layout is a dead path in the other, and a dead path is the only remedy offered to a frozen 1.x
// contract. Nothing found: the message says where the script lives instead of naming a file that
// does not exist.
const selfDir = dirname(fileURLToPath(import.meta.url));
const migrateScript =
  ['migrate-contract.py', '../tools/migrate-contract.py', '../../../tools/migrate-contract.py']
    .map((p) => resolve(selfDir, p))
    .find(existsSync) || null;

function refuse1x(dir) {
  const how = migrateScript
    ? `  Migrate it, then re-run:\n` +
      `    python ${migrateScript} --contract ${dir} --dry-run\n` +
      `    python ${migrateScript} --contract ${dir}`
    : `  Migrate it with tools/migrate-contract.py, shipped by the design plugin, then re-run:\n` +
      `    python <design-plugin>/tools/migrate-contract.py --contract ${dir} --dry-run\n` +
      `    python <design-plugin>/tools/migrate-contract.py --contract ${dir}\n` +
      `  Not found next to this linter (${selfDir}); copy it there, or run adjust/03-migrate.`;
  console.error(`Contract in the 1.x format (no release.json): ${dir}\n${how}`);
  process.exit(3);
}

// Contract dirs strictly below `root`, whole tree, skipping dot-dirs and node_modules.
function nestedContractDirs(root) {
  const found = [];
  const walk = (dir) => {
    let entries;
    try { entries = readdirSync(dir, { withFileTypes: true }); } catch { return; }
    for (const e of entries) {
      if (!e.isDirectory() || e.name.startsWith('.') || e.name === 'node_modules') continue;
      const sub = resolve(dir, e.name);
      if (isContractDir(sub)) found.push(sub);
      walk(sub);
    }
  };
  walk(root);
  return found;
}

function refuseAmbiguous(root, nested, origin) {
  console.error(
    `Ambiguous contract: ${root} was guessed from ${origin}, but the tree also holds:\n` +
    nested.map((d) => '  ' + relative(root, d)).join('\n') + '\n' +
    '  Pass --contract <dir>. The tool does not pick for you.'
  );
  process.exit(2);
}

function findContractDir() {
  if (contractDirArg) {
    const d = resolve(contractDirArg);
    const origin = namedContract ? '--contract' : 'the positional argument';
    if (isContractDir(d)) return { dir: d, origin };
    if (is1xContractDir(d)) refuse1x(d);
    console.error(`Contract not found in provided dir: ${contractDirArg}`);
    process.exit(2);
  }
  if (isContractDir(htmlDir)) {
    const nested = nestedContractDirs(htmlDir);
    if (nested.length) refuseAmbiguous(htmlDir, nested, 'the markup directory');
    return { dir: htmlDir, origin: 'the markup directory' };
  }
  if (is1xContractDir(htmlDir)) refuse1x(htmlDir);
  const designDir = resolve(cwd, 'design');
  if (isContractDir(designDir)) {
    const nested = nestedContractDirs(designDir);
    if (nested.length) refuseAmbiguous(designDir, nested, 'design/ at the working directory');
    return { dir: designDir, origin: 'design/ at the working directory' };
  }
  if (is1xContractDir(designDir)) refuse1x(designDir);
  console.error(
    'Contract not found.\n' +
    '  Looked in: ' + htmlDir + '\n' +
    '  Looked in: ' + designDir + '\n' +
    '  Provide --contract <dir>, or run from project root.'
  );
  process.exit(2);
}

const { dir: contractDir, origin: contractOrigin } = findContractDir();

// Read the artifacts release.json declares. An artifact declared but absent, or unparseable, is
// an environment error (exit 2) — never a silent fallback: every rule below is derived from one
// of these files, and a missing file would leave rules inert and return a green run over nothing.
function readArtifact(name) {
  const path = resolve(contractDir, name);
  if (!existsSync(path)) {
    console.error(`Artifact declared by release.json but missing: ${path}`);
    process.exit(2);
  }
  try {
    return JSON.parse(readFileSync(path, 'utf8'));
  } catch (e) {
    console.error(`Unreadable artifact ${path}: ${e.message}`);
    process.exit(2);
  }
}

const release = readArtifact('release.json');
const declared = Object.keys(release.artifacts || {});
if (!declared.length) {
  console.error(`release.json declares no artifact: ${resolve(contractDir, 'release.json')}`);
  process.exit(2);
}
// The five rules derive from these three. An undeclared one is not a smaller contract, it is a
// disabled rule: components.json missing leaves Rule 1 with an empty vocabulary and every class
// valid, policies.json missing leaves Rules 3 and 4 inert, and the run still returns 0. Since
// release.json is hand-written at freeze, the case is reachable, so it is refused (exit 2).
// oracle.json is not required here: it is written only when the brief produces measure targets,
// and no rule below reads it.
const REQUIRED = ['tokens.json', 'components.json', 'policies.json'];
const undeclared = REQUIRED.filter((name) => !declared.includes(name));
if (undeclared.length) {
  console.error(
    `release.json declares no ${undeclared.join(', ')}: ${resolve(contractDir, 'release.json')}\n` +
    `  Declared: ${declared.join(', ') || '(none)'}\n` +
    '  The five lint rules derive from tokens.json, components.json and policies.json.\n' +
    '  Undeclared, they would go inert and the run would return 0 over nothing.'
  );
  process.exit(2);
}
// Presence and parseability are checked for every declared artifact, including those no rule
// below consumes (oracle.json is read by the measure adapter, not by these five rules).
const artifacts = Object.fromEntries(declared.map((name) => [name, readArtifact(name)]));
const tokens = artifacts['tokens.json'] || {};
const manifest = artifacts['components.json'] || {};
const policies = artifacts['policies.json'] || {};
// An absent or unreadable markup file is an invocation error (exit 2), not a violation: left
// unguarded, the throw exits 1 and a mistyped path reads in CI as a failed lint on real markup.
let html;
try {
  html = readFileSync(htmlPath, 'utf8');
} catch (e) {
  console.error(`Unreadable markup file ${htmlPath}: ${e.message}`);
  process.exit(2);
}

// Build valid class sets from the component anatomy — no hard-coded values
const components = manifest.components || {};
const validClasses = new Set();
const knownBases = new Set();
const utilityPrefixes = policies.$utilityPrefixes || [];

// Shape refusal. An artifact whose shape does not match its declaration is an environment error
// (exit 2), never a violation and never a pass. The sites below are taken on faith otherwise, and
// the failure is silent rather than loud: a component that is a string leaves `comp.base`
// undefined, `knownBases` holds `undefined`, no markup class ever matches a declared block, and
// every class is treated as a utility — a green run over a contract that declares nothing.
// Validation happens HERE, at derivation, not at each use site: a malformed contract is malformed
// independently of the markup scanned, and `$utilityPrefixes` is only read under --strict on a
// BEM-shaped undeclared class, which would make the refusal depend on the file passed.
function shapeOf(v) {
  if (v === null) return 'null';
  if (v === undefined) return 'absent';
  if (Array.isArray(v)) return 'an array';
  const t = typeof v;
  return /^[aeiou]/.test(t) ? `an ${t}` : `a ${t}`;
}

function refuseShape(artifact, fieldPath, expected, got) {
  // The value is shown, not just its type: on `"btn"` or `42` the type alone leaves the reader
  // hunting for which entry is wrong. Truncated, because a malformed field is often a whole
  // object pasted at the wrong depth, and an untruncated dump buries the message it carries.
  const seen = JSON.stringify(got) ?? String(got);
  const shown = seen.length > 120 ? seen.slice(0, 117) + '...' : seen;
  console.error(
    `${artifact} § ${fieldPath} is ${shapeOf(got)}, expected ${expected}: ${resolve(contractDir, artifact)}\n` +
    `  Got: ${shown}\n` +
    '  The lint rules derive from this field. Read as is, the run would return a verdict about\n' +
    '  a vocabulary the contract does not declare. Fix the artifact, or re-run its generator.'
  );
  process.exit(2);
}

const isPlainObject = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);

if (manifest.components !== undefined && !isPlainObject(manifest.components)) {
  refuseShape('components.json', 'components', 'an object', manifest.components);
}
for (const [name, comp] of Object.entries(components)) {
  if (!isPlainObject(comp)) refuseShape('components.json', `components.${name}`, 'an object', comp);
  if (typeof comp.base !== 'string' || !comp.base) {
    refuseShape('components.json', `components.${name}.base`, 'a non-empty string', comp.base);
  }
  for (const sub of ['elements', 'modifiers']) {
    if (comp[sub] === undefined) continue;
    if (!isPlainObject(comp[sub])) {
      refuseShape('components.json', `components.${name}.${sub}`, 'an object', comp[sub]);
    }
    for (const [key, cls] of Object.entries(comp[sub])) {
      if (typeof cls !== 'string' || !cls) {
        refuseShape('components.json', `components.${name}.${sub}.${key}`, 'a non-empty string', cls);
      }
    }
  }
}
if (policies.$utilityPrefixes !== undefined) {
  if (!Array.isArray(policies.$utilityPrefixes)) {
    refuseShape('policies.json', '$utilityPrefixes', 'an array of strings', policies.$utilityPrefixes);
  }
  policies.$utilityPrefixes.forEach((p, i) => {
    if (typeof p !== 'string') {
      refuseShape('policies.json', `$utilityPrefixes[${i}]`, 'a string', p);
    }
  });
}

for (const comp of Object.values(components)) {
  validClasses.add(comp.base);
  knownBases.add(comp.base);
  for (const cls of Object.values(comp.elements || {})) validClasses.add(cls);
  for (const cls of Object.values(comp.modifiers || {})) validClasses.add(cls);
}

// Mode is declared, never inferred. Inferring it from an empty component set turned an
// unwritten contract into a green utility-first run; a 2.0 contract always carries it.
const mode = policies.mode;
if (mode !== 'bem' && mode !== 'utility-first') {
  console.error(
    `policies.json declares no usable mode (${JSON.stringify(mode)}): ${resolve(contractDir, 'policies.json')}\n` +
    '  Expected "bem" or "utility-first". The tool does not infer it.'
  );
  process.exit(2);
}

// Additive `usage` block; absent on BEM-only contracts, which leaves Rules 3/4 inert.
// Shape: references/contract-schema.md § policies.json.
const usage = policies.usage || null;

// Flatten token paths from tokens.json — no hard-coded paths
function flattenTokenPaths(obj, prefix) {
  const paths = new Set();
  for (const [k, v] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === 'object' && '$value' in v) {
      paths.add(path);
    } else if (v && typeof v === 'object') {
      for (const p of flattenTokenPaths(v, path)) paths.add(p);
    }
  }
  return paths;
}

const { themes: _themes, ...baseTokens } = tokens;
const tokenPaths = flattenTokenPaths(baseTokens, '');

// Forward-map each token path to the CSS custom property the generator emits: `--` + path,
// `.` → `-`. Forward only — reversing var → path is ambiguous when a segment already contains
// a hyphen. Must mirror references/token-schema.md § Adapter: design/adapters/tokens.css.
// A theme overlay re-declares the SAME var name in its own selector block, and may only
// override a path already present in the base tree, so `themes` is excluded from the flatten
// and themed references need no handling here.
const validVars = new Set([...tokenPaths].map((p) => '--' + p.replace(/\./g, '-')));

const errors = [];
const warnings = [];
// Which of the five rules actually ran, marked at the rule site so the list cannot drift from
// the guards. A rule left inert by `mode` or by an absent `usage` block is absent here: a green
// run says nothing about a rule that never executed, and the runner must be able to see that.
const realized = [];

// Rule 1: class vocabulary (ERROR) — BEM mode only; Rules 3/4 carry utility-first instead.
// Flags only classes whose block part is a declared base. Literal `class="…"`/`className="…"`
// only — dynamic bindings are an accepted gap, covered by the sc-<language>:design-bridge pivot.
if (mode !== 'utility-first') {
  realized.push('class-vocabulary');
  for (const match of html.matchAll(/class(?:Name)?\s*=\s*["']([^"']+)["']/g)) {
    for (const cls of match[1].trim().split(/\s+/)) {
      if (!cls) continue;
      const blockPart = cls.split('__')[0].split('--')[0];
      if (knownBases.has(blockPart)) {
        if (!validClasses.has(cls)) {
          errors.push(`Unknown design-system class "${cls}" (block "${blockPart}" is declared but this element/modifier is not)`);
        }
        continue;
      }
      // blockPart not declared — utility class, UNLESS --strict and it's BEM-shaped
      // (contains __ or --), which signals a typo'd or undeclared component base
      // rather than a genuine utility class (e.g. "heor__title", "crad--featured").
      if (!strict) continue;
      const isBemShaped = cls.includes('__') || cls.includes('--');
      if (!isBemShaped) continue;
      if (utilityPrefixes.some((p) => cls.startsWith(p))) continue;
      warnings.push(`BEM-shaped class "${cls}" has no declared block "${blockPart}" — typo, or add "${blockPart}" to components.json, or its prefix to policies.json § $utilityPrefixes`);
    }
  }
}

// Rule 2: CSS custom property reference check (ERROR)
// Catches var(--token-name) references to non-existent tokens.
realized.push('token-reference');
for (const match of html.matchAll(/var\((--[\w-]+)\)/g)) {
  const varName = match[1];
  if (!validVars.has(varName)) {
    errors.push(`Unknown token reference var(${varName}) — no matching token in tokens.json`);
  }
}

// Rule 3: raw hex (ERROR) — gated on `usage.rawHexForbidden`, inert without a `usage` block.
// Scoped to `style="…"` and inline `<style>` only: both are unambiguous CSS-value contexts, so
// hex-shaped strings elsewhere (`href="#cafe"`, hash routes) cannot false-positive. Generated
// adapters are never lint targets, so they need no path exclusion.
if (usage && usage.rawHexForbidden) {
  realized.push('raw-hex');
  const hexRe = /#[0-9a-fA-F]{3,8}\b/g;
  for (const match of html.matchAll(/style\s*=\s*["']([^"']*)["']/g)) {
    for (const hex of match[1].matchAll(hexRe)) {
      errors.push(`Raw hex colour "${hex[0]}" in style="…" is forbidden by usage.rawHexForbidden — use a design token (var(--…)) instead`);
    }
  }
  for (const match of html.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/g)) {
    for (const hex of match[1].matchAll(hexRe)) {
      errors.push(`Raw hex colour "${hex[0]}" in <style> block is forbidden by usage.rawHexForbidden — use a design token (var(--…)) instead`);
    }
  }
}

// Rule 4: colour-utility namespaces (ERROR) — gated on `usage.colorUtilityPrefixes`, utility-first
// only. The colour segment of a utility class must resolve to a top-level `color.*` group of
// tokens.json; prefixes are contract-declared, never hard-coded. This is the utility-first
// counterpart of Rule 1: the closed vocabulary is namespaces, not class names.
// Shape constraint: those prefixes are dual-purpose (`text-lg`, `border-2`, `ring-offset-2` are
// not colours), and only `<prefix>-<namespace>-<2-3 digit shade>` is treated as a colour
// reference. Trade-off: unshaded keywords (`bg-white`) escape the check.
if (mode === 'utility-first' && usage && Array.isArray(usage.colorUtilityPrefixes) && usage.colorUtilityPrefixes.length) {
  realized.push('colour-namespace');
  const colorNamespaces = new Set(Object.keys(baseTokens.color || {}));
  const escaped = usage.colorUtilityPrefixes.map((p) => p.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  const classRe = new RegExp(`^(?:${escaped.join('|')})-(.+)$`);
  const shadedRe = /^([a-z][a-z0-9]*)-(\d{2,3})$/;
  for (const match of html.matchAll(/class(?:Name)?\s*=\s*["']([^"']+)["']/g)) {
    for (const cls of match[1].trim().split(/\s+/)) {
      if (!cls) continue;
      const m = classRe.exec(cls);
      if (!m) continue;
      const shaded = shadedRe.exec(m[1]);
      if (!shaded) continue;
      const namespace = shaded[1];
      if (!colorNamespaces.has(namespace)) {
        errors.push(`Colour utility class "${cls}" uses namespace "${namespace}" not declared under tokens.json § color.* (allowed: ${[...colorNamespaces].join(', ') || '(none declared)'})`);
      }
    }
  }
}

// Rule 5: `--report-unused` (REPORT-ONLY) — the manifest → code direction. Lists manifest entries
// with no literal occurrence in this file. Deliberately outside `errors`/`warnings`: it never
// changes the exit code, since an entry may be declared ahead of its first use.
// A single run only proves "unused in this file"; `adjust/02-freeze.md § Étape 2bis` concludes
// "unused in the project" only when every file of the glob reports it.
// Limit: literal substring search, no AST — a dynamically assembled class name is a false
// positive, which is why this direction never blocks.
const unused = [];
if (reportUnused) {
  realized.push('unused-declaration');
  for (const comp of Object.values(components)) {
    const entries = [comp.base, ...Object.values(comp.elements || {}), ...Object.values(comp.modifiers || {})];
    for (const entry of entries) {
      if (entry && !html.includes(entry)) unused.push(entry);
    }
  }
}

// Report. The resolved contract is stated on every run, pass or fail: a verdict is only
// meaningful against a named contract, and a reader must never have to infer which one.
const label = `[lint-core] ${htmlFile}`;

if (jsonOut) {
  process.stdout.write(JSON.stringify({
    tool: 'lint-core',
    file: htmlFile,
    contract: contractDir,
    contractOrigin,
    mode,
    strict,
    realized,
    errors,
    warnings,
    unused,
    exit: errors.length ? 1 : 0,
  }) + '\n');
  process.exit(errors.length ? 1 : 0);
}

console.log(`  CONTRACT ${contractDir} (${contractOrigin}), mode ${mode}`);
for (const w of warnings) console.warn(`  WARN  ${w}`);
for (const e of errors) console.error(`  ERROR ${e}`);
for (const u of unused) console.log(`  UNUSED ${u} — declared in manifest, no literal occurrence in ${htmlFile} (report-only, never blocking)`);

if (errors.length) {
  console.error(`${label}: ${errors.length} error(s), ${warnings.length} warning(s) — FAIL`);
  process.exit(1);
} else {
  console.log(`${label}: ${warnings.length} warning(s)${reportUnused ? `, ${unused.length} unused (report-only)` : ''} — OK`);
  process.exit(0);
}
