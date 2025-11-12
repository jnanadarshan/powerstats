# Health Tab - Debugging Guide

## Quick Diagnosis

If the Health tab doesn't show data, follow these steps:

### Step 1: Check Browser Console
1. Open dashboard: `http://your-device/`
2. Press **F12** (or right-click → Inspect)
3. Go to **Console** tab
4. Click **Health** tab
5. Look for error messages

Expected console output should show:
```
Fetching health data...
Health data received: {disk: {...}, memory: {...}, ...}
Updating Health UI with data: {...}
```

If you see errors, continue with steps below.

---

## Troubleshooting Checklist

### Issue 1: "health.cgi not found" or 404 error

**Cause:** health.cgi file doesn't exist or web server can't find it

**Fix:**
```bash
# Check if file exists
ls -la /var/www/html/health.cgi

# If missing, copy it
cp opt/power-monitor/../var/www/html/health.cgi /var/www/html/

# Make executable
chmod +x /var/www/html/health.cgi

# Verify
curl http://localhost/health.cgi | head -20
```

---

### Issue 2: "health.cgi" but no JSON response

**Cause:** CGI script running but not returning valid JSON

**Check the actual error:**
```bash
# Run health.cgi directly
python3 /var/www/html/health.cgi

# Should see JSON output, if you see Python errors, fix them
```

---

### Issue 3: JSON response shows errors

**Example response:**
```json
{
  "error": "No module named 'psutil'",
  "disk": {"error": "No module named 'psutil'"},
  ...
}
```

**Fix:** Install psutil
```bash
apk add py3-psutil
```

---

### Issue 4: "health.py not found" error

**Cause:** health.py doesn't exist

**Fix:**
```bash
# Check if file exists
ls -la /opt/power-monitor/health.py

# If missing, make sure it's in the repo:
# File should be at: opt/power-monitor/health.py

# Copy it manually if needed
cp opt/power-monitor/health.py /opt/power-monitor/
chmod +x /opt/power-monitor/health.py
```

---

## Manual Testing

### Test 1: Can Python access the health module?

```bash
cd /opt/power-monitor
python3 -c "from health import SystemHealth; print('OK')"
```

If it fails, you'll see the error.

---

### Test 2: Does health.py work?

```bash
python3 /opt/power-monitor/health.py /opt/power-monitor/config.json
```

Should output JSON like:
```json
{
  "timestamp": "...",
  "disk": {
    "percent": 33.3,
    "total_gb": 0.24,
    ...
  },
  ...
}
```

---

### Test 3: Can health.cgi be called?

```bash
# Method 1: Direct Python execution
python3 /var/www/html/health.cgi

# Method 2: Via curl (if web server running)
curl http://localhost/health.cgi

# Method 3: Check in browser
# Open: http://your-device/test_health.html
# Click "Test /health.cgi" button
```

---

## Common Errors & Solutions

### Error: "Cannot find config.json"

```python
FileNotFoundError: [Errno 2] No such file or directory: '/opt/power-monitor/config.json'
```

**Solution:**
```bash
# Check if config.json exists
ls -la /opt/power-monitor/config.json

# If missing, copy from example
cp /opt/power-monitor/config.example.json /opt/power-monitor/config.json

# Edit with your settings
vi /opt/power-monitor/config.json
```

---

### Error: "daily.json not found"

```
Unable to determine last_collection_ist
```

**Solution:**
```bash
# Run collector to create daily.json
python3 /opt/power-monitor/collector.py

# Verify file was created
ls -la /var/www/html/daily.json

# Check contents
cat /var/www/html/daily.json | python3 -m json.tool
```

---

### Error: "psutil module not found"

```python
ModuleNotFoundError: No module named 'psutil'
```

**Solution:**
```bash
# Install psutil
apk add py3-psutil

# Verify
python3 -c "import psutil; print(psutil.disk_usage('/'))"
```

---

## Browser Console Debugging

### Enable More Detailed Logging

