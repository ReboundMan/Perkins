"""Look for personal information in a folder before it is shared: email addresses, phone
numbers, Social Security-shaped numbers, home-folder paths, Claude artifact links, and
real-looking job posting links. Optionally also a private list of exact strings that must
never appear (your name, your employers), kept outside the repository.

Run it on your own fork before you push, and on your data folder before you share any of it.
CLI: pii-check [PATH] [--blocklist FILE] [--allow FILE] [--history]
Exit 0 when clean, 1 when anything is found.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", "node_modules", ".venv", "venv", "reviews"}
# Folders whose contents are fictional by design (tests and examples use made-up employers on
# real job board hosts); only the posting-link pattern skips them.
FICTION_DIRS = ("tests/", "examples/")

PATTERNS = {
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "phone": re.compile(r"(?<![\d-])(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?![\d-])"),
    "ssn-shaped number": re.compile(r"(?<![\d-])\d{3}-\d{2}-\d{4}(?![\d-])"),
    "home-folder path": re.compile(r"[A-Za-z]:\\+Users\\+(?!<|Public\b|you\b|USERNAME\b)[^\\\s\"'`]+"
                                   r"|/(?:Users|home)/(?!<|you\b|runner\b|USER\b)[A-Za-z0-9._-]+"),
    "claude artifact link": re.compile(r"claude\.ai/(?:code/)?artifact/[A-Za-z0-9-]+"),
    "job posting link": re.compile(
        r"(?:greenhouse\.io/[\w-]+/jobs/\d+|ashbyhq\.com/[\w.-]+/[0-9a-f]{8}-[0-9a-f-]{27,}"
        r"|lever\.co/[\w-]+/[0-9a-f]{8}-[0-9a-f-]{27,}|myworkdayjobs\.com/[^\s)]*?/job/"
        r"|icims\.com/jobs/\d+|bamboohr\.com/careers/\d+|workable\.com/(?:j|view)/[A-Z0-9]{6,})"),
}
SAFE_EMAIL = re.compile(r"(?:@(?:example\.(?:com|org|net)|users\.noreply\.github\.com)$|^no-?reply@)", re.I)
SAFE_PHONE = re.compile(r"555[ .-]?01\d\d")  # the range reserved for fiction


def load_list(path: Path | None) -> list[str]:
    if not path or not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            out.append(s)
    return out


def files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            yield Path(dirpath) / name


def is_binary(data: bytes) -> bool:
    return b"\x00" in data[:8192]


def scan_text(text: str, where: str, rel: str, block: list[str], allow: list[str]) -> list[str]:
    hits = []
    for n, line in enumerate(text.splitlines(), 1):
        # Allowed strings are removed first, so an allowed phrase can't trip either check.
        for a in allow:
            line = re.sub(re.escape(a), " ", line, flags=re.I)
        for kind, rx in PATTERNS.items():
            if kind == "job posting link" and rel.replace("\\", "/").startswith(FICTION_DIRS):
                continue
            for m in rx.finditer(line):
                s = m.group(0)
                if kind == "email" and SAFE_EMAIL.search(s):
                    continue
                if kind == "phone" and SAFE_PHONE.search(s):
                    continue
                hits.append(f"{where}:{n}: {kind}: {s}")
        low = line.lower()
        hits += [f"{where}:{n}: blocklisted: {b}" for b in block if b.lower() in low]
    return hits


def scan_tree(root: Path, block: list[str], allow: list[str]) -> list[str]:
    hits = []
    for path in files(root):
        rel = str(path.relative_to(root))
        data = path.read_bytes()
        if is_binary(data):
            text = data.decode("latin-1").lower()
            hits += [f"{rel}: blocklisted (binary): {b}" for b in block if b.lower() in text]
            continue
        hits += scan_text(data.decode("utf-8", errors="replace"), rel, rel, block, allow)
    return hits


def scan_history(root: Path, block: list[str], allow: list[str]) -> list[str]:
    """Every commit on every branch and tag: author and committer, message, and diff."""
    out = subprocess.run(["git", "-C", str(root), "log", "--all", "-p", "--format=commit %H%nauthor %an <%ae>%ncommitter %cn <%ce>%n%B"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    if out.returncode != 0:
        return [f"git log failed: {out.stderr.strip()}"]
    hits, commit, path = [], "?", ""
    for line in out.stdout.splitlines():
        if line.startswith("commit "):
            commit, path = line[7:15], ""
        elif line.startswith("+++ ") or line.startswith("--- "):
            target = line[4:].strip()
            if target != "/dev/null":
                path = target[2:] if target[:2] in ("a/", "b/") else target
            continue
        elif line.startswith("diff --git ") or line.startswith("index ") or line.startswith("@@"):
            continue
        if path and line[:1] in "+- ":
            # A changed or context line inside a file's diff: judge it as that file's text.
            hits += scan_text(line[1:], f"history {commit} {path}", path, block, allow)
        elif not path:
            # Commit header: author, committer, and message.
            hits += scan_text(line, f"history {commit}", "history", block, allow)
    return sorted(set(hits))


def add_arguments(p) -> None:
    p.add_argument("path", nargs="?", default=".", help="folder to check (default: current folder)")
    p.add_argument("--blocklist", type=Path, help="a private file of exact strings that must never appear")
    p.add_argument("--allow", type=Path, help="strings that are fine (default: .pii-allow in the folder)")
    p.add_argument("--history", action="store_true", help="also check every commit in the folder's git history")


def cli(args, cfg=None, today=None) -> int:
    root = Path(args.path).resolve()
    allow = load_list(args.allow or (root / ".pii-allow"))
    block = load_list(args.blocklist)
    hits = scan_tree(root, block, allow)
    if args.history:
        hits += scan_history(root, block, allow)
    for h in hits:
        print(h)
    print(f"{len(hits)} finding{'s' if len(hits) != 1 else ''} in {root}")
    return 1 if hits else 0
