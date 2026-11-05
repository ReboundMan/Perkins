from datetime import date

import pytest

from perkins import config as C
from perkins import init as I
from perkins import tracker as T
from helpers import claims_home, make_home

TODAY = date(2027, 3, 10)


def test_search_is_clean(tmp_path):
    cfg = make_home(tmp_path)
    assert cfg.mode == C.SEARCH
    assert not cfg.log_dir.exists() and not cfg.nudges.exists()
    tr = T.Tracker.load(cfg.tracker)
    assert not tr.table(T.SUBMITTED).has(T.CLAIM_COL)
    assert cfg.dashboard.exists() and "class='claim-panel'" not in cfg.dashboard.read_text(encoding="utf-8")
    for f in ("master.md", "tailoring-model.md", "style.md", "fact-sheet.md", "tracker.md", "perkins.toml"):
        assert (tmp_path / f).exists()


def test_claims_adds_the_claim_pieces(tmp_path):
    cfg = claims_home(tmp_path, today=TODAY)
    assert cfg.claims and cfg.state == "wa" and cfg.claim_start == date(2027, 2, 28)
    assert cfg.log_dir.is_dir() and cfg.evidence_dir.is_dir() and cfg.nudges.exists()
    tr = T.Tracker.load(cfg.tracker)
    for name in T.CLAIM_TABLES:
        h = tr.table(name).header
        assert h.index(T.CLAIM_COL) == h.index("Next follow-up") - 1
    assert (cfg.log_dir / "week-ending-2027-03-13.md").exists()


def test_switching_on_never_edits_existing_rows(tmp_path):
    cfg = make_home(tmp_path)
    tr = T.Tracker.load(cfg.tracker)
    tr.add(T.SUBMITTED, {"Submitted": "2027-03-02", "Company": "Larkspur Analytics", "Status": "Applied"})
    tr.save()
    before = {name: T.Tracker.load(cfg.tracker).table(name).dicts() for name in T.CLAIM_TABLES}
    claims_home(tmp_path, today=TODAY)
    after = T.Tracker.load(cfg.tracker)
    for name in T.CLAIM_TABLES:
        t = after.table(name)
        assert all(len(r) == len(t.header) for r in t.rows), f"{name}: a row is wider than its header"
        rows = t.dicts()
        assert [{k: v for k, v in r.items() if k != T.CLAIM_COL} for r in rows] == before[name]
        assert all(r[T.CLAIM_COL] == "" for r in rows)
    row = after.table(T.SUBMITTED).dicts()[0]
    assert row["Company"] == "Larkspur Analytics" and row["Status"] == "Applied"
    assert "\\|" not in cfg.tracker.read_text(encoding="utf-8")


def test_switching_off_keeps_the_log_byte_identical(tmp_path):
    cfg = claims_home(tmp_path, today=TODAY)
    week = cfg.log_dir / "week-ending-2027-03-13.md"
    before = week.read_bytes()
    I.init(tmp_path, C.SEARCH, date(2027, 3, 20), claim_end=date(2027, 3, 13), pointer=False)
    after = C.load(tmp_path)
    assert after.mode == C.SEARCH and after.claim_end == date(2027, 3, 13)
    assert week.read_bytes() == before


def test_init_never_overwrites_your_files(tmp_path):
    make_home(tmp_path)
    (tmp_path / "master.md").write_text("mine", encoding="utf-8")
    make_home(tmp_path)
    assert (tmp_path / "master.md").read_text(encoding="utf-8") == "mine"


def test_unknown_state_is_refused_with_the_known_ones(tmp_path):
    with pytest.raises(C.ConfigError, match="wa"):
        make_home(tmp_path, C.CLAIMS, state="zz")


def test_weekly_target_rises_to_the_state_minimum(tmp_path):
    cfg = make_home(tmp_path)
    cfg.weekly_target = 1
    C.save(cfg)
    assert claims_home(tmp_path, today=TODAY).weekly_target == 3


def test_pointer_is_written_only_when_asked(tmp_path):
    make_home(tmp_path)
    assert not C.POINTER.exists()
    I.init(tmp_path, C.SEARCH, TODAY, pointer=True)
    assert C.POINTER.read_text(encoding="utf-8").strip() == str(tmp_path.resolve())
    assert C.find_home() == tmp_path.resolve()


def test_config_round_trips(tmp_path):
    cfg = claims_home(tmp_path, today=TODAY)
    cfg.scan = {"interval_days": 10, "exclude": ["Intern"]}
    C.save(cfg)
    again = C.load(tmp_path)
    assert again.scan == {"interval_days": 10, "exclude": ["Intern"]}
    assert again.claim_start == cfg.claim_start


def test_bad_config_values_say_what_to_fix(tmp_path):
    make_home(tmp_path)
    p = tmp_path / "perkins.toml"
    p.write_text(p.read_text(encoding="utf-8").replace('mode = "search"', 'mode = "hunt"'), encoding="utf-8")
    with pytest.raises(C.ConfigError, match="mode"):
        C.load(tmp_path)


def test_missing_config_points_to_setup(tmp_path):
    with pytest.raises(C.ConfigError, match="setup"):
        C.load(tmp_path)


def test_every_state_file_loads():
    for code in C.available_states():
        st = C.load_state(code)
        assert st.required > 0 and st.sources and st.last_checked and st.kinds
