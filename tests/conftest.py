"""Make the repo root importable, and keep every test away from the real home folder."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _no_real_home(tmp_path_factory, monkeypatch):
    """No test may read or write ~/.perkins or depend on PERKINS_HOME."""
    from perkins import config
    monkeypatch.setattr(config, "POINTER", tmp_path_factory.mktemp("pointer") / ".perkins")
    monkeypatch.delenv("PERKINS_HOME", raising=False)
