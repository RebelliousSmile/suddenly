---
name: agentic-readiness-framework
description: Evaluation grid for AI-compatible project architecture. Use when auditing an existing project or framing a new one for agentic development.
---

# Agentic Readiness Framework

> Based on "AI Is Forcing Us To Write Good Code" — Logic.inc (Dec. 2025)
> Purpose: evaluate or frame a project's technology choices and practices
> against their compatibility with an effective agentic workflow.

---

## How to use this document

**For an existing project (audit):** go through the tables column by column.
Each "❌ signal" is a question to ask: *why was this choice made, and what is the cost of fixing it?*
The "Prioritization" section at the end tells you in which order to act.

**For a new project (framing):** use the "Recommended" columns as a starting point.
Document any assumed deviations in the project's `CLAUDE.md` with their justification.

**Reading rule:** a single isolated ❌ signal is manageable. Multiple ❌ signals in the same axis
mean the agent will work in a degraded environment — errors will be more frequent, corrections
more costly, and human supervision more necessary.

---

## Core principle

AI agents do not improve a bad codebase — they amplify its flaws.
An agent in a well-structured project converges toward the right solution.
The same agent in a poorly structured project propagates bad patterns at scale.

Every decision below answers a single question:
**does this choice reduce or increase the decision space left to the agent?**

---

## The 4 foundational principles

### 1. Tests: 100% coverage, fast suite

100% coverage is not a quality target — it is an agent control mechanism.
At 100%, any uncovered line necessarily comes from what the agent just wrote,
making the coverage report an unambiguous todo list.
Below that, the agent makes subjective choices about what "deserves" to be tested,
which introduces non-determinism into its workflow.

**Important limit:** coverage measures *execution*, not *correctness*. 100% coverage
with weak assertions is a false ceiling — the agent can still introduce wrong behavior
in already-covered lines. Coverage is necessary but not sufficient; it must be paired
with meaningful assertions and clear test intent.

Speed is equally critical: the agent must run tests after every modification.
A slow suite stretches the feedback loop and discourages frequent checks.
Logic.inc runs 10,000+ assertions in under a minute by caching third-party API calls
via their open source library `fast-forward`.

**Signals of a compatible project:**
- Coverage enforced at 100% in CI on modified files
- Unit suite fast enough that the agent runs it after every change (target: < 60s — adjust based on project size and parallelism)
- Unit tests with no dependency on DB or network

**Warning signals:**
- Coverage threshold < 80% or not enforced
- Tests coupled to live APIs or dev database
- Suite slow enough that running it after every change is impractical

---

### 2. Typing: eliminate invalid states at compile time

The compiler is the agent's first guardrail. Every invalid state eliminated statically
is a class of errors the agent can no longer introduce.

This is not just a "TypeScript vs PHP" question — it is about what the type system can
*structurally forbid*. TypeScript with `strict: true` and semantic types (`OrderId`, `QrPayload`)
makes it impossible to confuse two business identifiers: the compiler rejects the code before
the agent can even submit it. PHPStan level 8 fills the same role in PHP.

Without strict typing, the agent must infer constraints from narrative context —
a source of silent errors that tests alone cannot intercept.

**Signals of a compatible project:**
- TypeScript `strict: true` + `noUncheckedIndexedAccess`, zero errors in CI
- PHPStan level 8, zero errors in CI
- IDs and business values typed with explicit names, not bare primitives
- API contract defined in OpenAPI, client types auto-generated (when applicable)
- ORM with types inferred from the DB schema (when applicable)

**Warning signals:**
- `any` in TypeScript, `mixed` in PHP without justification
- IDs passed as bare `string` or `int` everywhere
- No API spec, types written by hand or absent
- Raw SQL queries without typed results

---

### 3. Tooling: automate every guardrail

Every manual check is a decision delegated back to the agent.
Lint, format, typecheck, tests: everything must run automatically,
without the agent having to think about it. A single command must verify everything.

**Signals of a compatible project:**
- `npm run check` or `composer check` runs typecheck + lint + tests + coverage
- Lint and format applied in pre-commit hook AND in CI
- CI blocks merge if any criterion fails

**Warning signals:**
- Tooling configured but not automatically enforced
- Separate undocumented commands
- Formatting left to the developer's discretion

---

### 4. Agent context: give the agent a precise working environment

The quality of context given to the agent is itself a guardrail.
A well-written `CLAUDE.md` with commands, domain rules, and architectural constraints
directly reduces the agent's decision space — it is often the highest-ROI investment
relative to its cost, and the most overlooked.

