# Player identity in MTGO logs — Phase 2.5 prereq

Question: does MTGO consistently place the local player as "Player 1"
(or at any fixed ordinal position) inside `.dat` or `.log` files, such
that we can derive self-identity from log structure alone rather than
needing agent config to tell us our MTGO username?

---

## Verdict: **inconclusive → treat as unreliable**

No evidence in either the research brief, the Phase 2.5 plan, or the
existing parser/fixtures shows that MTGO uses a stable ordinal marker
for the local player. The only documented approach for identifying
self in the log is to take the username from agent config and look for
it in the player roster.

---

## Evidence considered

### 1. Research brief (`docs/research/2026-04-18-mtgo-log-structure.md`)

- Player names are extracted by splitting on `" joined the game"`.
  Roster is built from "all unique names from the file" — no mention
  of a positional signal (lines 90–91).
- The example snippet uses `Player01` / `Opponent89` as *placeholder*
  names — those are literal usernames in BigPeet's test data, not
  MTGO-synthesized tokens. Cannot infer the local player from the
  `01` suffix.
- Explicit warning: "if one MTGO username is a prefix of another in
  the same match, naive string matching corrupts extraction" (line
  256–258). Implies the parser has always treated roster order as
  irrelevant and matches by full-name string.

### 2. Phase 2.5 plan (`docs/plans/2026-04-18-phase-2.5-parser-and-quarantine.md`)

- `@P(.+?) joined the game` — "Player roster — opponent = roster
  **minus self (self from agent config)**" (line 100). Self-identity
  is explicitly sourced from agent config, not the log.
- Dice-roll line `@P(.+?) rolled a (\d+)` — "Match start; both players
  appear once each (4× in re-rolls)" (line 99). Roll order is
  determined by MTGO's RNG, not local-vs-remote.
- `@P(.+?) chooses to (not )?play first` determines play/draw — this
  is again *per match* and random, not a stable per-user marker.
- Confidence-triage's "empty_player" failure mode exists specifically
  because opponent extraction can fail — the rule set does not treat
  roster order as a fallback signal (line 138).

### 3. Existing parser (`agent/parser.py`)

- The current stub has an `OPPONENT_PATTERN = r"opponent[:\s]+(?P<opp>\S+)"`
  regex — it searches for the literal word "opponent" which, per the
  Phase 2.5 plan's bug list, matches normal play text (line 16 of
  plan). No concept of positional identity.
- `parse_text_log` returns a `ParsedMatch` without resolving winner
  identity at all ("we treat any 'wins the match' line as a signal
  and leave winner identity unresolved" — `parser.py:83-85`).

### 4. Fixtures

- `tests/` contains no real MTGO log fixtures (only synthetic
  strings like `"testplayer wins the match"`). Nothing to check
  ordinal positioning against empirically.
- `agent/` ships no bundled sample logs.
- The 358-sample corpus Phase 2.5 was refined against is not in this
  repo — it was analyzed out-of-tree per the plan.

---

## Implication for Phase 2.5

Self-identity must come from **agent config** (the user's MTGO
username, set at registration or added later). Once present, the
parser matches it against the roster to disambiguate perspective.

- If agent config lacks the MTGO username: the parser cannot
  confidently assign win/loss perspective. Quarantine with
  `empty_player` or a new `no_self_identity` reason.
- Do **not** attempt "local player = first name encountered" or
  similar positional heuristics. There is no documented basis for
  this and the Phase 2.5 rule set already routes around it.

---

## Corpus questions worth answering when the fixture set lands

Phase 2.5 plans to import anonymized fixtures under
`tests/fixtures/mtgo_logs/`. When they arrive, a 10-minute sanity
check can strengthen or invalidate this verdict:

1. Does `@P<name> joined the game` always list the local player
   first, second, or neither?
2. Does `@P<name> rolled a <N>` place the local player first in any
   reproducible pattern?
3. Is there any header bytes in the `.dat` binary portion that
   encodes "who is on this client" — e.g., a session-user marker?
   (The brief does not mention one.)

If any of these turns out to be reliable, the parser can cross-check
agent config against the positional signal and warn on mismatch. But
the primary identity source should remain agent config.
