"""Look for personal information in a folder before it is shared: email addresses, phone
numbers, Social Security-shaped numbers, home-folder paths, Claude artifact links,
real-looking job posting links, and leaked keys or tokens. Optionally also a private list
of exact strings that must never appear (your name, your employers), kept outside the
repository.

It fails closed: a list file or folder that doesn't exist is an error, not a clean result,
and a file it can't read as text is reported, not skipped.

Run it on your own fork before you push, and on your data folder before you share any of it.
CLI: pii-check [PATH] [--blocklist FILE] [--allow FILE] [--history]
Exit 0 when clean, 1 when anything is found, 2 when it couldn't run.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from .errors import PerkinsError

SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", "node_modules", ".venv", "venv", "reviews"}
# Folders whose contents are fictional by design (tests and examples use made-up employers on
# real job board hosts); only the posting-link pattern skips them.
FICTION_DIRS = ("tests/", "examples/")

PATTERNS = {
    # The lookbehind anchors the match start, which keeps this linear on long tokens.
    "email": re.compile(r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]{1,255}\.[A-Za-z]{2,}"),
    "phone": re.compile(r"(?<![\d-])(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?![\d-])"),
    "ssn-shaped number": re.compile(r"(?<![\d-])\d{3}-\d{2}-\d{4}(?![\d-])"),
    "home-folder path": re.compile(r"[A-Za-z]:\\+Users\\+(?!<|Public\b|you\b|USERNAME\b)[^\\\s\"'`]+"
                                   r"|/(?:Users|home)/(?!<|you\b|runner\b|USER\b)[A-Za-z0-9._-]+"),
    "claude artifact link": re.compile(r"claude\.ai/(?:code/)?artifact/[A-Za-z0-9-]+"),
    "job posting link": re.compile(
        r"(?:greenhouse\.io/[\w-]+/jobs/\d+|ashbyhq\.com/[\w.-]+/[0-9a-f]{8}-[0-9a-f-]{27,}"
        r"|lever\.co/[\w-]+/[0-9a-f]{8}-[0-9a-f-]{27,}|myworkdayjobs\.com/[^\s)]*?/job/"
        r"|icims\.com/jobs/\d+|bamboohr\.com/careers/\d+|workable\.com/(?:j|view)/[A-Z0-9]{6,})"),
    "key or token": re.compile(
        r"(?:\bgh[pousr]_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{40,}|\bsk-[A-Za-z0-9_-]{20,}"
        r"|\bAKIA[0-9A-Z]{16}\b|\bxox[abprs]-[A-Za-z0-9-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)"),
}
# Not personal: the example domains, GitHub no-reply addresses, no-reply senders, and the
# top-level domains reserved for testing and documentation (RFC 2606: .test, .example, .invalid, .localhost).
SAFE_EMAIL = re.compile(r"(?:@(?:example\.(?:com|org|net)|users\.noreply\.github\.com)$|^no-?reply@|\.(?:test|example|invalid|localhost)$)", re.I)
SAFE_PHONE = re.compile(r"555[ .-]?01\d\d")  # the range reserved for fiction


class PiiError(PerkinsError):
    """The check couldn't run as asked."""


def load_list(path: Path | None, required: bool) -> list[str]:
    if not path:
        return []
    if not path.is_file():
        if required:
            raise PiiError(f"{path} doesn't exist. A missing list would make the check pass, so it stops instead.")
        return []
    return [s for s in (l.strip() for l in path.read_text(encoding="utf-8").splitlines()) if s and not s.startswith("#")]


def files(root: Path):
    if root.is_file():
        yield root
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            yield Path(dirpath) / name


def decode(data: bytes) -> str | None:
    """Text from bytes: UTF-8, or UTF-16 (with a BOM, or the NUL pattern Windows tools write).
    None means it isn't text."""
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16", errors="replace")
    head = data[:4096]
    if head and head.count(b"\x00") > len(head) // 4:
        for enc in ("utf-16-le", "utf-16-be"):
            try:
                text = data.decode(enc)
            except UnicodeDecodeError:
                continue
            if text and sum(c.isprintable() or c.isspace() for c in text[:2000]) / min(len(text), 2000) > 0.9:
                return text
        return None
    if b"\x00" in head:
        return None
    return data.decode("utf-8", errors="replace")


def mask(kind: str, s: str) -> str:
    if kind == "ssn-shaped number":
        return s[:3] + "-**-****"
    if kind == "key or token":
        return s[:6] + "..."
    return s


