# Time Zone Friend

A beginner-friendly, offline command-line tool for scheduling calls across time zones.

Tell it who is in the call and where they live (city or IANA zone name from a
bundled offline list), and it will:

- draw a **heatmap of everyone's waking hours** across a 24-hour UTC window,
- suggest **overlap windows** ranked by how many people are awake,
- **flag awkward nights** when a slot edges outside comfortable core hours,
- export the chosen slot as a **zone-safe `.ics`** calendar file.

It is a single pure-stdlib Python program. No internet, no API keys, no accounts.
Daylight-saving correctness comes from Python's built-in `zoneinfo` database:
every timestamp is computed at the real instant it happens, so DST jumps,
half-hour offsets (Adelaide, Lord Howe), and opposite-hemisphere seasons are all
handled quietly in the background.

Great for online clubs, book clubs, and family calls spread across the globe.

Made with care by **Asdale Dynamics, LLC** — part of the beginner-friendly AI
toolkit at <https://dylanasdale.github.io> (AI explained "like a friend would").

## Requirements

- Python 3.9 or newer, with the standard `zoneinfo` data (already on Linux, macOS,
  and most systems; on Windows run `pip install tzdata` once if needed).

## Install

```bash
pip install .              # installs the `tzfriend` command
# ...or run it straight from the folder without installing:
python -m tzfriend
```

## Quick start

```bash
tzfriend add Alice "America/New_York"   # IANA name...
tzfriend add Bob tokyo                  # ...or a friendly city
tzfriend add Charlie sydney

tzfriend list      # who is saved
tzfriend show      # heatmap of waking hours
tzfriend overlap   # ranked overlap suggestions (1 is best)
tzfriend export 1  # save slot #1 as meeting.ics
```

`show`, `overlap`, and `export` share helpful options:

```bash
--date 2026-06-10   # anchor date (default: today, UTC)
--span 48           # 24, 48, or 72 hour window
--waking 7-23       # each person's wake window, local hours
--core 8-22         # comfortable hours; outside these a slot gets flagged [night: NAME]
```

Participants are remembered locally in `participants.json` (override with
`--file`). Remove with `tzfriend remove Bob`. Not sure which zone to use?

```bash
tzfriend zones               # common city shortcuts
tzfriend zones auck          # search the 599-zone bundled offline list
```

## Example: the heatmap

```text
UTC window starting 2026-06-10 00:00Z, 24 hours
UTC      (zone                    ) 00 01 02 03 04 05 06 07 08 09 ...
Alice    (America/New_York        ) █ █ █ · · · · · · · · █ █ █ █ █ ...
Bob      (Asia/Tokyo              ) █ █ █ █ █ █ █ █ █ █ █ █ █ █ · · ...
Charlie  (Australia/Sydney        ) █ █ █ █ █ █ █ █ █ █ █ █ █ · · · ...
night    (                        )     n                 n n n
```

`█` = awake, `·` = asleep (in each person's own local time). The `night` row
marks columns where an awake person is outside core hours, so you can see an
awkward slot before anyone groans about it.

## Why the .ics is "zone-safe"

Calendar files that say *"9 PM local time in America/New_York"* break the moment
a DST rule changes. Time Zone Friend writes `DTSTART:20260612T220000Z` — the
exact UTC instant — so every calendar app converts it correctly for each
attendee, wherever and whenever they are in the world, DST or not.

## Testing

```bash
pip install .[dev]
pytest
```

The test suite covers the tricky DST edge cases explicitly: US/EU spring-forward
and fall-back, southern-hemisphere seasons (Sydney in October and April), and
Australia/Lord Howe's half-hour DST shift.

## Project layout

```
tzfriend/
  cli.py        command-line interface
  schedule.py   participants, heatmap grid, overlap finder
  zones.py      bundled offline IANA zone list + city aliases
  ics.py        zone-safe .ics export
  data/zones.txt  bundled zone list (offline)
tests/          pytest suite
```

## Privacy

Everything is local: participants live in a small JSON file next to where you
run it, nothing is uploaded, and the tool works fully offline.

## License

MIT — see `LICENSE`. Copyright (c) 2026 Asdale Dynamics, LLC.
