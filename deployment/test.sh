#!/bin/sh
# Test script to verify installation

set -e

echo "================================================"
echo "Power Monitoring System Test"
echo "================================================"
echo ""

# Check if config exists
if [ ! -f /opt/power-monitor/config.json ]; then
    echo "❌ Configuration file not found: /opt/power-monitor/config.json"
    echo "   Create it based on config.example.json"
    exit 1
fi
echo "✓ Configuration file found"

# Check Python dependencies
echo ""
echo "Checking Python dependencies..."
python3 -c "import requests; import jinja2" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✓ Python dependencies installed"
else
    echo "❌ Python dependencies missing"
    echo "   Run: pip3 install -r requirements.txt"
    exit 1
fi

# Test config loading
echo ""
echo "Testing configuration loading..."
python3 /opt/power-monitor/config_manager.py
if [ $? -eq 0 ]; then
    echo "✓ Configuration valid"
else
    echo "❌ Configuration invalid"
    exit 1
fi

# Check maintenance mode
echo ""
echo "Checking maintenance mode..."
if [ -f /etc/monitor.conf ]; then
    echo "✓ State file exists"
    cat /etc/monitor.conf
else
    echo "❌ State file missing: /etc/monitor.conf"
    exit 1
fi

# Check lighttpd
echo ""
echo "Checking web server..."
if rc-service lighttpd status > /dev/null 2>&1; then
    echo "✓ lighttpd is running"
else
    echo "⚠ lighttpd is not running"
    echo "   Start it with: rc-service lighttpd start"
fi

# Check cron job
echo ""
echo "Checking cron job..."
if crontab -l | grep -q "collector.py"; then
    echo "✓ Cron job configured"
    crontab -l | grep collector.py
else
    echo "❌ Cron job not found"
    exit 1
fi

# Check file permissions
echo ""
echo "Checking file permissions..."
if [ -x /opt/power-monitor/collector.py ]; then
    echo "✓ collector.py is executable"
else
    echo "❌ collector.py is not executable"
    exit 1
fi

if [ -x /opt/power-monitor/publisher.py ]; then
    echo "✓ publisher.py is executable"
else
    echo "❌ publisher.py is not executable"
    exit 1
fi

if [ -x /var/www/html/admin.cgi ]; then
    echo "✓ admin.cgi is executable"
else
    echo "❌ admin.cgi is not executable"
    exit 1
fi

echo ""
echo "================================================"
echo "Test Results"
echo "================================================"
echo "✓ All basic checks passed!"
echo ""
echo "To test the full system:"
echo "1. Run collector manually: python3 /opt/power-monitor/collector.py"
echo "2. Run publisher manually: python3 /opt/power-monitor/publisher.py"
echo "3. Check web interface: http://$(hostname -i)/"
echo "4. Check admin panel: http://$(hostname -i)/admin.cgi"
echo ""