Without explicit context, the agent infers conventions from the codebase.
If those conventions are inconsistent or implicit, the agent will propagate the noise.

**Signals of a compatible project:**
- `CLAUDE.md` documents the single `check` command, project conventions, and key constraints
- Architectural boundaries are explicit: which modules the agent must not modify alone, which patterns to follow
- Domain rules are written as rules files (e.g. `.claude/rules/`) scoped to relevant paths

**Warning signals:**
- No `CLAUDE.md`, or one that only describes the project without specifying agent behavior
- Conventions exist only in developers' heads or in README prose
- No rules file to constrain agent decisions at the module level

---

## Decision tables by technology

### Language and framework

| Context | Recommended | Why it's agentic |
|---------|------------|-----------------|
| New backend project | TypeScript / Node.js or Bun | Types inferred at every layer (parameters, returns, DB, API). Unified tooling ecosystem: Biome, Vitest, openapi-typescript work together without configuration friction |
| Frontend or fullstack app | TypeScript strict + framework static analysis | End-to-end types via OpenAPI. Template-level type checking (vue-tsc for Vue/Nuxt, svelte-check for SvelteKit, tsc for Next.js) catches errors beyond TypeScript files. The choice of framework matters less than enabling strict typing and template checking |
| Edge deployment | Drizzle (any framework) | Drizzle does not depend on a full Node runtime — native TypeScript schema, compatible with Vercel/Cloudflare without adaptation |
| PrestaShop module | PHP 8.x + PHPStan level 8 | Non-negotiable client constraint. PHPStan level 8 = functional equivalent of TypeScript strict |
| Script / internal tool | Python 3.10+ + Mypy strict | Windows/Linux portability, rich AI SDK ecosystem. **Reserve for tools, not product code** |
| Reusable CLI tool | Rust | The Rust compiler eliminates invalid states at compile time by construction. **Important tension:** the agentic tooling ecosystem around Rust is less mature than TypeScript — the agent will make more errors on advanced Rust. Reserve for cases where performance or runtime-free deployment is non-negotiable |
| Client-side processing (WASM) | Rust + wasm-pack | Rust compiles to WebAssembly with TypeScript bindings auto-generated by `wasm-pack`. **Same tension as above:** only relevant when client-side processing is justified (encryption before upload, large file imports, complex real-time business rule validation) |

> **On Python:** Logic.inc's argument ("don't use Python, even with annotations") targets product code.
> Python remains the best choice for tooling scripts, AI SDK integrations and portable CLI tools —
> domains where its portability and ecosystem are decisive.
> With Mypy strict + Ruff + Pydantic, guardrails are sufficient for this scope.

> **On WASM:** WASM moves processing from the server to the browser without replacing it.
> Persistence and critical security rules stay server-side — always.
> Relevant cases: CSV/Excel import > 10,000 rows, encryption of sensitive data before upload,
> complex real-time business rule validation, QR codes with sensitive data.

---

### Tech selection — weighted alternatives principle

For each architectural component, the agent scores 3 candidate technologies across two axes,
then derives a weighted recommendation.

#### Scoring axes

| Axis | Scale | Definition |
|------|-------|------------|
| **LLM coverage** | 1–3 | Representation in training data, API stability, ecosystem maturity |
| **Human supervision** | 1–3 | Inferred capacity of the human to review and correct agent output |

**Combined score** = LLM × 0.6 + Supervision × 0.4 *(rounded to 1 decimal)*

#### Human supervision inference rules

| Source | Score |
|--------|-------|
| Technology already present in the existing codebase | 3 — mastered |
| Mentioned in `CLAUDE.md` but not used in code | 2 — familiar |
| Absent from all project context | 1 — unknown |

> **Greenfield projects:** if no existing code is present, the agent must ask the human about
> stack preferences before generating alternatives and document the answers in the audit report.

#### LLM floor rule

If the recommended option has an LLM score ≥ 1 point below the best available alternative,
the agent must signal a **deviation**: document the component, the LLM gap, the justification,
and the estimated agentic impact. The human must explicitly confirm the deviation at validation.

#### Coherence pass

After all component recommendations are established, the agent verifies:
- No inter-component friction (e.g. ORM incompatible with DB, CI tool not supporting the test runner)
- Stack is consistent with the functional and technical constraints identified from the project

---

### Tests