Edit `dashboard.html` and find the `fetchHealthData()` function, add this:

```javascript
async function fetchHealthData() {
    try {
        console.log('🔍 Fetching health data from /health.cgi');
        const response = await fetch('health.cgi');
        console.log('📡 Response status:', response.status);
        console.log('📡 Response headers:', response.headers);
        
        const text = await response.text();
        console.log('📊 Raw response:', text);
        
        const data = JSON.parse(text);
        console.log('✅ Parsed JSON:', data);
        updateHealthUI(data);
    } catch (error) {
        console.error('❌ Error:', error);
        console.error('Stack:', error.stack);
        showHealthError();
    }
}
```

Then check Console tab for detailed output.

---

## Network Debugging

### Check if health.cgi is reachable

```bash
# Using curl
curl -v http://localhost/health.cgi 2>&1 | head -30

# Check response headers
curl -i http://localhost/health.cgi

# Check for Python errors in output
curl http://localhost/health.cgi 2>&1 | grep -i error
```

---

## Web Server Configuration

### Check if CGI is enabled in lighttpd

```bash
# Check lighttpd config
grep -i "cgi" /etc/lighttpd/lighttpd.conf

# Should contain something like:
# server.modules = ( "mod_cgi" )
# cgi.assign = ( ".cgi" => "/usr/bin/python3" )
```

### Restart web server

```bash
# Restart lighttpd
rc-service lighttpd restart

# Check if running
ps aux | grep lighttpd

# Check logs
tail -f /var/log/lighttpd/error.log
```

---

## Step-by-Step Debug

1. **Open browser console (F12)**
2. **Click Health tab**
3. **Check Console for messages**
4. **If error, copy full error message**
5. **Run in terminal:**
   ```bash
   python3 /opt/power-monitor/health.py /opt/power-monitor/config.json
   ```
6. **Check output or error**
7. **Fix issue based on error message**
8. **Reload browser**

---

## Health Check Script

Use the provided test script:

```bash
sh deployment/test_health.sh
```

This will check:
- ✓ Files exist
- ✓ Permissions
- ✓ Python modules
- ✓ Direct execution
- ✓ HTTP access

---

## Still Not Working?

### Collect Debug Info

```bash
echo "=== Files ===" 
ls -la /opt/power-monitor/health.py /var/www/html/health.cgi

echo "=== Direct Test ==="
python3 /opt/power-monitor/health.py /opt/power-monitor/config.json 2>&1 | head -50

echo "=== HTTP Test ==="
curl http://localhost/health.cgi 2>&1 | head -50

echo "=== CGI Config ==="
grep -i "cgi\|assign" /etc/lighttpd/lighttpd.conf

echo "=== Web Server Status ==="
ps aux | grep lighttpd
```

Share this output for further assistance.

---

## Quick Fixes

Try these in order:

```bash
# 1. Make files executable
chmod +x /opt/power-monitor/health.py
chmod +x /var/www/html/health.cgi

# 2. Install dependencies
apk add py3-psutil

# 3. Restart web server
rc-service lighttpd restart

# 4. Reload browser
# F5 or Ctrl+Shift+R for hard refresh

# 5. Run collector
python3 /opt/power-monitor/collector.py

# 6. Try test page
# Open: http://your-device/test_health.html
```

---

## Expected Output

When Health tab works correctly, you should see:

✅ **Disk Usage**: Percentage with progress bar  
✅ **Memory Usage**: Percentage with progress bar  
✅ **Last Collection (IST)**: Timestamp  
✅ **Next Collection In**: Countdown timer  
✅ **GitHub Status**: Configuration and last publish time  
✅ **Auto-refresh**: Data updates every 10 seconds  

---

## Contact Support

If still stuck, provide:
1. Error message from browser console (F12)
2. Output of: `python3 /opt/power-monitor/health.py /opt/power-monitor/config.json`
3. Output of: `curl http://localhost/health.cgi`
4. Output of: `ls -la /opt/power-monitor/health.py /var/www/html/health.cgi`
