# Changelog

## 0.3.0 (2026-07-12)

### Fixed

- Live train matching works again: Traveline destination text is now normalised
  ("X Metro Station" suffix stripped, "Newcastle Airport" → "Airport") so it
  matches the KML feed's bare names. Without this, v0.2.0 showed every
  departure as "Scheduled" with no live status.
- Sunderland-line route data restored: Fellgate, Brockley Whins, and East
  Boldon were missing from the green-line route (Pelaw→Seaburn was one 5-minute
  hop instead of four segments totalling ~11 minutes).
- Route resolution now slices by terminus code instead of magic indices:
  "Sunderland" trains previously routed only as far as Pallion, and
  "Regent Centre" / "Monument East" routes ran in the wrong direction.
  Brockley Whins short-turn workings are now recognised.

### Changed (prediction calibration, field-tested 2026-07-04)

- Live ETAs now include 0.2 minutes of dwell time per intermediate stop,
  removing a systematic optimism bias that grew with distance
  (+1.57 min average before, −0.02 min after, validated across six stations).
- The "Early (~Xm)" status has been removed. Field testing showed those
  estimates were model error, not early running — Metro trains hold to
  schedule. Live estimates more than 2 minutes ahead of the timetable now
  fall back to the scheduled time and report "On time"; the matched train ID
  remains visible in attributes.
- Displayed prediction accuracy after calibration: MAE 1.24 min overall,
  ~0.8 min for trains within 10 minutes (out-of-sample, 1,802 predictions).
  Full report in `docs/research/2026-07-04-prediction-accuracy.md`.

### Build

- Dependency bumps (dependabot): actions/checkout 7.0.0, astral-sh/setup-uv
  8.2.0, home-assistant/actions pin, devcontainer node feature 2.1.0,
  pyright 1.1.411.

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
