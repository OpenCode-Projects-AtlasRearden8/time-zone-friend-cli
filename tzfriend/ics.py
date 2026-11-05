"""Export a chosen slot as a zone-safe .ics file (UTC times, no local tzid guessing)."""

from datetime import datetime, timezone
import zlib


def _ics_dt(instant):
    return instant.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def build_ics(title, slot, people, prodid="//Asdale Dynamics LLC//Time Zone Friend//EN"):
    description_lines = []
    for person in people:
        if person.name in slot.awake:
            start_local = slot.start_utc.astimezone(person.zone)
            end_local = slot.end_utc.astimezone(person.zone)
            description_lines.append(
                f"{person.name}: {start_local.strftime('%a %H:%M')}-{end_local.strftime('%H:%M')} ({person.zone_name})"
            )
    summary = title or "Time Zone Friend meeting"
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{prodid}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:tzfriend-{slot.start_utc.strftime('%Y%m%dT%H%M%SZ')}-{zlib.crc32(('-'.join(slot.awake)).encode())}@tzfriend",
        f"DTSTAMP:{_ics_dt(datetime.now(timezone.utc))}",
        f"DTSTART:{_ics_dt(slot.start_utc)}",
        f"DTEND:{_ics_dt(slot.end_utc)}",
        f"SUMMARY:{summary}",
        f"DESCRIPTION:{'\\n'.join(description_lines)}",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(lines) + "\r\n"


def write_ics(path, title, slot, people):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(build_ics(title, slot, people))
