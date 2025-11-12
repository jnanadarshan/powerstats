#!/bin/bash
# Test health monitoring system
# Run this on the Luckfox Pico after installation

echo "Testing Health Monitoring System"
echo "================================="
echo

# Test 1: Check if health.py exists and is executable
echo "1. Checking health.py..."
if [ -f "/opt/power-monitor/health.py" ]; then
    echo "   ✓ health.py found"
    if [ -x "/opt/power-monitor/health.py" ]; then
        echo "   ✓ health.py is executable"
    else
        echo "   ✗ health.py is not executable"
        echo "   Fix: chmod +x /opt/power-monitor/health.py"
    fi
else
    echo "   ✗ health.py not found"
fi
echo

# Test 2: Check if psutil is installed
echo "2. Checking psutil installation..."
if python3 -c "import psutil" 2>/dev/null; then
    echo "   ✓ psutil is installed"
else
    echo "   ✗ psutil not found"
    echo "   Fix: apk add py3-psutil"
fi
echo

# Test 3: Check if health.cgi exists
echo "3. Checking health.cgi..."
if [ -f "/var/www/html/health.cgi" ]; then
    echo "   ✓ health.cgi found"
    if [ -x "/var/www/html/health.cgi" ]; then
        echo "   ✓ health.cgi is executable"
    else
        echo "   ✗ health.cgi is not executable"
        echo "   Fix: chmod +x /var/www/html/health.cgi"
    fi
else
    echo "   ✗ health.cgi not found"
fi
echo

# Test 4: Run health.py directly
echo "4. Testing health.py output..."
if [ -f "/opt/power-monitor/health.py" ] && [ -f "/opt/power-monitor/config.json" ]; then
    python3 /opt/power-monitor/health.py /opt/power-monitor/config.json 2>&1 | head -20
    echo "   (showing first 20 lines)"
else
    echo "   ✗ Cannot test - missing files"
fi
echo

# Test 5: Test health.cgi via HTTP (if lighttpd is running)
echo "5. Testing health.cgi via HTTP..."
if pgrep lighttpd > /dev/null; then
    echo "   lighttpd is running"
    echo "   Fetching http://localhost/health.cgi ..."
    curl -s http://localhost/health.cgi | python3 -m json.tool 2>&1 | head -30
    echo "   (showing first 30 lines)"
else
    echo "   ✗ lighttpd is not running"
    echo "   Fix: rc-service lighttpd start"
fi
echo

# Test 6: Check config.json for health_check_interval
echo "6. Checking config.json..."
if [ -f "/opt/power-monitor/config.json" ]; then
    if grep -q "health_check_interval_seconds" /opt/power-monitor/config.json; then
        echo "   ✓ health_check_interval_seconds found in config"
        grep "health_check_interval_seconds" /opt/power-monitor/config.json
    else
        echo "   ⚠ health_check_interval_seconds not found (optional)"
    fi
else
    echo "   ✗ config.json not found"
fi
echo

echo "================================="
echo "Health System Test Complete"
echo
echo "To test in browser:"
echo "1. Open: http://$(hostname -i)/"
echo "2. Click the 'Health' tab"
echo "3. You should see disk/memory usage, collection status, and GitHub status"
echo "4. Data should refresh every 10 seconds"
