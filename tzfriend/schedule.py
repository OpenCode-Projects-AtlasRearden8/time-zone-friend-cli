"""Scheduling model: participant storage, heatmap grid, overlap suggestions."""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
import json

import zoneinfo

from .zones import resolve


@dataclass
class Person:
    name: str
    zone_name: str

    @property
    def zone(self):
        return zoneinfo.ZoneInfo(self.zone_name)

    def as_dict(self):
        return {"name": self.name, "zone": self.zone_name}


DEFAULT_STORE = "participants.json"
WAKING_START = 7
WAKING_END = 23  # awake hours: [7:00, 23:00) local
CORE_START = 8
CORE_END = 22  # fully comfortable: [8:00, 22:00) local


@dataclass
class Slot:
    start_utc: datetime
    hours: int
    awake: list  # Person names awake for the whole slot
    nights: list = field(default_factory=list)  # names whose local time hits night

    @property
    def end_utc(self):
        return self.start_utc + timedelta(hours=self.hours)


def load_people(path=DEFAULT_STORE):
    try:
        with open(path, encoding="utf-8") as f:
            rows = json.load(f)
    except FileNotFoundError:
        return []
    out = []
    for row in rows:
        out.append(Person(row["name"], row["zone"]))
    return out


def save_people(people, path=DEFAULT_STORE):
    with open(path, "w", encoding="utf-8") as f:
        json.dump([p.as_dict() for p in people], f, indent=2)
        f.write("\n")


def add_person(name, zone_query, path=DEFAULT_STORE):
    zone_name = resolve(zone_query)
    if zone_name is None:
        raise ValueError(f"Unknown time zone or city: {zone_query!r}")
    people = load_people(path)
    for existing in people:
        if existing.name.lower() == name.strip().lower():
            existing.zone_name = zone_name
            save_people(people, path)
            return people, zone_name, True
    people.append(Person(name.strip(), zone_name))
    save_people(people, path)
    return people, zone_name, False


def remove_person(name, path=DEFAULT_STORE):
    people = load_people(path)
    kept = [p for p in people if p.name.lower() != name.strip().lower()]
    save_people(kept, path)
    return kept


def hour_columns(anchor_date, span_hours=24):
    """Return `span_hours` hour-start instants in UTC, starting at 00:00 UTC on anchor_date."""
    start = datetime(anchor_date.year, anchor_date.month, anchor_date.day, tzinfo=timezone.utc)
    return [start + timedelta(hours=i) for i in range(span_hours)]


def is_awake(person, instant, waking=(WAKING_START, WAKING_END)):
    hour = instant.astimezone(person.zone).hour
    return waking[0] <= hour < waking[1]


def is_night(person, instant, core=(CORE_START, CORE_END)):
    hour = instant.astimezone(person.zone).hour
    return not (core[0] <= hour < core[1])


def heatmap_rows(people, columns, waking=(WAKING_START, WAKING_END)):
    """Return {name: [0/1..awake flags]} aligned with columns."""
    rows = {}
    for p in people:
        rows[p.name] = [int(is_awake(p, col, waking)) for col in columns]
    return rows


def awake_counts(people, columns, waking=(WAKING_START, WAKING_END)):
    """Return list of (count, set_of_awake_names) per column."""
    counts = []
    for col in columns:
        awake = [p for p in people if is_awake(p, col, waking)]
        counts.append((len(awake), {p.name for p in awake}))
    return counts


def contiguous_runs(flags):
    """Return [(start_index, length)] for runs of True."""
    runs, i = [], 0
    while i < len(flags):
        if flags[i]:
            j = i
            while j + 1 < len(flags) and flags[j + 1]:
                j += 1
            runs.append((i, j - i + 1))
            i = j + 1
        else:
            i += 1
    return runs


def find_slots(people, anchor_date, span_hours=24, waking=(WAKING_START, WAKING_END), core=(CORE_START, CORE_END)):
    """Find overlap windows, best-attendee first, flags for night-edge hours."""
    columns = hour_columns(anchor_date, span_hours)
    counts = awake_counts(people, columns, waking)
    best = max([c for c, _ in counts], default=0)
    slots = []
    if not people or best == 0:
        return slots
    for level in range(best, 0, -1):
        flags = [c >= level for c, _ in counts]
        for start_idx, length in contiguous_runs(flags):
            names = set.intersection(*[set(a) for _, a in counts[start_idx:start_idx + length]])
            start_utc = columns[start_idx]
            slot = Slot(start_utc, length, sorted(names))
            for name in slot.awake:
                person = next(p for p in people if p.name == name)
                end_local = (start_utc + timedelta(hours=length) - timedelta(microseconds=1)).astimezone(person.zone)
                if not (core[0] <= end_local.hour < core[1]) or is_night(person, start_utc, core):
                    slot.nights.append(name)
            slots.append(slot)
        if slots:
            break
    # Prefer more awake hours in window, then fewer night participants, then earlier start.
    slots.sort(key=lambda s: (-len(s.awake), -s.hours, len(s.nights), s.start_utc))
    return slots


def local_window(person, slot):
    """Human label like 'Wed 09:00-11:00 local' for a person over a slot."""
    start_local = slot.start_utc.astimezone(person.zone)
    end_local = slot.end_utc.astimezone(person.zone)
    day = start_local.strftime("%a")
    return (
        f"{day} {start_local.strftime('%H:%M')}-{end_local.strftime('%H:%M')}"
        if start_local.date() == end_local.date()
        else f"{start_local.strftime('%a %H:%M')}-{end_local.strftime('%a %H:%M')}"
    )


def parse_date(text):
    if not text:
        return date.today()
    return date.fromisoformat(text)
