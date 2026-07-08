"""CLI surface: version flag alias + subcommand stay in sync."""
from __future__ import annotations

import pytest

from app import cli


def test_version_flag_exits_zero(capsys, monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["insightiq", "--version"])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 0
    assert f"insightiq {cli.__version__}" in capsys.readouterr().out


def test_version_subcommand(capsys, monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["insightiq", "version"])
    cli.main()
    assert f"insightiq {cli.__version__}" in capsys.readouterr().out