def allowed(found: str, line: str, allow: list[str]) -> bool:
    """A finding is excused only by an allow entry that contains the found text and appears on
    the same line. A short entry ("Jane", "com") can't hide a longer finding."""
    low_line, low_found = line.lower(), found.lower()
    return any(a.lower() in low_line and low_found in a.lower() for a in allow)


def scan_text(text: str, where: str, rel: str, block: list[str], allow: list[str]) -> list[str]:
    hits = []
    fiction = rel.replace("\\", "/").startswith(FICTION_DIRS)
    for n, line in enumerate(text.split("\n"), 1):
        for kind, rx in PATTERNS.items():
            if kind == "job posting link" and fiction:
                continue
            for m in rx.finditer(line):
                s = m.group(0)
                if (kind == "email" and SAFE_EMAIL.search(s)) or (kind == "phone" and SAFE_PHONE.search(s)):
                    continue
                if not allowed(s, line, allow):
                    hits.append(f"{where}:{n}: {kind}: {mask(kind, s)}")
        low = line.lower()
        hits += [f"{where}:{n}: blocklisted: {b}" for b in block if b.lower() in low and not allowed(b, line, allow)]
    return hits


def scan_tree(root: Path, block: list[str], allow: list[str]) -> list[str]:
    hits = []
    base = root if root.is_dir() else root.parent
    for path in files(root):
        rel = str(path.relative_to(base))
        data = path.read_bytes()
        text = decode(data)
        if text is None:
            raw = data.decode("latin-1").lower()
            found = [b for b in block if b.lower() in raw]
            hits += [f"{rel}: blocklisted (binary): {b}" for b in found]
            if not found and not any(rel.replace("\\", "/") == a for a in allow):
                hits.append(f"{rel}: binary file, not checked for patterns (review it by hand, or list its path in .pii-allow)")
            continue
        hits += scan_text(text, rel, rel, block, allow)
    return hits


def scan_history(root: Path, block: list[str], allow: list[str]) -> list[str]:
    """Every commit on every branch and tag: author, committer, message, and each changed line,
    judged as text of the file it belongs to."""
    out = subprocess.run(["git", "-C", str(root), "log", "--all", "-p", "--format=commit %H%nauthor %an <%ae>%ncommitter %cn <%ce>%n%B"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    if out.returncode != 0:
        raise PiiError(f"git log failed: {out.stderr.strip()}")
    hits, commit, path, in_header = [], "?", "", False
    for line in out.stdout.split("\n"):
        if line.startswith("commit ") and not in_header:
            commit, path = line[7:15], ""
            continue
        if line.startswith("diff --git "):
            in_header, path = True, ""
            continue
        if in_header:
            # Diff headers run from "diff --git" to the first hunk; only here do ---/+++ name files.
            if line.startswith("+++ ") or line.startswith("--- "):
                target = line[4:].strip()
                if target != "/dev/null":
                    path = target[2:] if target[:2] in ("a/", "b/") else target
            elif line.startswith("@@"):
                in_header = False
            continue
        if path and line[:1] in "+- ":
            if line.startswith("@@"):
                continue
            hits += scan_text(line[1:], f"history {commit} {path}", path, block, allow)
        elif line.startswith("@@") and path:
            continue
        elif not path:
            hits += scan_text(line, f"history {commit}", "history", block, allow)
    return sorted(set(hits))


def add_arguments(p) -> None:
    p.add_argument("path", nargs="?", default=".", help="folder or file to check (default: current folder)")
    p.add_argument("--blocklist", type=Path, help="a private file of exact strings that must never appear")
    p.add_argument("--allow", type=Path, help="strings that are fine (default: .pii-allow in the folder)")
    p.add_argument("--history", action="store_true", help="also check every commit in the folder's git history")


def cli(args, cfg=None, today=None) -> int:
    root = Path(args.path).resolve()
    if not root.exists():
        raise PiiError(f"{root} doesn't exist, so there's nothing to check.")
    base = root if root.is_dir() else root.parent
    allow = load_list(args.allow, required=True) if args.allow else load_list(base / ".pii-allow", required=False)
    block = load_list(args.blocklist, required=True)
    hits = scan_tree(root, block, allow)
    if args.history:
        hits += scan_history(base, block, allow)
    for h in hits:
        print(h)
    print(f"{len(hits)} finding{'s' if len(hits) != 1 else ''} in {root}")
    return 1 if hits else 0
