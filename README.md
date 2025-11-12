# Power Consumption Monitoring System

A lightweight, resource-efficient power monitoring system designed for embedded devices like the Luckfox Pico Max. Collects data from Home Assistant, generates beautiful dashboards, and publishes to GitHub Pages.

## 🚀 Installation Summary

```bash
# 1. Clone repository
git clone https://github.com/YOUR_USERNAME/powerstats.git
cd powerstats

# 2. Edit config.json with your credentials
vi config.json

# 3. Run installation
sudo sh install.sh

# 4. Access dashboard
# Open http://<device-ip>/ in your browser
```

That's it! The system will automatically collect data every 10 minutes.

## Features

- 🔌 **Home Assistant Integration**: Fetches power consumption data via REST API
- 📊 **Multi-Entity Monitoring**: Track voltage, power, energy, solar, and power factor simultaneously
- 📈 **Beautiful Dashboards**: Interactive Chart.js visualizations with real-time updates
- � **System Health Monitoring**: Real-time disk, memory, collection status, and GitHub sync tracking
- �🌐 **GitHub Pages Publishing**: Automatic deployment to static hosting
- 🔧 **Web-Based Admin**: Simple maintenance mode and manual sync controls
- 💾 **Minimal Footprint**: ~100MB total, runs on 256MB RAM devices
- 🔄 **Rolling Data Window**: Maintains 7-day history automatically
- ⚙️ **Maintenance Mode**: Pause data collection when needed
- 🔋 **Power Cut Detection**: Automatic outage tracking and reporting
- ⚡ **Backward Compatible**: Works with single or multiple sensors

## System Requirements

### Hardware
- **Minimum**: 256MB RAM, 256MB storage
- **Tested on**: Luckfox Pico Max
- **Network**: WiFi/Ethernet connectivity

### Software
- Alpine Linux (or compatible)
- Python 3.x
- lighttpd web server

## Quick Start

### 1. Clone Repository

On your Luckfox Pico Max:

```sh
# Clone the repository
git clone https://github.com/YOUR_USERNAME/powerstats.git
cd powerstats
```

### 2. Configure

Edit `config.json` with your credentials:

```sh
vi config.json
```

**Required Configuration:**

```json
{
  "home_assistant": {
    "url": "http://homeassistant.local:8123",
    "token": "YOUR_HOME_ASSISTANT_LONG_LIVED_ACCESS_TOKEN",
    "entities": {
      "voltage": "sensor.voltage",
      "daily_energy": "sensor.daily_energy",
      "power": "sensor.live_power",
      "solar": "sensor.solar_power",
      "power_factor": "sensor.power_factor"
    }
  },
  "github": {
    "token": "YOUR_GITHUB_PERSONAL_ACCESS_TOKEN",
    "repo": "username/repo-name",
    "branch": "main"
  },
  "data": {
    "directory": "/var/www/html",
    "retention_days": 7
  },
  "web": {
    "root": "/var/www/html"
  },
  "paths": {
    "state_file": "/var/lib/power-monitor/state.json"
  }
}
```

**Note:** If you only have one sensor, you can point all entities to it, or use the old format with just `entity_id`. See [CONFIG_MIGRATION_GUIDE.md](CONFIG_MIGRATION_GUIDE.md) for details.

**Getting Your Tokens:**

#### Home Assistant Token
1. Log into Home Assistant
2. Go to Profile → Security → Long-Lived Access Tokens
3. Create token and copy to `config.json`
4. Find your sensor entity ID in Developer Tools → States

#### GitHub Token & Repository
1. Create a new repository: `https://github.com/new`
2. Generate Personal Access Token:
   - Go to Settings → Developer settings → Personal access tokens → Tokens (classic)
   - Click "Generate new token (classic)"
   - Select scope: `repo` (full control of private repositories)
   - Copy token to `config.json`
3. Update `config.json` with: `username/repo-name`

### 3. Install

Run the installation script:

```sh
sudo sh install.sh
```

The script will:
1. ✓ Validate `config.json`
2. ✓ Install dependencies (Python, lighttpd)
3. ✓ Setup cron jobs
4. ✓ Install application files
5. ✓ Validate GitHub API access
6. ✓ Validate Home Assistant API access
7. ✓ Start web server
8. ✓ Display access URL

### 4. Access Dashboard

After installation completes, access your dashboard:

```
http://<device-ip>/
```

The IP address will be displayed at the end of installation.

## 🎯 Multi-Entity Monitoring

The system now supports tracking **5 different metrics** simultaneously:

