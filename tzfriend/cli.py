"""Command-line interface for Time Zone Friend."""

import argparse
import sys

from . import __version__, ics, schedule
from . import zones
from .zones import FRIENDLY_ALIASES

STORE_PATH_HELP = "JSON file used to remember participants (default: participants.json)"


def build_parser():
    parser = argparse.ArgumentParser(
        prog="tzfriend",
        description=(
            "Schedule calls across time zones. Offline, pure stdlib, DST-correct.\n"
            "Typical flow: 'tzfriend add Bob Sydney' -> 'tzfriend show' ->\n"
            "'tzfriend overlap' -> 'tzfriend export' (writes meeting.ics)."
        ),
    )
    parser.add_argument("--version", action="version", version=f"tzfriend {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="add (or update) a participant by city/zone")
    p_add.add_argument("name", help="participant name or nickname")
    p_add.add_argument("zone", help="IANA zone name or friendly city (e.g. 'America/New_York' or 'new york')")
    p_add.add_argument("--file", default=schedule.DEFAULT_STORE, help=STORE_PATH_HELP)

    p_rm = sub.add_parser("remove", help="remove a participant")
    p_rm.add_argument("name")
    p_rm.add_argument("--file", default=schedule.DEFAULT_STORE, help=STORE_PATH_HELP)

    p_list = sub.add_parser("list", help="list saved participants")
    p_list.add_argument("--file", default=schedule.DEFAULT_STORE, help=STORE_PATH_HELP)

    p_show = sub.add_parser("show", help="heatmap of waking hours across a 24-hour UTC window")
    p_show.add_argument("--date", default=None, help="start date, YYYY-MM-DD (default: today, UTC)")
    p_show.add_argument("--span", type=int, default=24, choices=range(24, 73, 24), help="span in hours (24, 48 or 72)")
    p_show.add_argument("--waking", default="7-23", help="awake local hours, e.g. 7-23")
    p_show.add_argument("--core", default="8-22", help="comfortable core hours; outside these slots get a night flag")
    p_show.add_argument("--file", default=schedule.DEFAULT_STORE, help=STORE_PATH_HELP)

    p_over = sub.add_parser("overlap", help="suggest overlap windows for everyone")
    p_over.add_argument("--date", default=None)
    p_over.add_argument("--span", type=int, default=24, choices=range(24, 73, 24))
    p_over.add_argument("--waking", default="7-23")
    p_over.add_argument("--core", default="8-22")
    p_over.add_argument("--limit", type=int, default=8)
    p_over.add_argument("--file", default=schedule.DEFAULT_STORE, help=STORE_PATH_HELP)

    p_exp = sub.add_parser("export", help="export a suggested slot as .ics (zone-safe UTC times)")
    p_exp.add_argument("slot", nargs="?", type=int, default=1, help="1-based slot number from 'overlap' output")
    p_exp.add_argument("--out", default="meeting.ics")
    p_exp.add_argument("--title", default="Time Zone Friend meeting")
    p_exp.add_argument("--date", default=None)
    p_exp.add_argument("--span", type=int, default=24, choices=range(24, 73, 24))
    p_exp.add_argument("--waking", default="7-23")
    p_exp.add_argument("--core", default="8-22")
    p_exp.add_argument("--file", default=schedule.DEFAULT_STORE, help=STORE_PATH_HELP)

    p_zones = sub.add_parser("zones", help="search the bundled offline zone list")
    p_zones.add_argument("query", nargs="?", default="")
    return parser


def parse_hours(text, low=0, high=24):
    start_text, _, end_text = text.partition("-")
    start, end = int(start_text), int(end_text)
    if not (low <= start < end <= high):
        raise ValueError(f"hours must be low < high in [{low}, {high}]: {text!r}")
    return start, end


def person_by_name(people, name):
    for p in people:
        if p.name == name:
            return p
    return None


def cmd_add(args):
    try:
        people, zone_name, updated = schedule.add_person(args.name, args.zone, args.file)
    except ValueError as err:
        print(f"Could not resolve {args.zone!r}. Closest bundled matches:")
        for candidate in zones.search(args.zone):
            print(f"  {candidate}")
        return 1
    verb = "updated" if updated else "added"
    print(f"{verb} {people[-1].name if not updated else args.name}: {zone_name} ({len(people)} saved in {args.file})")
    return 0


def cmd_remove(args):
    people = schedule.load_people(args.file)
    kept = schedule.remove_person(args.name, args.file)
    if len(kept) == len(people):
        print(f"No participant named {args.name!r} found in {args.file}.")
        return 1
    print(f"Removed {args.name!r}. {len(kept)} participant(s) remain in {args.file}.")
    return 0


def cmd_list(args):
    people = schedule.load_people(args.file)
    if not people:
        print(f"No participants saved in {args.file} yet. Try: tzfriend add Alice \"America/New_York\"")
        return 0
    width = max(len(p.name) for p in people)
    for p in people:
        print(f"{p.name:<{width}}  {p.zone_name}")
    return 0


def _common_args(args):
    people = schedule.load_people(args.file)
    waking = parse_hours(args.waking)
    core = parse_hours(args.core)
    anchor = schedule.parse_date(args.date)
    slots = schedule.find_slots(people, anchor, args.span, waking, core)
    return people, waking, core, anchor, slots


def cmd_show(args):
    people, waking, core, anchor, slots = _common_args(args)
    if not people:
        print(f"No participants in {args.file} yet. Try: tzfriend add Alice \"America/New_York\"")
        return 1
    columns = schedule.hour_columns(anchor, args.span)
    rows = schedule.heatmap_rows(people, columns, waking)
    names = [p.name for p in people]
    name_width = max(len(n) for n in names)
    utc_header = " ".join(c.strftime("%H") for c in columns)
    print(f"UTC window starting {columns[0].strftime('%Y-%m-%d 00:00')}Z, {args.span} hours")
    print(f"{'UTC':<{name_width}}  ({'zone':<24}) {utc_header}")
    for p in sorted(people, key=lambda x: x.name):
        flags = rows[p.name]
        cells = " ".join("\u2588" if f else "\u00b7" for f in flags)
        print(f"{p.name:<{name_width}}  ({p.zone_name[:24]:<24}) {cells}")
    by_name = {p.name: p for p in people}
    night_marks = " ".join(
        "n" if any(
            schedule.is_awake(by_name[n], columns[i], waking) and schedule.is_night(by_name[n], columns[i], core)
            for n in names
        )
        else " "
        for i in range(args.span)
    )
    print(f"{'night':<{name_width}}  ({'':<24}) {night_marks}")
    print(f"Legend: \u2588 awake, \u00b7 asleep (local hours {args.waking}).")
    print(f"night row: column hours where any awake participant is outside core hours {args.core} local.")
    # Show even small wakes when nobody aligns fully
    print()
    if slots:
        print("Full-overlap windows found. Run: tzfriend overlap")
    else:
        partial = schedule.awake_counts(people, columns, waking)
        best = max([c for c, _ in partial], default=0)
        if best:
            print(f"No window where everyone is awake. Best partial overlap: {best}/{len(people)} awake. Run: tzfriend overlap")
    return 0


def cmd_overlap(args):
    people, waking, core, anchor, slots = _common_args(args)
    if not people:
        print(f"No participants in {args.file} yet. Try: tzfriend add Alice \"America/New_York\"")
        return 1
    if not slots:
        print("No overlapping awake windows found at all. Widen --waking or check zones with 'tzfriend list'.")
        return 1
    by_name = {p.name: p for p in people}
    shown = slots[: max(1, args.limit)]
    for index, slot in enumerate(shown, start=1):
        flag = ""
        if slot.nights:
            flag = f"  [night: {', '.join(slot.nights)}]"
        label = f"{slot.start_utc.strftime('%Y-%m-%d %H:%M')}Z +{slot.hours}h"
        print(f"{index:>2}. {label}  everyone: {'yes' if len(slot.awake) == len(people) else str(len(slot.awake))}/{len(people)}{flag}")
        for name in slot.awake:
            print(f"      {name:<{max(len(n) for n in by_name)}}  {schedule.local_window(by_name[name], slot)} local")
    print()
    print("Night = any part outside core hours " + args.core + " local. Export with: tzfriend export 1 --out call.ics")
    if len(slot.awake) < len(people) and slots:
        missed = [n for n in by_name if n not in slots[0].awake]
        print(f"Note: nobody is awake with: {', '.join(missed)} in the best window shown.")
    return 0


def cmd_export(args):
    people, waking, core, anchor, slots = _common_args(args)
    if not slots:
        print("Nothing to export: no overlap windows found (see 'tzfriend overlap').")
        return 1
    if args.slot < 1 or args.slot > len(slots):
        print(f"Slot {args.slot} is out of range; {len(slots)} slot(s) available. Run: tzfriend overlap")
        return 1
    slot = slots[args.slot - 1]
    ics.write_ics(args.out, args.title, slot, people)
    print(f"Wrote {args.out} for {slot.start_utc.strftime('%Y-%m-%d %H:%M')}Z - {slot.end_utc.strftime('%H:%M')}Z")
    print("Times in the .ics are UTC ('Z'); calendar apps convert to each attendee's local time, surviving DST automatically.")
    return 0


def cmd_zones(args):
    query = args.query
    if not query:
        common = sorted(zones.FRIENDLY_ALIASES.items())
        print(f"Common city shortcuts ({len(common)}):")
        for key, value in common:
            print(f"  {key:<22} -> {value}")
        print(f"\nUse 'tzfriend zones <text>' to search {len(zones.bundled_zones())} bundled IANA zones.")
        return 0
    matches = zones.search(query)
    exact = zones.resolve(query)
    if exact:
        print(f"Resolves to: {exact}")
    if matches:
        print("Matches in bundled offline list:")
        for m in matches:
            print(f"  {m}")
    elif not exact:
        print(f"No bundled zone matches {query!r}.")
        return 1
    return 0


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = {
        "add": cmd_add,
        "remove": cmd_remove,
        "list": cmd_list,
        "show": cmd_show,
        "overlap": cmd_overlap,
        "export": cmd_export,
        "zones": cmd_zones,
    }[args.command]
    try:
        return handler(args)
    except ValueError as err:
        print(f"Error: {err}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
