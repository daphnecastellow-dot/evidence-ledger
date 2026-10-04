#!/usr/bin/env python3
"""Keep evidence classes distinct while preserving provenance and derivation."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any

FORMAT = "evidence-ledger/0.1"
SOURCE_KINDS = (
    "primary", "contemporary-report", "later-retelling",
    "reference", "analysis", "other",
)
EVIDENCE_TYPES = (
    "observation", "firsthand-report", "secondhand-report",
    "documentary-record", "interpretation", "inference", "repetition",
)
STANCES = ("supports", "contradicts", "context", "unclear")
INDEPENDENCE = ("independent", "dependent", "unknown")


class LedgerError(Exception):
    pass


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def valid_date(value: str) -> bool:
    if re.fullmatch(r"\d{4}", value):
        return True
    try:
        if re.fullmatch(r"\d{4}-\d{2}", value):
            dt.date.fromisoformat(value + "-01")
            return True
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            dt.date.fromisoformat(value)
            return True
    except ValueError:
        return False
    return False


def new_project(title: str) -> dict[str, Any]:
    title = title.strip()
    if not title:
        raise LedgerError("title cannot be empty")
    return {
        "format": FORMAT,
        "title": title,
        "created_at": now_utc(),
        "claims": [],
        "sources": [],
        "entries": [],
    }


def next_id(items: list[dict[str, Any]], prefix: str) -> str:
    high = 0
    for item in items:
        value = item.get("id", "")
        if value.startswith(prefix) and value[len(prefix):].isdigit():
            high = max(high, int(value[len(prefix):]))
    return f"{prefix}{high + 1:03d}"


def find(items: list[dict[str, Any]], item_id: str, label: str) -> dict[str, Any]:
    for item in items:
        if item["id"] == item_id:
            return item
    raise LedgerError(f"{label} not found: {item_id}")


def validate(data: dict[str, Any]) -> None:
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise LedgerError("unsupported project format")
    if not isinstance(data.get("title"), str) or not data["title"].strip():
        raise LedgerError("project requires a title")
    for key in ("claims", "sources", "entries"):
        if not isinstance(data.get(key), list):
            raise LedgerError(f"project requires a {key} list")

    cids: set[str] = set()
    for claim in data["claims"]:
        cid = claim.get("id")
        if not isinstance(cid, str) or not cid or cid in cids:
            raise LedgerError("invalid or duplicate claim id")
        cids.add(cid)
        if not isinstance(claim.get("text"), str) or not claim["text"].strip():
            raise LedgerError(f"{cid}: claim text cannot be empty")

    sids: set[str] = set()
    for source in data["sources"]:
        sid = source.get("id")
        if not isinstance(sid, str) or not sid or sid in sids:
            raise LedgerError("invalid or duplicate source id")
        sids.add(sid)
        if source.get("kind") not in SOURCE_KINDS:
            raise LedgerError(f"{sid}: invalid source kind")
        if not isinstance(source.get("label"), str) or not source["label"].strip():
            raise LedgerError(f"{sid}: source label cannot be empty")
        if source.get("date") and not valid_date(source["date"]):
            raise LedgerError(f"{sid}: invalid date")

    eids: set[str] = set()
    for entry in data["entries"]:
        eid = entry.get("id")
        if not isinstance(eid, str) or not eid or eid in eids:
            raise LedgerError("invalid or duplicate evidence id")
        eids.add(eid)

    for entry in data["entries"]:
        eid = entry["id"]
        if entry.get("claim") not in cids:
            raise LedgerError(f"{eid}: unknown claim")
        if entry.get("type") not in EVIDENCE_TYPES:
            raise LedgerError(f"{eid}: invalid evidence type")
        if entry.get("stance") not in STANCES:
            raise LedgerError(f"{eid}: invalid stance")
        if entry.get("independence") not in INDEPENDENCE:
            raise LedgerError(f"{eid}: invalid independence state")
        if not isinstance(entry.get("text"), str) or not entry["text"].strip():
            raise LedgerError(f"{eid}: evidence text cannot be empty")
        for sid in entry.get("sources", []):
            if sid not in sids:
                raise LedgerError(f"{eid}: unknown source {sid}")
        for parent in entry.get("derived_from", []):
            if parent not in eids:
                raise LedgerError(f"{eid}: unknown derived-from entry {parent}")
            if parent == eid:
                raise LedgerError(f"{eid}: an entry cannot derive from itself")


def load(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise LedgerError(f"project not found: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LedgerError(f"invalid JSON: {exc}") from exc
    validate(data)
    return data


def save(path: str | Path, data: dict[str, Any]) -> None:
    validate(data)
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def add_claim(data: dict[str, Any], text: str, note: str | None = None) -> str:
    if not text.strip():
        raise LedgerError("claim text cannot be empty")
    cid = next_id(data["claims"], "C")
    data["claims"].append({"id": cid, "text": text.strip(), "note": note or ""})
    return cid


def add_source(
    data: dict[str, Any], label: str, kind: str, date: str | None = None,
    url: str | None = None, note: str | None = None,
) -> str:
    if kind not in SOURCE_KINDS:
        raise LedgerError("invalid source kind")
    if date and not valid_date(date):
        raise LedgerError("date must be YYYY, YYYY-MM, or YYYY-MM-DD")
    if not label.strip():
        raise LedgerError("source label cannot be empty")
    sid = next_id(data["sources"], "S")
    data["sources"].append({
        "id": sid, "label": label.strip(), "kind": kind, "date": date or "",
        "url": url or "", "note": note or "",
    })
    return sid


def add_entry(
    data: dict[str, Any], claim: str, text: str, evidence_type: str, stance: str,
    independence: str, sources: list[str] | None = None,
    derived_from: list[str] | None = None, note: str | None = None,
) -> str:
    find(data["claims"], claim, "claim")
    if evidence_type not in EVIDENCE_TYPES:
        raise LedgerError("invalid evidence type")
    if stance not in STANCES:
        raise LedgerError("invalid stance")
    if independence not in INDEPENDENCE:
        raise LedgerError("invalid independence state")
    if not text.strip():
        raise LedgerError("evidence text cannot be empty")

    source_ids = list(dict.fromkeys(sources or []))
    parent_ids = list(dict.fromkeys(derived_from or []))
    for sid in source_ids:
        find(data["sources"], sid, "source")
    for eid in parent_ids:
        find(data["entries"], eid, "evidence entry")

    eid = next_id(data["entries"], "E")
    data["entries"].append({
        "id": eid,
        "claim": claim,
        "text": text.strip(),
        "type": evidence_type,
        "stance": stance,
        "independence": independence,
        "sources": source_ids,
        "derived_from": parent_ids,
        "note": note or "",
        "created_at": now_utc(),
    })
    return eid


def audit(data: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    for entry in data["entries"]:
        eid = entry["id"]
        if not entry.get("sources") and not entry.get("derived_from"):
            findings.append(f"{eid}: no recorded source or derivation bridge")
        if entry["type"] in ("interpretation", "inference") and not entry.get("derived_from"):
            findings.append(f"{eid}: {entry['type']} has no recorded evidence basis")
        if entry["type"] == "repetition" and entry["independence"] == "independent":
            findings.append(f"{eid}: repetition is marked independent; verify that classification")
    return findings


def render_matrix(data: dict[str, Any]) -> str:
    headers = list(EVIDENCE_TYPES)
    lines = [
        "| Claim | " + " | ".join(headers) + " |",
        "|---|" + "|".join("---:" for _ in headers) + "|",
    ]
    for claim in data["claims"]:
        counts = {kind: 0 for kind in headers}
        for entry in data["entries"]:
            if entry["claim"] == claim["id"]:
                counts[entry["type"]] += 1
        lines.append("| " + claim["id"] + " | " + " | ".join(str(counts[h]) for h in headers) + " |")
    if not data["claims"]:
        return "_No claims yet._\n"
    return "\n".join(lines) + "\n"


def render_markdown(data: dict[str, Any]) -> str:
    source_labels = {s["id"]: s["label"] for s in data["sources"]}
    lines = [
        f"# {data['title']}", "",
        f"_Evidence Ledger format: `{FORMAT}`_", "",
        "> Evidence type, stance, and independence are recorded separately. None is an automatic truth score.",
        "", "## Claims", "",
    ]
    if not data["claims"]:
        lines += ["_No claims yet._", ""]
    for claim in data["claims"]:
        lines += [f"### {claim['id']}", "", claim["text"], ""]
        if claim.get("note"):
            lines += [f"**Note:** {claim['note']}", ""]
        entries = [e for e in data["entries"] if e["claim"] == claim["id"]]
        for entry in entries:
            lines += [
                f"#### {entry['id']} · {entry['type']} · {entry['stance']}", "",
                entry["text"], "",
                f"**Independence:** {entry['independence']}", "",
            ]
            if entry.get("sources"):
                lines += [
                    "**Sources:** " + ", ".join(f"{sid} · {source_labels[sid]}" for sid in entry["sources"]),
                    "",
                ]
            if entry.get("derived_from"):
                lines += ["**Derived from:** " + ", ".join(entry["derived_from"]), ""]
            if entry.get("note"):
                lines += [f"**Note:** {entry['note']}", ""]

    lines += ["## Evidence-type matrix", "", render_matrix(data).rstrip(), "", "## Structural audit", ""]
    findings = audit(data)
    if findings:
        lines += [f"- {item}" for item in findings]
    else:
        lines.append("_No structural audit flags._")
    return "\n".join(lines).rstrip() + "\n"


def render_mermaid(data: dict[str, Any]) -> str:
    lines = ["flowchart LR"]
    for claim in data["claims"]:
        label = claim["text"].replace('"', "'").replace("\n", " ")
        lines.append(f'  {claim["id"]}["{claim["id"]} · {label}"]')
    for source in data["sources"]:
        label = source["label"].replace('"', "'").replace("\n", " ")
        lines.append(f'  {source["id"]}["{source["id"]} · {label}"]')
    for entry in data["entries"]:
        label = entry["text"].replace('"', "'").replace("\n", " ")
        lines.append(f'  {entry["id"]}["{entry["id"]} · {entry["type"]} · {label}"]')
        for sid in entry["sources"]:
            lines.append(f'  {sid} -->|source for| {entry["id"]}')
        for parent in entry["derived_from"]:
            lines.append(f'  {parent} -->|derived into| {entry["id"]}')
        lines.append(f'  {entry["id"]} -->|{entry["stance"]}| {entry["claim"]}')
    return "\n".join(lines) + "\n"


def summary(data: dict[str, Any]) -> str:
    return (
        f"{data['title']}: {len(data['claims'])} claim(s), "
        f"{len(data['sources'])} source(s), {len(data['entries'])} evidence entry(ies), "
        f"{len(audit(data))} audit flag(s)"
    )


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="evidence-ledger",
        description="Separate evidence classes while preserving provenance and derivation.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    q = sub.add_parser("new")
    q.add_argument("file")
    q.add_argument("--title", required=True)

    q = sub.add_parser("claim")
    q.add_argument("file")
    q.add_argument("text")
    q.add_argument("--note")

    q = sub.add_parser("source")
    q.add_argument("file")
    q.add_argument("label")
    q.add_argument("--kind", choices=SOURCE_KINDS, default="other")
    q.add_argument("--date")
    q.add_argument("--url")
    q.add_argument("--note")

    q = sub.add_parser("entry")
    q.add_argument("file")
    q.add_argument("claim_id")
    q.add_argument("text")
    q.add_argument("--type", dest="evidence_type", choices=EVIDENCE_TYPES, required=True)
    q.add_argument("--stance", choices=STANCES, required=True)
    q.add_argument("--independence", choices=INDEPENDENCE, default="unknown")
    q.add_argument("--source", action="append", default=[])
    q.add_argument("--derived-from", action="append", default=[])
    q.add_argument("--note")

    for name in ("show", "check", "audit"):
        q = sub.add_parser(name)
        q.add_argument("file")

    for name in ("render", "matrix", "mermaid"):
        q = sub.add_parser(name)
        q.add_argument("file")
        q.add_argument("-o", "--output")

    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "new":
            if Path(args.file).exists():
                raise LedgerError(f"refusing to overwrite existing file: {args.file}")
            save(args.file, new_project(args.title))
            print(f"created {args.file}")
            return 0

        data = load(args.file)

        if args.command == "claim":
            cid = add_claim(data, args.text, args.note)
            save(args.file, data)
            print(cid)
        elif args.command == "source":
            sid = add_source(data, args.label, args.kind, args.date, args.url, args.note)
            save(args.file, data)
            print(sid)
        elif args.command == "entry":
            eid = add_entry(
                data, args.claim_id, args.text, args.evidence_type, args.stance,
                args.independence, args.source, args.derived_from, args.note,
            )
            save(args.file, data)
            print(eid)
        elif args.command == "show":
            print(summary(data))
        elif args.command == "check":
            print(f"ok: {args.file}")
        elif args.command == "audit":
            findings = audit(data)
            if findings:
                print("\n".join(findings))
            else:
                print("no structural audit flags")
        else:
            output = {
                "render": render_markdown,
                "matrix": render_matrix,
                "mermaid": render_mermaid,
            }[args.command](data)
            if args.output:
                Path(args.output).write_text(output, encoding="utf-8")
                print(args.output)
            else:
                print(output, end="")
        return 0
    except LedgerError as exc:
        print(f"evidence-ledger: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
