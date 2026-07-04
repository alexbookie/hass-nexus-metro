"""Static data for the Tyne and Wear Metro network.

Contains route definitions, inter-station travel times, station metadata,
and ATCO code mappings for querying Traveline departures.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Inter-station travel times (minutes), derived from timetable data.
# Keyed by (from_code, to_code) in both directions.
# ---------------------------------------------------------------------------
_SEGMENT_TIMES: dict[tuple[str, str], float] = {}


def _add(pairs: list[tuple[str, str, float]]) -> None:
    for a, b, m in pairs:
        _SEGMENT_TIMES[(a, b)] = m
        _SEGMENT_TIMES[(b, a)] = m


_add(
    [
        # Green line: Airport -> South Gosforth
        ("APT", "CAL", 2),
        ("CAL", "BFT", 3),
        ("BFT", "KSP", 2),
        ("KSP", "FAW", 2),
        ("FAW", "WBR", 1),
        ("WBR", "RGC", 2),
        ("RGC", "SGF", 4),
        # Shared: South Gosforth -> Pelaw
        ("SGF", "ILF", 1),
        ("ILF", "WJS", 2),
        ("WJS", "JES", 2),
        ("JES", "HAY", 1),
        ("HAY", "MTS", 2),
        ("MTS", "CEN", 2),
        ("CEN", "GHD", 2),
        ("GHD", "GST", 2),
        ("GST", "FEL", 2),
        ("FEL", "HTH", 1),
        ("HTH", "PLW", 3),
        # Green South Hylton branch: Pelaw -> South Hylton
        ("PLW", "SBN", 5),
        ("SBN", "SMD", 2),
        ("SMD", "MSP", 2),
        ("MSP", "SUN", 3),
        ("SUN", "PLI", 1),
        ("PLI", "UNI", 1),
        ("UNI", "MLF", 2),
        ("MLF", "PAL", 2),
        ("PAL", "SHL", 4),
        # Green South Shields branch: Pelaw -> South Shields
        ("PLW", "HEB", 4),
        ("HEB", "JAR", 3),
        ("JAR", "BDE", 2),
        ("BDE", "TDK", 4),
        ("TDK", "CHI", 2),
        ("CHI", "SSS", 2),
        # Yellow line: St James -> coast -> South Gosforth
        ("SJM", "MTW", 2),
        ("MTW", "MAN", 2),
        ("MAN", "BYK", 2),
        ("BYK", "CRD", 2),
        ("CRD", "WKG", 2),
        ("WKG", "WSD", 2),
        ("WSD", "HDR", 2),
        ("HDR", "HOW", 3),
        ("HOW", "PCM", 2),
        ("PCM", "MWL", 2),
        ("MWL", "NSH", 2),
        ("NSH", "TYN", 3),
        ("TYN", "CUL", 3),
        ("CUL", "WTL", 1),
        ("WTL", "MSN", 2),
        ("MSN", "WMN", 2),
        ("WMN", "SMR", 3),
        ("SMR", "NPK", 2),
        ("NPK", "PMV", 2),
        ("PMV", "BTN", 3),
        ("BTN", "FLE", 1),
        ("FLE", "LBN", 2),
        ("LBN", "SGF", 3),
        # Monument cross-platform connection
        ("MTS", "MTW", 0),
        ("HAY", "MTW", 2),
    ]
)

FALLBACK_SEGMENT_TIME = 2.0


def get_segment_time(from_code: str, to_code: str) -> float:
    """Get travel time between two adjacent stations."""
    return _SEGMENT_TIMES.get((from_code, to_code), FALLBACK_SEGMENT_TIME)


# ---------------------------------------------------------------------------
# Route definitions (ordered station code lists)
# ---------------------------------------------------------------------------
GREEN_AIRPORT_TO_SOUTH_HYLTON: list[str] = [
    "APT",
    "CAL",
    "BFT",
    "KSP",
    "FAW",
    "WBR",
    "RGC",
    "SGF",
    "ILF",
    "WJS",
    "JES",
    "HAY",
    "MTS",
    "CEN",
    "GHD",
    "GST",
    "FEL",
    "HTH",
    "PLW",
    "SBN",
    "SMD",
    "MSP",
    "SUN",
    "PLI",
    "UNI",
    "MLF",
    "PAL",
    "SHL",
]

GREEN_AIRPORT_TO_SOUTH_SHIELDS: list[str] = [
    "APT",
    "CAL",
    "BFT",
    "KSP",
    "FAW",
    "WBR",
    "RGC",
    "SGF",
    "ILF",
    "WJS",
    "JES",
    "HAY",
    "MTS",
    "CEN",
    "GHD",
    "GST",
    "FEL",
    "HTH",
    "PLW",
    "HEB",
    "JAR",
    "BDE",
    "TDK",
    "CHI",
    "SSS",
]

YELLOW_ST_JAMES_TO_SOUTH_SHIELDS: list[str] = [
    "SJM",
    "MTW",
    "MAN",
    "BYK",
    "CRD",
    "WKG",
    "WSD",
    "HDR",
    "HOW",
    "PCM",
    "MWL",
    "NSH",
    "TYN",
    "CUL",
    "WTL",
    "MSN",
    "WMN",
    "SMR",
    "NPK",
    "PMV",
    "BTN",
    "FLE",
    "LBN",
    "SGF",
    "ILF",
    "WJS",
    "JES",
    "HAY",
    "MTS",
    "CEN",
    "GHD",
    "GST",
    "FEL",
    "HTH",
    "PLW",
    "HEB",
    "JAR",
    "BDE",
    "TDK",
    "CHI",
    "SSS",
]

# Stations only on the Yellow line coast section
YELLOW_ONLY_STATIONS: frozenset[str] = frozenset(
    {
        "SJM",
        "MTW",
        "MAN",
        "BYK",
        "CRD",
        "WKG",
        "WSD",
        "HDR",
        "HOW",
        "PCM",
        "MWL",
        "NSH",
        "TYN",
        "CUL",
        "WTL",
        "MSN",
        "WMN",
        "SMR",
        "NPK",
        "PMV",
        "BTN",
        "FLE",
        "LBN",
    }
)

# Destinations that arrive on platform 1/3 (inbound) vs platform 2/4 (outbound)
INBOUND_DESTINATIONS: frozenset[str] = frozenset(
    {
        "South Hylton",
        "South Shields",
        "Pelaw",
        "Sunderland",
    }
)
OUTBOUND_DESTINATIONS: frozenset[str] = frozenset(
    {
        "Airport",
        "St James",
        "Regent Centre",
        "Monument East",
    }
)


def route_for_train(destination: str, current_station: str) -> list[str] | None:
    """Pick the correct route for a train based on destination and current position."""
    if destination == "South Hylton":
        return GREEN_AIRPORT_TO_SOUTH_HYLTON
    if destination == "Airport":
        return list(reversed(GREEN_AIRPORT_TO_SOUTH_HYLTON))
    if destination == "South Shields":
        if current_station in YELLOW_ONLY_STATIONS:
            return YELLOW_ST_JAMES_TO_SOUTH_SHIELDS
        return GREEN_AIRPORT_TO_SOUTH_SHIELDS
    if destination == "St James":
        return list(reversed(YELLOW_ST_JAMES_TO_SOUTH_SHIELDS))
    if destination == "Regent Centre":
        return list(reversed(GREEN_AIRPORT_TO_SOUTH_HYLTON[:7]))
    if destination == "Pelaw":
        return GREEN_AIRPORT_TO_SOUTH_SHIELDS[:19]
    if destination == "Sunderland":
        return GREEN_AIRPORT_TO_SOUTH_HYLTON[:27]
    if destination == "Monument East":
        return list(reversed(YELLOW_ST_JAMES_TO_SOUTH_SHIELDS[:6]))
    return None


def travel_time(route: list[str], from_idx: int, to_idx: int) -> float:
    """Calculate total travel time between two points on a route."""
    total = 0.0
    for i in range(from_idx, to_idx):
        total += get_segment_time(route[i], route[i + 1])
    return total


# ---------------------------------------------------------------------------
# Station metadata
# ---------------------------------------------------------------------------

# Internal station code -> human-readable name
STATION_NAMES: dict[str, str] = {
    "APT": "Airport",
    "CAL": "Callerton Parkway",
    "BFT": "Bank Foot",
    "KSP": "Kingston Park",
    "FAW": "Fawdon",
    "WBR": "Wansbeck Road",
    "RGC": "Regent Centre",
    "SGF": "South Gosforth",
    "ILF": "Ilford Road",
    "WJS": "West Jesmond",
    "JES": "Jesmond",
    "HAY": "Haymarket",
    "MTS": "Monument",
    "MTW": "Monument",
    "CEN": "Central Station",
    "GHD": "Gateshead",
    "GST": "Gateshead Stadium",
    "FEL": "Felling",
    "HTH": "Heworth",
    "PLW": "Pelaw",
    "HEB": "Hebburn",
    "JAR": "Jarrow",
    "BDE": "Bede",
    "TDK": "Tyne Dock",
    "CHI": "Chichester",
    "SSS": "South Shields",
    "SBN": "Seaburn",
    "SMD": "Stadium of Light",
    "MSP": "St Peter's",
    "SUN": "Sunderland",
    "PLI": "Park Lane",
    "UNI": "University",
    "MLF": "Millfield",
    "PAL": "Pallion",
    "SHL": "South Hylton",
    "SJM": "St James",
    "MAN": "Manors",
    "BYK": "Byker",
    "CRD": "Chillingham Road",
    "WKG": "Walkergate",
    "WSD": "Wallsend",
    "HDR": "Hadrian Road",
    "HOW": "Howdon",
    "PCM": "Percy Main",
    "MWL": "Meadow Well",
    "NSH": "North Shields",
    "TYN": "Tynemouth",
    "CUL": "Cullercoats",
    "WTL": "Whitley Bay",
    "MSN": "Monkseaton",
    "WMN": "West Monkseaton",
    "SMR": "Shiremoor",
    "NPK": "Northumberland Park",
    "PMV": "Palmersville",
    "BTN": "Benton",
    "FLE": "Four Lane Ends",
    "LBN": "Longbenton",
    "FGT": "Fellgate",
    "BYW": "Brockley Whins",
    "EBO": "East Boldon",
}

# KML station name (lowercase) -> internal station code
# Used to parse "last seen" events from the KML feed
STATION_NAME_TO_CODE: dict[str, str] = {name.lower(): code for code, name in STATION_NAMES.items()}
# Add known aliases and variations
STATION_NAME_TO_CODE.update(
    {
        "central station": "CEN",
        "gateshead stadium": "GST",
        "stadium of light": "SMD",
        "st peter's": "MSP",
        "st james": "SJM",
        "south gosforth": "SGF",
        "west jesmond": "WJS",
        "ilford road": "ILF",
        "chillingham road": "CRD",
        "hadrian road": "HDR",
        "percy main": "PCM",
        "meadow well": "MWL",
        "north shields": "NSH",
        "whitley bay": "WTL",
        "west monkseaton": "WMN",
        "northumberland park": "NPK",
        "four lane ends": "FLE",
        "tyne dock": "TDK",
        "south shields": "SSS",
        "south hylton": "SHL",
        "park lane": "PLI",
        "brockley whins": "BYW",
        "east boldon": "EBO",
        "bank foot": "BFT",
        "kingston park": "KSP",
        "wansbeck road": "WBR",
        "regent centre": "RGC",
        "callerton parkway": "CAL",
    }
)


# ---------------------------------------------------------------------------
# ATCO code mappings for Traveline queries
# Each station has an ATCO base code; append platform number for full code.
# e.g. "9400ZZTWAPT" + "1" = "9400ZZTWAPT1" for Airport Platform 1
# ---------------------------------------------------------------------------
STATION_ATCO_BASE: dict[str, str] = {
    # Green line: Airport -> South Gosforth
    "APT": "9400ZZTWAPT",
    "CAL": "9400ZZTWCTP",
    "BFT": "9400ZZTWBKF",
    "KSP": "9400ZZTWKSP",
    "FAW": "9400ZZTWFDN",
    "WBR": "9400ZZTWWBK",
    "RGC": "9400ZZTWRGC",
    "SGF": "9400ZZTWSGF",
    # Shared: South Gosforth -> Pelaw
    "ILF": "9400ZZTWIFD",
    "WJS": "9400ZZTWWJM",
    "JES": "9400ZZTWJMD",
    "HAY": "9400ZZTWHMT",
    "MTS": "9400ZZTWMMT",  # Monument platforms 1/2 (N-S)
    "MTW": "9400ZZTWMMT",  # Monument platforms 3/4 (E-W) — same ATCO base
    "CEN": "9400ZZTWCST",
    "GHD": "9400ZZTWGHD",
    "GST": "9400ZZTWGHS",
    "FEL": "9400ZZTWFLG",
    "HTH": "9400ZZTWHPW",
    "PLW": "9400ZZTWPLW",
    # Green South Shields branch
    "HEB": "9400ZZTWHBN",
    "JAR": "9400ZZTWJRW",
    "BDE": "9400ZZTWBDE",
    "TDK": "9400ZZTWTYD",
    "CHI": "9400ZZTWCHT",
    "SSS": "9400ZZTWSSH",
    # Green South Hylton branch
    "SBN": "9400ZZTWSBN",
    "SMD": "9400ZZTWSOL",
    "MSP": "9400ZZTWSTP",
    "SUN": "9400ZZTWSND",
    "PLI": "9400ZZTWPRK",
    "UNI": "9400ZZTWUNI",
    "MLF": "9400ZZTWMFD",
    "PAL": "9400ZZTWPLN",
    "SHL": "9400ZZTWSHY",
    # Yellow line: St James + coast
    "SJM": "9400ZZTWSTJ",
    "MAN": "9400ZZTWMNS",
    "BYK": "9400ZZTWBKR",
    "CRD": "9400ZZTWCHM",
    "WKG": "9400ZZTWWGT",
    "WSD": "9400ZZTWWND",
    "HDR": "9400ZZTWHRN",
    "HOW": "9400ZZTWHDN",
    "PCM": "9400ZZTWPYM",
    "MWL": "9400ZZTWMDW",
    "NSH": "9400ZZTWNSH",
    "TYN": "9400ZZTWTYM",
    "CUL": "9400ZZTWCCS",
    "WTL": "9400ZZTWWHB",
    "MSN": "9400ZZTWMST",
    "WMN": "9400ZZTWWMS",
    "SMR": "9400ZZTWSHM",
    "NPK": "9400ZZTWNDP",
    "PMV": "9400ZZTWPVL",
    "BTN": "9400ZZTWBTN",
    "FLE": "9400ZZTWFLE",
    "LBN": "9400ZZTWLBT",
    # Additional stations
    "FGT": "9400ZZTWFGT",
    "BYW": "9400ZZTWBRW",
    "EBO": "9400ZZTWEBN",
}

# Default platform numbers per station. Most have 1 and 2.
# Monument has 4 platforms: 1/2 (N-S Green) and 3/4 (E-W Yellow).
STATION_PLATFORM_NUMBERS: dict[str, list[int]] = {code: [1, 2] for code in STATION_ATCO_BASE}
STATION_PLATFORM_NUMBERS["MTS"] = [1, 2]
STATION_PLATFORM_NUMBERS["MTW"] = [3, 4]

# Platform descriptions for config flow display
PLATFORM_DESCRIPTIONS: dict[str, dict[int, str]] = {
    "MTS": {1: "Southbound (Green)", 2: "Northbound (Green)"},
    "MTW": {3: "Eastbound (Yellow)", 4: "Westbound (Yellow)"},
}


def get_atco_code(station_code: str, platform_number: int) -> str | None:
    """Build the full ATCO code for a station platform."""
    base = STATION_ATCO_BASE.get(station_code)
    if base is None:
        return None
    return f"{base}{platform_number}"


def get_platform_description(station_code: str, platform_number: int) -> str:
    """Get a human-readable description for a platform."""
    if station_code in PLATFORM_DESCRIPTIONS:
        return PLATFORM_DESCRIPTIONS[station_code].get(platform_number, f"Platform {platform_number}")
    if platform_number == 1:
        return "Platform 1"
    return "Platform 2"


def get_configurable_stations() -> dict[str, str]:
    """Return stations available for configuration, excluding MTW (Monument E-W).

    Monument is handled as a single station with 4 platforms.
    MTW shares the same physical station as MTS.
    """
    stations: dict[str, str] = {}
    for code, name in STATION_NAMES.items():
        if code == "MTW":
            continue
        if code in STATION_ATCO_BASE:
            stations[code] = name
    return stations