| Need | Recommended | Alternative | ❌ Signal |
|------|------------|-------------|----------|
| JS/TS tests | Vitest | Jest | No tests, or no coverage measurement |
| PHP tests | PHPUnit | Pest | Manual tests only |
| Third-party API call caching | fast-forward (Logic.inc) | MSW | Real network calls in unit tests |
| JS/TS coverage | v8 native Vitest | Istanbul | Threshold < 100% or not enforced in CI |
| PHP coverage | pcov | Xdebug | Coverage not measured |

```typescript
// vitest.config.ts — enforced thresholds
export default defineConfig({
  test: {
    coverage: {
      provider: 'v8',
      thresholds: { lines: 100, functions: 100, branches: 100 }
    }
  }
})
```

---

### Typing and code quality

| Need | Recommended | Alternative | ❌ Signal |
|------|------------|-------------|----------|
| TS static analysis | `vue-tsc --noEmit`, `svelte-check`, or `tsc --noEmit` in CI | tsc | `strict: false` or tolerated errors |
| PHP static analysis | PHPStan level 8 | Psalm | Level < 5 or absent |
| Python static analysis | Mypy strict | Pyright | No static analysis |
| JS/TS lint + format | Biome | ESLint + Prettier | No shared style, manual formatting |
| PHP lint + format | PHP-CS-Fixer | PHPCS | Inconsistent style between files |
| Python lint + format | Ruff | Flake8 + Black | No linter |
| Python data structures | Pydantic | dataclasses | Untyped `dict` everywhere |

---

### ORM and data access (TypeScript)

| Context | Recommended | Why |
|---------|------------|-----|
| Project handed off to others | **Prisma** | Excellent DX, large community, extensive documentation — reduces the agent's need to infer usage patterns from sparse examples |
| Nuxt / Edge app | **Drizzle** | Native TypeScript schema (no external `.prisma` file), compatible with Cloudflare Workers and Vercel Edge without adaptation |
| Complex SQL queries | **Kysely** | Typed query builder closest to raw SQL. Full control over queries, types inferred from schema. Logic.inc's choice |
| Avoid | TypeORM | Fragile decorators, imprecise types on results, poor readability for an agent |

```typescript
// Prisma — expressive, good for teams
const orders = await prisma.order.findMany({
  where: { userId, status: 'PENDING' },
  include: { items: true }
})

// Drizzle — native TS schema, Edge-compatible
const orders = await db.select().from(ordersTable)
  .where(and(eq(ordersTable.userId, userId), eq(ordersTable.status, 'PENDING')))

// Kysely — explicit typed SQL (Logic.inc's choice)
const orders = await db.selectFrom('orders')
  .where('user_id', '=', userId)
  .where('status', '=', 'PENDING')
  .selectAll().execute()
```

---

### API and cross-layer contracts (OpenAPI)

*Applicable when the project owns and controls its backend API.*

| Need | Recommended | ❌ Signal |
|------|------------|----------|
| Spec generation from PHP | swagger-php | API types written by hand or absent |
| TS types from spec | openapi-typescript | `any` on fetch responses |
| Typed TS HTTP client | openapi-fetch | axios without types |
| Spec validation in CI | swagger-cli | Unvalidated spec, silent drift |
| Interactive documentation | @redocly/cli | No API documentation |
| Breaking change detection | @optic/cli | Breaking changes discovered in production |

**Two approaches depending on context:**
- **API-first** (new projects): write the spec before the code, generate stubs and types.
  The spec is the contract, the code is the implementation.
- **Code-first** (legacy PrestaShop): annotate existing code, generate spec from `swagger-php`
  annotations. Less pure, but applicable without a rewrite.

---

### CI/CD

A CI pipeline that does not block is **more dangerous than no CI at all**.
It creates a false sense of security: the agent believes its modifications are validated
when they are not. The value of a CI pipeline for an agentic workflow comes entirely from
its ability to reject — a permissive pipeline is just a status display with no consequence.

| Need | Recommended | ❌ Signal |
|------|------------|----------|
| Quality pipeline | GitHub Actions / GitLab CI | CI present but not blocking merge — worse than no CI |
| Typecheck | framework static analysis tool + PHPStan | Type errors ignored or unchecked in CI |
| Tests + coverage | Vitest + PHPUnit with enforced thresholds | Green CI without measured coverage or threshold at 0% |
| Lint | Biome + PHP-CS-Fixer in check mode (not fix) | Formatting unchecked — agent can submit poorly formatted code |
| API spec validation | swagger-cli (when applicable) | Spec modified without validation — silent drift between spec and implementation |

