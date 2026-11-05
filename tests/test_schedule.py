import json
from datetime import date, datetime, timedelta, timezone

import pytest

from tzfriend import schedule


def make_person(name, zone_name):
    return schedule.Person(name, zone_name)


def utc(y, m, d, h):
    return datetime(y, m, d, h, tzinfo=timezone.utc)


class TestStore:
    def test_add_load_save_roundtrip(self, tmp_path):
        store = str(tmp_path / "people.json")
        people, zone_name, updated = schedule.add_person("Alice", "America/New_York", store)
        assert zone_name == "America/New_York"
        assert not updated
        people2, _, updated2 = schedule.add_person("Alice", "Asia/Tokyo", store)
        assert updated2 is True
        assert len(people2) == 1
        loaded = schedule.load_people(store)
        assert [p.name for p in loaded] == ["Alice"]
        assert loaded[0].zone_name == "Asia/Tokyo"
        with open(store, encoding="utf-8") as f:
            assert json.loads(f.read()) == [{"name": "Alice", "zone": "Asia/Tokyo"}]

    def test_add_resolves_friendly_city(self, tmp_path):
        store = str(tmp_path / "people.json")
        _, zone_name, _ = schedule.add_person("Bo", "sydney", store)
        assert zone_name == "Australia/Sydney"

    def test_add_unknown_zone_raises(self, tmp_path):
        store = str(tmp_path / "people.json")
        with pytest.raises(ValueError):
            schedule.add_person("Bo", "Narnia/Cair_Paravel", store)

    def test_remove(self, tmp_path):
        store = str(tmp_path / "people.json")
        schedule.add_person("A", "UTC", store)
        schedule.add_person("B", "Asia/Tokyo", store)
        kept = schedule.remove_person("A", store)
        assert [p.name for p in kept] == ["B"]
        kept = schedule.remove_person("nobody-there", store)
        assert [p.name for p in kept] == ["B"]


class TestAwake:
    def test_awake_matches_local_hours(self):
        ny = make_person("Alice", "America/New_York")
        jan = utc(2026, 1, 15, 14)  # 09:00 EST
        assert schedule.is_awake(ny, jan) is True
        early = utc(2026, 1, 15, 2)  # 21:00 previous day EST -> awake (7h-23h? 21:00 is awake)
        assert schedule.is_awake(ny, early) is True
        midnight = utc(2026, 1, 15, 5)  # 00:00 EST -> asleep
        assert schedule.is_awake(ny, midnight) is False

    def test_waking_window_wide(self):
        p = make_person("Bo", "Europe/London")
        late = utc(2026, 6, 1, 22)  # 23:00 BST -> outside default waking [7,23)
        assert schedule.is_awake(p, late) is False
        edge = utc(2026, 6, 1, 6)  # 07:00 BST -> first awake hour
        assert schedule.is_awake(p, edge) is True


class TestGrid:
    def test_hour_columns(self):
        cols = schedule.hour_columns(date(2026, 3, 8), 24)
        assert len(cols) == 24
        assert cols[0] == utc(2026, 3, 8, 0)
        assert cols[23] == utc(2026, 3, 8, 23)

    def test_heatmap_rows(self):
        people = [make_person("A", "Asia/Tokyo"), make_person("B", "America/Los_Angeles")]
        cols = schedule.hour_columns(date(2026, 6, 10), 24)
        rows = schedule.heatmap_rows(people, cols)
        # Tokyo is UTC+9: awake local 07:00-23:00 means awake UTC columns 00Z-13Z and 22Z-23Z.
        assert sum(rows["A"]) == 16
        assert rows["A"][0:14] == [1] * 14
        assert rows["A"][14:22] == [0] * 8
        assert rows["A"][22:24] == [1] * 2
        # Los Angeles in June (UTC-7): awake columns 00Z-05Z (prev local evening) and 14Z-23Z.
        la = rows["B"]
        assert la[0:6] == [1] * 6
        assert la[6:14] == [0] * 8
        assert la[14:24] == [1] * 10


class TestSlots:
    def test_contiguous_runs(self):
        assert schedule.contiguous_runs([1, 1, 0, 1]) == [(0, 2), (3, 1)]
        assert schedule.contiguous_runs([]) == []
        assert schedule.contiguous_runs([0, 0]) == []

    def test_simple_overlap_two_zones(self):
        people = [make_person("NY", "America/New_York"), make_person("Bird", "America/Chicago")]
        slots = schedule.find_slots(people, date(2026, 6, 10))
        # NY awake 11:00Z-03:00Z(+1d), Chicago awake 12:00Z-04:00Z(+1d) -> overlap 16 long when clipped by grid
        assert slots
        best = slots[0]
        assert set(best.awake) == {"NY", "Bird"}
        assert best.start_utc.hour == 12

    def test_finds_partial_window_when_full_impossible(self):
        # Four persons spread around the globe: no hour has all four awake.
        people = [
            make_person("A", "Asia/Tokyo"),
            make_person("B", "America/Los_Angeles"),
            make_person("C", "Europe/Berlin"),
            make_person("D", "America/New_York"),
        ]
        slots = schedule.find_slots(people, date(2026, 6, 10))
        assert slots
        assert len(slots[0].awake) < 4
        assert all(len(s.awake) < 4 for s in slots)
        best_people = set(slots[0].awake)
        assert best_people and best_people <= {p.name for p in people}
        assert "C" not in slots[0].awake

    def test_no_people_no_slots(self):
        assert schedule.find_slots([], date(2026, 1, 1)) == []

    def test_night_flag_marks_outside_core(self):
        # Tokyo awake from 22:00Z (07:00 local) is inside core 8-22? 07:00 is outside core -> night
        people = [make_person("Tok", "Asia/Tokyo")]
        slots = schedule.find_slots(people, date(2026, 6, 10), core=(8, 22))
        early = [s for s in slots if s.start_utc.hour == 22]
        assert early and "Tok" in early[0].nights

    def test_local_window_label(self):
        p = make_person("N", "Europe/Berlin")
        slot = schedule.Slot(utc(2026, 6, 10, 12), 2, ["N"])
        assert schedule.local_window(p, slot) == "Wed 14:00-16:00"

    def test_parse_date_default_today(self):
        assert schedule.parse_date("2026-11-04") == date(2026, 11, 4)
        assert schedule.parse_date("") == datetime.now(timezone.utc).date()

    def test_lorda_invariant(self):  # guards the grid helper stays aligned after refactors
        cols = schedule.hour_columns(date(2026, 1, 1), 48)
        assert cols[47] == utc(2026, 1, 1, 0) + timedelta(hours=47)
