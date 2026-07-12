# Integration: Nexus Metro

## What This Does
Integrates the Tyne and Wear Metro departure information with Home Assistant.
Combines Traveline scheduled departures with live KML train positions to provide
real-time status (On time / Delayed / Scheduled) per platform.

## Data Sources (both auth-free)

### 1. Traveline Scheduled Departures
- Endpoint: `https://www.traveline.info/stops/{ATCO_CODE}`
- Header: `X-Requested-With: XMLHttpRequest` (returns clean HTML fragment)
- Parse: regex on sr-only text for service, destination, departure time
- Returns: scheduled times like "5 mins", "Due", "22:41"
- ATCO codes per platform (e.g. 9400ZZTWWJM1 = West Jesmond Platform 1)

### 2. KML Live Train Positions
- Endpoint: `https://app-metrortiapi-prod-001.azurewebsites.net/api/geo/trainstatuses.kml?d={timestamp_ms}`
- Returns: XML/KML with Placemark per active train
- Parse: coordinates, last event (Arrived/Departed/Approaching/Ready), station, platform, time, destination
- CORS enabled, no auth required

### Combined Logic
- Traveline = baseline scheduled times
- Match each departure to a live KML train heading to same destination
- Use timetable-derived inter-station travel times for ETA estimation
- Status: "On time" if live ETA within 3 mins of scheduled, "Delayed (~Xm)" if >3m late, "Scheduled" if no match
- Trains at terminus (READY/Arrived at route origin) treated as "On time"

## Entities
| Platform | Entity | Description |
|----------|--------|-------------|
| sensor | Platform N scheduled | Raw Traveline scheduled departure time |
| sensor | Platform N live estimate | KML-derived estimated arrival time |
| sensor | Platform N next departure | Combined best-available time with status |

Each sensor: state = minutes until next train. Attributes include destination, full departure list,
and (for combined) status, train ID, live estimate, scheduled due.

## Known Issues / Gotchas
- Traveline returns empty results outside operating hours (~05:30-23:30)
- KML feed may lag behind actual train positions by 1-2 minutes
- ATCO codes differ from internal route codes (e.g. Heworth = HPW in ATCO, HTH internally)
- Monument has 4 platforms: 1/2 (N-S Green) and 3/4 (E-W Yellow), same ATCO base
- Station name variations in KML may not match — aliases handled in STATION_NAME_TO_CODE

## Current Status
- [x] Traveline + KML API clients
- [x] Train matching / ETA estimation logic
- [x] Config flow (station + platform selection from static data)
- [x] Options flow (polling interval)
- [x] DataUpdateCoordinator (combined fetch)
- [x] Three sensor types per platform (scheduled, live, combined)
- [x] ATCO codes for all 60 stations
- [x] Tests (66 passing)
- [ ] Diagnostics support

## Quick Reference
- **Domain:** `nexus_metro`
- **Class prefix:** `NexusMetro`
- **Main code:** `custom_components/nexus_metro/`
- **Validate:** `script/check`
- **Test:** `script/test`
- **Run HA:** `./script/develop`
