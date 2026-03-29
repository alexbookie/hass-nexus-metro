# Nexus Metro

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield]

Real-time Tyne and Wear Metro departure information for Home Assistant.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/alexbookie/hass-nexus-metro?quickstart=1)

## Features

- **Real-time departures**: See the next trains arriving at any Metro station
- **Per-platform sensors**: Monitor specific platforms or the entire station
- **Multiple departure slots**: Track the next 3 upcoming trains per platform
- **Line and destination info**: See which line (Green/Yellow) and destination for each train
- **Countdown timers**: Minutes-until-arrival updated every 30 seconds between API polls
- **Configurable polling**: Adjust the update interval (60-300 seconds, default 90)

## Entities

For each monitored platform, the integration creates:

Entity | Description
-- | --
`Platform N next departure` | Minutes until the next train (state = minutes, -1 = arrived)
`Platform N 2nd departure` | Minutes until the 2nd train
`Platform N 3rd departure` | Minutes until the 3rd train
`Platform N destination` | Destination of the next train
`Platform N line` | Line colour of the next train (GREEN or YELLOW)

Each departure sensor includes extra attributes: destination, line, train number, last event, scheduled/predicted times, and a `next_trains` list (on the first slot).

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

- **Update interval** — how often to fetch departure data (60-300 seconds)

## Troubleshooting

### No data / "Unknown" state

The Metro API returns empty data overnight when there is no service running. This is normal behaviour.

### Connection errors

The integration uses an unofficial API that backs the Nexus Pop mobile app. If the API changes or goes down, the integration will show unavailable. Check the [issue tracker](https://github.com/alexbookie/hass-nexus-metro/issues) for known issues.

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
[hacsbadge]: https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/alexbookie/hass-nexus-metro.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40alexbookie-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/alexbookie/hass-nexus-metro.svg?style=for-the-badge
[releases]: https://github.com/alexbookie/hass-nexus-metro/releases
[user_profile]: https://github.com/alexbookie