| Entity | Purpose | Example Sensor |
|--------|---------|----------------|
| **Voltage** | Grid voltage monitoring | `sensor.voltage` |
| **Daily Energy** | Daily consumption tracking | `sensor.daily_energy` |
| **Power** | Live power usage | `sensor.live_power` |
| **Solar** | Solar generation | `sensor.solar_power` |
| **Power Factor** | Power quality metric | `sensor.power_factor` |

### Benefits
- ✅ **Comprehensive monitoring** - All metrics in one place
- ✅ **Single API call** - Efficient data collection
- ✅ **Backward compatible** - Works with old configs
- ✅ **Flexible setup** - Use 1 or all 5 entities

### Configuration Options

**Option 1: Multiple Sensors (Recommended)**
```json
"entities": {
  "voltage": "sensor.voltage",
  "daily_energy": "sensor.energy",
  "power": "sensor.power",
  "solar": "sensor.solar",
  "power_factor": "sensor.pf"
}
```

**Option 2: Single Sensor (Fallback)**
```json
"entities": {
  "voltage": "sensor.power",
  "daily_energy": "sensor.power",
  "power": "sensor.power",
  "solar": "sensor.power",
  "power_factor": "sensor.power"
}
```

**Option 3: Old Format (Still Works)**
```json
"entity_id": "sensor.power"
```

For detailed migration instructions, see [CONFIG_MIGRATION_GUIDE.md](CONFIG_MIGRATION_GUIDE.md).

## Architecture

```
┌─────────────────────────────────────────────┐
│         Luckfox Pico Max (Alpine)          │
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │   lighttpd (Port 80)                 │  │
│  │   - Serves dashboard                 │  │
│  │   - Runs admin.cgi                   │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │   collector.py (cron: every 10min)   │  │
│  │   - Fetches Home Assistant data      │  │
│  │   - Generates HTML dashboard         │  │
│  │   - Maintains 7-day rolling window   │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │   publisher.py (after collection)    │  │
│  │   - Pushes to GitHub via API         │  │
│  │   - Updates GitHub Pages             │  │
│  └──────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

## File Structure

### Repository Structure
```
powerstats/
├── config.json              # ← EDIT THIS FIRST!
├── install.sh              # Installation script
├── uninstall.sh            # Uninstallation script
├── README.md               # This file
├── opt/
│   └── power-monitor/
│       ├── collector.py    # Data collection script
│       ├── publisher.py    # GitHub publisher
│       ├── config_manager.py
│       ├── utils.py
│       └── templates/
│           └── dashboard.html
└── var/
    └── www/
        └── html/
            ├── index.html  # Dashboard
            └── admin.cgi   # Admin interface
```

### Installed System Structure
```
/opt/power-monitor/
├── collector.py
├── publisher.py
├── config_manager.py
├── config.json              # Copied from repo
└── templates/
    └── dashboard.html

/var/www/html/
├── index.html              # Dashboard
├── admin.cgi               # Admin interface
├── daily.json              # Last 24 hours
├── weekly.json             # Last 7 days
├── monthly.json            # Last 30 days (synced to GitHub)
└── yearly.json             # Last 365 days (synced to GitHub)

/etc/
└── monitor.conf            # Maintenance mode state

/root/
└── config.json             # Symlink to /opt/power-monitor/config.json
```

## Usage

### Automatic Operation

The system runs automatically via cron:
- Collects data every 10 minutes
- Updates dashboard
- Publishes to GitHub Pages

### Admin Interface

Access `http://<device-ip>/admin.cgi` to:
- Toggle maintenance mode
- Trigger manual sync
- View system status

**Default credentials:**
- Username: `admin`
- Password: Set in `config.json`

### Manual Operations

```sh
# Run collection manually
python3 /opt/power-monitor/collector.py

# Publish to GitHub manually
python3 /opt/power-monitor/publisher.py

# Check maintenance mode
cat /etc/monitor.conf

# View logs
tail -f /var/log/power-monitor-collector.log
tail -f /var/log/power-monitor-publisher.log
tail -f /var/log/lighttpd/access.log
```

### Maintenance Mode

Enable maintenance mode to pause data collection:

```sh
# Via web interface
# Access http://<device-ip>/admin.cgi and click "Enable Maintenance Mode"

# Via command line
echo "maintenance_mode=true" > /etc/monitor.conf

# Disable
echo "maintenance_mode=false" > /etc/monitor.conf
```

## Troubleshooting

### No Data Appearing

