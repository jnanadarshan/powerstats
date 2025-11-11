# Power Consumption Monitoring System

A lightweight, resource-efficient power monitoring system designed for embedded devices like the Luckfox Pico Max. Collects data from Home Assistant, generates beautiful dashboards, and publishes to GitHub Pages.

## Features

- 🔌 **Home Assistant Integration**: Fetches power consumption data via REST API
- 📊 **Beautiful Dashboards**: Interactive Chart.js visualizations
- 🌐 **GitHub Pages Publishing**: Automatic deployment to static hosting
- 🔧 **Web-Based Admin**: Simple maintenance mode and manual sync controls
- 💾 **Minimal Footprint**: ~100MB total, runs on 256MB RAM devices
- 🔄 **Rolling Data Window**: Maintains 7-day history automatically
- ⚙️ **Maintenance Mode**: Pause data collection when needed

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

### 1. Installation

On your Luckfox Pico Max (as root):

```sh
cd /tmp
# Upload the entire project directory
cd powerstats/deployment
chmod +x install.sh
./install.sh
```

### 2. Configuration

Create `/opt/power-monitor/config.json` based on the example:

```json
{
  "homeassistant": {
    "url": "https://your-ha-instance.local:8123",
    "token": "your_long_lived_access_token",
    "entity_id": "sensor.power_consumption"
  },
  "github": {
    "token": "ghp_your_github_token",
    "repo_owner": "your-username",
    "repo_name": "power-stats-pages",
    "branch": "main"
  },
  "data": {
    "retention_days": 7,
    "collection_interval_minutes": 10
  },
  "admin": {
    "username": "admin",
    "password_hash": "your_password"
  },
  "paths": {
    "state_file": "/etc/monitor.conf",
    "web_root": "/var/www/html",
    "data_file": "/var/www/html/data.json"
  }
}
```

**Important Configuration Steps:**

#### Home Assistant Token
1. Log into Home Assistant
2. Go to Profile → Security → Long-Lived Access Tokens
3. Create a new token and copy it to `config.json`

#### GitHub Token & Repository
1. Create a new public repository (e.g., `power-stats-pages`)
2. Go to Settings → Pages → Enable GitHub Pages (source: root)
3. Generate a Personal Access Token:
   - Go to GitHub Settings → Developer settings → Personal access tokens
   - Create token with `repo` permissions
4. Add token to `config.json`

### 3. Test Installation

```sh
cd /tmp/powerstats/deployment
chmod +x test.sh
./test.sh
```

### 4. Manual Test Run

```sh
# Test data collection
python3 /opt/power-monitor/collector.py

# Test GitHub publishing
python3 /opt/power-monitor/publisher.py

# Check web interface
curl http://localhost/
```

### 5. Access Interfaces

- **Dashboard**: `http://<device-ip>/`
- **Admin Panel**: `http://<device-ip>/admin.cgi`

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

```
/opt/power-monitor/
├── collector.py              # Main data collection script
├── publisher.py              # GitHub Pages publisher
├── config_manager.py         # Configuration handler
├── config.json              # Your configuration (create this!)
├── config.example.json      # Configuration template
└── templates/
    └── dashboard.html       # Dashboard template

/var/www/html/
├── index.html              # Generated dashboard
├── data.json               # 7-day data storage
└── admin.cgi               # Admin interface

/etc/
└── monitor.conf            # Maintenance mode state
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
git clone <your-repo>
cd powerstats

# Install dependencies
pip install -r requirements.txt

# Copy example config
cp opt/power-monitor/config.example.json opt/power-monitor/config.json

# Edit config.json with your settings

# Run collector
python opt/power-monitor/collector.py

# Run publisher
python opt/power-monitor/publisher.py
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
cd /tmp/powerstats/deployment
chmod +x uninstall.sh
./uninstall.sh
```

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
