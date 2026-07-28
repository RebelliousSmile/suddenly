#!/usr/bin/env python3
"""migrate-contract.py — turn a 1.x monolithic contract into the 2.0 artifacts.

Two independent, idempotent, replayable passes:

  --contract <dir>  redistributes the 1.x manifest into tokens/components/policies/oracle +
                    release.json, applying the table of
                    `references/contract-schema.md § Redistribution depuis un contrat 1.x`.
                    Nothing is invented and nothing is dropped — a key the table does not name
                    is carried verbatim and reported as an anomaly, never discarded.

  --ledger <dir>    converts the Markdown deviation ledger (ds-deviation-ledger.md) into the
                    structured deviations.json, one entry per `### DEV-NNN` block. An entry the
                    parser cannot map to a sanctionable deviation is reported, never dropped.

Exactly one pass per invocation. The maturity status is not computed here: `status.py` is the
only implementation, and this script prints back what it returns.

Usage:
  python migrate-contract.py --contract <dir> [--dry-run] [--mode bem|utility-first]
                             [--now <ISO-8601>]
  python migrate-contract.py --ledger <dir> [--dry-run]

`status.py` travels with this script: both are copied side by side into a consuming project.
Its absence is an environment error (exit 2), never a traceback — an uncaught ImportError exits
1, which the exit-code space reserves for a violation.

Exit:
  0  migrated, or already 2.0 (no-op)
  2  invocation error, missing runtime dependency, a structurally invalid artifact, or a
     decision the tool refuses to guess (undeclared mode)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import status
except ImportError:
    print(
        "status.py not found next to %s.\n"
        "  It is the only implementation of the maturity status and this script prints back\n"
        "  what it returns. Copy it from the design plugin's tools/ directory, or run the\n"
        "  migration from there." % Path(__file__).resolve().parent,
        file=sys.stderr,
    )
    sys.exit(2)

BACKUP_DIR = ".contract-1x"
SCHEMA = "design/references/contract-schema"
FORMAT = "2.0"
MODES = ("bem", "utility-first")

TOKENS, COMPONENTS, POLICIES, ORACLE, RELEASE = (
    "tokens.json", "components.json", "policies.json", "oracle.json", "release.json")
ARTIFACTS = (TOKENS, COMPONENTS, POLICIES, ORACLE)

# --ledger pass. The Markdown ledger is read by a fixed name so the pass needs no second argument;
# deviations.json is written beside it. Both live in the contract directory in a real project.
DEVIATIONS = "deviations.json"
LEDGER_FILE = "ds-deviation-ledger.md"
# A block header: "### DEV-001 — <title>" with any dash (em/en/hyphen) and any spacing.
LEDGER_HEADING = re.compile(r"^###\s+(DEV-\d+)\b\s*[—–-]?\s*(.*)$")
# A field line inside a block: "- key: value" (the ledger uses no space after the colon on some
# lines, e.g. "contract value:fontSize = 17px" — so \s* not \s+).
LEDGER_FIELD = re.compile(r"^\s*[-*]\s*([^:]+?):\s*(.*)$")
# "contract value: <prop> = <value>" — split on the first '=' only; the value may itself contain '='.
LEDGER_CONTRACT_VALUE = re.compile(r"^\s*([A-Za-z][\w-]*)\s*=\s*(.+)$")

# The 1.x keys the redistribution table names. Anything else is carried verbatim and reported.
KNOWN_TOP = {"$schema", "$version", "mode", "$utilityPrefixes", "components", "usage", "oracle"}
KNOWN_COMPONENT = {"base", "elements", "modifiers", "backgrounds", "foregrounds", "a11y", "oracle"}

# 1.x enforcement values, retyped against references/enforcement-registry.md. "pivot-only"
# named no evidence, so it names no realizer: it lands on the marker, never on a guess.
UNREALIZED = "unrealized"
ENFORCEMENT_1X = {"baseline": "markup"}

# Adapter consumer by extension - a role, never a platform.
CONSUMER_BY_SUFFIX = {
    ".css": "stylesheet",
    ".scss": "stylesheet source",
    ".sass": "stylesheet source",
    ".less": "stylesheet source",
    ".json": "platform token file",
    ".js": "build configuration",
    ".mjs": "build configuration",
    ".cjs": "build configuration",
    ".ts": "build configuration",
}
UNKNOWN_CONSUMER = "unknown"


def fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 2


def shape_of(value) -> str:
    if value is None:
        return "null"
    return {dict: "an object", list: "an array", str: "a string",
            bool: "a boolean", int: "a number", float: "a number"}.get(
        type(value), f"a {type(value).__name__}")


def fail_shape(path: Path, field: str, expected: str, got) -> int:
    """A structurally invalid artifact is an environment error, never a traceback.

    Left unguarded these sites raise AttributeError, which exits 1 — the code the exit-code
    space reserves for a violation — and prints a stack trace instead of naming the field.
    """
    seen = json.dumps(got, ensure_ascii=False)
    if len(seen) > 120:
        seen = seen[:117] + "..."
    # Resolved, unlike the sibling fail() calls in this file: this message is meant to be
    # pasted as evidence, and a relative path is unciteable outside the shell that produced it.
    return fail(f"{path.name} {field} is {shape_of(got)}, expected {expected}: {path.resolve()}\n"
                f"  Got: {seen}\n"
                "  The redistribution reads this field. Read as is, the migration would crash, or\n"
                "  write an artifact the linter cannot derive its rules from.")


def check_shape(manifest, path: Path) -> int | None:
    """Refuse a manifest the redistribution cannot walk. Returns an exit code, or None."""
    if not isinstance(manifest, dict):
        return fail_shape(path, "$", "an object", manifest)
    components = manifest.get("components")
    if components is None:
        return None
    if not isinstance(components, dict):
        return fail_shape(path, "$.components", "an object", components)
    for name, comp in components.items():
        if not isinstance(comp, dict):
            return fail_shape(path, f"$.components.{name}", "an object", comp)
    return None


def sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def dump(obj: dict) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


def adapter_table(contract_dir: Path) -> tuple[list[dict], list[str]]:
    """One entry per adapter actually present, each carrying its consumer role."""
    entries: list[dict] = []
    anomalies: list[str] = []
    root = contract_dir / "adapters"
    if not root.is_dir():
        return entries, anomalies
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        consumer = CONSUMER_BY_SUFFIX.get(path.suffix.lower(), UNKNOWN_CONSUMER)
        rel = path.relative_to(contract_dir).as_posix()
        entries.append({"artifact": rel, "consumer": consumer})
        if consumer == UNKNOWN_CONSUMER:
            anomalies.append(f"adapter {rel}: consumer not derivable from the extension, complete it by hand")
    return entries, anomalies


def split(manifest: dict, mode: str) -> tuple[dict, list[tuple[str, str]], list[str]]:
    """Redistribute the 1.x manifest into the three derived artifact payloads."""
    mapping: list[tuple[str, str]] = []
    anomalies: list[str] = []

    components: dict = {}
    oracle_components: dict = {}
    for name, comp in (manifest.get("components") or {}).items():
        anatomy: dict = {}
        for key, value in comp.items():
            if key == "oracle":
                continue
            anatomy[key] = value
            if key not in KNOWN_COMPONENT:
                anomalies.append(
                    f"$.components.{name}.{key}: outside the redistribution table, kept in {COMPONENTS}")
        components[name] = anatomy
        if comp.get("oracle"):
            oracle_components[name] = comp["oracle"]
    if components:
        mapping.append(("$.components.*.<anatomy>", f"{COMPONENTS}.components"))
    if oracle_components:
        mapping.append(("$.components.*.oracle", f"{ORACLE}.components.*"))

    policies: dict = {"$schema": f"{SCHEMA}#policies", "mode": mode}
    mapping.append(("$.mode" if "mode" in manifest else "--mode", f"{POLICIES}.mode"))
    if "$utilityPrefixes" in manifest:
        policies["$utilityPrefixes"] = manifest["$utilityPrefixes"]
        mapping.append(("$.$utilityPrefixes", f"{POLICIES}.$utilityPrefixes"))
    if "usage" in manifest:
        usage = dict(manifest["usage"])
        rules = []
        for rule in usage.get("rules") or []:
            rule = dict(rule)
            before = rule.get("enforcement")
            after = ENFORCEMENT_1X.get(before, UNREALIZED)
            rule["enforcement"] = after
            if after == UNREALIZED:
                anomalies.append(
                    f"$.usage.rules[{rule.get('id', '?')}].enforcement: "
                    f"{before or 'absent'} names no realizer, written {UNREALIZED}; "
                    "re-type it from references/enforcement-registry.md")
            rules.append(rule)
        if rules:
            usage["rules"] = rules
        policies["usage"] = usage
        mapping.append(("$.usage", f"{POLICIES}.usage"))

    oracle: dict = {"$schema": f"{SCHEMA}#oracle", "components": oracle_components}
    if manifest.get("oracle"):
        oracle["contract"] = manifest["oracle"]
        mapping.append(("$.oracle", f"{ORACLE}.contract"))
        anomalies.append(
            f"$.oracle: contract-level hints, kept in {ORACLE}.contract; only the per-component form has a reader")

    for key, value in manifest.items():
        if key in KNOWN_TOP:
            continue
        policies[key] = value
        mapping.append((f"$.{key}", f"{POLICIES}.{key}"))
        anomalies.append(f"$.{key}: outside the redistribution table, kept in {POLICIES}")

    payload = {COMPONENTS: {"$schema": f"{SCHEMA}#components", "components": components},
               POLICIES: policies}
    # An empty oracle.json is not written, and not declared: a contract without measure
    # targets has no oracle side. Its only reader is the measure adapter, never the linter.
    if oracle_components or oracle.get("contract"):
        payload[ORACLE] = oracle
    return payload, mapping, anomalies


def migrate(contract_dir: Path, mode_arg: str | None, dry_run: bool, now: str) -> int:
    if not contract_dir.is_dir():
        return fail(f"Contract directory not found: {contract_dir}")

    if (contract_dir / RELEASE).is_file():
        print(f"CONTRACT {contract_dir}\n"
              f"NO-OP    {RELEASE} present - already 2.0, nothing to migrate.")
        return 0

    manifest_path = contract_dir / COMPONENTS
    tokens_path = contract_dir / TOKENS
    for path in (tokens_path, manifest_path):
        if not path.is_file():
            return fail(f"Not a 1.x contract: {path.name} missing in {contract_dir}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return fail(f"Unreadable {COMPONENTS}: {exc}")

    # Before any field is read, including in the dry-run path: a dry run that crashes is not a
    # dry run, and the shape is what every read below takes on faith.
    bad_shape = check_shape(manifest, manifest_path)
    if bad_shape is not None:
        return bad_shape

    declared_mode = manifest.get("mode")
    if declared_mode and mode_arg and declared_mode != mode_arg:
        return fail(f'Mode conflict: {COMPONENTS} declares "{declared_mode}", --mode says "{mode_arg}". '
                    "Drop --mode, or fix the contract. The tool does not pick between them.")
    if declared_mode and declared_mode not in MODES:
        return fail(f'Unknown mode "{declared_mode}" in {manifest_path}. Expected one of: {", ".join(MODES)}.')
    mode = declared_mode or mode_arg
    if not mode:
        return fail(f"Undeclared mode in {manifest_path}. Pass --mode {'|'.join(MODES)}. "
                    "The tool refuses to guess it: the wrong mode leaves the vocabulary rules inert "
                    "and turns a green run into a verdict about nothing.")

    payload, mapping, anomalies = split(manifest, mode)
    adapters, adapter_anomalies = adapter_table(contract_dir)
    anomalies += adapter_anomalies
    if adapters:
        payload[POLICIES]["adapters"] = adapters
        mapping.append(("adapters/*", f"{POLICIES}.adapters"))

    charter = status.read_charter(contract_dir)
    version = manifest.get("$version")
    if not version:
        version = charter["version"] or "0.0.0"
        anomalies.append(f'$.$version absent - {RELEASE} declares "{version}", read from the charter or defaulted')
    if not charter["present"]:
        anomalies.append(f"charter {charter['path']} absent - recorded in {RELEASE}.charter, and the status is capped by it")
    elif charter["version"] and charter["version"] != version:
        anomalies.append(f'declared versions differ - {COMPONENTS} "{version}", charter "{charter["version"]}"; '
                         f"both are recorded in {RELEASE}, neither is a violation")

    manifest_hash = sha256(manifest_path)
    source_hash = {TOKENS: sha256(tokens_path)}
    release = {
        "$schema": f"{SCHEMA}#release",
        "$format": FORMAT,
        "designSystem": {"version": version},
        "artifacts": {name: {"version": version, "sourceHash": source_hash.get(name, manifest_hash)}
                      for name in ARTIFACTS if name == TOKENS or name in payload},
        "charter": {"present": charter["present"], "path": charter["path"], "version": charter["version"]},
        "provenance": {"producedBy": Path(__file__).name, "producedAt": now, "from": "1.x contract"},
        "checks": None,
        "status": status.compute(status.observe(contract_dir)),
    }

    mapping = ([(TOKENS, f"{TOKENS} (unchanged)"),
                ("$.$version", f"{RELEASE}.designSystem.version, artifacts.*.version")]
               + mapping
               + [(charter["path"], f"{RELEASE}.charter")])

    width = max(len(src) for src, _ in mapping)
    lines = [f"CONTRACT {contract_dir}",
             f"MODE     {mode} ({'declared' if declared_mode else '--mode'})",
             f"STATUS   {release['status']}",
             "MAPPING"]
    lines += [f"  {src.ljust(width)}  ->  {dst}" for src, dst in mapping]
    lines.append("ADAPTERS")
    lines += [f"  {e['artifact']}  ->  {e['consumer']}" for e in adapters] or ["  (none)"]
    lines.append("ANOMALIES")
    lines += [f"  {a}" for a in anomalies] or ["  (none)"]

    if dry_run:
        lines.append("DRY RUN  nothing written")
        print("\n".join(lines))
        return 0

    backup = contract_dir / BACKUP_DIR
    backup.mkdir(exist_ok=True)
    for name in (COMPONENTS, TOKENS, charter["path"]):
        src = contract_dir / name
        if src.is_file():
            shutil.copy2(src, backup / Path(name).name)

    for name, obj in payload.items():
        (contract_dir / name).write_text(dump(obj), encoding="utf-8")
    (contract_dir / RELEASE).write_text(dump(release), encoding="utf-8")

    lines.append(f"WRITTEN  {', '.join(list(payload) + [RELEASE])}")
    lines.append(f"BACKUP   {BACKUP_DIR}/")
    print("\n".join(lines))
    return 0


def parse_ledger(text: str) -> list[dict]:
    """Split a Markdown deviation ledger into one raw block per `### DEV-NNN` heading.

    Order is source order — the report and deviations.json both preserve it, so a replay writes
    a byte-identical file. Lines before the first heading (title, index table) are ignored.
    """
    blocks: list[dict] = []
    current: dict | None = None
    last_key: str | None = None
    for line in text.splitlines():
        head = LEDGER_HEADING.match(line)
        if head:
            current = {"id": head.group(1), "title": head.group(2).strip(), "fields": {}}
            blocks.append(current)
            last_key = None
            continue
        if current is None:
            continue
        field = LEDGER_FIELD.match(line)
        if field:
            last_key = field.group(1).strip().lower()
            current["fields"][last_key] = field.group(2).strip()
            continue
        # A wrapped field value: indented continuation of the previous field (the template aligns
        # multi-line justifications under their key). Indentation is the discriminator — a section
        # heading or an index-table row starts at column 0, so neither is absorbed here.
        if last_key and line[:1].isspace() and line.strip():
            current["fields"][last_key] += " " + line.strip()
    return blocks


def ledger_to_deviations(blocks: list[dict]) -> tuple[list[dict], list[str]]:
    """Map each raw block onto a deviations.json § active entry, per deviations-schema.md.

    An entry the parser cannot turn into a sanctionable deviation (no target, no prop/expected)
    is still emitted and reported — never dropped — so the human reconciling the migration sees
    every gap. The schema field it lacks is what later makes the oracle answer OPEN, honestly.
    """
    active: list[dict] = []
    anomalies: list[str] = []
    for block in blocks:
        eid, fields = block["id"], block["fields"]
        entry: dict = {"id": eid, "status": "active"}

        target = fields.get("component") or fields.get("selector(s)") or ""
        entry["target"] = target
        if not target:
            anomalies.append(f"{eid}: no 'component' or 'selector(s)' line - target left empty, "
                             "reconcile it with the oracle target name by hand")

        contract_value = fields.get("contract value", "")
        match = LEDGER_CONTRACT_VALUE.match(contract_value)
        if match:
            entry["prop"] = match.group(1)
            entry["expected"] = match.group(2).strip()
        else:
            anomalies.append(f"{eid}: no parseable 'contract value: <prop> = <value>' - the entry "
                             "carries no expected value, so the oracle would answer OPEN")

        entry["date"] = fields.get("date", "")
        if fields.get("expires"):
            entry["expires"] = fields["expires"]
        entry["reason"] = fields.get("justification") or block["title"]
        active.append(entry)
    return active, anomalies


def migrate_ledger(ledger_dir: Path, dry_run: bool) -> int:
    if not ledger_dir.is_dir():
        return fail(f"Ledger directory not found: {ledger_dir}")
    source = ledger_dir / LEDGER_FILE
    if not source.is_file():
        return fail(f"No {LEDGER_FILE} in {ledger_dir}. The --ledger pass reads the Markdown "
                    "deviation ledger by that name and writes deviations.json beside it.")

    blocks = parse_ledger(source.read_text(encoding="utf-8"))
    active, anomalies = ledger_to_deviations(blocks)
    payload = {"$schema": f"{SCHEMA}#deviations", "active": active}

    width = max((len(b["id"]) for b in blocks), default=0)
    lines = [f"LEDGER   {source}", f"ENTRIES  {len(active)}", "IDENTIFIERS"]
    for entry in active:
        detail = f"target={entry['target'] or '(empty)'}  prop={entry.get('prop', '(none)')}  " \
                 f"expected={entry.get('expected', '(none)')}"
        lines.append(f"  {entry['id'].ljust(width)}  ->  {detail}")
    if not active:
        lines.append("  (none)")
    lines.append("ANOMALIES")
    lines += [f"  {a}" for a in anomalies] or ["  (none)"]

    if dry_run:
        lines.append("DRY RUN  nothing written")
        print("\n".join(lines))
        return 0

    (ledger_dir / DEVIATIONS).write_text(dump(payload), encoding="utf-8")
    lines.append(f"WRITTEN  {DEVIATIONS}")
    print("\n".join(lines))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Migrate a 1.x design-system contract, or its "
                                                 "Markdown deviation ledger, to the 2.0 artifacts.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--contract", metavar="DIR", help="contract directory (1.x monolith → 2.0 artifacts)")
    source.add_argument("--ledger", metavar="DIR",
                        help=f"directory holding {LEDGER_FILE} (Markdown ledger → {DEVIATIONS})")
    parser.add_argument("--dry-run", action="store_true", help="report only, write nothing")
    parser.add_argument("--mode", choices=MODES, help="vocabulary mode, when the contract declares none")
    parser.add_argument("--now", metavar="ISO-8601",
                        help="pin provenance.producedAt, so a migration is byte-reproducible")
    args = parser.parse_args(argv)

    if args.ledger:
        for name, value in (("--mode", args.mode), ("--now", args.now)):
            if value:
                return fail(f"{name} belongs to the --contract pass, not --ledger.")
        return migrate_ledger(Path(args.ledger), args.dry_run)

    now = args.now or datetime.now(timezone.utc).isoformat(timespec="seconds")
    return migrate(Path(args.contract), args.mode, args.dry_run, now)


if __name__ == "__main__":
    sys.exit(main())
