import base64
import json

import pytest

from perkins import sync_check as Y

DOC = "doc-123"


def export_line(name, text, stamp="2027-03-10T10:00:00Z", doc=DOC):
    raw = text.encode("utf-8")
    result = {"verdict": "allow", "rev": 7, "frame": {"slug": doc},
              "data": {"name": f"{name}.md", "format": "markdown", "bytes": len(raw),
                       "bytes_b64": base64.b64encode(raw).decode()}}
    entry = {"type": "user", "timestamp": stamp,
             "message": {"content": [{"type": "tool_result", "content": [{"type": "text", "text": json.dumps(result)}]}]}}
    return json.dumps(entry)


def transcript(tmp_path, *lines):
    p = tmp_path / "t.jsonl"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def test_match_ignores_line_endings_and_trailing_space(tmp_path):
    (tmp_path / "master.md").write_bytes(b"# Jordan\r\n\r\nLine  \r\n")
    t = transcript(tmp_path, export_line("Master resume", "# Jordan\n\nLine\n\n"))
    bad, out = Y.check_pairs(tmp_path, DOC, {"Master resume": "master.md"}, t)
    assert bad == 0 and out[0].startswith("OK")


def test_newest_export_wins_and_a_mismatch_is_shown(tmp_path):
    (tmp_path / "master.md").write_text("# Jordan\n\nTeam of 40\n", encoding="utf-8")
    t = transcript(tmp_path,
                   export_line("Master resume", "# Jordan\n\nTeam of 40\n", "2027-03-10T10:00:00Z"),
                   export_line("Master resume", "# Jordan\n\nTeam of 35\n", "2027-03-10T11:00:00Z"))
    bad, out = Y.check_pairs(tmp_path, DOC, {"Master resume": "master.md"}, t)
    assert bad == 1 and out[0].startswith("MISMATCH") and any("Team of 35" in l for l in out)


def test_other_docs_and_missing_exports_fail_closed(tmp_path):
    (tmp_path / "master.md").write_text("x\n", encoding="utf-8")
    t = transcript(tmp_path, export_line("Master resume", "x\n", doc="someone-else"))
    bad, out = Y.check_pairs(tmp_path, DOC, {"Master resume": "master.md"}, t)
    assert bad == 1 and out[0].startswith("NOT EXPORTED")


def test_no_doc_id_is_an_error(tmp_path):
    with pytest.raises(Y.SyncError, match="docs_id"):
        Y.check_pairs(tmp_path, "", {"Master resume": "master.md"}, tmp_path / "t.jsonl")


def test_no_session_id_is_an_error(monkeypatch):
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
    with pytest.raises(Y.SyncError, match="CLAUDE_CODE_SESSION_ID"):
        Y.transcripts()
