# Permission Fix Summary

## Issue
Permission denied error when collector tries to write to `/var/www/html/daily.json.tmp`:
```
PermissionError: [Errno 13] Permission denied: '/var/www/html/daily.json.tmp'
```

## Changes Made

### 1. Install Scripts (`install.sh` and `deployment/install.sh`)

**Added proper directory ownership and permissions:**
- Set `/var/www/html` ownership to `root:lighttpd` 
- Set directory permissions to `775` (rwxrwxr-x)
- This allows root (collector) to write and lighttpd (web server) to read

**Added JSON file permission fixes:**
- After initial collection, set JSON files to `root:lighttpd` ownership
- Set file permissions to `664` (rw-rw-r--)

### 2. Collector Script (`opt/power-monitor/collector.py`)

**Updated `_ensure_data_file()` method:**
- Added `os.chmod(self.data_file, 0o664)` after creating new files
- Ensures newly created files are readable by web server

**Updated `_write_data()` method:**
- Added `os.chmod(temp_file, 0o664)` before replacing files
- Ensures temporary files have correct permissions before atomic replacement

### 3. New Files

**`fix_permissions.sh`:**
- Quick fix script for existing installations
- Can be run without reinstalling
- Fixes all permission issues in one command

**`PERMISSION_FIX.md`:**
- Complete documentation of the issue and solutions
- Includes manual fix instructions
- Verification steps

## Why This Works

1. **Collector runs as root** (via cron) - needs write access to `/var/www/html`
2. **Web server runs as lighttpd** - needs read access to JSON files
3. **Solution**: 
   - Directory owned by `root:lighttpd` with `775` permissions
   - Files owned by `root:lighttpd` with `664` permissions
   - Both processes can access what they need

## For Users

### New Installations
Simply run the updated `install.sh` - all fixes are included.

### Existing Installations
Run the fix script:
```bash
sudo sh fix_permissions.sh
```

Or follow manual instructions in `PERMISSION_FIX.md`.

## Testing
After applying fix:
```bash
sudo python3 /opt/power-monitor/collector.py
ls -lh /var/www/html/*.json
```

Should see files owned by `root:lighttpd` with no permission errors.
