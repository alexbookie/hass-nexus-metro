# Integration: Nexus Metro

## What This Does
Integrates the Tyne and Wear Metro real-time departure information with Home Assistant.
Exposes: sensors showing next train departures per platform at a configured station.

## API Details
- Base URL: https://metro-rti.nexus.org.uk/api
- Auth: Bearer JWT token scraped from web app (requires User-Agent: `okhttp/3.12.1`)
- Rate limits: Undocumented; upstream refreshes every ~2 minutes
- Docs: https://github.com/danielgjackson/metro-rti (community reverse-engineered)
- This is an unofficial API backing the Nexus Pop mobile app

### Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/stations` | `{code: name}` map of all 60 stations |
| GET | `/stations/platforms` | `{code: [{platformNumber, direction, helperText}]}` |
| GET | `/times/{STATION}/{PLATFORM}` | Array of next trains (up to ~4) |

## Entities
| Platform | Entity | Source |
|----------|--------|--------|
| sensor | Platform N next departure | GET /times/{station}/{platform} |

Each sensor: state = minutes until next train, attributes include destination, line (GREEN/YELLOW),
train number, last event, scheduled/predicted times, and full next_trains list.

## Known Issues / Gotchas
- Unofficial API — could require auth or change at any time
- No timezone in timestamps — all times are UK local (Europe/London)
- `dueIn` = -1 means train has arrived at platform
- Empty array returned overnight when no service running
- Service alerts require separate authenticated Azure API (out of scope)
- `/stations` and `/stations/platforms` may return 401 without correct User-Agent

## Current Status
- [x] API client with typed models
- [x] Config flow (station selection + platform filter)
- [x] Options flow (polling interval)
- [x] DataUpdateCoordinator
- [x] Sensor platform (per-platform departure sensors)
- [x] Tests (82 passing)
- [ ] Diagnostics support
- [ ] Reauth flow (if API starts requiring auth)

## Quick Reference
- **Domain:** `nexus_metro`
- **Class prefix:** `NexusMetro`
- **Main code:** `custom_components/nexus_metro/`
- **Validate:** `script/check`
- **Test:** `script/test`
- **Run HA:** `./script/develop`
