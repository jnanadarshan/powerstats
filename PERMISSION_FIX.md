# Permission Fix for Alpine Device

## Problem

When clicking "Sync to Github" on the admin panel or when the collector runs via cron, you may encounter this error:

```
PermissionError: [Errno 13] Permission denied: '/var/www/html/daily.json.tmp'
```

## Root Cause

The collector script runs as `root` (via cron), but the `/var/www/html` directory was owned by the `lighttpd:lighttpd` user/group with permissions that didn't allow root to write files.

## Solution

### Option 1: Quick Fix (For Existing Installations)

Run the permission fix script on your Alpine device:

```bash
cd /opt/power-monitor
wget https://raw.githubusercontent.com/jnanadarshan/powerstats/main/fix_permissions.sh
chmod +x fix_permissions.sh
sudo sh fix_permissions.sh
```

Or manually copy the `fix_permissions.sh` script from this repository and run it as root.

### Option 2: Manual Fix

If you can't run the script, manually fix permissions:

```bash
# Fix /var/www/html directory
sudo chown -R root:lighttpd /var/www/html
sudo chmod 775 /var/www/html

# Fix existing JSON files
sudo chown root:lighttpd /var/www/html/*.json
sudo chmod 664 /var/www/html/*.json

# Clean up any stuck temporary files
sudo rm -f /var/www/html/*.tmp

# Fix log files
sudo chown lighttpd:lighttpd /var/log/power-monitor-*.log
sudo chmod 644 /var/log/power-monitor-*.log

# Fix monitor.conf
sudo chown root:lighttpd /etc/monitor.conf
sudo chmod 664 /etc/monitor.conf
```

### Option 3: Reinstall (Recommended for Clean Setup)

If you're setting up a new device, the latest `install.sh` script includes these fixes. Simply:

```bash
git clone https://github.com/jnanadarshan/powerstats.git
cd powerstats
# Configure your config.json
sudo sh install.sh
```

## Verification

After applying the fix, test the collector:

```bash
sudo python3 /opt/power-monitor/collector.py
```

Check for successful data collection:

```bash
ls -lh /var/www/html/*.json
cat /var/log/power-monitor-collector.log | tail -20
```

You should see:
- JSON files owned by `root:lighttpd` with `664` permissions
- No permission errors in the log
- Successfully written data points

## What Changed

1. **Directory Permissions**: `/var/www/html` now has `775` permissions and is owned by `root:lighttpd`
   - Owner (root): read, write, execute
   - Group (lighttpd): read, write, execute
   - Others: read, execute

2. **File Permissions**: JSON files now have `664` permissions
   - Owner (root): read, write
   - Group (lighttpd): read, write
   - Others: read

3. **Collector Updates**: The collector now explicitly sets permissions on files it creates

This ensures:
- The collector (running as root) can create and write files
- The web server (running as lighttpd) can read the files
- Proper security boundaries are maintained
