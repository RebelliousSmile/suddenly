#!/usr/bin/env node
// lint-core.mjs — portable design-system linter
// Derives valid sets from tokens.json + components.json at runtime; no hard-coded values.
// Usage: node lint-core.mjs <html-file> [<contract-dir>] [--strict] [--report-unused]
// Exit 0 = clean (warnings only), Exit 1 = errors found, Exit 2 = usage error
//
// Reused as the freeze-time reconciliation oracle (Part 5, A10): `adjust/02-freeze.md
// § Étape 2bis — Réconciliation avec le code réel (retrofit)` invokes this exact script,
// unmodified per-file, against every file of the mode-derived glob (`**/*.{html,vue,jsx,tsx}`)
// BEFORE a manifest is frozen — so "code vs contract" has a single scanning implementation
// that never drifts between the freeze gate and the ongoing `enforce/03-lint-instances` gate.
// Rule 1 (bem) and Rule 4 (utility-first) already carry the freeze step's **code → manifeste**
// direction (a class/utility used in real code but absent from the manifest = ERROR here =
// blocking at freeze). The **manifeste → code** direction (a declared entry never used in real
// code) is not an error condition of the baseline lint — see `--report-unused` below.

import { readFileSync, existsSync } from 'fs';
import { resolve, dirname } from 'path';

const rawArgs = process.argv.slice(2);
const strict = rawArgs.includes('--strict');
const reportUnused = rawArgs.includes('--report-unused');
const args = rawArgs.filter((a) => a !== '--strict' && a !== '--report-unused');
const [htmlFile, contractDirArg] = args;

if (!htmlFile) {
  console.error('Usage: node lint-core.mjs <html-file> [<contract-dir>] [--strict] [--report-unused]');
  process.exit(2);
}

const htmlPath = resolve(htmlFile);
const htmlDir = dirname(htmlPath);
const cwd = process.cwd();

// Resolve contract dir:
// 1) explicit CLI arg
// 2) same directory as the HTML file (fixture pattern)
// 3) design/ at CWD (production pattern)
function findContractDir() {
  if (contractDirArg) {
    const d = resolve(contractDirArg);
    if (existsSync(resolve(d, 'tokens.json')) && existsSync(resolve(d, 'components.json'))) return d;
    console.error(`Contract not found in provided dir: ${contractDirArg}`);
    process.exit(2);
  }
  if (existsSync(resolve(htmlDir, 'tokens.json')) && existsSync(resolve(htmlDir, 'components.json'))) {
    return htmlDir;
  }
  const designDir = resolve(cwd, 'design');
  if (existsSync(resolve(designDir, 'tokens.json')) && existsSync(resolve(designDir, 'components.json'))) {
    return designDir;
  }
  console.error(
    'Contract not found.\n' +
    '  Looked in: ' + htmlDir + '\n' +
    '  Looked in: ' + designDir + '\n' +
    '  Provide a contract dir as the second argument, or run from project root.'
  );
  process.exit(2);
}

const contractDir = findContractDir();
const tokens = JSON.parse(readFileSync(resolve(contractDir, 'tokens.json'), 'utf8'));
const manifest = JSON.parse(readFileSync(resolve(contractDir, 'components.json'), 'utf8'));
const html = readFileSync(htmlPath, 'utf8');

// Build valid class sets from manifest — no hard-coded values
const components = manifest.components || {};
const validClasses = new Set();
const knownBases = new Set();
const utilityPrefixes = manifest.$utilityPrefixes || [];

for (const comp of Object.values(components)) {
  validClasses.add(comp.base);
  knownBases.add(comp.base);
  for (const cls of Object.values(comp.elements || {})) validClasses.add(cls);
  for (const cls of Object.values(comp.modifiers || {})) validClasses.add(cls);
}

// Mode (A6): explicit `mode` field on the manifest wins. Otherwise infer from the BEM
// `components` map — no components declared means no BEM vocabulary exists to check, so the
// contract is treated as utility-first by default. This is the guard against finding #2 (the
// class-vocab rule firing "clean" vacuously — 0 hits — on a Tailwind/Vue/React codebase that
// never uses BEM classes at all).
const mode = manifest.mode || (Object.keys(components).length === 0 ? 'utility-first' : 'bem');

// Usage rules (A4/A5): additive `usage` block — coexists with the BEM `components` map, absent
// entirely on legacy BEM-only manifests (Rules 3/4 below are then simply inert, zero behaviour
// change). See adjust/references/manifest-schema.md § "Bloc usage" for the full shape.
const usage = manifest.usage || null;

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

// Forward-map each token path to the CSS custom property the generator emits
// (`--` + path with `.` → `-`). This direction is lossless; reversing var → path
// is ambiguous whenever a path segment already contains a hyphen (e.g. `text-muted`,
// `semantic-grimoire`), which produced false "unknown token" errors. Must mirror the
// generator rule in references/token-schema.md ("Flatten … `--<group>-<…>-<name>`, `.` → `-`").
//
// Themes (tokens.json § "Modes / themes"): a theme overlay re-declares the SAME
// `--var` name inside its own CSS selector block (`.dark`, `[data-theme="grimoire"]`,
// …) — never a suffixed name (A2 decision, 2026-07-05). Rule 2 below already matches
// `var(--x)` anywhere in the HTML regardless of which selector block declares `--x`
// in the generated CSS, so themed references need no code change here. The overlay
// only ever overrides a path that already exists in the base tree (schema invariant),
// so its var names are already covered by `tokenPaths` above — the top-level
// `themes` key itself is excluded from the flatten so no unreferenced synthetic
// path (e.g. `--themes-dark-color-semantic-background`) is added to `validVars`.
const validVars = new Set([...tokenPaths].map((p) => '--' + p.replace(/\./g, '-')));

