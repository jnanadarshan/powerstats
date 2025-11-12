# Health Monitoring Feature

## Overview
The Health tab provides real-time system monitoring for your Luckfox Pico Max device, showing resource usage, data collection status, and GitHub sync information.

## Features

### 1. **System Resources**
- **Disk Usage**: Real-time storage monitoring with visual progress bar
  - Total, used, and free space in GB
  - Percentage used
  - Color-coded alerts (green < 75%, orange < 90%, red ≥ 90%)
  
- **Memory Usage**: RAM monitoring with visual progress bar
  - Total, used, and available memory in MB
  - Percentage used
  - Color-coded alerts (green < 75%, orange < 90%, red ≥ 90%)

### 2. **Data Collection Status**
- **Last Collection Time**: Shows when data was last collected from Home Assistant (in IST timezone)
- **Next Collection Countdown**: Live countdown timer showing minutes and seconds until next collection
- **Collection Interval**: Displays the configured collection interval (default: 10 minutes)

### 3. **GitHub Sync Status**
- **Configuration**: Shows if GitHub is properly configured (✅/❌)
- **Repository**: Displays the connected GitHub repository
- **Last Publish Time**: Shows when data was last published to GitHub (in IST timezone)
- **Status**: Current sync status (Success/Error/Unknown) with color coding

### 4. **Auto-Refresh**
- Health data automatically refreshes every 10 seconds (configurable)
- Countdown timer updates every second
- Visual indicator shows last update time

## Configuration

### config.json
Add the following to your `config.json`:

```json
{
  "data": {
    "retention_days": 7,
    "collection_interval_minutes": 10,
    "health_check_interval_seconds": 10
  }
}
```

**Parameters:**
- `health_check_interval_seconds`: How often to refresh health data (default: 10)

## Installation

The health monitoring system is automatically installed with the main installation script.

### Manual Installation (if needed)

1. **Install psutil:**
   ```bash
   apk add py3-psutil
   ```

2. **Copy health files:**
   ```bash
   cp opt/power-monitor/health.py /opt/power-monitor/
   cp var/www/html/health.cgi /var/www/html/
   chmod +x /opt/power-monitor/health.py
   chmod +x /var/www/html/health.cgi
   ```

3. **Test health endpoint:**
   ```bash
   python3 /opt/power-monitor/health.py /opt/power-monitor/config.json
   ```

## Testing

Run the test script to verify installation:

```bash
sh deployment/test_health.sh
```

The script will check:
- ✓ health.py exists and is executable
- ✓ psutil is installed
- ✓ health.cgi exists and is executable
- ✓ health.py produces valid JSON
- ✓ health.cgi is accessible via HTTP
- ✓ config.json has health settings

## Usage

1. Open your Power Monitor dashboard: `http://your-device-ip/`
2. Click the **Health** tab in the navigation bar
3. View real-time system health metrics
4. Data auto-refreshes every 10 seconds

## API Endpoint

### GET /health.cgi

Returns JSON with system health data:

```json
{
  "timestamp": "2024-01-15T10:30:00.000000+00:00",
  "disk": {
    "path": "/var/www/html",
    "total_gb": 0.24,
    "used_gb": 0.08,
    "free_gb": 0.16,
    "percent": 33.3
  },
  "memory": {
    "total_mb": 256.0,
    "used_mb": 128.5,
    "available_mb": 127.5,
    "percent": 50.2
  },
  "collection": {
    "last_collection_ist": "2024-01-15 16:00:00 IST",
    "last_collection_utc": "2024-01-15T10:30:00+00:00",
    "next_collection_ist": "2024-01-15 16:10:00 IST",
    "seconds_until_next": 420,
    "interval_minutes": 10
  },
  "github": {
    "configured": true,
    "last_publish_ist": "2024-01-15 16:05:00 IST",
    "status": "Success",
    "repo": "username/powerstats-data",
    "branch": "main"
  }
}
```

## Troubleshooting

### Health tab shows "Error"
**Cause:** health.cgi cannot be accessed or returned invalid data

**Solution:**
```bash
# Check if health.cgi is executable
ls -la /var/www/html/health.cgi

# Test health.cgi manually
python3 /var/www/html/health.cgi

# Check lighttpd error logs
tail -f /var/log/lighttpd/error.log
```

### Disk/Memory shows 0%
**Cause:** psutil not installed or cannot read system info

**Solution:**
```bash
# Install psutil
apk add py3-psutil

# Test psutil
python3 -c "import psutil; print(psutil.disk_usage('/'));"
```

### Countdown timer not working
**Cause:** No data collected yet or daily.json doesn't exist

**Solution:**
```bash
# Run collector manually
python3 /opt/power-monitor/collector.py

# Check if daily.json exists
ls -la /var/www/html/daily.json
```

### GitHub status shows "Not Configured"
**Cause:** GitHub token or repo not set in config.json

**Solution:**
```bash
# Edit config.json and add GitHub credentials
vi /opt/power-monitor/config.json

# Add:
{
  "github": {
    "token": "ghp_xxxxxxxxxxxx",
    "repo": "username/repo-name",
    "branch": "main"
  }
}
```

### "Last Collection" shows "Never"
**Cause:** Collector hasn't run yet or daily.json is missing

**Solution:**
```bash
# Check cron job
crontab -l | grep collector

# Run collector manually
python3 /opt/power-monitor/collector.py

# Check logs
tail -f /var/log/power-monitor-collector.log
```

## Architecture

### Components

1. **health.py** - Python module for system health monitoring
   - Uses `psutil` for disk and memory info
   - Reads `daily.json` for collection status
   - Reads state file for GitHub status
   - Returns JSON report

2. **health.cgi** - CGI endpoint
   - Calls health.py
   - Returns JSON response
   - Handles errors gracefully

3. **dashboard.html** - Health tab UI
   - Fetches data from health.cgi every 10 seconds
   - Updates UI in real-time
   - Shows countdown timer
   - Color-codes resource usage

### Data Flow

```
Browser                health.cgi              health.py
   |                       |                       |
   |-- GET /health.cgi --> |                       |
   |                       |-- import health ---> |
   |                       |                       |
   |                       |                       |-- psutil.disk_usage()
   |                       |                       |-- psutil.virtual_memory()
   |                       |                       |-- read daily.json
   |                       |                       |-- read state.json
   |                       |                       |
   |                       | <-- JSON report ----- |
   | <-- JSON response --- |                       |
   |                       |                       |
   |-- (10 seconds later) --|                      |
```

### IST Timezone Conversion

All times are stored in UTC but displayed in IST (UTC+5:30):
- Last collection time
- Next collection time
- Last GitHub publish time

## Performance Impact

- **Negligible**: Health monitoring uses < 1% CPU
- **Memory**: ~2-3 MB additional RAM
- **Network**: ~1 KB per request (every 10 seconds)
- **Disk**: No additional writes (read-only)

## Security

- Health endpoint is read-only
- No authentication required (local network only)
- No sensitive data exposed (config tokens not shown)
- All data is from local system

## Future Enhancements

Potential additions:
- [ ] CPU temperature monitoring
- [ ] Network usage statistics
- [ ] Process monitoring (collector/publisher status)
- [ ] System uptime tracking
- [ ] Historical health metrics
- [ ] Alert thresholds for disk/memory
- [ ] Email/notification on critical resource usage
