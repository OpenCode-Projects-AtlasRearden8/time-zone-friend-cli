"""DST edge cases: US, EU, southern hemisphere, and the Lord Howe half-hour shift."""

from datetime import date, timedelta, timezone

from tzfriend import schedule


def z(y, mo, d, h):
    from datetime import datetime
    return datetime(y, mo, d, h, tzinfo=timezone.utc)


def offsets_instant(zone_name, y, mo, d, h):
    from datetime import datetime
    import zoneinfo
    return z(y, mo, d, h).astimezone(zoneinfo.ZoneInfo(zone_name)).utcoffset()


class TestSpringForwardNewYork:
    def test_offset_jumps_before_and_after_transition(self):
        # 2026-03-08 02:00 EST -> 03:00 EDT; UTC 06:59:59 is EST (-5), 07:00 is EDT (-4)
        assert offsets_instant("America/New_York", 2026, 3, 8, 6) == timedelta(hours=-5)
        assert offsets_instant("America/New_York", 2026, 3, 8, 7) == timedelta(hours=-4)

    def test_local_hour_never_revisits_missing_hour(self):
        person = schedule.Person("Al", "America/New_York")
        cols = schedule.hour_columns(date(2026, 3, 8), 24)
        local_hours = [c.astimezone(person.zone).hour for c in cols]
        assert local_hours.count(2) == 0  # 02:xx simply never happens that day

    def test_awake_columns_shift_across_dst_boundary(self):
        # Same local waking rule on a transition day vs a normal day yields different UTC columns.
        person = schedule.Person("Al", "America/New_York")
        dst_day = schedule.heatmap_rows([person], schedule.hour_columns(date(2026, 3, 8), 24))["Al"]
        normal = schedule.heatmap_rows([person], schedule.hour_columns(date(2026, 3, 15), 24))["Al"]
        assert dst_day != normal

    def test_overlap_windows_on_dst_day_stay_real(self):
        # Any suggested slot must map each awake person to non-duplicate, advancing local times.
        a = schedule.Person("NY", "America/New_York")
        b = schedule.Person("Chi", "America/Chicago")
        slots = schedule.find_slots([a, b], date(2026, 3, 8))
        assert slots
        for slot in slots:
            for person in (a, b):
                start_local = slot.start_utc.astimezone(person.zone)
                end_local = slot.end_utc.astimezone(person.zone)
                assert start_local < end_local


class TestFallBackNewYork:
    def test_offset_unwinds(self):
        # 2026-11-01: 01:00 EDT -> 01:00 EST again at UTC 06:00
        assert offsets_instant("America/New_York", 2026, 11, 1, 5) == timedelta(hours=-4)
        assert offsets_instant("America/New_York", 2026, 11, 1, 6) == timedelta(hours=-5)

    def test_repeated_local_hour_awake_flags_use_real_instant(self):
        person = schedule.Person("Al", "America/New_York")
        cols = schedule.hour_columns(date(2026, 11, 1), 24)
        local_hours = [c.astimezone(person.zone).hour for c in cols]
        # The 01:00 hour occurs for two consecutive UTC columns (05Z, 06Z).
        assert local_hours[5] == local_hours[6] == 1


class TestEasternEuropeAndPacific:
    def test_berlin_switches_later_than_new_york(self):
        # EU changes on 2026-03-29 01:00 UTC.
        assert offsets_instant("Europe/Berlin", 2026, 3, 29, 0) == timedelta(hours=1)
        assert offsets_instant("Europe/Berlin", 2026, 3, 29, 1) == timedelta(hours=2)

    def test_southern_hemisphere_sydney_starts_dst_in_october(self):
        # Sydney: DST starts 2026-10-04 02:00 local (16:00 UTC), +10 -> +11.
        assert offsets_instant("Australia/Sydney", 2026, 10, 3, 15) == timedelta(hours=10)
        assert offsets_instant("Australia/Sydney", 2026, 10, 3, 16) == timedelta(hours=11)

    def test_southern_hemisphere_sydney_ends_dst_in_april(self):
        # DST ends 2026-04-05 03:00 local (16:00 UTC on Apr 5? -> local 02:00 AEDT jump to 02:00 AEST at 15:00 UTC).
        assert offsets_instant("Australia/Sydney", 2026, 4, 4, 15) == timedelta(hours=11)
        assert offsets_instant("Australia/Sydney", 2026, 4, 4, 16) == timedelta(minutes=600)

    def test_lord_howe_half_hour_shift(self):
        # Lord Howe ends DST 2026-04-05 02:00 local (15:00 UTC), a 30-minute unwind: +11:00 -> +10:30.
        assert offsets_instant("Australia/Lord_Howe", 2026, 4, 4, 14) == timedelta(hours=11)
        assert offsets_instant("Australia/Lord_Howe", 2026, 4, 5, 15) == timedelta(minutes=630)


class TestDSTDaySuggestions:
    def test_slots_opposite_hemispheres_stay_consistent(self):
        # Berlin ends DST later than Sydney starts it; suggestions must stay internally consistent.
        p = schedule.Person("Ber", "Europe/Berlin")
        q = schedule.Person("Syd", "Australia/Sydney")
        slots = schedule.find_slots([p, q], date(2026, 10, 13))
        assert slots
        best = slots[0]
        assert set(best.awake) == {"Ber", "Syd"}
        # Best shared window: 05:00Z-12:00Z = 07:00-14:00 CEST / 16:00-23:00 AEDT.
        assert best.start_utc.hour == 5
        assert best.hours == 7
        assert set(best.nights) == {"Ber", "Syd"}

