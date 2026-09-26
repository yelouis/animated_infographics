"""Tests for doctor checks, including mflux tool and model support."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from animated_infographics.cli import app

runner = CliRunner()


def test_doctor_missing_mflux_exits_4() -> None:
    with patch(
        "shutil.which", side_effect=lambda name: None if "mflux" in name else "/usr/bin/" + name
    ):
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 4
        assert "MISSING mflux-generate-flux2 on PATH" in result.stdout


def test_doctor_mflux_missing_klein_model_exits_4() -> None:
    def fake_which(name: str) -> str | None:
        if name == "mflux-generate-flux2":
            return "/bin/mflux-generate-flux2"
        return "/usr/bin/" + name

    mock_proc = MagicMock()
    mock_proc.stdout = "options: --model dev, schnell"
    mock_proc.stderr = ""
    mock_proc.returncode = 0

    with patch("shutil.which", side_effect=fake_which):
        with patch("subprocess.run", return_value=mock_proc):
            result = runner.invoke(app, ["doctor"])
            assert result.exit_code == 4
            assert "MISSING mflux-generate-flux2 with flux2-klein-4b support" in result.stdout
