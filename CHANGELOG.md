# Changelog

## 0.2.0 (2026-07-04)

### Changed (data source rewrite)

- Replaced the Nexus RTI JSON API (token-gated by Nexus in mid-2026, breaking v0.1.0)
  with a new two-source architecture: Traveline scheduled departures + the open
  Nexus KML live-train feed.
- Existing config entries migrate automatically (v1 → v2); no re-configuration
  needed. The primary departure sensors keep their entity IDs.
- The v0.1.0 destination and line sensors are no longer provided; any orphaned
  entities can be removed from the entity registry after updating.

### Features

- Scheduled departures from Traveline stop pages (per-platform ATCO codes)
- Live train positions from the open Nexus KML feed (`trainstatuses.kml`)
- Train matching engine pairing scheduled departures with live trains:
  On time / Delayed (~Xm) / Early (~Xm) / Scheduled status per departure
- Live ETA estimation using timetable-derived inter-station travel times
- Three sensor types per platform (five entities): scheduled, live estimate,
  and combined next/2nd/3rd departure
- Station and ATCO reference data for all 60 Metro stations
- No authentication required by either data source (removes JWT token scraping)

### Fixed

- Integration no longer breaks when Nexus rotates or gates RTI API tokens

## 0.1.0 (2026-03-29)

### Features

- Real-time departure sensors for Tyne and Wear Metro stations
- Config flow with station selection and platform filtering
- Options flow for configurable polling interval
- Per-platform sensors showing next departure time, destination, and line
- Full train details (scheduled/predicted times, train number) in sensor attributes
- JWT token authentication with automatic refresh

### Infrastructure

- GitHub Actions CI: Hassfest, HACS validation, Ruff linting
- Dependabot for automated dependency updates
