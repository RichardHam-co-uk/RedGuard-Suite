import json
from pathlib import Path

import pytest

from redguard import cli


def test_main_with_config_returns_zero(config_file: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("sys.argv", ["redguard", "--config", str(config_file)])
    assert cli.main() == 0


def test_main_uses_default_config_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Build the default config location relative to a temp cwd so the test is hermetic.
    default = Path("configs") / "config.public.example.json"
    target = tmp_path / default
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"targets": ["example.com"], "modules": {}}), encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["redguard"])
    assert cli.main() == 0


def test_main_missing_config_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    missing = tmp_path / "does_not_exist.json"
    monkeypatch.setattr("sys.argv", ["redguard", "--config", str(missing)])
    with pytest.raises(FileNotFoundError):
        cli.main()
