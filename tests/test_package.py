"""The plugin as shipped: the CLI, the manifests, the skills, and the house rules for text."""
import json
import re
from pathlib import Path

import pytest

import run as R
from perkins import __version__

ROOT = Path(__file__).resolve().parents[1]
SKILLS = sorted((ROOT / "skills").glob("*/SKILL.md"))
TEXT_SUFFIXES = {".md", ".py", ".toml", ".json", ".yml", ".html", ".txt"}


def call(capsys, *argv):
    code = R.main(list(argv))
    return code, capsys.readouterr()


def test_version_and_states(capsys):
    code, out = call(capsys, "version")
    assert code == 0 and __version__ in out.out
    code, out = call(capsys, "states")
    assert code == 0 and out.out.startswith("wa  Washington (ESD): 3 activities a week")


def test_cli_end_to_end(tmp_path, capsys):
    d = str(tmp_path)
    assert call(capsys, "--data", d, "--today", "2027-03-10", "init", "--no-pointer", "--mode", "search-claims",
                "--state", "wa", "--claim-start", "2027-03-01")[0] == 0
    assert call(capsys, "--data", d, "--today", "2027-03-10", "tracker", "add", "Considering",
                "--set", "Company=Larkspur Analytics", "--set", "Role=Director", "--set", "Resume=Ready")[0] == 0
    code, out = call(capsys, "--data", d, "--today", "2027-03-10", "status", "--json")
    r = json.loads(out.out)
    assert code == 0 and r["resumes_ready"] == ["Larkspur Analytics, Director"]
    assert "Larkspur Analytics" in (tmp_path / "dashboard.html").read_text(encoding="utf-8")


def test_user_errors_exit_2_with_a_message(tmp_path, capsys):
    code, out = call(capsys, "--data", str(tmp_path), "status")
    assert code == 2 and "setup" in out.err


def test_manifests_agree():
    plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    assert plugin["name"] == "perkins" and plugin["version"] == __version__
    (entry,) = market["plugins"]
    assert entry["name"] == "perkins" and entry["source"] == "./" and entry["version"] == __version__
    assert market["name"] == "perkins"


def test_version_has_one_source_and_every_copy_matches_it():
    """VERSION is the one place the version is set; a bump that misses a copy fails here."""
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert re.fullmatch(r"\d+\.\d+\.\d+", version), "VERSION must be plain semver, such as 0.2.0"
    assert __version__ == version
    assert f"**Version:** {version}" in (ROOT / "spec" / "SPEC.md").read_text(encoding="utf-8")
    log = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [Unreleased]" in log, "CHANGELOG.md keeps an [Unreleased] section (Keep a Changelog)"
    released = re.findall(r"^## \[(\d+\.\d+\.\d+)\] - \d{4}-\d{2}-\d{2}$", log, re.M)
    assert released and released[0] == version, "the newest dated CHANGELOG section must be VERSION"


@pytest.mark.parametrize("skill", SKILLS, ids=lambda p: p.parent.name)
def test_skill_frontmatter(skill):
    text = skill.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert m, "missing frontmatter"
    fm = dict(line.split(": ", 1) for line in m.group(1).splitlines())
    assert fm["name"] == skill.parent.name
    assert len(fm["description"]) > 80
    assert '${CLAUDE_PLUGIN_ROOT}/run.py' in fm["allowed-tools"]


def test_every_cli_command_a_skill_uses_exists():
    known = set(R.COMMANDS) | {"init", "version", "states"}
    for skill in SKILLS:
        for cmd in re.findall(r"run\.py\"? ([a-z][a-z-]*)", skill.read_text(encoding="utf-8")):
            if cmd.startswith("-"):
                continue
            assert cmd in known, f"{skill.parent.name} uses unknown command {cmd!r}"


def test_no_em_dashes_anywhere():
    bad = []
    for p in ROOT.rglob("*"):
        if p.suffix in TEXT_SUFFIXES and ".git" not in p.parts and "__pycache__" not in p.parts:
            if chr(0x2014) in p.read_text(encoding="utf-8", errors="replace"):
                bad.append(str(p.relative_to(ROOT)))
    assert bad == []
