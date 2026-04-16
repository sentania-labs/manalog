"""MTGO log parser — stub.

The binary .dat format isn't reverse-engineered yet. parse_dat_file is a
typed stub that logs a TODO and returns None. parse_text_log handles a
subset of MTGO's plaintext logs enough to produce a partial ParsedMatch
with a win/loss result.

Both functions feed parse_file, which tries the binary path first and
falls back to text.
"""
from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path


logger = logging.getLogger(__name__)


@dataclass
class ParsedPlay:
    turn: int
    caster: str
    action_type: str
    card_name: str
    targets: list[str] = field(default_factory=list)


@dataclass
class ParsedGame:
    game_number: int
    on_play: bool | None = None
    mulligans: int = 0
    winner: str | None = None
    plays: list[ParsedPlay] = field(default_factory=list)


@dataclass
class ParsedMatch:
    mtgo_match_id: str
    format: str | None = None
    opponent: str | None = None
    result: str | None = None
    games: list[ParsedGame] = field(default_factory=list)
    raw_file: str = ""


WINS_PATTERN = re.compile(r"(?P<player>\S+)\s+wins the match", re.IGNORECASE)
LOSES_PATTERN = re.compile(r"(?P<player>\S+)\s+loses the match", re.IGNORECASE)
FORMAT_PATTERN = re.compile(
    r"format[:\s]+(?P<fmt>modern|legacy|vintage|pioneer|standard|pauper|commander|draft|sealed)",
    re.IGNORECASE,
)
OPPONENT_PATTERN = re.compile(r"opponent[:\s]+(?P<opp>\S+)", re.IGNORECASE)


def parse_dat_file(path: Path) -> ParsedMatch | None:
    logger.debug("TODO: reverse-engineer .dat format (%s)", path)
    return None


def parse_text_log(path: Path) -> ParsedMatch | None:
    if not path.exists() or not path.is_file():
        return None

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        logger.exception("Failed to read text log: %s", path)
        return None

    if not text.strip():
        return None

    result: str | None = None
    opponent: str | None = None
    fmt: str | None = None

    # "me" is a convention — the agent cannot know the username with certainty
    # from text logs without config. We treat any 'wins the match' / 'loses
    # the match' line as a signal and leave winner identity unresolved.
    wins_hits = WINS_PATTERN.findall(text)
    loses_hits = LOSES_PATTERN.findall(text)

    if wins_hits:
        result = "win"
    elif loses_hits:
        result = "loss"

    fmt_match = FORMAT_PATTERN.search(text)
    if fmt_match:
        fmt = fmt_match.group("fmt").lower()

    opp_match = OPPONENT_PATTERN.search(text)
    if opp_match:
        opponent = opp_match.group("opp")

    if result is None and fmt is None and opponent is None:
        return None

    mtgo_match_id = f"text-{path.stem}-{uuid.uuid4().hex[:8]}"
    return ParsedMatch(
        mtgo_match_id=mtgo_match_id,
        format=fmt,
        opponent=opponent,
        result=result,
        games=[],
        raw_file=str(path),
    )


def parse_file(path: Path) -> ParsedMatch | None:
    try:
        dat_result = parse_dat_file(path)
    except Exception:
        logger.exception("parse_dat_file failed on %s", path)
        dat_result = None

    try:
        text_result = parse_text_log(path)
    except Exception:
        logger.exception("parse_text_log failed on %s", path)
        text_result = None

    if dat_result is None:
        return text_result
    if text_result is None:
        return dat_result
    # Both succeeded — prefer the richer result (more games).
    if len(dat_result.games) >= len(text_result.games):
        return dat_result
    return text_result
