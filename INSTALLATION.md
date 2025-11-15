# Power Monitoring System - Installation Guide

## Prerequisites

Before starting, you'll need:

1. **Luckfox Pico Max** with Alpine Linux
2. **Home Assistant** instance with REST API access
3. **GitHub account** for data storage and Pages hosting
4. **Network connectivity** on the device

## Installation Steps

### Step 1: Clone Repository

```bash
git clone https://github.com/jnanadarshan/powerstats.git
cd powerstats
```

### Step 2: Configure System

Edit the `config.json` file:

```bash
vi config.json
```

#### Required Fields:

**Home Assistant:**
- `url`: Your Home Assistant URL (e.g., `http://homeassistant.local:8123`)
- `token`: Long-lived access token from HA Profile → Security
- `entities.power_sensor`: Entity ID for power consumption (e.g., `sensor.power_consumption`)
- `entities.solar_sensor`: Entity ID for solar generation (e.g., `sensor.solar_generation`)

**GitHub:**
- `token`: Personal access token with `repo` permissions
- `repo`: Your repository in format `username/repo-name`
- `branch`: Branch name (usually `main`)
- `user.name`: Your Git username
- `user.email`: Your Git email

**Finding Entity IDs:**
1. Open Home Assistant
2. Go to Developer Tools → States
3. Search for your power/solar sensors
4. Copy the entity_id

### Step 3: Run Installation

```bash
sudo sh install.sh
```

The script will:
1. ✓ Validate config.json
2. ✓ Install Python, lighttpd, and dependencies (~40 MB)
3. ✓ Setup cron jobs (data collection schedule is configurable via `config.json`)
4. ✓ Install application files
5. ✓ Validate GitHub API access
6. ✓ Validate Home Assistant API access
7. ✓ Start web server
8. ✓ Run initial data collection
### mDNS / Local hostnames

During installation, you'll be prompted whether to enable local mDNS (Bonjour) hostname resolution (e.g., `power.local`). If enabled, the installer will:
- Persist mDNS settings to `/opt/power-monitor/config.json` (`mdns.enabled`, `mdns.hostname`, `mdns.http_port`)
- Install a lightweight Python Zeroconf advertiser and enable a system service so `power.local` is discoverable
- Optionally set the system hostname to the mDNS hostname

This is optional and defaults to disabled.


### Step 4: Access Dashboard

Open your browser to:
```
http://<device-ip>/
```

The device IP will be shown at the end of installation.

## What Happens After Installation?

### Automatic Operations

- **Data Collection**: Schedule defined in `config.json` (`data.local_collection_interval_minutes`)
   - Fetches power data from Home Assistant
   - Updates local JSON files (daily, weekly)

- **Data Publishing**: Schedule defined in `config.json` (`data.publish_interval_minutes`)
   - Syncs monthly and yearly data to GitHub
   - Updates GitHub Pages

### Manual Operations

If needed, you can run these commands:

```bash
# Collect data manually
python3 /opt/power-monitor/collector.py

# Publish to GitHub manually
python3 /opt/power-monitor/publisher.py

# Restart web server
sudo rc-service lighttpd restart

# View logs
tail -f /var/log/power-monitor-collector.log
tail -f /var/log/power-monitor-publisher.log

# Edit config
vi /root/config.json
```

## Troubleshooting

### Installation Fails: "config.json not found"
```bash
# Make sure you're in the repo directory
cd powerstats
ls -l config.json
```

### Installation Fails: "config.json is not valid JSON"
```bash
# Validate your JSON syntax
python3 -c "import json; json.load(open('config.json'))"
```

### GitHub API Validation Fails
- Verify your token has `repo` permissions
- Check repository name format: `username/repo-name`
- Ensure repository exists and is accessible

### Home Assistant API Validation Fails
- Verify HA URL is correct and accessible from device
- Check token is valid (create new one if expired)
- Verify entity IDs exist in Developer Tools → States

### Web Server Not Starting
```bash
# Check lighttpd status
sudo rc-service lighttpd status

# Check logs
sudo tail /var/log/lighttpd/error.log

# Restart service
sudo rc-service lighttpd restart
```

### No Data Appearing
```bash
# Check collector logs
tail -f /var/log/power-monitor-collector.log

# Test Home Assistant connection
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "http://homeassistant.local:8123/api/states/sensor.power_consumption"
```

## System Commands

### Service Management
```bash
# Start web server
sudo rc-service lighttpd start

# Stop web server
sudo rc-service lighttpd stop

# Restart web server
sudo rc-service lighttpd restart

# Check status
sudo rc-service lighttpd status
```

### Cron Management
```bash
# View cron jobs
crontab -l

# Edit cron jobs
crontab -e
```

### Configuration
```bash
# Edit config (symlinked to /root for easy access)
vi /root/config.json

# Or edit original
vi /opt/power-monitor/config.json

# Changes take effect on next cron run (no restart needed)
```

## Updating Configuration

If you need to change settings after installation:

1. Edit the config file:
   ```bash
   vi /root/config.json
   ```

2. Save changes (Ctrl+X, then Y in vi)

3. Changes take effect on next cron run (within the configured interval)
   Or trigger manually:
   ```bash
   python3 /opt/power-monitor/collector.py
   python3 /opt/power-monitor/publisher.py
   ```

## Upgrading

If you want to update the application from your GitHub repo, use `upgrade.sh` located at the top level of the repository. The script supports:

- UI files (e.g., `/var/www/html/admin.cgi`, `theme.css`)
- Backend Python files in `/opt/power-monitor/`
- Template files under `/opt/power-monitor/templates/` (if your repository includes them)

The script preserves `config.json` and all local JSON data files. For UI-only upgrades that fetch `var/www/html` and optional templates, `deployment/ui-upgrade.sh` can be used to perform a sparse checkout and deploy only UI-related files.

The upgrade script will automatically back up existing `var/www/html` files to `/root/powerstats-ui-backup-<timestamp>` before overwriting them so you can restore if something goes wrong.

Run the script as root and follow the prompts:

```bash
sudo sh upgrade.sh
```

## Uninstallation

To completely remove the system:

```bash
cd powerstats
sudo sh uninstall.sh
```

This will:
- Stop lighttpd service
- Remove cron jobs
- Remove all application files
- Remove configuration files
- Optionally remove installed packages

## Support

For issues:
1. Check logs in `/var/log/`
2. Review this guide
3. Create an issue on GitHub with:
   - Error messages from logs
   - Steps to reproduce
   - System information

## Quick Reference

| Command | Description |
|---------|-------------|
| `sudo sh install.sh` | Install system |
| `sudo sh uninstall.sh` | Remove system |
| `vi /root/config.json` | Edit configuration |
| `sudo rc-service lighttpd restart` | Restart web server |
| `python3 /opt/power-monitor/collector.py` | Collect data manually |
| `python3 /opt/power-monitor/publisher.py` | Publish to GitHub |
| `tail -f /var/log/power-monitor-collector.log` | View collector logs |
| `crontab -l` | View cron schedule |

## File Locations

| Path | Description |
|------|-------------|
| `/opt/power-monitor/` | Application directory |
| `/opt/power-monitor/config.json` | Configuration file |
| `/root/config.json` | Config symlink (easy access) |
| `/var/www/html/` | Web root (dashboard files) |
| `/var/www/html/*.json` | Data files (daily, weekly, monthly, yearly) |
| `/var/log/power-monitor-*.log` | Application logs |
| `/var/log/lighttpd/` | Web server logs |
| `/etc/monitor.conf` | Maintenance mode state |
