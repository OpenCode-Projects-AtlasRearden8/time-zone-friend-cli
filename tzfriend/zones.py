"""Bundled offline IANA zone list plus friendly city aliases."""

from functools import lru_cache
from importlib import resources

import zoneinfo

FRIENDLY_ALIASES = {
    "almaty": "Asia/Almaty",
    "amsterdam": "Europe/Amsterdam",
    "athens": "Europe/Athens",
    "atlanta": "America/New_York",
    "auckland": "Pacific/Auckland",
    "bangalore": "Asia/Kolkata",
    "bangkok": "Asia/Bangkok",
    "barcelona": "Europe/Madrid",
    "beijing": "Asia/Shanghai",
    "berlin": "Europe/Berlin",
    "bogota": "America/Bogota",
    "boston": "America/New_York",
    "brisbane": "Australia/Brisbane",
    "calgary": "America/Edmonton",
    "chennai": "Asia/Kolkata",
    "chicago": "America/Chicago",
    "dallas": "America/Chicago",
    "delhi": "Asia/Kolkata",
    "denver": "America/Denver",
    "detroit": "America/Detroit",
    "dubai": "Asia/Dubai",
    "dublin": "Europe/Dublin",
    "hanoi": "Asia/Ho_Chi_Minh",
    "havana": "America/Havana",
    "helsinki": "Europe/Helsinki",
    "hong kong": "Asia/Hong_Kong",
    "honolulu": "Pacific/Honolulu",
    "houston": "America/Chicago",
    "istanbul": "Europe/Istanbul",
    "jakarta": "Asia/Jakarta",
    "jerusalem": "Asia/Jerusalem",
    "johannesburg": "Africa/Johannesburg",
    "kyiv": "Europe/Kyiv",
    "kolkata": "Asia/Kolkata",
    "london": "Europe/London",
    "los angeles": "America/Los_Angeles",
    "madrid": "Europe/Madrid",
    "manila": "Asia/Manila",
    "melbourne": "Australia/Melbourne",
    "mexico city": "America/Mexico_City",
    "miami": "America/New_York",
    "montreal": "America/Montreal",
    "moscow": "Europe/Moscow",
    "mumbai": "Asia/Kolkata",
    "nairobi": "Africa/Nairobi",
    "new delhi": "Asia/Kolkata",
    "new york": "America/New_York",
    "osaka": "Asia/Tokyo",
    "oslo": "Europe/Oslo",
    "paris": "Europe/Paris",
    "perth": "Australia/Perth",
    "philadelphia": "America/New_York",
    "phoenix": "America/Phoenix",
    "prague": "Europe/Prague",
    "reykjavik": "Atlantic/Reykjavik",
    "rio": "America/Sao_Paulo",
    "rio de janeiro": "America/Sao_Paulo",
    "rome": "Europe/Rome",
    "santiago": "America/Santiago",
    "sao paulo": "America/Sao_Paulo",
    "san francisco": "America/Los_Angeles",
    "seattle": "America/Los_Angeles",
    "seoul": "Asia/Seoul",
    "shanghai": "Asia/Shanghai",
    "singapore": "Asia/Singapore",
    "stockholm": "Europe/Stockholm",
    "sydney": "Australia/Sydney",
    "taipei": "Asia/Taipei",
    "tokyo": "Asia/Tokyo",
    "toronto": "America/Toronto",
    "vancouver": "America/Vancouver",
    "vienna": "Europe/Vienna",
    "warsaw": "Europe/Warsaw",
    "washington dc": "America/New_York",
    "wellington": "Pacific/Auckland",
    "zurich": "Europe/Zurich",
}


@lru_cache(maxsize=1)
def bundled_zones():
    """Return the bundled offline list of IANA zone names (sorted)."""
    text = resources.files("tzfriend").joinpath("data/zones.txt").read_text(encoding="utf-8")
    return [line for line in text.splitlines() if line.strip()]


@lru_cache(maxsize=None)
def known_zone(name):
    """Return the IANA name if it resolves offline, else None."""
    candidate = name
    if candidate not in ("UTC", "utc") and candidate not in bundled_zones():
        # Tolerate alias-like capitalization of well-known zones.
        lowered = candidate.replace(" ", "_")
        matches = [z for z in bundled_zones() if z.lower() == lowered.lower()]
        if not matches:
            return None
        candidate = matches[0]
    try:
        zoneinfo.ZoneInfo(candidate)
    except Exception:
        return None
    return candidate


def resolve(query):
    """Resolve a user query to a single IANA zone name, or None."""
    query = query.strip()
    direct = known_zone(query)
    if direct:
        return direct
    alias = FRIENDLY_ALIASES.get(query.lower())
    if alias:
        return alias
    return None


def search(query):
    "Return up to 8 bundled zone names matching the query."
    needle = query.strip().lower().replace(" ", "_")
    if not needle:
        return []
    alias_targets = {
        target for key, target in FRIENDLY_ALIASES.items() if needle in key
    }
    starts = [z for z in bundled_zones() if needle in z.lower()]
    merged, seen = [], set()
    for candidate in list(alias_targets) + starts:
        if candidate not in seen:
            seen.add(candidate)
            merged.append(candidate)
    return merged[:8]
