import subprocess
from pathlib import Path

from perkins import pii_check as P


def hits_for(tmp_path, rel, text, block=(), allow=()):
    f = tmp_path / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text, encoding="utf-8")
    return P.scan_tree(tmp_path, list(block), list(allow))


def test_finds_each_kind(tmp_path):
    text = "\n".join([
        "mail me at someone@mailhost.co",
        "call 206-555-2368",
        "ssn 123-45-6789",
        r"path C:\Users\alex\Documents",
        "path /home/alex/notes",
        "https://claude.ai/artifact/abc123",
        "https://job-boards.greenhouse.io/acme/jobs/12345",
    ])
    kinds = {h.split(": ")[1] for h in hits_for(tmp_path, "a.md", text)}
    assert kinds == {"email", "phone", "ssn-shaped number", "home-folder path", "claude artifact link", "job posting link"}


def test_fiction_is_fine(tmp_path):
    text = ("jordan@example.com, (503) 555-0142, ~/job-search, /home/you/x, C:\\Users\\<you>\\x, "
            "123+name@users.noreply.github.com, noreply@example.org, 2027-03-10")
    assert hits_for(tmp_path, "a.md", text) == []


def test_posting_links_are_fine_in_fixtures_and_examples(tmp_path):
    link = "https://job-boards.greenhouse.io/larkspur/jobs/4242"
    assert hits_for(tmp_path, "tests/test_x.py", link) == []
    assert hits_for(tmp_path, "examples/x.md", link) == []
    assert hits_for(tmp_path, "docs/x.md", link) != []


def test_blocklist_and_allow(tmp_path):
    assert hits_for(tmp_path, "a.md", "Hello Pat Example", block=["pat example"])
    assert not hits_for(tmp_path, "b/a.md", "Hello Pat Example", block=["pat example"], allow=["Hello Pat Example"])


def test_blocklist_reaches_binaries(tmp_path):
    (tmp_path / "x.bin").write_bytes(b"\x00\x01Pat Example\x00")
    assert P.scan_tree(tmp_path, ["pat example"], []) == ["x.bin: blocklisted (binary): pat example"]


def test_history_scan_sees_old_commits_and_authors(tmp_path):
    def git(*a):
        subprocess.run(["git", "-C", str(tmp_path), *a], check=True, capture_output=True)
    git("init", "-q")
    git("config", "user.name", "Test")
    git("config", "user.email", "someone@mailhost.co")
    (tmp_path / "a.md").write_text("Pat Example\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-qm", "first")
    (tmp_path / "a.md").write_text("clean\n", encoding="utf-8")
    git("commit", "-qam", "second")
    assert P.scan_tree(tmp_path, ["pat example"], []) == []
    hist = P.scan_history(tmp_path, ["pat example"], [])
    assert any("blocklisted: pat example" in h for h in hist)
    assert any("email" in h for h in hist)


def test_reserved_test_domains_are_not_personal(tmp_path):
    assert hits_for(tmp_path, "a.md", "jane@realmail.test and pat@site.example and x@y.invalid") == []
