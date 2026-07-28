#!/usr/bin/env python3
"""run-gates.py - aggregation runner for the enforcement of one contract.

Routes, never evaluates. Every rule is realized by someone else: the markup rules by
`skills/enforce/adapters/lint-core.mjs`, the others by a `sc-<language>:design-bridge`
pivot that writes back a report. This runner reads the contract, invokes the realizers it
can invoke, collects the reports of those it cannot, and returns one exit code whatever the
call site. It reads no target file and matches no pattern of its own.

A rule with no realizer is not silently dropped: it is listed as unrealized, with its
reason, and it never changes the exit code. Declaring it is what stops it being read as
verified.

Registry of enforcement types:  references/enforcement-registry.md
Configuration:                  references/gate-config-schema.md

Prerequisite: Python 3.10+ to start this runner at all, Node.js 18+ for it to invoke the
portable linter. Both are stated in skills/enforce/references/gate-wiring.md.

The runner also opposes the contract's maturity: conformity may only be asserted at or
above `THRESHOLD` (references/maturity-status.md). Below it, the report still lists every
violation the linter and the pivots found, but the run cannot claim conformity — it names
the path that would raise the status and returns 4. The threshold has one executable source,
the `THRESHOLD` constant of `tools/status.py`, imported here rather than restated.

Usage:  python run-gates.py --config <file>
Exit:   0  no violation, and the contract is at or above the conformity threshold
        1  at least one violation, from the linter or from a pivot report
        2  invocation or environment error: unreadable configuration, unknown enforcement
           type, required runtime absent
        3  the contract is in 1.x format - migrate it first (tools/migrate-contract.py)
        4  the contract sits below the conformity threshold: conformity is not asserted, the
           violations are still reported, and the path that raises the status is named
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

# The status computation lives in one place. run-gates imports THRESHOLD and the compute
# path from it rather than repeating either the literal or the ladder logic.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from status import THRESHOLD, compute, meets_threshold, observe  # noqa: E402

POLICIES = "policies.json"
RELEASE = "release.json"

# Mirrors references/enforcement-registry.md. The value is who realizes the type; None is
# the marker itself. A type absent from this table is a decision the runner refuses to make.
REALIZER = {
    "markup": "lint-core",
    "stylesheet": "pivot",
    "source-graph": "pivot",
    "stored-content": "pivot",
    "platform-config": "pivot",
    "unrealized": None,
}


class GateError(Exception):
    """A run that cannot go on, carrying the exit code it must produce.

    The runner has one caller-visible contract: an exit code. Raising rather than threading
    `int | None` through every helper keeps each step readable and keeps the code that ends
    the run next to the reason it ends — the message is printed at the raise site, so a new
    failure path cannot forget to say why.
    """

    def __init__(self, code: int) -> None:
        super().__init__(f"gate run aborted with exit {code}")
        self.code = code


def abort(message: str, code: int = 2) -> GateError:
    """Print the diagnosis and build the error to raise. `raise abort(...)` reads as one step."""
    print(message, file=sys.stderr)
    return GateError(code)


def fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 2


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        raise SystemExit(fail(f"{path}: invalid JSON - {exc}"))


def expand(base: Path, patterns) -> list[Path]:
    """Glob relative to the configuration file. A literal path is kept as written, so a
    missing target is reported by name instead of vanishing from an empty match."""
    found: list[Path] = []
    for pattern in patterns:
        if any(ch in pattern for ch in "*?["):
            found.extend(sorted(base.glob(pattern)))
        else:
            found.append(base / pattern)
    return found


def read_config(config_path: Path) -> dict:
    config = read_json(config_path)
    if config is None:
        raise abort(f"Configuration not found: {config_path}")
    if not isinstance(config, dict):
        raise abort(f"{config_path}: expected an object at the root.")
    return config


def resolve_contract(config: dict, config_path: Path) -> Path:
    """Locate the contract and refuse a 1.x one before any realizer is invoked."""
    contract_dir = (config_path.parent / config.get("contract", ".")).resolve()
    if not contract_dir.is_dir():
        raise abort(f"{config_path}: contract directory not found: {contract_dir}")
    if not (contract_dir / RELEASE).is_file():
        raise abort(f"CONTRACT {contract_dir}\n"
                    f"  {RELEASE} absent - contract in 1.x format.\n"
                    f"  Migrate it: python tools/migrate-contract.py --contract {contract_dir}",
                    code=3)
    return contract_dir


def type_rules(contract_dir: Path) -> list[tuple[str, str]]:
    """Type every declared rule before invoking anything: an untyped rule makes the whole run
    meaningless, and finding that out after half the targets were linted helps nobody."""
    policies = read_json(contract_dir / POLICIES)
    if policies is None:
        raise abort(f"{contract_dir / POLICIES}: not found, the contract declares it.")

    typed: list[tuple[str, str]] = []
    for index, rule in enumerate((policies.get("usage") or {}).get("rules") or []):
        rule_id = rule.get("id") or f"usage.rules[{index}]"
        kind = rule.get("enforcement")
        if kind not in REALIZER:
            raise abort(f"{contract_dir / POLICIES}: rule \"{rule_id}\" declares "
                        f"enforcement {kind or 'nothing'}, outside the registry.\n"
                        f"  Allowed: {', '.join(sorted(REALIZER))}\n"
                        f"  See references/enforcement-registry.md")
        typed.append((rule_id, kind))
    return typed


def collect_targets(config: dict, config_path: Path) -> list[Path]:
    targets = expand(config_path.parent, config.get("targets") or [])
    missing = [t for t in targets if not t.is_file()]
    if missing:
        raise abort(f"{config_path}: target(s) not found: "
                    + ", ".join(str(m) for m in missing))
    return targets


def lint_markup(config: dict, config_path: Path, contract_dir: Path,
                targets: list[Path]) -> tuple[list[str], set[str]]:
    """Run the portable linter over every target. Returns its violations and the markup rules
    it reports having realized."""
    violations: list[str] = []
    realized: set[str] = set()
    if not targets:
        return violations, realized

    base = config_path.parent
    linter = (base / config.get("linter", "")).resolve() if config.get("linter") else None
    if linter is None or not linter.is_file():
        raise abort(f"{config_path}: `linter` must point at the portable linter; "
                    f"got {config.get('linter') or 'nothing'}.")
    if shutil.which("node") is None:
        raise abort("Node.js not found on PATH. The runner invokes the portable linter "
                    "with it; without Node no markup rule can be realized.\n"
                    "  Install Node.js 18+, or remove the markup targets from "
                    f"{config_path}.")

    for target in targets:
        argv = ["node", str(linter), str(target), "--contract", str(contract_dir), "--json"]
        if config.get("strict"):
            argv.append("--strict")
        proc = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8")
        if proc.returncode in (2, 3):
            # The linter already diagnosed it; its code is the run's code.
            sys.stderr.write(proc.stderr)
            raise GateError(proc.returncode)
        report = json.loads(proc.stdout) if proc.stdout.strip() else {}
        realized.update(report.get("realized") or [])
        for message in report.get("errors") or []:
            violations.append(f"{target}: {message}")
    return violations, realized


def resolve_pivot_reports(config: dict, config_path: Path) -> list[Path]:
    """A pivot is a skill and cannot be invoked from here, but the native linter it installs is
    a process like any other. Declared with a `command`, it is re-run before its report is
    read, so the report cannot be stale; declared as a bare path, the report is whatever the
    last run left there. Its absence is what makes the rules unrealized at run time."""
    base = config_path.parent
    paths: list[Path] = []
    for entry in config.get("pivotReports") or []:
        if isinstance(entry, str):
            paths.extend(expand(base, [entry]))
            continue
        if not isinstance(entry, dict) or not entry.get("path"):
            raise abort(f"{config_path}: each pivotReports entry is a path, or an object "
                        f"carrying `path` and optionally `command`; got {entry!r}.")
        command = entry.get("command")
        if command:
            if not isinstance(command, list) or not all(isinstance(a, str) for a in command):
                raise abort(f"{config_path}: `command` of {entry['path']} must be a list of "
                            "strings - no shell, so no quoting rule to get wrong.")
            try:
                # Its exit code says "violations found", which its report already carries in
                # full. Reading the report is what decides; the code here would only duplicate.
                subprocess.run(command, cwd=base, capture_output=True, text=True)
            except FileNotFoundError:
                raise abort(f"{config_path}: realizer not found: {command[0]}\n"
                            f"  Declared to produce {entry['path']}. Install it, or drop the "
                            "`command` to read the report as it stands.")
        paths.append(base / entry["path"])
    return paths


def read_pivot_reports(report_paths: list[Path],
                       config_path: Path) -> tuple[dict[str, str], dict[str, str], list[str]]:
    """Returns, per rule id: who realized it, who declined it, and the violations found."""
    reported: dict[str, str] = {}
    declined: dict[str, str] = {}
    violations: list[str] = []
    for path in report_paths:
        payload = read_json(path)
        if payload is None:
            raise abort(f"{config_path}: pivot report not found: {path}")
        realizer = payload.get("realizer") or str(path)
        for entry in payload.get("rules") or []:
            rule_id = entry.get("id")
            if not rule_id:
                raise abort(f"{path}: a report entry declares no rule id.")
            if entry.get("status") == "unrealized":
                # The pivot was assigned the rule and says it did not realize it. Louder than
                # silence, and the only case that tells apart "not run" from "cannot cover".
                declined[rule_id] = realizer
                continue
            reported[rule_id] = realizer
            if entry.get("status") == "fail":
                for message in entry.get("violations") or [rule_id]:
                    violations.append(f"{realizer}: {message}")
    return reported, declined, violations


def render_rules(typed: list[tuple[str, str]], reported: dict[str, str],
                 declined: dict[str, str]) -> list[str]:
    """Print one line per declared rule; return the ids left unrealized."""
    unrealized: list[str] = []
    for rule_id, kind in typed:
        if kind == "markup":
            print(f"  REALIZED   {rule_id} ({kind}) by lint-core")
        elif rule_id in reported:
            # TODO(human): a rule declared `unrealized` in the contract but present in a pivot
            # report reaches this branch and is printed REALIZED. Decide what that collision
            # means and encode it here.
            print(f"  REALIZED   {rule_id} ({kind}) by {reported[rule_id]}")
        elif rule_id in declined:
            unrealized.append(rule_id)
            print(f"  UNREALIZED {rule_id} ({kind}) - {declined[rule_id]} reports it unrealized")
        elif kind == "unrealized":
            unrealized.append(rule_id)
            print(f"  UNREALIZED {rule_id} - declared with no realizer")
        else:
            unrealized.append(rule_id)
            print(f"  UNREALIZED {rule_id} ({kind}) - no report from its realizer")
    return unrealized


def render_verdict(contract_dir: Path, targets: list[Path], realized_markup: set[str],
                   typed: list[tuple[str, str]], reported: dict[str, str],
                   declined: dict[str, str], violations: list[str]) -> int:
    print(f"CONTRACT {contract_dir}")
    print(f"TARGETS  {len(targets)} file(s), markup rules realized: "
          f"{', '.join(sorted(realized_markup)) or 'none'}")

    unrealized = render_rules(typed, reported, declined)

    for message in violations:
        print(f"  VIOLATION {message}")

    if unrealized:
        print(f"UNREALIZED {len(unrealized)} rule(s) - reported, never counted as verified, "
              "and never a violation.")

    exit_code = 0
    if violations:
        print(f"FAIL {len(violations)} violation(s).")
        exit_code = 1

    # Oppose the maturity threshold last, once every violation is already on the report. Below
    # it, conformity cannot be asserted whatever the violation count - so exit 4 supersedes
    # both the 1 of a violation and the 0 of a clean run, and the report keeps the violations.
    status_value = compute(observe(contract_dir))
    if not meets_threshold(status_value):
        print(f"BELOW THRESHOLD status \"{status_value}\" is under \"{THRESHOLD}\"; "
              "conformity is not asserted.")
        print(f"  Raise it: python tools/status.py --contract {contract_dir} names the status; "
              "record the missing checks at adjust/02-freeze.md and lift the capping gaps.")
        print("  See references/maturity-status.md for the gap-to-cap table.")
        return 4

    if not violations:
        print("OK   no violation.")
    return exit_code


def run(config_path: Path) -> int:
    """Read, realize, report. Each step raises GateError with its own exit code; this function
    holds the order of the steps and nothing else."""
    try:
        config = read_config(config_path)
        contract_dir = resolve_contract(config, config_path)
        typed = type_rules(contract_dir)
        targets = collect_targets(config, config_path)

        violations, realized_markup = lint_markup(config, config_path, contract_dir, targets)
        report_paths = resolve_pivot_reports(config, config_path)
        reported, declined, pivot_violations = read_pivot_reports(report_paths, config_path)
        violations.extend(pivot_violations)

        return render_verdict(contract_dir, targets, realized_markup, typed,
                              reported, declined, violations)
    except GateError as error:
        return error.code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="run-gates.py",
        description="Aggregate the enforcement of one contract into a single exit code.")
    parser.add_argument("--config", required=True,
                        help="gate configuration file; every path it holds is relative to it")
    args = parser.parse_args(argv)
    # Violation messages are contract text and carry whatever the contract is written in.
    # A gate must never die on the encoding of the console or of a redirection.
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    return run(Path(args.config))


if __name__ == "__main__":
    sys.exit(main())
