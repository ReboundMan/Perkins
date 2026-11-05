from pathlib import Path

import pytest

from perkins import tracker as T

DOC = """# Job search tracker

Intro line that must survive.

## Submitted

| Submitted | Company | Role | Next follow-up |
|---|---|---|---|
| 2027-03-02 | Larkspur Analytics | [Director](https://jobs.example.com/a) | 2027-03-16 |

A note under the table.

## Considering

| Found | Company | Role | Resume | Status | Next step |
|---|---|---|---|---|---|
| 2027-03-01 | Kestrel Energy | Head of CS | Ready | Resume ready | Submit |
| 2027-03-01 | Kestrel Energy | VP of CS | Not built | Lead | Read |
"""


@pytest.fixture()
def tr(tmp_path):
    p = tmp_path / "tracker.md"
    p.write_text(DOC, encoding="utf-8")
    return T.Tracker.load(p)


def test_roundtrip_keeps_text(tr):
    tr.save()
    out = tr.path.read_text(encoding="utf-8")
    assert "Intro line that must survive." in out
    assert "A note under the table." in out
    assert T.Tracker.load(tr.path).table("Submitted").rows == tr.table("Submitted").rows


def test_add_goes_to_top_and_escapes_pipes(tr):
    tr.add("Submitted", {"Company": "Alder | Robotics", "Role": "VP\nPrograms"})
    tr.save()
    t = T.Tracker.load(tr.path).table("Submitted")
    assert T.plain(t.rows[0][1]) == "Alder \\| Robotics"
    assert t.rows[0][2] == "VP Programs"
    assert len(t.rows) == 2


def test_unknown_column_is_an_error(tr):
    with pytest.raises(T.TrackerError):
        tr.add("Submitted", {"Nope": "x"})


def test_find_ignores_links_and_case(tr):
    assert tr.find("Submitted", {"Role": "director"}) == [0]


def test_find_one_refuses_ambiguity(tr):
    with pytest.raises(T.TrackerError):
        tr.find_one("Considering", {"Company": "Kestrel"})
    assert tr.find_one("Considering", {"Company": "Kestrel", "Role": "VP"}) == 1


def test_move_carries_shared_columns(tr):
    idx = tr.find_one("Considering", {"Role": "Head of CS"})
    tr.move("Considering", "Submitted", idx, {"Submitted": "2027-03-04"})
    sub, con = tr.table("Submitted"), tr.table("Considering")
    assert sub.rows[0][:3] == ["2027-03-04", "Kestrel Energy", "Head of CS"]
    assert len(con.rows) == 1


def test_update_and_section_prefix(tr):
    tr.update("consid", 0, {"Status": "Held for the week ending 2027-03-13"})
    assert tr.table("Considering").get(tr.table("Considering").rows[0], "Status").startswith("Held")


def test_ensure_column_adds_empty_cells_once(tr):
    assert tr.ensure_column("Submitted", "Claim log", before="Next follow-up") is True
    assert tr.ensure_column("Submitted", "Claim log", before="Next follow-up") is False
    t = tr.table("Submitted")
    assert t.header == ["Submitted", "Company", "Role", "Claim log", "Next follow-up"]
    assert t.rows[0][3] == "" and t.rows[0][4] == "2027-03-16"


def test_split_row_handles_escaped_pipes():
    assert T.split_row("| a \\| b | c |") == ["a \\| b", "c"]


def test_missing_tracker_says_run_setup(tmp_path):
    with pytest.raises(T.TrackerError, match="setup"):
        T.Tracker.load(tmp_path / "nope.md")
