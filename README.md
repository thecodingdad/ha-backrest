# Backrest

Home Assistant integration to monitor and control Backrest backup server instances. Provides real-time backup status, plan tracking, and maintenance operations.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/thecodingdad/ha-backrest)](https://github.com/thecodingdad/ha-backrest/releases)

## Features

- Real-time monitoring of backup plan status and health
- Track last backup time, next scheduled backup, and backup duration
- Monitor file count, snapshot count, and data size per plan/repo
- Binary sensor for backup plan health state
- Trigger backups and run maintenance tasks directly from Home Assistant
- Configurable polling interval

## Prerequisites

- Home Assistant 2026.3.0 or newer
- Running Backrest server with API access

## Installation

### HACS (Recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=thecodingdad&repository=ha-backrest&category=integration)

Or add manually:
1. Open HACS in your Home Assistant instance
2. Click the three dots in the top right corner and select **Custom repositories**
3. Enter `https://github.com/thecodingdad/ha-backrest` and select **Integration** as the category
4. Click **Add**, then search for "Backrest" and download it
5. Restart Home Assistant

### Manual Installation

1. Download the latest release from [GitHub Releases](https://github.com/thecodingdad/ha-backrest/releases)
2. Copy the `custom_components/backrest` folder to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

### Setup

1. Go to **Settings** -> **Devices & Services**
2. Click **Add Integration**
3. Search for "Backrest"
4. Follow the setup wizard

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `url` | string | required | Backrest API endpoint URL |
| `username` | string | optional | API username |
| `password` | string | optional | API password |
| `scan_interval` | integer | 60 | Polling interval in seconds (10-3600) |

## Entities

The integration creates the following entities for each backup plan and repository.

### Sensors

| Sensor | Description |
|--------|-------------|
| Last Backup Status | Status of the most recent backup run |
| Last Backup Time | Timestamp of the last completed backup |
| Next Scheduled Backup | Timestamp of the next planned backup run |
| Backup Duration | Duration of the last backup operation |
| File Count | Number of files included in the backup |
| Snapshot Count | Number of snapshots stored |
| Data Size | Total size of backup data |
| Operation ID | Identifier of the last backup operation |
| Display Message | Human-readable status message |
| Hours Since Last Backup | Number of hours elapsed since the last successful backup |

### Binary Sensors

| Binary Sensor | Description |
|---------------|-------------|
| Backup Plan Health | Indicates whether the backup plan is healthy |

### Buttons

| Button | Description |
|--------|-------------|
| Trigger Backup | Manually start a backup for this plan |
| Run Maintenance | Execute maintenance tasks for this plan |

## Multilanguage Support

This integration supports English and German.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