> **Important CI distinction:** the linter must run in `check` mode (not `--apply`)
> to block on errors, not silently fix them. A CI that auto-corrects hides problems
> instead of reporting them to the agent.
> In pre-commit hooks, auto-fix is appropriate — the developer sees the change before committing.

---

## Investment prioritization

If a project shows multiple ❌ signals, here is the recommended intervention order.

### Priority 1 — Low cost, immediate impact

Install Biome or Ruff with a pre-commit hook (< 1h).
Create or improve `CLAUDE.md`: document the single `check` command, key constraints, and domain rules (< 1h).
Configure coverage enforcement at 100% on **new files only** from day one — do not set a low global
threshold as a stepping stone, as an unenforced or low-threshold metric gives the agent no signal.

### Priority 2 — Medium cost, strong impact on feedback loop

Mock external API calls in unit tests to make the suite fast enough to run after every change.
Introduce an OpenAPI spec for the main endpoints (if the project owns its backend API).
Expand 100% coverage to existing files progressively, starting with pure business logic.

### Priority 3 — High cost, structural long-term impact

**PHPStan on a legacy project:** do not activate level 8 all at once — a legacy project
will immediately surface hundreds of errors that will block all work.
Recommended strategy:
1. Activate at level 1
2. Generate a baseline: `phpstan analyse --generate-baseline`
   (the baseline ignores existing errors without removing them)
3. Gradually increase the level (1 → 3 → 5 → 8), cleaning the baseline incrementally
4. The agent can handle baseline cleanup incrementally —
   exactly the kind of repetitive task where it excels

**TypeScript strict on an existing JS codebase:** same logic — activate `strict: true`
file by file via `// @ts-check` or migrating module by module, not in one global pass.

**ORM migration:** migrate to a typed ORM if raw SQL queries are numerous.
Start with new modules, not a global rewrite.

**Semantic types:** introduce TypeScript branded types and PHP Value Objects for business IDs
as a priority — this is the most efficient change relative to its cost,
and the agent can do it module by module without breaking the existing codebase.

---

## Branching and conflict management in multi-agent context

When multiple agents work in parallel on separate worktrees, the merge strategy becomes
a quality parameter in its own right. A merge conflict the agent must resolve without
sufficient context is a source of silent errors — it will choose a syntactically plausible
resolution that may be semantically incorrect.

**The multi-agent specific problem:** a human resolving a merge conflict understands the intent
of both branches. An agent resolving the same conflict only has access to the text of both
versions — it does not know the intent behind each modification if it is not documented
in the code or in the commits.

### Principles

**Short branches, frequent rebases.**
In multi-agent projects, a branch that lives more than 2-3 days accumulates divergences with `main`.
The greater the divergence, the more complex the conflict resolution and the higher
the agent's error risk. Daily rebase on `main` as the default rule.

**Atomic commits with explicit messages.**
One commit = one intent. A clear commit message is context the agent can read to understand
*why* a modification was made, not just what it does.
In case of conflict, an agent with explicit commit messages will choose better than without.

**Feature scoping to minimize overlaps.**
Before launching multiple agents in parallel, identify files likely to be modified by
multiple branches simultaneously. Assign scopes to minimize intersections —
ideally, two agents working in parallel do not touch the same files.

### Recommended strategy

| Context | Strategy | Why |
|---------|---------|-----|
| Independent features in parallel | Separate branches + frequent rebase on `main` | Minimizes divergence, conflicts resolved early when still simple |
| Feature with dependent sub-tasks | Parent feature branch + child sub-branches | Agent works on a sub-branch, merges into parent, never directly into `main` |
| Urgent hotfix during agentic work | Hotfix branch from `main`, immediate rebase on all active branches | Prevents the hotfix from creating conflicts discovered late |
| Merge conflict detected | Agent stops, human resolves, then resumes | Never let the agent resolve alone a conflict on semantically critical files |

### Rule to encode in CLAUDE.md

```markdown
## Branching
- Rebase on `main` before starting any work session
- Atomic commits — one commit = one intent, explicit message
- Never resolve a merge conflict on core business logic files without human validation
  — report the conflict and stop
```

---

*Sources: [AI Is Forcing Us To Write Good Code](https://bits.logic.inc/p/ai-is-forcing-us-to-write-good-code) · [Engineering Is Becoming Beekeeping](https://bits.logic.inc/p/engineering-is-becoming-beekeeping) · [fast-forward](https://github.com/with-logic/fast-forward)*
