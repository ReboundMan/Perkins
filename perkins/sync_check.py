"""Check that Claude Docs tabs match their Markdown files (the optional Docs mirror).

The Docs connector's `export` tool returns a tab's Markdown inline as base64. Rather than
have anyone retype it, this reads the exports straight from the Claude Code session's
transcript (~/.claude/projects/*/<session id>.jsonl, plus its subagents), keeping the
newest export of each tab, and diffs it with the file after normalizing line endings and
trailing whitespace. The transcript format belongs to Claude Code and may change; if it
does, this fails closed (it reports the export as missing).

CLI:
  sync-check --pair "Master resume=master.md" [--pair "TAB=FILE" ...] [--transcript PATH]
  sync-check --compare A.md B.md
Exit 0 when every pair matches, 1 on any mismatch or missing export, 2 when nothing to check.
"""
from __future__ import annotations

import base64
import difflib
import json
import os
from pathlib import Path

PROJECTS = Path.home() / ".claude" / "projects"


class SyncError(Exception):
    """The check could not run; the message says why."""


def norm(text: str) -> list[str]:
    lines = [l.rstrip() for l in text.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    while lines and not lines[-1]:
        lines.pop()
    return lines


def diff(a_text: str, b_text: str, a_name: str, b_name: str) -> list[str]:
    return list(difflib.unified_diff(norm(a_text), norm(b_text), a_name, b_name, lineterm="", n=0))


def transcripts() -> list[Path]:
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID", "").strip()
    if not sid:
        raise SyncError("CLAUDE_CODE_SESSION_ID is not set: run this from the Claude Code session that did the exports, or pass --transcript.")
    main = sorted(PROJECTS.glob(f"*/{sid}.jsonl"))
    if not main:
        raise SyncError(f"No transcript for session {sid} under {PROJECTS}.")
    return main + sorted(PROJECTS.glob(f"*/{sid}/subagents/*.jsonl"))


def exports(paths: list[Path], doc_id: str) -> dict:
    """The newest Markdown export of each tab of one doc, by tab name."""
    found = {}
    for path in paths:
        with path.open(encoding="utf-8") as f:
            for line in f:
                if "bytes_b64" not in line:
                    continue
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                content = (entry.get("message") or {}).get("content")
                if entry.get("type") != "user" or not isinstance(content, list):
                    continue
                for part in content:
                    if not isinstance(part, dict) or part.get("type") != "tool_result":
                        continue
                    texts = part.get("content")
                    texts = [texts] if isinstance(texts, str) else [t.get("text", "") for t in texts or [] if isinstance(t, dict)]
                    for text in texts:
                        try:
                            result = json.loads(text)
                        except ValueError:
                            continue
                        if not isinstance(result, dict):
                            continue
                        data = result.get("data")
                        if ((result.get("frame") or {}).get("slug") != doc_id or not isinstance(data, dict)
                                or data.get("format") != "markdown" or "bytes_b64" not in data):
                            continue
                        raw = base64.b64decode(data["bytes_b64"])
                        if data.get("bytes") is not None and len(raw) != data["bytes"]:
                            raise SyncError(f"Export of {data.get('name')} decodes to {len(raw)} bytes, not {data['bytes']}.")
                        tab = str(data.get("name", "")).removesuffix(".md")
                        stamp = entry.get("timestamp", "")
                        if tab not in found or stamp >= found[tab]["stamp"]:
                            found[tab] = {"text": raw.decode("utf-8"), "rev": result.get("rev"), "stamp": stamp}
    return found


def check_pairs(home: Path, doc_id: str, pairs: dict, transcript: Path | None = None) -> tuple[int, list[str]]:
    if not doc_id:
        raise SyncError("docs_id is empty in perkins.toml, so there is no Docs mirror to check.")
    found = exports([transcript] if transcript else transcripts(), doc_id)
    bad, out = 0, []
    for tab, rel in pairs.items():
        md = (home / rel) if not Path(rel).is_absolute() else Path(rel)
        if tab not in found:
            out.append(f"NOT EXPORTED  {tab}: export it with format markdown, then run this again")
            bad += 1
        elif not md.exists():
            out.append(f"NO MARKDOWN   {tab}: expected {md}")
            bad += 1
        else:
            d = diff(md.read_text(encoding="utf-8"), found[tab]["text"], f"{md.name} (Markdown)",
                     f"{tab} (Docs, rev {found[tab]['rev']})")
            if d:
                out.append(f"MISMATCH      {tab}")
                out += ["    " + l for l in d]
                bad += 1
            else:
                out.append(f"OK            {tab} (Docs rev {found[tab]['rev']})")
    return bad, out


def add_arguments(p) -> None:
    p.add_argument("--pair", action="append", default=[], metavar="TAB=FILE",
                   help="a Docs tab name and its Markdown file (relative to the data folder)")
    p.add_argument("--transcript", type=Path, help="read exports from this transcript file")
    p.add_argument("--compare", nargs=2, metavar=("A", "B"), help="compare two Markdown files directly")


def cli(args, cfg, today=None) -> int:
    if args.compare:
        a, b = (Path(x) for x in args.compare)
        d = diff(a.read_text(encoding="utf-8"), b.read_text(encoding="utf-8"), str(a), str(b))
        print("\n".join(d) if d else "OK  the two files match")
        return 1 if d else 0
    pairs = {}
    for p in args.pair:
        if "=" not in p:
            raise SyncError(f"--pair takes TAB=FILE, not {p!r}")
        tab, f = p.split("=", 1)
        pairs[tab.strip()] = f.strip()
    if not pairs:
        print("Nothing to check: pass at least one --pair.")
        return 2
    bad, out = check_pairs(cfg.home, cfg.docs_id, pairs, args.transcript)
    print("\n".join(out))
    return 1 if bad else 0