const errors = [];
const warnings = [];

// Rule 1: class vocabulary check (ERROR) — BEM mode only (A6).
// Never runs on a utility-first contract: a Tailwind/Vue/React codebase has no BEM classes to
// match against `components`, so running this rule there is not merely useless but actively
// misleading (a green "0 errors" that looks like a passing check but never checked anything —
// finding #2). In utility-first mode, Rules 3/4 below carry the real enforcement instead.
if (mode !== 'utility-first') {
  // Only flags classes whose block part is a known component base — skips utility classes.
  // Matches literal `class="…"` (HTML/Vue/Svelte/Astro) and `className="…"` (JSX/TSX).
  // Static string literals only — dynamic bindings (`:class`, `{expr}`) are an accepted gap,
  // documented at sc-js:design-bridge / sc-php:design-bridge.
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
      warnings.push(`BEM-shaped class "${cls}" has no declared block "${blockPart}" — typo, or add "${blockPart}" to components.json / $utilityPrefixes`);
    }
  }
}

// Rule 2: CSS custom property reference check (ERROR)
// Catches var(--token-name) references to non-existent tokens.
for (const match of html.matchAll(/var\((--[\w-]+)\)/g)) {
  const varName = match[1];
  if (!validVars.has(varName)) {
    errors.push(`Unknown token reference var(${varName}) — no matching token in tokens.json`);
  }
}

// Rule 3: raw-hex forbidden (ERROR) — per `usage.rawHexForbidden` (A4).
// Inert unless the manifest declares a `usage` block (backward compatible with BEM-only
// contracts). Scoped to `style="…"` attribute values and inline `<style>…</style>` blocks —
// both are unambiguous CSS-value contexts, so the regex cannot false-positive on non-colour
// hex-shaped strings elsewhere in the markup (e.g. `href="#cafe"` anchors, hash-router paths).
// Adapter files generated by `diffuse` (tokens.css, theme.css) are never passed to lint-core as
// a lint target, so they are out of scope by construction — no path exclusion needed here.
if (usage && usage.rawHexForbidden) {
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

// Rule 4: allowed colour namespaces (ERROR) — per `usage.colorUtilityPrefixes` (A4), utility-first
// only. A Tailwind-style colour utility class (`bg-…`, `text-…`, `border-…`, `ring-…` — the exact
// prefix list is contract-declared, never hard-coded here) must resolve its colour segment to a
// top-level `color.*` group declared in tokens.json (e.g. `brand`, `neutral`, `semantic`) — never
// an out-of-contract palette name (Tailwind's default `red`/`blue`/… scales, for instance). This
// is the "class-vocab equivalent" for utility-first: closed vocabulary shifts from BEM class
// names to token-usage namespaces (adjust/references/manifest-schema.md § mode utility-first).
//
// These same prefixes are dual-purpose in real Tailwind usage: `text-lg`/`text-center` (size/align),
// `border-2`/`border-t` (width/side), `ring-2`/`ring-offset-2` (width/offset) share `text`/`border`/
// `ring` with genuine colour utilities (`text-red-500`, `border-neutral-200`). There is no closed-
// vocabulary signal to tell these apart other than the shape Tailwind's own colour scale always
// takes: `<prefix>-<namespace>-<shade>` with a 2-3 digit numeric shade. A bare single-segment class
// (`text-lg`, `border-2`, `ring-2`, `ring-offset-2` — "offset" has no numeric-shade sibling segment
// of its own) is therefore never treated as a colour reference; only `<name>-<NN|NNN>` triggers the
// namespace check. Known trade-off: unshaded bare colour keywords (`bg-white`, `border-black`) are
// no longer flagged even when undeclared — accepted to avoid blocking real utility-first codebases.
if (mode === 'utility-first' && usage && Array.isArray(usage.colorUtilityPrefixes) && usage.colorUtilityPrefixes.length) {
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

// Rule 5 (report-only, additive) — `--report-unused`: the manifeste → code direction (A10.3) of
// the freeze reconciliation step. Lists BEM manifest entries (`components.*.base`/`.elements`/
// `.modifiers`) with zero literal-string occurrence in this scanned file — a component/element/
// modifier declared in the just-written manifest that describes nothing yet built. Per A10.3 this
// direction is NEVER blocking: it is intentionally kept out of `errors`/`warnings` and never
// changes the exit code, even with the flag on — a manifest entry may legitimately be declared
// ahead of its first use. Default off; existing fixtures and invocations are unaffected either way.
//
// Reused across a whole glob, one invocation per file: `adjust/02-freeze.md § Étape 2bis` treats
// an entry as truly "unused in the project" only once every scanned file reports it unused — a
// single-file run only proves it is unused *in this file*.
//
// Heuristic limit (documented, not fixed): literal substring search only, no AST. A class name
// assembled dynamically at runtime (e.g. `` `btn--${variant}` ``, `:class="isPrimary && 'btn--primary'"`)
// never appears as a literal substring in the source text and is reported as a false "unused"
// positive — precisely why this direction stays warning/ledger-only and never blocks a freeze.
const unused = [];
if (reportUnused) {
  for (const comp of Object.values(components)) {
    const entries = [comp.base, ...Object.values(comp.elements || {}), ...Object.values(comp.modifiers || {})];
    for (const entry of entries) {
      if (entry && !html.includes(entry)) unused.push(entry);
    }
  }
}

// Report
const label = `[lint-core] ${htmlFile}`;
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
