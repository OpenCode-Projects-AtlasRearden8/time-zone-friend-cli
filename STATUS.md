# STATUS — Time Zone Friend

Last updated: 2026-11-05

## What was built

`time-zone-friend` — a pure-stdlib, offline Python CLI for scheduling calls
across time zones. It keeps a local `participants.json` roster, draws an ASCII
heatmap of each person's waking hours over a 24/48/72-hour UTC window, ranks
overlap windows (awake count → window length → fewest night-edged people →
earliest), flags slots that reach outside "core" hours as awkward nights, and
exports the chosen slot as a zone-safe RFC 5545 `.ics` (UTC `Z` times, so every
calendar app converts correctly through future DST changes).

- Entry points: `python -m tzfriend` and the installed `tzfriend` script
  (`tzfriend.cli:main`, declared in `pyproject.toml`).
- Commands: `add`, `remove`, `list`, `show`, `overlap`, `export`, `zones`.
- `tzfriend/zones.py` bundles all 599 IANA zones offline
  (`tzfriend/data/zones.txt`, shipped as package data) plus ~75 friendly city
  aliases (`add Bob tokyo` → `Asia/Tokyo`).
- DST correctness via `zoneinfo`: all awake/night decisions are made at real
  UTC instants converted to each person's zone.

## How to run it

```bash
pip install .                    # or use `python -m tzfriend` in the repo
tzfriend add Alice "America/New_York"
tzfriend add Bob tokyo
tzfriend show                    # heatmap
tzfriend overlap                 # ranked suggestions with [night: ...] flags
tzfriend export 1 --out call.ics # zone-safe calendar file
python -m pytest                 # test suite (needs: pip install .[dev])
```

## Verification results (2026-11-05)

- `python3 -m pytest`: **40 passed** (no warnings), Python 3.13.5.
- Manual end-to-end run (add/list/show/overlap/export): verified correct output;
  `export` produced a valid `VCALENDAR` with UTC `DTSTART`/`DTEND` and a
  per-person local-time `DESCRIPTION`.
- DST spot checks in the live CLI: New York's heatmap on 2026-03-08 correctly
  reflects the missing 02:xx hour and the offset jump at 07:00Z.
- Clean-venv install (`python3 -m venv`, `pip install .`) verified: the
  `tzfriend` entry point works and the bundled zone list is found outside the
  source tree.

## Known gaps / limitations

- Suggestions are hourly (per-hour grid); sub-hour precision or 15-minute
  granularity is not supported yet.
- DST-database updates come from the system `zoneinfo`/`tzdata`; the bundled
  `zones.txt` is a zone-name list (rules come from tzdata), so extreme-future
  rule changes follow whatever tzdata is installed.
- No rich text/TUI colors; output is plain ASCII (portable everywhere).
- `overlap` recomputes suggestions each time, so slot numbering is stable only
  for the same date/flags across consecutive runs.
- The `night` flag uses a single core-hours pair (default 8-22) for everyone;
  per-person core hours are not supported yet.

## Author / license

Built by Asdale Dynamics, LLC. MIT — see `LICENSE`
(`Copyright (c) 2026 Asdale Dynamics, LLC`). Local-first, offline, no secrets
or personal data anywhere in the repository.
