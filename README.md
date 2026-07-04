# Nexus Metro

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield]

Real-time Tyne and Wear Metro departure information for Home Assistant.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/alexbookie/hass-nexus-metro?quickstart=1)

## Features

- **Live departure status**: Combines Traveline scheduled times with live train
  positions from the Nexus KML feed for On time / Delayed / Early / Scheduled status
- **Per-platform sensors**: Monitor specific platforms or the entire station
- **Multiple departure slots**: Track the next 3 upcoming trains per platform
- **Live ETA estimation**: Timetable-derived inter-station travel times refine
  arrival estimates for matched trains
- **Countdown timers**: Minutes-until-arrival updated every 30 seconds between API polls
- **Configurable polling**: Adjust the update interval (30-300 seconds, default 60)
- **No authentication**: Both data sources are open — no API keys or tokens

## Entities

For each monitored platform, the integration creates:

Entity | Description
-- | --
`Platform N next departure` | Minutes until the next train, live estimate preferred over scheduled
`Platform N departure 2` / `departure 3` | Minutes until the 2nd and 3rd trains
`Platform N scheduled` | Raw Traveline scheduled departure (minutes)
`Platform N live estimate` | KML-derived live arrival estimate (minutes)

Departure sensors include extra attributes: destination, status (On time / Delayed /
Early / Scheduled), scheduled due time, live estimate, matched train ID, and a
`departures` list with the next 4 trains (on the primary sensor).

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click **Integrations** > **+ Explore & Download Repositories**
3. Search for **Nexus Metro**
4. Click **Download**
5. Restart Home Assistant

### Manual

1. Download the `custom_components/nexus_metro/` folder from this repository
2. Copy it to your Home Assistant `custom_components/` directory
3. Restart Home Assistant

## Configuration

1. Go to **Settings** > **Devices & Services**
2. Click **+ Add Integration**
3. Search for **Nexus Metro**
4. Select your Metro station from the dropdown
5. Choose which platforms to monitor (or leave all selected)

### Options

After setup, click **Configure** on the integration to adjust:

- **Update interval** — how often to fetch departure data (30-300 seconds)

## Data Sources

- **Scheduled departures**: [Traveline](https://www.traveline.info/) stop pages
  (per-platform ATCO codes)
- **Live train positions**: the open Nexus KML feed that powers the official
  live Metro map

Both sources are unofficial and unauthenticated; the integration polls them
politely (default 60 s) and degrades to scheduled-only data if the live feed
is unavailable.

## Troubleshooting

### No data / "Unknown" state

Traveline returns empty data outside Metro operating hours (roughly 05:30-23:30). This is normal behaviour.

### Connection errors

The integration relies on unofficial data sources. If they change or go down, sensors may show unavailable. Check the [issue tracker](https://github.com/alexbookie/hass-nexus-metro/issues) for known issues.

### Debug logging

Add this to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.nexus_metro: debug
```

## Development

### Cloud (Recommended)

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/alexbookie/hass-nexus-metro?quickstart=1)

### Local

Requires Docker and VS Code with the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers).

1. Clone this repository
2. Open in VS Code
3. Click "Reopen in Container" when prompted

### Scripts

Command | Description
-- | --
`script/develop` | Start Home Assistant with the integration loaded
`script/test` | Run the test suite
`script/check` | Run type checking, linting, and spell checking

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Made with care by [@alexbookie][user_profile]**

---

[commits-shield]: https://img.shields.io/github/commit-activity/y/alexbookie/hass-nexus-metro.svg?style=for-the-badge
[commits]: https://github.com/alexbookie/hass-nexus-metro/commits/main
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/alexbookie/hass-nexus-metro.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40alexbookie-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/alexbookie/hass-nexus-metro.svg?style=for-the-badge
[releases]: https://github.com/alexbookie/hass-nexus-metro/releases
[user_profile]: https://github.com/alexbookie
