from __future__ import annotations

import io
import json

from redline.cli import main


def test_cli_offline_emits_json(tmp_path, capsys) -> None:
    contract = tmp_path / "c.txt"
    contract.write_text(
        "Payment is net 90 days. Client may request unlimited revisions.",
        encoding="utf-8",
    )

    assert main([str(contract), "--offline", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["overall_risk"] == "high"
    assert data["model"] is None
    assert data["findings"]


def test_cli_offline_markdown(tmp_path, capsys) -> None:
    contract = tmp_path / "c.txt"
    contract.write_text("Designer shall indemnify and hold harmless Client.", encoding="utf-8")

    assert main([str(contract), "--offline"]) == 0
    out = capsys.readouterr().out
    assert "# Redline report" in out
    assert "Indemnity" in out


def test_cli_missing_file(capsys) -> None:
    assert main(["does-not-exist.txt", "--offline"]) == 1
    assert "cannot read" in capsys.readouterr().err


def test_cli_empty_input_errors(monkeypatch, capsys) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("   \n"))
    assert main(["-", "--offline"]) == 1
    assert "empty" in capsys.readouterr().err.lower()
