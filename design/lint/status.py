#!/usr/bin/env python3
"""status.py — maturity status of a design-system contract.

The ONLY implementation of the status computation. No other code derives one; a tool
that needs a status calls `compute()` or this CLI and prints back what it returns.

The status is a ladder: the first unmet condition stops the climb, then a recorded gap may
cap it lower. A contract with no charter therefore caps at the first rung whatever else
holds — the ladder caps, it never skips a rung.

  rung 1  the artifacts exist
  rung 2  + the charter is present
  rung 3  + checks have been run (release.json declares them)
  rung 4  + the contrast check and the declarative-state check both pass

The threshold above which conformity may be invoked is `THRESHOLD`, the single executable
source of that value; `run-gates.py` imports it, and `references/maturity-status.md` is the
single human source. Nothing else restates the literal.

Usage:  python status.py --contract <dir>            print the status
        python status.py --contract <dir> --states   print the declarative-state report (JSON)
Exit:   0 printed on stdout, contract directory on stderr · 2 unusable contract directory
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# The four literals live here and nowhere else.
LADDER = ["extracted", "normalized", "validated", "production-ready"]

# The conformity threshold. One executable source (this constant), one human source
# (references/maturity-status.md). run-gates.py imports it rather than repeating it.
THRESHOLD = "validated"

DEFAULT_CHARTER = "design-system.md"
RELEASE_FILE = "release.json"
COMPONENTS_FILE = "components.json"
STATE_KEYS = ("disabled", "error", "focus")

_VERSION_RE = re.compile(r"^version:\s*(\S+)\s*$", re.MULTILINE)


def meets_threshold(status: str) -> bool:
    """True when `status` sits at or above the conformity threshold on the ladder."""
    return LADDER.index(status) >= LADDER.index(THRESHOLD)


def _read_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def read_release(contract_dir: Path) -> dict | None:
    """Parse release.json, or None when the contract has no release root (1.x)."""
    return _read_json(contract_dir / RELEASE_FILE)


def read_charter(contract_dir: Path, release: dict | None = None) -> dict:
    """Observe the charter document: path, presence, declared version.

    The path comes from the release root when there is one, so a contract that renamed
    its charter stays observable; otherwise the contract-wide default applies.
    """
    rel_path = DEFAULT_CHARTER
    if release:
        rel_path = (release.get("charter") or {}).get("path") or DEFAULT_CHARTER
    path = contract_dir / rel_path
    present = path.is_file()
    version = None
    if present:
        try:
            match = _VERSION_RE.search(path.read_text(encoding="utf-8"))
        except OSError:
            match = None
        if match:
            version = match.group(1)
    return {"path": rel_path, "present": present, "version": version}


def check_states(contract_dir: Path) -> dict:
    """Declarative presence of the interactive states per component, without any markup.

    A component may declare `states` with the three closed keys disabled/error/focus as
    booleans, or omit the object (static). A partial object — a missing key — is the gap:
    freeze cannot tell an oversight from an intended omission.
    """
    components = (_read_json(contract_dir / COMPONENTS_FILE) or {}).get("components") or {}
    report: dict[str, dict] = {}
    all_pass = True
    for name, spec in components.items():
        states = (spec or {}).get("states")
        if states is None:
            report[name] = {"declared": False, "complete": True, "present": []}
            continue
        complete = all(isinstance(states.get(k), bool) for k in STATE_KEYS)
        present = [k for k in STATE_KEYS if states.get(k) is True]
        report[name] = {"declared": True, "complete": complete, "present": present}
        if not complete:
            all_pass = False
    return {"ran": True, "allPass": all_pass, "components": report}


def gap_cap(release: dict | None) -> int | None:
    """Lowest rung any recorded gap caps the status at, or None when no gap caps."""
    caps = [LADDER.index(g["caps"])
            for g in (release or {}).get("gaps") or []
            if isinstance(g, dict) and g.get("caps") in LADDER]
    return min(caps) if caps else None


def contrast_pass(check: dict) -> bool:
    """`allPass` alone is true by vacuity on zero pairs — it must be read with the count.

    `pairs` absent means the check was recorded before the field existed: `allPass` is trusted
    as it was written, since re-reading it as false would demote contracts whose pairs were
    genuinely compared. Present and zero is the case this exists for, and it never passes.
    """
    if not check.get("allPass"):
        return False
    return check.get("pairs", 1) > 0


def observe(contract_dir: Path) -> dict:
    """The facts the status is computed from: charter, recorded checks, recorded gaps."""
    release = read_release(contract_dir)
    charter = read_charter(contract_dir, release)
    checks = (release or {}).get("checks") or {}
    return {
        "charter_present": charter["present"],
        "checks_run": bool(release and release.get("checks")),
        "contrast_pass": contrast_pass(checks.get("contrast") or {}),
        "states_pass": bool((checks.get("states") or {}).get("allPass")),
        "gap_cap": gap_cap(release),
    }


def compute(facts: dict) -> str:
    """Climb the ladder to the last rung whose condition holds, then apply the gap cap."""
    reached = 0
    if facts.get("charter_present"):
        reached = 1
        if facts.get("checks_run"):
            reached = 2
            if facts.get("contrast_pass") and facts.get("states_pass"):
                reached = 3
    cap = facts.get("gap_cap")
    if cap is not None:
        reached = min(reached, cap)
    return LADDER[reached]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Maturity status of a design-system contract.")
    parser.add_argument("--contract", required=True, metavar="DIR",
                        help="contract directory")
    parser.add_argument("--states", action="store_true",
                        help="print the declarative-state report as JSON instead of the status")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")

    contract_dir = Path(args.contract)
    if not contract_dir.is_dir():
        print(f"Contract directory not found: {contract_dir}", file=sys.stderr)
        return 2
    # The subject goes to stderr, the value to stdout. A rung with no contract named is
    # unciteable as evidence, but `adjust/02-freeze.md` copies stdout verbatim into
    # `release.json § status` — anything added to that line would land in the contract.
    print(f"CONTRACT {contract_dir}", file=sys.stderr)
    if args.states:
        print(json.dumps(check_states(contract_dir), indent=2, sort_keys=True))
    else:
        print(compute(observe(contract_dir)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
