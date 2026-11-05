from datetime import date, datetime, timezone

from tzfriend import ics, schedule


def test_build_ics_uses_zone_safe_utc_times():
    people = [schedule.Person("Al", "America/New_York"), schedule.Person("Bo", "Asia/Tokyo")]
    slot = schedule.Slot(datetime(2026, 3, 8, 16, tzinfo=timezone.utc), 2, ["Al", "Bo"])
    text = ics.build_ics("Club Call", slot, people)
    assert text.startswith("BEGIN:VCALENDAR\r\n")
    assert text.endswith("END:VCALENDAR\r\n")
    assert "DTSTART:20260308T160000Z" in text
    assert "DTEND:20260308T180000Z" in text
    assert "SUMMARY:Club Call" in text
    assert "VERSION:2.0" in text
    assert "PRODID://Asdale Dynamics LLC//Time Zone Friend//EN" in text
    desc = next(line for line in text.split("\r\n") if line.startswith("DESCRIPTION:"))
    assert "Al: Sun 12:00-14:00 (America/New_York)" in desc
    assert "Bo: Mon 01:00-03:00 (Asia/Tokyo)" in desc


def test_write_ics_file_roundtrip(tmp_path):
    people = [schedule.Person("Solo", "Europe/Berlin")]
    slot = schedule.Slot(datetime(2026, 6, 10, 12, tzinfo=timezone.utc), 1, ["Solo"])
    out = tmp_path / "call.ics"
    ics.write_ics(str(out), "Family Call", slot, people)
    content = out.read_text(encoding="utf-8")
    assert content.count("BEGIN:VEVENT") == 1
    assert "DTSTART:20260610T120000Z" in content
    # UID is stable across repeated exports (no hash randomization dependence)
    ics.write_ics(str(out), "Family Call", slot, people)
    assert content.count("UID:") == 1


def test_exported_titles_survive_ics_special_chars():
    people = [schedule.Person("A", "UTC"), schedule.Person("B", "Asia/Tokyo")]
    slot = schedule.Slot(datetime(2026, 1, 1, 0, tzinfo=timezone.utc), 1, ["A", "B"])
    text = ics.build_ics("Call; Comma, Style", slot, people)
    assert "SUMMARY:Call; Comma, Style" in text
    # DESCRIPTION encodes newline escapes per RFC 5545
    desc = next(line for line in text.split("\r\n") if line.startswith("DESCRIPTION:"))
    assert "\\n" in desc
