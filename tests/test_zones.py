import zoneinfo

from tzfriend import zones


def test_bundled_zone_list_is_offline_complete():
    zones_list = zones.bundled_zones()
    assert len(zones_list) >= 400
    assert zones_list == sorted(zones_list)
    for name in zones_list:
        zoneinfo.ZoneInfo(name)  # every bundled entry must resolve offline


def test_known_zone_validates_real_and_rejects_garbage():
    assert zones.known_zone("Asia/Tokyo") == "Asia/Tokyo"
    assert zones.known_zone("Mars/Olympus_Mons") is None


def test_resolve_friendly_alias_and_direct_name():
    assert zones.resolve("new york") == "America/New_York"
    assert zones.resolve("New York") == "America/New_York"
    assert zones.resolve("AmericA/New_YorK") == "America/New_York"
    assert zones.resolve("totally not a zone") is None
