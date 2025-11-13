# Power Monitor - New Multi-JSON Architecture

## Overview

The application now uses **4 separate JSON files** with different retention periods and storage locations:

1. **daily.json** - Last 24 hours (12:00 AM to 11:59 PM)
   - Stored locally
   - Rotates at midnight automatically
   - Raw data at the configured collection interval (`data.local_collection_interval_minutes`)

2. **weekly.json** - Rolling 7 days
   - Stored locally
   - Hourly aggregated data
   - Updated daily at 12:02 AM

3. **monthly.json** - Rolling 30 days
   - Synced to GitHub
   - Daily aggregated data
   - Updated daily at 12:05 AM + pushed to GitHub

4. **yearly.json** - Rolling 365 days
   - Synced to GitHub
   - Daily aggregated data
   - Updated daily at 12:15 AM + pushed to GitHub

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Home Assistant                                               │
│ (Power Sensor)                                              │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ Collector runs at configured interval (see `config.json`)
                 ↓
┌─────────────────────────────────────────────────────────────┐
│ daily.json (Local Storage)                                  │
│ • Raw 10-minute data                                        │
│ • Rotates at midnight (00:00)                               │
│ • Used for "Today" view                                     │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ Nightly at 12:02 AM (scheduler.py)
                 ↓
┌─────────────────────────────────────────────────────────────┐
│ weekly.json (Local Storage)                                 │
│ • Hourly aggregated data                                    │
│ • Rolling 7 days                                            │
│ • Used for "7 Days" view                                    │
└─────────────────────────────────────────────────────────────┘
                 │
                 │ Nightly at 12:05 AM (scheduler.py)
                 ↓
┌─────────────────────────────────────────────────────────────┐
│ monthly.json (GitHub + Local Cache)                         │
│ • Daily aggregated data                                     │
│ • Rolling 30 days                                           │
│ • Used for "30 Days" view                                   │
│ • Synced to GitHub                                          │
└─────────────────────────────────────────────────────────────┘
                 │
                 │ Nightly at 12:15 AM (scheduler.py)
                 ↓
┌─────────────────────────────────────────────────────────────┐
│ yearly.json (GitHub + Local Cache)                          │
│ • Daily aggregated data                                     │
│ • Rolling 365 days                                          │
│ • Used for "365 Days" view                                  │
│ • Synced to GitHub                                          │
└─────────────────────────────────────────────────────────────┘
```

## Components

-### 1. collector.py (Updated)
- Collects data from Home Assistant at the configured interval (`data.local_collection_interval_minutes`)
- - Writes to `daily.json`
- Automatically rotates file at midnight
- Only keeps data from 00:00:00 to current time

### 2. aggregator.py (New)
- Aggregates data at scheduled times
- Three main functions:
  - `aggregate_weekly()` - Aggregates daily → hourly for 7 days
  - `aggregate_monthly()` - Aggregates daily → daily average for 30 days
  - `aggregate_yearly()` - Aggregates daily → daily average for 365 days

### 3. github_sync.py (New)
- Syncs monthly.json and yearly.json to GitHub
- Uses GitHub Contents API
- Handles file creation and updates
- Fetches existing data on startup

### 4. scheduler.py (New)
- Runs nightly jobs at specific times:
  - **12:02 AM**: Aggregate to weekly.json
  - **12:05 AM**: Aggregate to monthly.json + sync to GitHub
  - **12:15 AM**: Aggregate to yearly.json + sync to GitHub
- Prevents double-runs on same day
- Can run as daemon or one-shot

## Setup

### 1. Install Dependencies

```bash
pip install requests
```

### 2. Configure GitHub Token

Edit `/opt/power-monitor/config.json`:

```json
{
  "github": {
    "token": "ghp_your_personal_access_token",
    "repo": "your-username/power-stats-data",
    "branch": "main"
  }
}
```

**Creating a GitHub Token:**
1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Generate new token (classic)
3. Select scope: `repo` (Full control of private repositories)
4. Copy token and add to config.json

### 3. Create GitHub Repository

Create a new repository (public or private) to store monthly/yearly data:

```bash
# Example: https://github.com/your-username/power-stats-data
```

The scheduler will automatically create the `data/` folder and JSON files.

### 4. Update Collector Data File Path

Edit `/opt/power-monitor/config.json`:

```json
{
  "paths": {
    "data_dir": "/var/www/html"
  }
}
```

Update collector to use `daily.json`:

```python
# In config_manager.py, ensure data_file points to:
# /var/www/html/daily.json
```

### 5. Start Scheduler Daemon

```bash
# Run scheduler as daemon
python3 /opt/power-monitor/scheduler.py --daemon