1. **Check Home Assistant connectivity:**
   ```sh
   curl -H "Authorization: Bearer YOUR_TOKEN" \
        https://your-ha-instance.local:8123/api/states/sensor.power_consumption
   ```

2. **Check collector logs:**
   ```sh
   tail -f /var/log/power-monitor-collector.log
   ```

3. **Verify entity ID:**
   - Make sure the entity ID in `config.json` matches your Home Assistant sensor

### GitHub Publishing Fails

1. **Verify token permissions:**
   - Token needs `repo` scope
   - Repository must exist and be accessible

2. **Check publisher logs:**
   ```sh
   tail -f /var/log/power-monitor-publisher.log
   ```

3. **Test GitHub API access:**
   ```sh
   curl -H "Authorization: token YOUR_GITHUB_TOKEN" \
        https://api.github.com/user
   ```

### Web Interface Not Loading

1. **Check lighttpd status:**
   ```sh
   rc-service lighttpd status
   rc-service lighttpd restart
   ```

2. **Check permissions:**
   ```sh
   ls -la /var/www/html/
   chmod 644 /var/www/html/index.html
   chmod 755 /var/www/html/admin.cgi
   ```

3. **Check lighttpd logs:**
   ```sh
   tail -f /var/log/lighttpd/access.log
   tail -f /var/log/lighttpd/error.log
   ```

### High Memory Usage

1. **Check for zombie processes:**
   ```sh
   ps aux | grep python
   killall -9 python3  # if needed
   ```

2. **Reduce data retention:**
   - Edit `config.json` and reduce `retention_days`

3. **Monitor system resources:**
   ```sh
   free -m
   df -h
   ```

## Resource Usage

### Storage
- Alpine base: ~50MB
- Python + libs: ~40MB
- lighttpd: ~3MB
- Application: ~5MB
- Data files: ~1MB
- **Total: ~100MB**

### Memory (Peak)
- lighttpd: ~3MB
- collector.py: ~15MB (during execution)
- publisher.py: ~10MB (during execution)
- Alpine overhead: ~40MB
- **Total: ~70MB peak (180MB free)**

### Network
- Collection: ~5KB per request (every 10 min)
- GitHub push: ~50KB per push
- **Total: <1MB per hour**

## Development

### Local Testing (Windows/Mac/Linux)

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/powerstats.git
cd powerstats

# Install dependencies
pip install -r requirements.txt

# Edit config.json with your settings
vi config.json

# Run collector
python opt/power-monitor/collector.py

# Run publisher
python opt/power-monitor/publisher.py

# Test dashboard locally
cd var/www/html
python -m http.server 8000
# Open http://localhost:8000
```

### Modifying the Dashboard

1. Edit `opt/power-monitor/templates/dashboard.html`
2. Test locally by running collector
3. Deploy to device

### Adding New Features

The system is modular:
- `config_manager.py`: Configuration handling
- `collector.py`: Data collection and processing
- `publisher.py`: GitHub Pages deployment
- `admin.cgi`: Web-based administration

## Security Considerations

1. **Change Default Password**: Update admin credentials in `config.json`
2. **Secure Config File**: `chmod 600 /opt/power-monitor/config.json`
3. **Use HTTPS**: Configure lighttpd with SSL certificate (optional)
4. **Firewall**: Limit access to admin interface
5. **GitHub Tokens**: Use fine-grained tokens with minimal permissions

## Backup & Restore

### Backup

```sh
tar -czf power-monitor-backup.tar.gz \
    /opt/power-monitor/config.json \
    /var/www/html/data.json \
    /etc/monitor.conf
```

### Restore

```sh
tar -xzf power-monitor-backup.tar.gz -C /
```

## Uninstallation

```sh
cd powerstats
sudo sh uninstall.sh
```

The uninstall script will:
- Stop lighttpd service
- Remove cron jobs
- Remove application files
- Remove configuration files
- Optionally remove installed packages

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Test on real hardware if possible
4. Submit a pull request

## License

See LICENSE file for details.

## Support

For issues, questions, or contributions:
- Create an issue on GitHub
- Check existing issues and documentation
- Review logs for error messages

## Changelog

### Version 1.0.0
- Initial release
- Home Assistant integration
- GitHub Pages publishing
- Web-based admin interface
- Chart.js dashboards
- Maintenance mode
- Rolling 7-day data window

## Acknowledgments

- Built for Luckfox Pico Max
- Uses Chart.js for visualizations
- Inspired by lightweight IoT monitoring needs
- Designed for minimal resource consumption
