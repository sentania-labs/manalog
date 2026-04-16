"""Parser stub tests — .dat returns None, text log extracts win/loss."""
from __future__ import annotations

from pathlib import Path

from agent.parser import (
    ParsedMatch,
    parse_dat_file,
    parse_file,
    parse_text_log,
)


def test_parse_dat_returns_none(tmp_path: Path) -> None:
    dat = tmp_path / "GameLog_sample.dat"
    dat.write_bytes(b"\x00\x01\x02\x03")
    assert parse_dat_file(dat) is None


def test_parse_text_log_returns_none_on_empty(tmp_path: Path) -> None:
    log = tmp_path / "empty.log"
    log.write_text("")
    assert parse_text_log(log) is None


def test_parse_text_log_returns_none_on_unrecognized(tmp_path: Path) -> None:
    log = tmp_path / "unrecognized.log"
    log.write_text("nothing interesting happened here\njust random lines\n")
    assert parse_text_log(log) is None


def test_parse_text_log_win(tmp_path: Path) -> None:
    log = tmp_path / "match.log"
    log.write_text(
        "Opponent: scott_b\n"
        "Format: modern\n"
        "testplayer wins the match\n"
    )
    result = parse_text_log(log)
    assert result is not None
    assert isinstance(result, ParsedMatch)
    assert result.result == "win"
    assert result.format == "modern"
    assert result.opponent == "scott_b"


def test_parse_text_log_loss(tmp_path: Path) -> None:
    log = tmp_path / "loss.log"
    log.write_text("testplayer loses the match\n")
    result = parse_text_log(log)
    assert result is not None
    assert result.result == "loss"


def test_parse_file_fallback(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.dat"
    assert parse_file(missing) is None


def test_parse_file_text_fallback(tmp_path: Path) -> None:
    log = tmp_path / "GameLog_trailing.log"
    log.write_text("testplayer wins the match\n")
    result = parse_file(log)
    assert result is not None
    assert result.result == "win"