# Or run once for testing
python3 /opt/power-monitor/scheduler.py --once
```

### 6. Setup Systemd Service (Optional)

Create `/etc/systemd/system/power-monitor-scheduler.service`:

```ini
[Unit]
Description=Power Monitor Nightly Scheduler
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/power-monitor
ExecStart=/usr/bin/python3 /opt/power-monitor/scheduler.py --daemon
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable power-monitor-scheduler
sudo systemctl start power-monitor-scheduler
sudo systemctl status power-monitor-scheduler
```

## Dashboard Updates

The dashboard now loads different JSON files based on the active tab:

- **Today tab**: Fetches `daily.json`
- **7 Days tab**: Fetches `weekly.json`
- **30 Days tab**: Fetches `monthly.json` (from GitHub if not cached locally)
- **365 Days tab**: Fetches `yearly.json` (from GitHub if not cached locally)

## Manual Operations

### Test Aggregation

```bash
# Run all aggregations immediately
python3 /opt/power-monitor/aggregator.py /var/www/html
```

### Manual GitHub Sync

```bash
# Push to GitHub
python3 /opt/power-monitor/github_sync.py /var/www/html push

# Fetch from GitHub
python3 /opt/power-monitor/github_sync.py /var/www/html fetch
```

### Check Scheduler Status

```bash
# View logs
tail -f /var/log/power-monitor-scheduler.log

# Or if running as systemd service
sudo journalctl -u power-monitor-scheduler -f
```

## Data Flow Timeline

| Time       | Action                                    | Files Updated           |
|------------|-------------------------------------------|-------------------------|
| Every 10m  | Collector fetches from Home Assistant     | `daily.json`            |
| 00:00:00   | Midnight rotation clears daily.json       | `daily.json`            |
| 00:02:00   | Aggregate yesterday → weekly              | `weekly.json`           |
| 00:05:00   | Aggregate yesterday → monthly + sync      | `monthly.json` (GitHub) |
| 00:15:00   | Aggregate yesterday → yearly + sync       | `yearly.json` (GitHub)  |

## Storage Requirements

- **Local**: ~2-3 MB for daily.json + weekly.json
- **GitHub**: ~500 KB for monthly.json + yearly.json (per year)

## Troubleshooting

### Scheduler Not Running

```bash
# Check if scheduler is running
ps aux | grep scheduler

# Check logs
tail -f /var/log/power-monitor-scheduler.log
```

### GitHub Sync Failing

1. Verify token has `repo` scope
2. Check repository exists and is accessible
3. Verify token hasn't expired
4. Check network connectivity

```bash
# Test GitHub sync manually
python3 /opt/power-monitor/github_sync.py /var/www/html push
```

### Missing Data Files

```bash
# Initialize empty JSON files
cd /var/www/html
echo '{"data_points":[],"last_update":null}' > daily.json
echo '{"data_points":[],"last_update":null}' > weekly.json
echo '{"data_points":[],"last_update":null}' > monthly.json
echo '{"data_points":[],"last_update":null}' > yearly.json
```

## Migration from Old System

If migrating from the old single `data.json` system:

1. **Backup existing data:**
   ```bash
   cp /var/www/html/data.json /var/www/html/data.json.backup
   ```

2. **Split into new format:**
   ```bash
   # Use the last 24 hours as daily.json
   # Use all data aggregated as weekly.json
   # Run aggregator to generate monthly/yearly
   python3 /opt/power-monitor/aggregator.py /var/www/html
   ```

3. **Push to GitHub:**
   ```bash
   python3 /opt/power-monitor/github_sync.py /var/www/html push
   ```

## Benefits of New Architecture

1. **Reduced Local Storage**: Only 24h + 7d stored locally (~2-3 MB)
2. **Long-term History**: 30d/365d backed up to GitHub
3. **Faster Dashboard**: Smaller JSON files load faster
4. **Scalability**: Can extend to multi-year history
5. **Backup & Recovery**: GitHub acts as backup for long-term data
6. **Automatic Rotation**: No manual cleanup needed

## Future Enhancements

- [ ] Implement data compression for yearly.json
- [ ] Add S3/cloud storage option
- [ ] Implement incremental backups
- [ ] Add data export functionality
- [ ] Create restore from GitHub feature
